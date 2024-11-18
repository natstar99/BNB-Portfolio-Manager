# File: views/historical_data_view.py

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                              QHeaderView, QComboBox, QHBoxLayout, QPushButton,
                              QLabel, QDateEdit, QMessageBox, QAbstractItemView)
from PySide6.QtCore import Qt, QDate
from datetime import datetime
import logging

logging.basicConfig(level=logging.DEBUG, filename='import_transactions.log', filemode='w',
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HistoricalDataDialog(QDialog):
    def __init__(self, stock, db_manager, parent=None):
        self.stock = stock
        self.db_manager = db_manager
        super().__init__(parent)
        
        # Get DRP status before initialising UI
        self.drp_enabled = self.get_drp_status()
        self.init_ui()
        self.load_data()

    def get_drp_status(self):
        """Get the DRP status for the current stock."""
        result = self.db_manager.fetch_one(
            "SELECT drp FROM stocks WHERE id = ?",
            (self.stock.id,)
        )
        return bool(result[0]) if result else False

    def init_ui(self):
        """Initialise the user interface components."""
        self.setWindowTitle(f"Historical Data - {self.stock.name} ({self.stock.yahoo_symbol})")
        self.setMinimumWidth(1200)
        self.setMinimumHeight(800)
        
        layout = QVBoxLayout(self)

        # Filter controls
        filter_layout = QHBoxLayout()
        
        # Date range filter
        filter_layout.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        filter_layout.addWidget(self.date_from)
        
        filter_layout.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        filter_layout.addWidget(self.date_to)

        # Event type filter
        filter_layout.addWidget(QLabel("Show:"))
        self.event_filter = QComboBox()
        self.event_filter.addItems(["All", "Prices Only", "Transactions Only", "Corporate Actions Only"])
        filter_layout.addWidget(self.event_filter)

        # Apply filters button
        self.apply_filter_btn = QPushButton("Apply Filters")
        self.apply_filter_btn.clicked.connect(self.apply_filters)
        filter_layout.addWidget(self.apply_filter_btn)

        # Reset filters button
        self.reset_filter_btn = QPushButton("Reset Filters")
        self.reset_filter_btn.clicked.connect(self.reset_filters)
        filter_layout.addWidget(self.reset_filter_btn)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Table
        self.table = QTableWidget()
        
        # Set up table columns based on DRP status
        columns = [
            "Date",
            "Open",
            "High",
            "Low",
            "Close",
            "Adjusted Close",
            "Volume",
            "Stock Split",
            "Dividend",
            "Transaction Type",
            "Quantity",
            "Price",
            "Total Quantity",
            "Market Value"
        ]
        
        if self.drp_enabled:
            # Insert DRP Shares column before Total Quantity
            columns.insert(-2, "DRP Shares")
            
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        
        # Enable sorting
        self.table.setSortingEnabled(True)
        
        # Set column resize modes
        header = self.table.horizontalHeader()
        for i in range(len(columns)):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers) # Make the table read-only
        
        layout.addWidget(self.table)

        # Close button
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn)

    def load_data(self):
        try:
            # Using the recursive CTE query
            data = self.db_manager.fetch_all("""
                WITH RECURSIVE running_totals AS (
                    SELECT 
                        hp.date,
                        hp.open_price,
                        hp.high_price,
                        hp.low_price,
                        hp.close_price,
                        hp.adjusted_close,
                        hp.volume,
                        ss.ratio as split_ratio,
                        hp.dividend,
                        t.transaction_type,
                        t.quantity as transaction_quantity,
                        t.price as transaction_price,
                        hp.stock_id,
                        COALESCE(
                            CASE 
                                WHEN t.transaction_type = 'BUY' THEN t.quantity 
                                WHEN t.transaction_type = 'SELL' THEN -t.quantity 
                                ELSE 0 
                            END
                        , 0) as base_quantity_change,
                        0 as drp_shares,
                        0 as total_quantity_owned,
                        ROW_NUMBER() OVER (ORDER BY hp.date) as row_num
                    FROM historical_prices hp
                    LEFT JOIN transactions t ON hp.stock_id = t.stock_id 
                        AND hp.date = date(t.date)
                    LEFT JOIN stock_splits ss ON hp.stock_id = ss.stock_id 
                        AND hp.date = date(ss.date)
                    LEFT JOIN stocks s ON hp.stock_id = s.id
                    WHERE hp.stock_id = ?
                ),
                compounded_totals AS (
                    -- Base case: first row
                    SELECT 
                        date,
                        open_price,
                        high_price,
                        low_price,
                        close_price,
                        adjusted_close,
                        volume,
                        split_ratio,
                        dividend,
                        transaction_type,
                        transaction_quantity,
                        transaction_price,
                        stock_id,
                        base_quantity_change,
                        0 as drp_shares,  -- Explicit column for first row
                        base_quantity_change as total_quantity_owned,
                        row_num
                    FROM running_totals 
                    WHERE row_num = 1

                    UNION ALL

                    -- Recursive case
                    SELECT 
                        r.date,
                        r.open_price,
                        r.high_price,
                        r.low_price,
                        r.close_price,
                        r.adjusted_close,
                        r.volume,
                        r.split_ratio,
                        r.dividend,
                        r.transaction_type,
                        r.transaction_quantity,
                        r.transaction_price,
                        r.stock_id,
                        r.base_quantity_change,
                        CASE
                            WHEN s.drp = 1 AND r.dividend > 0 THEN
                                ROUND(r.dividend * ct.total_quantity_owned / r.close_price, 4)
                            ELSE 0
                        END as drp_shares,
                        ct.total_quantity_owned + r.base_quantity_change + 
                        CASE
                            WHEN s.drp = 1 AND r.dividend > 0 THEN
                                ROUND(r.dividend * ct.total_quantity_owned / r.close_price, 4)
                            ELSE 0
                        END as total_quantity_owned,
                        r.row_num
                    FROM running_totals r
                    JOIN compounded_totals ct ON r.row_num = ct.row_num + 1
                    JOIN stocks s ON r.stock_id = s.id
                )

                SELECT 
                    date,
                    open_price,
                    high_price,
                    low_price,
                    close_price,
                    adjusted_close,
                    volume,
                    split_ratio,
                    dividend,
                    transaction_type,
                    transaction_quantity,
                    transaction_price,
                    total_quantity_owned,
                    ROUND(close_price * total_quantity_owned, 2) as market_value,
                    drp_shares
                FROM compounded_totals
                ORDER BY date DESC
            """, (self.stock.id,))

            self.populate_table(data)

        except Exception as e:
            logger.error(f"Error loading historical data: {str(e)}")
            QMessageBox.warning(
                self,
                "Error Loading Data",
                f"Failed to load historical data: {str(e)}"
            )

    def populate_table(self, data):
        """Refresh the table with current data."""
        self.table.setRowCount(len(data))
        
        for row, record in enumerate(data):
            col = 0  # Use running column counter for cleaner code
            
            # Date
            self.table.setItem(row, col, QTableWidgetItem(record[0]))
            col += 1
            
            # Price data (Open, High, Low, Close, Adjusted Close)
            for i in range(1, 6):
                value = record[i]
                if value is not None:
                    self.table.setItem(row, col, QTableWidgetItem(f"{value:.2f}"))
                else:
                    self.table.setItem(row, col, QTableWidgetItem(""))
                col += 1

            # Volume
            self.table.setItem(row, col, QTableWidgetItem(str(record[6]) if record[6] else ""))
            col += 1

            # Stock Split
            split_ratio = record[7]
            if split_ratio:
                split_item = QTableWidgetItem(f"{split_ratio}:1")
                split_item.setBackground(Qt.blue)
                self.table.setItem(row, col, split_item)
            else:
                self.table.setItem(row, col, QTableWidgetItem(""))
            col += 1

            # Dividend
            dividend_value = record[8]
            if dividend_value and dividend_value > 0:
                dividend_item = QTableWidgetItem(f"{dividend_value:.4f}")
                dividend_item.setBackground(Qt.green)
                self.table.setItem(row, col, dividend_item)
            else:
                self.table.setItem(row, col, QTableWidgetItem(""))
            col += 1

            # Transaction Type, Quantity, Price
            self.table.setItem(row, col, QTableWidgetItem(record[9] if record[9] else ""))
            col += 1
            self.table.setItem(row, col, QTableWidgetItem(str(record[10]) if record[10] else ""))
            col += 1
            self.table.setItem(row, col, QTableWidgetItem(f"{record[11]:.2f}" if record[11] else ""))
            col += 1

            # DRP Shares (only if DRP is enabled)
            if self.drp_enabled:
                drp_shares = record[14]  # index 14 is drp_shares
                if drp_shares and drp_shares > 0:
                    drp_item = QTableWidgetItem(f"+{drp_shares:.4f}")
                    drp_item.setBackground(Qt.green)
                    self.table.setItem(row, col, drp_item)
                else:
                    self.table.setItem(row, col, QTableWidgetItem(""))
                col += 1

            # Total Quantity
            total_qty = record[12]
            if total_qty is not None:
                total_qty_item = QTableWidgetItem(f"{total_qty:.4f}")
                self.table.setItem(row, col, total_qty_item)
            else:
                self.table.setItem(row, col, QTableWidgetItem(""))
            col += 1

            # Market Value
            market_value = record[13]
            if market_value is not None:
                market_value_item = QTableWidgetItem(f"${market_value:.2f}")
                self.table.setItem(row, col, market_value_item)
            else:
                self.table.setItem(row, col, QTableWidgetItem(""))

            # Color coding for transactions
            if record[9]:  # If there's a transaction
                for transaction_col in range(9, 12):  # Transaction columns
                    item = self.table.item(row, transaction_col)
                    if item:
                        item.setBackground(Qt.lightGray)

    def apply_filters(self):
        date_from = self.date_from.date().toString("yyyy-MM-dd")
        date_to = self.date_to.date().toString("yyyy-MM-dd")
        filter_type = self.event_filter.currentText()

        # Base CTE query with date filter
        query = """
        WITH RECURSIVE running_totals AS (
            SELECT 
                hp.date,
                hp.open_price,
                hp.high_price,
                hp.low_price,
                hp.close_price,
                hp.adjusted_close,
                hp.volume,
                ss.ratio as split_ratio,
                hp.dividend,
                t.transaction_type,
                t.quantity as transaction_quantity,
                t.price as transaction_price,
                COALESCE(
                    CASE 
                        WHEN t.transaction_type = 'BUY' THEN t.quantity 
                        WHEN t.transaction_type = 'SELL' THEN -t.quantity 
                        ELSE 0 
                    END
                , 0) as base_quantity_change,
                0 as drp_shares,
                0 as total_quantity_owned,
                ROW_NUMBER() OVER (ORDER BY hp.date) as row_num
            FROM historical_prices hp
            LEFT JOIN transactions t ON hp.stock_id = t.stock_id 
                AND hp.date = date(t.date)
            LEFT JOIN stock_splits ss ON hp.stock_id = ss.stock_id 
                AND hp.date = date(ss.date)
            LEFT JOIN stocks s ON hp.stock_id = s.id
            WHERE hp.stock_id = ?
            AND hp.date BETWEEN ? AND ?
        """

        # Add filter conditions
        if filter_type == "Transactions Only":
            query += " AND t.transaction_type IS NOT NULL"
        elif filter_type == "Corporate Actions Only":
            query += " AND (ss.ratio IS NOT NULL OR hp.dividend > 0)"

        # Complete the CTE query
        query += """
            ),
            compounded_totals AS (
                SELECT 
                    *,
                    base_quantity_change as total_quantity_owned
                FROM running_totals 
                WHERE row_num = 1

                UNION ALL

                SELECT 
                    r.*,
                    CASE
                        WHEN s.drp = 1 AND r.dividend > 0 THEN
                            ROUND(r.dividend * ct.total_quantity_owned / r.close_price, 4)
                        ELSE 0
                    END as drp_shares,
                    ct.total_quantity_owned + r.base_quantity_change + 
                    CASE
                        WHEN s.drp = 1 AND r.dividend > 0 THEN
                            ROUND(r.dividend * ct.total_quantity_owned / r.close_price, 4)
                        ELSE 0
                    END as total_quantity_owned
                FROM running_totals r
                JOIN compounded_totals ct ON r.row_num = ct.row_num + 1
                JOIN stocks s ON r.stock_id = s.id
            )

            SELECT 
                date,
                open_price,
                high_price,
                low_price,
                close_price,
                adjusted_close,
                volume,
                split_ratio,
                dividend,
                transaction_type,
                transaction_quantity,
                transaction_price,
                total_quantity_owned,
                ROUND(close_price * total_quantity_owned, 2) as market_value,
                drp_shares
            FROM compounded_totals
            ORDER BY date DESC
        """

        data = self.db_manager.fetch_all(query, (self.stock.id, date_from, date_to))
        self.populate_table(data)

    def reset_filters(self):
        self.event_filter.setCurrentText("All")
        self.load_data()