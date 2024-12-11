# File: views/historical_data_view.py

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QTableWidget, QTableWidgetItem, QHeaderView, 
                              QLabel, QDateEdit, QDialogButtonBox, QCheckBox,
                              QAbstractItemView, QComboBox, QMessageBox,
                              QDoubleSpinBox, QFormLayout)
from PySide6.QtCore import Qt, QDate
from datetime import datetime
import logging

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
        self.setMinimumHeight(700)
        
        layout = QVBoxLayout(self)

        # Add transaction management buttons
        transaction_layout = QHBoxLayout()
        
        self.add_transaction_btn = QPushButton("Add Transaction")
        self.add_transaction_btn.clicked.connect(self.add_transaction)
        transaction_layout.addWidget(self.add_transaction_btn)
        
        self.delete_transaction_btn = QPushButton("Delete Selected Transaction")
        self.delete_transaction_btn.clicked.connect(self.delete_transaction)
        self.delete_transaction_btn.setEnabled(False)  # Initially disabled
        transaction_layout.addWidget(self.delete_transaction_btn)
        
        # Add update historical data button
        self.update_historical_btn = QPushButton("Update Historical Data")
        self.update_historical_btn.clicked.connect(self.update_historical_data)
        transaction_layout.addWidget(self.update_historical_btn)
        
        transaction_layout.addStretch()
        layout.addLayout(transaction_layout)

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
        self.event_filter.addItems(["All", "Prices Only", "Transactions Only", "Dividends Only"])
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
        
        # Set up all columns
        self.columns = [
            "Date",
            "Open",
            "High",
            "Low",
            "Close",
            "Adjusted Close",
            "Volume",
            "Stock Split",
            "Dividend",
            "Cash Dividend",
            "DRP Shares",
            "Transaction Type",
            "Quantity",
            "Price",
            "Total Shares",
            "Market Value"
        ]
        
        self.table.setColumnCount(len(self.columns))
        self.table.setHorizontalHeaderLabels(self.columns)
        
        # Enable sorting
        self.table.setSortingEnabled(True)
        
        # Set column resize modes
        header = self.table.horizontalHeader()
        for i in range(len(self.columns)):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        # Add table to layout
        layout.addWidget(self.table)

        # Close button
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn)

        # Set the layout
        self.setLayout(layout)

        # Connect table selection signal
        self.table.itemSelectionChanged.connect(self.update_button_states)

    def load_data(self):
            try:
                # Using the recursive CTE query with updated column names
                data = self.db_manager.fetch_all("""
                    WITH RECURSIVE running_totals AS (
                        SELECT 
                            COALESCE(hp.date, date(t.date)) as date,
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
                            COALESCE(hp.stock_id, t.stock_id) as stock_id,
                            COALESCE(
                                CASE 
                                    WHEN t.transaction_type = 'BUY' THEN t.quantity 
                                    WHEN t.transaction_type = 'SELL' THEN -t.quantity 
                                    ELSE 0 
                                END
                            , 0) as base_quantity_change,
                            0 as drp_shares,
                            0 as total_shares,
                            ROW_NUMBER() OVER (ORDER BY COALESCE(hp.date, date(t.date))) as row_num
                        FROM (
                            SELECT DISTINCT date FROM historical_prices WHERE stock_id = ?
                            UNION
                            SELECT DISTINCT date(date) FROM transactions WHERE stock_id = ?
                        ) dates
                        LEFT JOIN historical_prices hp ON dates.date = hp.date AND hp.stock_id = ?
                        LEFT JOIN transactions t ON dates.date = date(t.date) AND t.stock_id = ?
                        LEFT JOIN stock_splits ss ON dates.date = date(ss.date) AND ss.stock_id = ?
                        LEFT JOIN stocks s ON hp.stock_id = s.id OR t.stock_id = s.id
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
                            0 as drp_shares,
                            base_quantity_change as total_shares,
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
                                    ROUND(r.dividend * ct.total_shares / COALESCE(r.close_price, r.transaction_price), 4)
                                ELSE 0
                            END as drp_shares,
                            -- Apply split adjustments to the running total
                            CASE
                                WHEN r.split_ratio IS NOT NULL THEN
                                    -- When a split occurs, multiply existing shares by the split ratio
                                    (ct.total_shares * r.split_ratio) + r.base_quantity_change +
                                    CASE
                                        WHEN s.drp = 1 AND r.dividend > 0 THEN
                                            ROUND(r.dividend * ct.total_shares * r.split_ratio / COALESCE(r.close_price, r.transaction_price), 4)
                                        ELSE 0
                                    END
                                ELSE
                                    -- No split, just add new quantities
                                    ct.total_shares + r.base_quantity_change +
                                    CASE
                                        WHEN s.drp = 1 AND r.dividend > 0 THEN
                                            ROUND(r.dividend * ct.total_shares / COALESCE(r.close_price, r.transaction_price), 4)
                                        ELSE 0
                                    END
                            END as total_shares,
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
                        CASE
                            WHEN s.drp = 0 AND dividend > 0 
                            THEN dividend * total_shares
                            ELSE 0
                        END as cash_dividend,
                        CASE
                            WHEN s.drp = 1 AND dividend > 0
                            THEN drp_shares
                            ELSE 0
                        END as drp_shares,
                        transaction_type,
                        transaction_quantity,
                        transaction_price,
                        ROUND(total_shares, 4) as total_shares,
                        ROUND(COALESCE(close_price, transaction_price) * total_shares, 2) as market_value
                    FROM compounded_totals
                    JOIN stocks s ON s.id = ?
                    ORDER BY date DESC
                """, (self.stock.id, self.stock.id, self.stock.id, self.stock.id, self.stock.id, self.stock.id))

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
            
            # Dictionary to track which columns should be visible
            columns_with_data = {col: False for col in range(len(self.columns))}
            columns_with_data[0] = True  # Date column always visible
            columns_with_data[14] = True  # Total Shares always visible
            columns_with_data[15] = True  # Market Value always visible
            
            for row, record in enumerate(data):
                # Date (always shown)
                self.table.setItem(row, 0, QTableWidgetItem(record[0]))
                
                # Price data (Open through Volume)
                for col in range(1, 7):
                    value = record[col]
                    self.table.setItem(row, col, QTableWidgetItem(""))
                    if value is not None:
                        self.table.item(row, col).setText(f"{value:,.2f}")
                        columns_with_data[col] = True

                # Stock Split
                split_ratio = record[7]
                self.table.setItem(row, 7, QTableWidgetItem(""))
                if split_ratio:
                    split_item = QTableWidgetItem(f"{split_ratio}:1")
                    split_item.setBackground(Qt.blue)
                    split_item.setForeground(Qt.white)
                    self.table.setItem(row, 7, split_item)
                    columns_with_data[7] = True

                # Dividend
                dividend = record[8]
                self.table.setItem(row, 8, QTableWidgetItem(""))
                if dividend and dividend > 0:
                    dividend_item = QTableWidgetItem(f"${dividend:,.4f}")
                    dividend_item.setForeground(Qt.darkGreen)
                    self.table.setItem(row, 8, dividend_item)
                    columns_with_data[8] = True

                # Cash Dividend
                cash_dividend = record[9]
                self.table.setItem(row, 9, QTableWidgetItem(""))
                if cash_dividend and cash_dividend > 0:
                    cash_item = QTableWidgetItem(f"${cash_dividend:,.2f}")
                    cash_item.setForeground(Qt.darkGreen)
                    self.table.setItem(row, 9, cash_item)
                    columns_with_data[9] = True

                # DRP Shares
                drp_shares = record[10]
                self.table.setItem(row, 10, QTableWidgetItem(""))
                if drp_shares and drp_shares > 0:
                    drp_item = QTableWidgetItem(f"+{drp_shares:,.4f}")
                    drp_item.setForeground(Qt.blue)
                    self.table.setItem(row, 10, drp_item)
                    columns_with_data[10] = True

                # Transaction Type, Quantity, Price
                for col in range(11, 14):
                    value = record[col]
                    self.table.setItem(row, col, QTableWidgetItem(""))
                    if value:
                        if col == 13:  # Price column
                            self.table.item(row, col).setText(f"${value:,.2f}")
                        else:
                            self.table.item(row, col).setText(str(value))
                        self.table.item(row, col).setBackground(Qt.lightGray)
                        columns_with_data[col] = True

                # Total Shares
                total_shares = record[14]
                self.table.setItem(row, 14, QTableWidgetItem(""))
                if total_shares is not None:
                    self.table.item(row, 14).setText(f"{total_shares:,.4f}")

                # Market Value
                market_value = record[15]
                self.table.setItem(row, 15, QTableWidgetItem(""))
                if market_value is not None:
                    self.table.item(row, 15).setText(f"${market_value:,.2f}")

            # Hide empty columns
            for col in range(len(self.columns)):
                self.table.setColumnHidden(col, not columns_with_data[col])

            # Auto-resize visible columns
            self.table.resizeColumnsToContents()

    def apply_filters(self):
        """Apply date and type filters to the data."""
        date_from = self.date_from.date().toString("yyyy-MM-dd")
        date_to = self.date_to.date().toString("yyyy-MM-dd")
        filter_type = self.event_filter.currentText()

        # Use the same query structure as load_data, but with date filters
        query = """
            WITH RECURSIVE daily_data AS (
                SELECT 
                    d.date,
                    t.transaction_type,
                    t.quantity as transaction_quantity,
                    t.price as transaction_price,
                    SUM(COALESCE(
                        CASE 
                            WHEN t.transaction_type = 'BUY' THEN t.quantity 
                            WHEN t.transaction_type = 'SELL' THEN -t.quantity 
                            ELSE 0 
                        END
                    , 0)) OVER (ORDER BY d.date) as running_shares
                FROM (
                    SELECT DISTINCT date FROM historical_prices 
                    WHERE stock_id = ? AND date BETWEEN ? AND ?
                    UNION
                    SELECT DISTINCT date(date) FROM transactions 
                    WHERE stock_id = ? AND date BETWEEN ? AND ?
                ) d
                LEFT JOIN transactions t ON date(t.date) = d.date AND t.stock_id = ?
            ),
            full_data AS (
                SELECT 
                    dd.date,
                    hp.open_price,
                    hp.high_price,
                    hp.low_price,
                    hp.close_price,
                    hp.adjusted_close,
                    hp.volume,
                    ss.ratio as split_ratio,
                    hp.dividend,
                    CASE
                        WHEN s.drp = 0 THEN hp.dividend * dd.running_shares
                        ELSE 0
                    END as cash_dividend,
                    CASE
                        WHEN s.drp = 1 AND hp.dividend > 0 AND hp.close_price > 0
                        THEN (hp.dividend * dd.running_shares) / hp.close_price
                        ELSE 0
                    END as drp_shares,
                    dd.transaction_type,
                    dd.transaction_quantity,
                    dd.transaction_price,
                    dd.running_shares as total_shares,
                    COALESCE(hp.close_price, dd.transaction_price) * dd.running_shares as market_value
                FROM daily_data dd
                LEFT JOIN historical_prices hp ON dd.date = hp.date AND hp.stock_id = ?
                LEFT JOIN stock_splits ss ON dd.date = date(ss.date) AND ss.stock_id = ?
                JOIN stocks s ON s.id = ?
                WHERE 1=1
        """

        # Add filter conditions
        if filter_type == "Transactions Only":
            query += " AND dd.transaction_type IS NOT NULL"
        elif filter_type == "Prices Only":
            query += " AND dd.transaction_type IS NULL"
        elif filter_type == "Dividends Only":
            query += " AND (hp.dividend > 0)"

        query += """
            )
            SELECT * FROM full_data
            ORDER BY date DESC
        """

        # Update parameters to include date range
        data = self.db_manager.fetch_all(query, (
            self.stock.id, date_from, date_to,  # For first date filter
            self.stock.id, date_from, date_to,  # For second date filter
            self.stock.id,                      # For transactions join
            self.stock.id, self.stock.id, self.stock.id  # For final joins
        ))
        
        self.populate_table(data)

    def reset_filters(self):
        self.event_filter.setCurrentText("All")
        self.load_data()

    def update_button_states(self):
        """Enable/disable buttons based on selection state."""
        selected_items = self.table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            # Only enable delete button if a transaction is selected
            has_transaction = bool(self.table.item(row, 11).text()) # Check Transaction Type column
            self.delete_transaction_btn.setEnabled(has_transaction)
        else:
            self.delete_transaction_btn.setEnabled(False)

    def add_transaction(self):
        """Show dialog to add a new transaction."""
        dialog = AddTransactionDialog(self)
        if dialog.exec_():
            try:
                date, trans_type, quantity, price = dialog.get_transaction_data()
                
                # For SELL orders, verify sufficient shares are available
                if trans_type == "SELL":
                    # Get total shares owned as of the selected date
                    shares_owned = self.db_manager.fetch_one("""
                        SELECT SUM(CASE 
                            WHEN transaction_type = 'BUY' THEN quantity
                            WHEN transaction_type = 'SELL' THEN -quantity
                        END)
                        FROM transactions
                        WHERE stock_id = ?
                        AND date <= ?
                    """, (self.stock.id, date))
                    
                    total_shares = shares_owned[0] if shares_owned[0] else 0
                    
                    if quantity > total_shares:
                        QMessageBox.warning(
                            self,
                            "Invalid Transaction",
                            f"Cannot sell {quantity} shares. Only {total_shares:.4f} shares owned on {date}."
                        )
                        return
                
                # Format the transaction data the same way as the import controller
                transaction = [
                    (self.stock.id, date, quantity, price, 
                    trans_type, quantity, price)  # original_quantity and original_price same as inputs
                ]
                
                # Use the same bulk insert method as the import controller
                self.db_manager.bulk_insert_transactions(transaction)
                
                # Refresh the view to show new transaction
                self.load_data()
                
                QMessageBox.information(
                    self,
                    "Success",
                    "Transaction added successfully."
                )
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to add transaction: {str(e)}"
                )
                
    def delete_transaction(self):
        """Delete the selected transaction."""
        selected_items = self.table.selectedItems()
        if not selected_items:
            return
            
        row = selected_items[0].row()
        date = self.table.item(row, 0).text()
        trans_type = self.table.item(row, 11).text()  # Updated column index
        quantity = self.table.item(row, 12).text()    # Updated column index
        price = self.table.item(row, 13).text()       # Updated column index
        
        if not trans_type:  # Not a transaction row
            return
            
        confirm = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete this transaction?\n\n"
            f"Date: {date}\n"
            f"Type: {trans_type}\n"
            f"Quantity: {quantity}\n"
            f"Price: {price}",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            try:
                # Delete transaction from database
                self.db_manager.execute("""
                    DELETE FROM transactions 
                    WHERE stock_id = ? 
                    AND date = ? 
                    AND transaction_type = ?
                    AND quantity = ?
                    AND price = ?
                """, (
                    self.stock.id,
                    date,
                    trans_type,
                    float(quantity),
                    float(price.replace('$', ''))
                ))
                
                self.db_manager.conn.commit()
                
                # Refresh the view
                self.load_data()
                
                QMessageBox.information(
                    self,
                    "Success",
                    "Transaction deleted successfully."
                )
                
            except Exception as e:
                self.db_manager.conn.rollback()
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to delete transaction: {str(e)}"
                )

    def update_historical_data(self):
        """Update historical price data for the stock."""
        try:
            from utils.historical_data_collector import HistoricalDataCollector
            
            # Use the collector directly
            collector = HistoricalDataCollector(self.db_manager)
            if collector.collect_historical_data(
                self.stock.id, 
                self.stock.yahoo_symbol, 
                force_refresh=True,
                parent_widget=self
            ):
                # Refresh the view
                self.load_data()
                
                QMessageBox.information(
                    self,
                    "Success",
                    "Historical data updated successfully."
                )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to update historical data: {str(e)}"
            )

class AddTransactionDialog(QDialog):
    """
    Dialog for adding a new transaction to a stock.
    Allows users to specify transaction date, type, quantity and price.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialise the user interface components."""
        self.setWindowTitle("Add Transaction")
        layout = QFormLayout(self)

        # Date input
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(datetime.now().date())
        layout.addRow("Date:", self.date_edit)

        # Transaction type
        self.type_combo = QComboBox()
        self.type_combo.addItems(["BUY", "SELL"])
        layout.addRow("Type:", self.type_combo)

        # Quantity input
        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0.0001, 1000000)
        self.quantity_spin.setDecimals(4)
        self.quantity_spin.setValue(1)
        layout.addRow("Quantity:", self.quantity_spin)

        # Price input
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0.01, 1000000)
        self.price_spin.setDecimals(2)
        self.price_spin.setPrefix("$")
        self.price_spin.setValue(1.00)
        layout.addRow("Price:", self.price_spin)

        # Dialog buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addRow(self.button_box)

    def get_transaction_data(self):
        """Return the transaction data as a tuple."""
        return (
            self.date_edit.date().toPython(),
            self.type_combo.currentText(),
            self.quantity_spin.value(),
            self.price_spin.value()
        )
