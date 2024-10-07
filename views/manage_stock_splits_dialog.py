# File: views/manage_stock_splits_dialog.py

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QTableWidget, QTableWidgetItem, QHeaderView,
                               QLabel, QDateEdit, QDoubleSpinBox, QMessageBox)
from PySide6.QtCore import Qt
from datetime import datetime

class ManageStockSplitsDialog(QDialog):
    def __init__(self, db_manager, instrument_code, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.instrument_code = instrument_code
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Manage Stock Splits - {self.instrument_code}")
        layout = QVBoxLayout()

        # Table for existing splits
        self.splits_table = QTableWidget()
        self.splits_table.setColumnCount(3)  # Date, Ratio, Delete button
        self.splits_table.setHorizontalHeaderLabels(["Date", "Ratio", ""])
        self.splits_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.splits_table)

        # Add new split section
        add_split_layout = QHBoxLayout()
        add_split_layout.addWidget(QLabel("Date:"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(datetime.now().date())
        add_split_layout.addWidget(self.date_edit)

        add_split_layout.addWidget(QLabel("Ratio:"))
        self.ratio_spin = QDoubleSpinBox()
        self.ratio_spin.setRange(0.01, 100)
        self.ratio_spin.setValue(2)
        self.ratio_spin.setDecimals(2)
        add_split_layout.addWidget(self.ratio_spin)

        self.add_button = QPushButton("Add Split")
        self.add_button.clicked.connect(self.add_split)
        add_split_layout.addWidget(self.add_button)

        layout.addLayout(add_split_layout)

        # Close button
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        layout.addWidget(self.close_button)

        self.setLayout(layout)

        self.load_splits()

    def load_splits(self):
        stock = self.db_manager.get_stock(self.instrument_code)
        splits = self.db_manager.get_stock_splits(stock['id'])
        self.splits_table.setRowCount(len(splits))
        for row, split in enumerate(splits):
            self.splits_table.setItem(row, 0, QTableWidgetItem(split['date']))
            self.splits_table.setItem(row, 1, QTableWidgetItem(str(split['ratio'])))
            delete_button = QPushButton("Delete")
            delete_button.clicked.connect(lambda _, r=row: self.delete_split(r))
            self.splits_table.setCellWidget(row, 2, delete_button)

    def add_split(self):
        date = self.date_edit.date().toString("yyyy-MM-dd")
        ratio = self.ratio_spin.value()
        stock = self.db_manager.get_stock(self.instrument_code)
        self.db_manager.add_stock_split(stock['id'], date, ratio)
        self.load_splits()

    def delete_split(self, row):
        date = self.splits_table.item(row, 0).text()
        confirm = QMessageBox.question(self, "Confirm Deletion",
                                       f"Are you sure you want to delete the stock split on {date}?",
                                       QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            stock = self.db_manager.get_stock(self.instrument_code)
            self.db_manager.remove_stock_split(stock['id'], date)
            self.load_splits()