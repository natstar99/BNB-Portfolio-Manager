# File: views/historical_data_view.py

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                              QHeaderView, QComboBox, QHBoxLayout, QPushButton,
                              QLabel, QDateEdit)
from PySide6.QtCore import Qt, QDate
from datetime import datetime

class HistoricalDataDialog(QDialog):
    def __init__(self, stock, db_manager, parent=None):
        super().__init__(parent)
        self.stock = stock
        self.db_manager = db_manager
        self.init_ui()
        self.load_data()

    def init_ui(self):
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
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "Date",
            "Open",
            "High",
            "Low",
            "Close",
            "Adjusted Close",
            "Volume",
            "Transaction Type",
            "Quantity",
            "Stock Split",
            "Dividend"
        ])
        
        # Enable sorting
        self.table.setSortingEnabled(True)
        
        # Set column resize modes
        header = self.table.horizontalHeader()
        for i in range(11):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        layout.addWidget(self.table)

        # Close button
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn)

    def load_data(self):
        # Get the earliest date from historical prices
        earliest_date = self.db_manager.fetch_one("""
            SELECT MIN(date) FROM historical_prices WHERE stock_id = ?
        """, (self.stock.id,))[0]
        
        if earliest_date:
            self.date_from.setDate(QDate.fromString(earliest_date, "yyyy-MM-dd"))

        # Fetch all relevant data
        data = self.db_manager.fetch_all("""
            SELECT 
                hp.date,
                hp.open_price,
                hp.high_price,
                hp.low_price,
                hp.close_price,
                hp.adjusted_close,
                hp.volume,
                t.transaction_type,
                t.quantity,
                ss.ratio as split_ratio,
                0.0 as dividend  -- Placeholder for future dividend implementation
            FROM historical_prices hp
            LEFT JOIN transactions t ON hp.stock_id = t.stock_id 
                AND hp.date = date(t.date)
            LEFT JOIN stock_splits ss ON hp.stock_id = ss.stock_id 
                AND hp.date = date(ss.date)
            WHERE hp.stock_id = ?
            ORDER BY hp.date DESC
        """, (self.stock.id,))

        self.populate_table(data)

    def populate_table(self, data):
        self.table.setRowCount(len(data))
        for row, record in enumerate(data):
            # Date
            self.table.setItem(row, 0, QTableWidgetItem(record[0]))
            
            # Price data (with 2 decimal formatting)
            for col in range(1, 6):
                value = record[col]
                if value is not None:
                    self.table.setItem(row, col, QTableWidgetItem(f"{value:.2f}"))
                else:
                    self.table.setItem(row, col, QTableWidgetItem(""))

            # Volume
            self.table.setItem(row, 6, QTableWidgetItem(str(record[6]) if record[6] else ""))

            # Transaction Type
            self.table.setItem(row, 7, QTableWidgetItem(record[7] if record[7] else ""))

            # Quantity
            self.table.setItem(row, 8, QTableWidgetItem(str(record[8]) if record[8] else ""))

            # Stock Split
            self.table.setItem(row, 9, QTableWidgetItem(f"{record[9]}:1" if record[9] else ""))

            # Dividend
            self.table.setItem(row, 10, QTableWidgetItem(f"{record[10]:.4f}" if record[10] else ""))

            # Color code rows with events
            if any(record[7:]):  # If there's any transaction, split, or dividend
                for col in range(11):
                    item = self.table.item(row, col)
                    item.setBackground(Qt.lightGray)

    def apply_filters(self):
        date_from = self.date_from.date().toString("yyyy-MM-dd")
        date_to = self.date_to.date().toString("yyyy-MM-dd")
        filter_type = self.event_filter.currentText()

        # Build query based on filters
        query = """
            SELECT 
                hp.date,
                hp.open_price,
                hp.high_price,
                hp.low_price,
                hp.close_price,
                hp.adjusted_close,
                hp.volume,
                t.transaction_type,
                t.quantity,
                ss.ratio as split_ratio,
                0.0 as dividend
            FROM historical_prices hp
            LEFT JOIN transactions t ON hp.stock_id = t.stock_id 
                AND hp.date = date(t.date)
            LEFT JOIN stock_splits ss ON hp.stock_id = ss.stock_id 
                AND hp.date = date(ss.date)
            WHERE hp.stock_id = ?
                AND hp.date BETWEEN ? AND ?
        """

        if filter_type == "Transactions Only":
            query += " AND t.transaction_type IS NOT NULL"
        elif filter_type == "Corporate Actions Only":
            query += " AND (ss.ratio IS NOT NULL OR dividend > 0)"

        query += " ORDER BY hp.date DESC"

        data = self.db_manager.fetch_all(query, (self.stock.id, date_from, date_to))
        self.populate_table(data)

    def reset_filters(self):
        self.event_filter.setCurrentText("All")
        self.load_data()