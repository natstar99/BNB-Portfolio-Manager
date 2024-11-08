# File: views/verify_transactions_view.py

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QComboBox, QMessageBox, QLabel)
from PySide6.QtCore import Qt, Signal

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QComboBox, QMessageBox, QLabel, QProgressDialog,
                              QDateEdit, QDoubleSpinBox, QMenu, QDialogButtonBox)
from PySide6.QtCore import Qt, Signal
from datetime import datetime
import yfinance as yf
import concurrent.futures

class VerifyTransactionsDialog(QDialog):
    verification_completed = Signal(dict)  # Emits final verification results

    def __init__(self, transactions_data, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.transactions_data = transactions_data
        self.market_mappings = {}
        self.stock_data = {}
        self.verification_status = {}
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Verify Imported Transactions")
        self.setMinimumWidth(1000)
        self.setMinimumHeight(600)
        
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel(
            "Please verify the imported stocks. You can:\n"
            "• Assign market codes to each instrument\n"
            "• Verify stock information with Yahoo Finance\n"
            "• Manage stock splits\n"
            "• Re-verify stocks after making changes"
        )
        layout.addWidget(instructions)
        
        # Main table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Instrument Code",
            "Market",
            "Yahoo Symbol",
            "Stock Name",
            "Latest Price",
            "Splits",
            "Status",
            "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.table)
        
        # Buttons bar
        button_layout = QHBoxLayout()
        
        # Left side buttons
        self.verify_all_btn = QPushButton("Verify All with Yahoo")
        self.verify_all_btn.clicked.connect(self.verify_all_stocks)
        button_layout.addWidget(self.verify_all_btn)
        
        button_layout.addStretch()
        
        # Right side buttons
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Cancel | QDialogButtonBox.Ok,
            parent=self
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        button_layout.addWidget(self.buttons)
        
        layout.addLayout(button_layout)
        
        # Initialize table data
        self.populate_table()

    def populate_table(self):
        # Get unique instrument codes from transactions
        print(type(self.transactions_data))  # Add this at start of populate_table
        print(self.transactions_data.head()) # If it is a DataFrame
        instrument_codes = self.transactions_data['Instrument Code'].unique()
        self.table.setRowCount(len(instrument_codes))
        
        market_codes = self.db_manager.get_all_market_codes()
        
        for row, instrument_code in enumerate(instrument_codes):
            # Instrument Code
            self.table.setItem(row, 0, QTableWidgetItem(instrument_code))
            
            # Market Combo Box
            market_combo = QComboBox()
            market_combo.addItem("")  # Empty option
            for market_or_index, suffix in market_codes:
                market_combo.addItem(market_or_index, suffix)
            market_combo.currentIndexChanged.connect(
                lambda idx, r=row: self.on_market_changed(r)
            )
            self.table.setCellWidget(row, 1, market_combo)
            
            # Set existing market if available
            existing_stock = self.db_manager.get_stock(instrument_code)
            if existing_stock and existing_stock[6]:  # market_suffix
                market_suffix = existing_stock[6]
                index = market_combo.findData(market_suffix)
                if index >= 0:
                    market_combo.setCurrentIndex(index)
            
            # Yahoo Symbol (will be updated when market is selected)
            self.table.setItem(row, 2, QTableWidgetItem(""))
            
            # Stock Name (will be populated from Yahoo)
            self.table.setItem(row, 3, QTableWidgetItem(""))
            
            # Latest Price
            self.table.setItem(row, 4, QTableWidgetItem(""))
            
            # Splits (button will be added when data is available)
            self.table.setItem(row, 5, QTableWidgetItem(""))
            
            # Status
            status_item = QTableWidgetItem("Pending")
            status_item.setForeground(Qt.gray)
            self.table.setItem(row, 6, status_item)
            
            # Actions Button
            actions_btn = QPushButton("Actions ▼")
            actions_btn.clicked.connect(lambda _, r=row: self.show_actions_menu(r))
            self.table.setCellWidget(row, 7, actions_btn)

    def on_market_changed(self, row):
        instrument_code = self.table.item(row, 0).text()
        market_combo = self.table.cellWidget(row, 1)
        market_suffix = market_combo.currentData()
        
        # Update Yahoo Symbol
        yahoo_symbol = f"{instrument_code}{market_suffix}" if market_suffix else instrument_code
        self.table.item(row, 2).setText(yahoo_symbol)
        
        # Reset verification status
        self.update_status(row, "Pending", Qt.gray)
        
        # Store mapping
        self.market_mappings[instrument_code] = market_suffix

    def verify_all_stocks(self):
        progress = QProgressDialog("Verifying stocks with Yahoo Finance...", "Cancel", 0, self.table.rowCount(), self)
        progress.setWindowModality(Qt.WindowModal)
        
        for row in range(self.table.rowCount()):
            if progress.wasCanceled():
                break
                
            self.verify_stock(row)
            progress.setValue(row + 1)
        
        progress.close()

    def verify_stock(self, row):
        instrument_code = self.table.item(row, 0).text()
        yahoo_symbol = self.table.item(row, 2).text()
        
        if not yahoo_symbol:
            self.update_status(row, "No Symbol", Qt.red)
            return
        
        try:
            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info
            
            # Update stock name
            name = info.get('longName', 'N/A')
            self.table.item(row, 3).setText(name)
            
            # Update latest price
            price = info.get('currentPrice', 'N/A')
            self.table.item(row, 4).setText(str(price))
            
            # Get splits
            splits = ticker.splits
            if not splits.empty:
                splits_text = [f"{date.strftime('%Y-%m-%d')}: {ratio}" 
                             for date, ratio in splits.items()]
                self.table.item(row, 5).setText(", ".join(splits_text))
                
                # Store splits for later
                self.stock_data[instrument_code] = {
                    'splits': splits,
                    'name': name,
                    'price': price
                }
            
            self.update_status(row, "Verified", Qt.green)
            
        except Exception as e:
            self.update_status(row, "Failed", Qt.red)
            print(f"Error verifying {yahoo_symbol}: {str(e)}")

    def update_status(self, row, status, color):
        status_item = self.table.item(row, 6)
        status_item.setText(status)
        status_item.setForeground(color)
        self.verification_status[row] = status

    def show_actions_menu(self, row):
        menu = QMenu(self)
        
        verify_action = menu.addAction("Verify with Yahoo")
        verify_action.triggered.connect(lambda: self.verify_stock(row))
        
        manage_splits_action = menu.addAction("Manage Splits")
        manage_splits_action.triggered.connect(lambda: self.manage_splits(row))
        
        # Show menu at button
        button = self.table.cellWidget(row, 7)
        menu.exec_(button.mapToGlobal(button.rect().bottomLeft()))

    def manage_splits(self, row):
        instrument_code = self.table.item(row, 0).text()
        dialog = StockSplitsDialog(
            self.db_manager,
            instrument_code,
            initial_splits=self.stock_data.get(instrument_code, {}).get('splits', []),
            parent=self
        )
        if dialog.exec_():
            # Update splits display in table
            splits = dialog.get_splits()
            splits_text = [f"{date}: {ratio}" for date, ratio in splits]
            self.table.item(row, 5).setText(", ".join(splits_text))

    def show_context_menu(self, position):
        menu = QMenu(self)
        row = self.table.rowAt(position.y())
        
        if row >= 0:
            verify_action = menu.addAction("Verify with Yahoo")
            verify_action.triggered.connect(lambda: self.verify_stock(row))
            
            manage_splits_action = menu.addAction("Manage Splits")
            manage_splits_action.triggered.connect(lambda: self.manage_splits(row))
            
            menu.exec_(self.table.viewport().mapToGlobal(position))

    def accept(self):
        # Check if all stocks have been verified
        unverified = [row for row, status in self.verification_status.items() 
                     if status != "Verified"]
        
        if unverified:
            response = QMessageBox.question(
                self,
                "Unverified Stocks",
                "Some stocks haven't been verified. Continue anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if response == QMessageBox.No:
                return
        
        # Emit verification results
        results = {
            'market_mappings': self.market_mappings,
            'stock_data': self.stock_data,
            'verification_status': self.verification_status,
            'transactions_df': self.transactions_data
        }
        self.verification_completed.emit(results)
        super().accept()

class StockSplitsDialog(QDialog):
    def __init__(self, db_manager, instrument_code, initial_splits=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.instrument_code = instrument_code
        self.initial_splits = initial_splits or {}
        self.splits = {}  # Will store current splits
        self.init_ui()
        self.load_splits()

    def init_ui(self):
        self.setWindowTitle(f"Manage Stock Splits - {self.instrument_code}")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)

        # Add explanation
        layout.addWidget(QLabel(
            "Manage stock splits for this instrument. "
            "A split ratio of 2 means 2-for-1 split (quantity doubles, price halves)."
        ))

        # Table for existing splits
        self.splits_table = QTableWidget()
        self.splits_table.setColumnCount(3)  # Date, Ratio, Delete button
        self.splits_table.setHorizontalHeaderLabels(["Date", "Ratio", ""])
        self.splits_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.splits_table)

        # Add new split section
        add_split_layout = QHBoxLayout()
        
        # Date input
        add_split_layout.addWidget(QLabel("Date:"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(datetime.now().date())
        add_split_layout.addWidget(self.date_edit)

        # Ratio input
        add_split_layout.addWidget(QLabel("Ratio:"))
        self.ratio_spin = QDoubleSpinBox()
        self.ratio_spin.setRange(0.01, 100)
        self.ratio_spin.setValue(2)
        self.ratio_spin.setDecimals(2)
        add_split_layout.addWidget(self.ratio_spin)

        # Add button
        self.add_button = QPushButton("Add Split")
        self.add_button.clicked.connect(self.add_split)
        add_split_layout.addWidget(self.add_button)

        layout.addLayout(add_split_layout)

        # Dialog buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def load_splits(self):
        # Load initial splits (from Yahoo or database)
        self.splits = self.initial_splits.copy()
        self.refresh_table()

    def refresh_table(self):
        self.splits_table.setRowCount(len(self.splits))
        for row, (date, ratio) in enumerate(self.splits.items()):
            # Date
            date_item = QTableWidgetItem(date.strftime('%Y-%m-%d') if isinstance(date, datetime) else date)
            self.splits_table.setItem(row, 0, date_item)
            
            # Ratio
            ratio_item = QTableWidgetItem(str(ratio))
            self.splits_table.setItem(row, 1, ratio_item)
            
            # Delete button
            delete_button = QPushButton("Delete")
            delete_button.clicked.connect(lambda _, r=row: self.delete_split(r))
            self.splits_table.setCellWidget(row, 2, delete_button)

    def add_split(self):
        date = self.date_edit.date().toPython()
        ratio = self.ratio_spin.value()
        
        # Add to splits dictionary
        self.splits[date] = ratio
        self.refresh_table()

    def delete_split(self, row):
        date_item = self.splits_table.item(row, 0)
        date_str = date_item.text()
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        confirm = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the stock split on {date_str}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            if date in self.splits:
                del self.splits[date]
            self.refresh_table()

    def get_splits(self):
        return self.splits