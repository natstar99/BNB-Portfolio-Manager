# File: views/verify_transactions_view.py

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QComboBox, QMessageBox, QLabel, QProgressDialog,
                              QDateEdit, QDoubleSpinBox, QMenu, QDialogButtonBox,
                              QCheckBox, QAbstractItemView, QLineEdit, QApplication)
from PySide6.QtCore import Qt, Signal
from datetime import datetime
import yfinance as yf
import logging
import pandas as pd
from utils.historical_data_collector import HistoricalDataCollector
from views.historical_data_view import ManageHistoricalDataDialog
from utils.yahoo_finance_service import YahooFinanceService
from database.final_metrics_manager import PortfolioMetricsManager

logger = logging.getLogger(__name__)

class VerifyTransactionsDialog(QDialog):
    verification_completed = Signal(dict)  # Emits final verification results

    def __init__(self, transactions_data, db_manager, portfolio_id, parent=None):
        self.market_names = {}
        super().__init__(parent)
        self.db_manager = db_manager
        self.portfolio_id = portfolio_id
        self.transactions_data = transactions_data
        self.market_mappings = {}
        self.stock_data = {}
        self.verification_status = {}
        self.drp_settings = {}
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Verify Imported Transactions")
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(0.1*screen.width(), 0.1*screen.height(), 0.8*screen.width(), 0.8*screen.height())
        
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel(
            "Please verify the imported stocks. You can:\n"
            "• Assign market codes to each instrument\n"
            "• Verify stock information with Yahoo Finance\n"
            "• Manage stock splits and dividend reinvestment settings\n"
            "• Re-verify stocks after making changes"
        )
        layout.addWidget(instructions)
        
        # Main table
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "Instrument Code",
            "Market",
            "Yahoo Symbol",
            "Stock Name",
            "Latest Price",
            "Currency",
            "Splits",
            "DRP",
            "Status",
            "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.table)
        self.table.sortByColumn(0, Qt.AscendingOrder)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers) # Make table uneditable by default

        # Add management buttons
        management_layout = QHBoxLayout()
        
        self.add_instrument_btn = QPushButton("Add Instrument")
        self.add_instrument_btn.clicked.connect(self.add_instrument)
        management_layout.addWidget(self.add_instrument_btn)
        
        self.remove_selected_btn = QPushButton("Remove Selected")
        self.remove_selected_btn.clicked.connect(self.remove_selected)
        self.remove_selected_btn.setEnabled(False)  # Initially disabled
        management_layout.addWidget(self.remove_selected_btn)
        
        management_layout.addStretch()
        layout.insertLayout(1, management_layout)  # Add after instructions
        
        # Enable multi-selection in table
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        # Connect selection changed signal
        self.table.itemSelectionChanged.connect(self.update_button_states)
        
        # Buttons bar
        button_layout = QHBoxLayout()
        
        # Left side buttons
        left_buttons = QHBoxLayout()
        self.verify_all_btn = QPushButton("Verify All with Yahoo")
        self.verify_all_btn.clicked.connect(self.verify_all_stocks)
        left_buttons.addWidget(self.verify_all_btn)
        
        self.manage_markets_btn = QPushButton("Manage Markets")
        self.manage_markets_btn.clicked.connect(self.show_manage_markets)
        left_buttons.addWidget(self.manage_markets_btn)
        
        button_layout.addLayout(left_buttons)
        button_layout.addStretch()
        
        # Right side buttons
        self.buttons = QDialogButtonBox(parent=self)
        update_btn = QPushButton("Save and Update Data")
        exit_btn = QPushButton("Save and Exit")
        
        self.buttons.addButton(update_btn, QDialogButtonBox.AcceptRole)
        self.buttons.addButton(exit_btn, QDialogButtonBox.RejectRole)
        
        # Connect the buttons to their respective slots
        update_btn.clicked.connect(self.save_and_update)
        exit_btn.clicked.connect(self.save_and_exit)
        
        button_layout.addWidget(self.buttons)
        
        layout.addLayout(button_layout)
        
        # Initialise table data
        self.populate_table()

    def populate_table(self):
        """
        Populate the verification table with stock data.
        Shows both imported transactions and existing database stocks.
        """
        try:
            # Get all unique instrument codes from both transactions and database
            transaction_codes = set()
            if self.transactions_data is not None and 'Instrument Code' in self.transactions_data:
                transaction_codes = set(self.transactions_data['Instrument Code'].unique())
            
            # Get all stocks from database
            db_stocks = self.db_manager.get_all_stocks()
            db_codes = {stock[2] for stock in db_stocks}  # stock[2] is instrument_code
            
            # Combine unique codes from both sources
            all_instrument_codes = sorted(transaction_codes.union(db_codes))
            
            self.table.setRowCount(len(all_instrument_codes))
            
            # Get market codes for the dropdown
            market_codes = self.db_manager.get_all_market_codes()
            
            for row, instrument_code in enumerate(all_instrument_codes):
                # Initialise all table items first to prevent NoneType errors
                for col in range(self.table.columnCount()):
                    self.table.setItem(row, col, QTableWidgetItem(""))
                    
                # Set Instrument Code (Column 0)
                self.table.setItem(row, 0, QTableWidgetItem(instrument_code))
                
                # Get existing stock data from database if it exists
                existing_stock = self.db_manager.get_stock_by_instrument_code(instrument_code)
                
                # Create and setup Market Combo Box (Column 1)
                market_combo = QComboBox()
                market_combo.addItem("Select Market", "")
                for market_or_index, suffix in market_codes:
                    market_combo.addItem(market_or_index, market_or_index)
                self.table.setCellWidget(row, 1, market_combo)
                
                if existing_stock:
                    stock_id = existing_stock[0]
                    yahoo_symbol = existing_stock[1]
                    name = existing_stock[3]
                    current_price = existing_stock[4]
                    market_or_index = existing_stock[6]
                    market_suffix = existing_stock[7]
                    verification_status = existing_stock[8]
                    drp = existing_stock[9]
                    currency = existing_stock[10]
                    
                    # Set the market combo box value if we have one
                    if market_or_index:
                        index = market_combo.findText(market_or_index)
                        if index >= 0:
                            market_combo.setCurrentIndex(index)
                    
                    # Set Yahoo Symbol (Column 2)
                    self.table.setItem(row, 2, QTableWidgetItem(yahoo_symbol if yahoo_symbol else ""))
                    
                    # Set Stock Name (Column 3)
                    self.table.item(row, 3).setText(name or "")
                    
                    # Set Current Price (Column 4) and Currency (Column 5)
                    if current_price:
                        self.table.item(row, 4).setText(f"{current_price:.2f}")
                        self.table.item(row, 5).setText(currency)
                    
                    # Check for splits and set indicator (Column 6)
                    splits = self.db_manager.get_stock_splits(stock_id)
                    split_indicator = "✓" if splits else ""
                    self.table.item(row, 6).setText(split_indicator)
                    
                    # Set DRP checkbox (Column 7)
                    drp_checkbox = QCheckBox()
                    drp_checkbox.setChecked(bool(drp))
                    drp_checkbox.stateChanged.connect(lambda state, r=row: self.on_drp_changed(r))
                    self.table.setCellWidget(row, 7, drp_checkbox)
                    self.drp_settings[instrument_code] = bool(drp)
                    
                    # Set verification status (Column 8)
                    if verification_status == "Delisted":
                        self.update_status(row, "Delisted", Qt.black)
                    elif name:
                        if name == "N/A":
                            self.update_status(row, "Not Found", Qt.red)
                        else:
                            self.update_status(row, verification_status, Qt.darkGreen if verification_status == "Verified" else Qt.gray)
                    else:
                        self.update_status(row, "Pending", Qt.gray)
                            
                else:
                    # Handle new stock
                    # Set empty Yahoo Symbol (will be updated when market is selected)
                    self.table.item(row, 2).setText(instrument_code)
                    
                    # Initialise other columns as empty
                    self.table.item(row, 3).setText("")  # Name
                    self.table.item(row, 4).setText("")  # Price
                    self.table.item(row, 6).setText("")  # Splits
                    
                    # Add DRP checkbox for new stock (Column 6)
                    drp_checkbox = QCheckBox()
                    drp_checkbox.setChecked(False)
                    drp_checkbox.stateChanged.connect(lambda state, r=row: self.on_drp_changed(r))
                    self.table.setCellWidget(row, 7, drp_checkbox)
                    self.drp_settings[instrument_code] = False
                    
                    # Set initial verification status as Pending (Column 8)
                    self.update_status(row, "Pending", Qt.gray)
                
                # Connect market combo box signal
                # Important: Connect after setting initial value to avoid triggering updates
                market_combo.currentIndexChanged.connect(
                    lambda idx, r=row: self.on_market_changed(r)
                )
                
                # Create Actions Button (Column 9)
                actions_btn = QPushButton("Actions ▼")
                actions_btn.clicked.connect(lambda _, r=row: self.show_actions_menu(r))
                self.table.setCellWidget(row, 9, actions_btn)

                # Store the initial verification status
                if row not in self.verification_status:
                    self.verification_status[row] = "Pending"

        except Exception as e:
            logging.error(f"Error populating table: {str(e)}")
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to populate table: {str(e)}"
            )

    def on_market_changed(self, row):
        """Handle changes to the market selection dropdown."""
        try:
            instrument_code = self.table.item(row, 0).text()
            market_combo = self.table.cellWidget(row, 1)
            market_or_index = market_combo.currentData()
            yahoo_symbol_item = self.table.item(row, 2)
            
            # Get market suffix from database
            if market_or_index:
                result = self.db_manager.fetch_one(
                    "SELECT market_suffix FROM market_codes WHERE market_or_index = ?",
                    (market_or_index,)
                )
                market_suffix = result[0] if result else ""
                yahoo_symbol = f"{instrument_code}{market_suffix}" if market_suffix else instrument_code
                yahoo_symbol_item.setText(yahoo_symbol)
                self.market_mappings[instrument_code] = market_suffix
            else:
                yahoo_symbol_item.setText(instrument_code)
                self.market_mappings[instrument_code] = ""
            
            # Reset verification status
            self.update_status(row, "Pending", Qt.gray)
            
        except Exception as e:
            logging.error(f"Error in on_market_changed: {str(e)}")

    def show_manage_markets(self):
        """Show the manage markets dialog and refresh markets after closing."""
        from views.manage_markets_dialog import ManageMarketsDialog
        dialog = ManageMarketsDialog(self.db_manager, self)
        if dialog.exec_():
            self.refresh_market_combos()

    def refresh_market_combos(self):
        """Refresh all market combo boxes with updated market codes."""
        market_codes = self.db_manager.get_all_market_codes()
        
        for row in range(self.table.rowCount()):
            market_combo = self.table.cellWidget(row, 1)
            current_market = market_combo.currentData()
            
            market_combo.clear()
            market_combo.addItem("Select Market", "")
            
            for market_or_index, suffix in market_codes:
                market_combo.addItem(market_or_index, market_or_index)
            
            if current_market:
                index = market_combo.findData(current_market)
                if index >= 0:
                    market_combo.setCurrentIndex(index)
                    
            self.on_market_changed(row)  # Update Yahoo symbols

    def on_yahoo_symbol_changed(self, row):
        try:
            instrument_code = self.table.item(row, 0).text()
            yahoo_symbol = self.table.item(row, 2).text()
            
            # Update the database with the manual override
            self.db_manager.update_stock_yahoo_override(instrument_code, yahoo_symbol)
            
            # Reset verification status
            self.update_status(row, "Pending", Qt.gray)
            
        except Exception as e:
            print(f"Error in on_yahoo_symbol_changed: {str(e)}")

    def verify_all_stocks(self):
        progress = QProgressDialog("Verifying stocks with Yahoo Finance...", "Cancel", 0, self.table.rowCount(), self)
        progress.setWindowModality(Qt.WindowModal)
        
        for row in range(self.table.rowCount()):
            if self.table.item(row, 8).text() != "Delisted":
                if progress.wasCanceled():
                    break
                    
                self.initiate_verification(row)
                progress.setValue(row + 1)
        
        progress.close()

    def on_drp_changed(self, row):
        """Handle changes to the DRP checkbox."""
        drp_checkbox = self.table.cellWidget(row, 7)  # Column 7 is DRP
        instrument_code = self.table.item(row, 0).text()
        stock = self.db_manager.get_stock_by_instrument_code(instrument_code)
        if stock:
            stock_id = stock[0]
            is_checked = drp_checkbox.isChecked()
            self.db_manager.update_stock_drp(stock_id, is_checked)
            self.drp_settings[instrument_code] = is_checked

    def initiate_verification(self, row):
        """
        Verify stock using Yahoo Finance service.
        
        Args:
            row (int): The row number in the table to verify
        """
        instrument_code = self.table.item(row, 0).text()
        yahoo_symbol = self.table.item(row, 2).text()
        
        if not yahoo_symbol:
            self.update_status(row, "No Symbol", Qt.red)
            return
        
        try:
            # Use YahooFinanceService to verify stock
            result = YahooFinanceService.verify_stock(yahoo_symbol)
            
            if result['error']:
                self.update_status(row, "Failed", Qt.red)
                logger.error(f"Error verifying {yahoo_symbol}: {result['error']}")
                return
            
            # Update stock name
            self.table.item(row, 3).setText(result['name'])
            
            # Update verification status
            if result['exists']:
                self.update_status(row, "Verified", Qt.darkGreen)
            else:
                self.update_status(row, "Not Found", Qt.red)
            
            # Update latest price
            self.table.item(row, 4).setText(str(result['current_price']))

            # Update currency
            trading_currency = result['currency']
            self.table.item(row, 5).setText(trading_currency)
            
            # Get market settings
            market_combo = self.table.cellWidget(row, 1)
            market_or_index = market_combo.currentData()
            market_suffix = self.db_manager.get_market_code_suffix(market_or_index) if market_or_index else ""
            
            # Store the verified data
            self.stock_data[instrument_code] = {
                'name': result['name'],
                'price': result['current_price'],
                'symbol': yahoo_symbol,
                'market_or_index': market_or_index,
                'market_suffix': market_suffix,
                'drp': self.drp_settings.get(instrument_code, False),
                'trading_currency': trading_currency,  # Store trading currency
                'current_currency': None  # Initialise as None
            }

            # Add splits if any found
            if result['splits'] is not None:
                self.table.item(row, 6).setText("✓")
                self.stock_data[instrument_code]['splits'] = result['splits']
            else:
                self.table.item(row, 6).setText("")
                
        except Exception as e:
            self.update_status(row, "Failed", Qt.red)
            logger.error(f"Error verifying {yahoo_symbol}: {str(e)}")

    def update_status(self, row, status, color):
        """Update the verification status for a given row."""
        # Ensure the status cell exists, create it if it doesn't
        status_item = self.table.item(row, 8)  # Status is column 8
        if status_item is None:
            status_item = QTableWidgetItem("")
            self.table.setItem(row, 8, status_item)
        
        status_item.setText(status)
        
        # Special handling for delisted status
        if status == "Delisted":
            font = status_item.font()
            font.setBold(True)
            status_item.setFont(font)
            status_item.setForeground(Qt.black)
        else:
            status_item.setForeground(color)
        
        self.verification_status[row] = status

    def show_actions_menu(self, row):
        menu = QMenu(self)
        
        verify_action = menu.addAction("Verify with Yahoo")
        verify_action.triggered.connect(lambda: self.initiate_verification(row))
        
        delist_action = menu.addAction("Mark as Delisted")
        delist_action.triggered.connect(lambda: self.mark_as_delisted(row))
        
        manage_splits_action = menu.addAction("Manage Splits")
        manage_splits_action.triggered.connect(lambda: self.manage_splits(row))
        
        # Show menu at button
        button = self.table.cellWidget(row, 9) # Actions menu in column 9
        menu.exec_(button.mapToGlobal(button.rect().bottomLeft()))

    def manage_splits(self, row):
        """Show the splits management dialog for the stock at the specified row."""
        instrument_code = self.table.item(row, 0).text()
        yahoo_splits = self.stock_data.get(instrument_code, {}).get('splits', {})
        
        dialog = StockSplitsDialog(
            self.db_manager,
            instrument_code,
            initial_splits=yahoo_splits,
            parent=self
        )
        
        if dialog.exec_():
            # Refresh the splits indicator in the table
            has_splits = bool(dialog.get_splits())
            self.table.item(row, 6).setText("✓" if has_splits else "")

    def show_context_menu(self, position):
        menu = QMenu(self)
        row = self.table.rowAt(position.y())
        
        if row >= 0:
            verify_action = menu.addAction("Verify with Yahoo")
            verify_action.triggered.connect(lambda: self.initiate_verification(row))
            
            manage_splits_action = menu.addAction("Manage Splits")
            manage_splits_action.triggered.connect(lambda: self.manage_splits(row))
            
            menu.exec_(self.table.viewport().mapToGlobal(position))

    def mark_as_delisted(self, row):
        """Mark a stock as delisted and update its status."""
        try:
            # Get current stock information
            instrument_code = self.table.item(row, 0).text()
            
            # Confirm action with user
            confirm = QMessageBox.question(
                self,
                "Confirm Delisting",
                f"Are you sure you want to mark {instrument_code} as delisted?\n"
                "This will preserve the stock's historical data but mark it as no longer trading.",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if confirm == QMessageBox.Yes:
                # Update the status in the table
                status_item = QTableWidgetItem("Delisted")
                font = status_item.font()
                font.setBold(True)
                status_item.setFont(font)
                status_item.setForeground(Qt.black)
                self.table.setItem(row, 8, status_item)
                
                # Update verification status in memory
                self.verification_status[row] = "Delisted"
                
                # Update the stock data dictionary
                if instrument_code in self.stock_data:
                    self.stock_data[instrument_code]['verification_status'] = "Delisted"
                
                # If the stock exists in the database, update it immediately
                stock = self.db_manager.get_stock_by_instrument_code(instrument_code)
                if stock:
                    stock_id = stock[0]
                    self.db_manager.execute("""
                        UPDATE stocks 
                        SET verification_status = 'Delisted',
                            last_updated = ?
                        WHERE id = ?
                    """, (datetime.now().replace(microsecond=0), stock_id))
                    self.db_manager.conn.commit()
                
                QMessageBox.information(
                    self,
                    "Stock Delisted",
                    f"{instrument_code} has been marked as delisted."
                )
                
        except Exception as e:
            logging.error(f"Error marking stock as delisted: {str(e)}")
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to mark stock as delisted: {str(e)}"
            )

    def update_button_states(self):
        """Enable/disable buttons based on selection state."""
        has_selection = len(self.table.selectedItems()) > 0
        self.remove_selected_btn.setEnabled(has_selection)

    def add_instrument(self):
        """Show dialog to add a new instrument code and optionally add transactions."""
        dialog = AddInstrumentDialog(self)
        if dialog.exec_():
            instrument_code = dialog.get_instrument_code()
            if not instrument_code:
                return
                
            # Check if instrument code already exists
            existing = False
            for row in range(self.table.rowCount()):
                if self.table.item(row, 0).text() == instrument_code:
                    existing = True
                    break
            
            if existing:
                QMessageBox.warning(
                    self,
                    "Duplicate Instrument",
                    f"Instrument code {instrument_code} already exists."
                )
                return
                
            # Add new row to table
            current_row = self.table.rowCount()
            self.table.setRowCount(current_row + 1)
            
            # Set instrument code
            self.table.setItem(current_row, 0, QTableWidgetItem(instrument_code))
            
            # Add market combo box
            market_combo = QComboBox()
            market_combo.addItem("Select Market", "")
            market_codes = self.db_manager.get_all_market_codes()
            for market_or_index, suffix in market_codes:
                market_combo.addItem(market_or_index, market_or_index)
            self.table.setCellWidget(current_row, 1, market_combo)
            
            # Initialise other columns
            for col in range(2, 8):
                self.table.setItem(current_row, col, QTableWidgetItem(""))
                
            # Add DRP checkbox
            drp_checkbox = QCheckBox()
            drp_checkbox.setChecked(False)
            drp_checkbox.stateChanged.connect(lambda state, r=current_row: self.on_drp_changed(r))
            self.table.setCellWidget(current_row, 7, drp_checkbox)
            
            # Set initial status
            self.update_status(current_row, "Pending", Qt.gray)
            
            # Add actions button
            actions_btn = QPushButton("Actions ▼")
            actions_btn.clicked.connect(lambda _, r=current_row: self.show_actions_menu(r))
            self.table.setCellWidget(current_row, 9, actions_btn)
            
            # Connect market combo signal
            market_combo.currentIndexChanged.connect(
                lambda idx, r=current_row: self.on_market_changed(r)
            )

            # Add basic stock record to database
            stock_id = self.db_manager.add_stock(
                yahoo_symbol=instrument_code,  # Initially same as instrument code
                instrument_code=instrument_code,
                name=None,
                current_price=None,
                verification_status="Pending",
                trading_currency=None,
                current_currency=None,  # Will be set during verification
            )

            # Associate the stock with the portfolio
            if self.portfolio_id:
                self.db_manager.add_stock_to_portfolio(self.portfolio_id, stock_id)

            # After adding to database, ask about transactions
            response = QMessageBox.question(
                self,
                "Add Transactions",
                "Would you like to add transactions for this instrument now?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if response == QMessageBox.Yes:
                stock_tuple = self.db_manager.get_stock_by_instrument_code(instrument_code)
                if stock_tuple:
                    from models.stock import Stock  # Make sure to import Stock
                    stock = Stock(
                        id=stock_tuple[0],
                        yahoo_symbol=stock_tuple[1],
                        instrument_code=stock_tuple[2],
                        name=stock_tuple[3],
                        current_price=stock_tuple[4],
                        last_updated=stock_tuple[5],
                        db_manager=self.db_manager
                    )
                    dialog = ManageHistoricalDataDialog(
                        stock=stock,
                        db_manager=self.db_manager,
                        parent=self
                    )
                    # Hide the update data button
                    dialog.update_data_btn.hide()
                    # Change button box to have Save instead of Close
                    dialog.button_box.clear()
                    save_btn = QPushButton("Save")
                    save_btn.clicked.connect(dialog.accept)
                    dialog.button_box.addButton(save_btn, QDialogButtonBox.AcceptRole)
                    cancel_btn = QPushButton("Cancel") 
                    cancel_btn.clicked.connect(dialog.reject)
                    dialog.button_box.addButton(cancel_btn, QDialogButtonBox.RejectRole)
                    
                    dialog.exec_()

    def remove_selected(self):
        """Remove selected instruments after appropriate warnings and validation."""
        selected_rows = sorted(set(item.row() for item in self.table.selectedItems()))
        if not selected_rows:
            return
            
        # Check for existing transactions
        instruments_with_transactions = []
        for row in selected_rows:
            instrument_code = self.table.item(row, 0).text()
            stock = self.db_manager.get_stock_by_instrument_code(instrument_code)
            if stock:
                stock_id = stock[0]
                transactions = self.db_manager.fetch_one(
                    "SELECT COUNT(*) FROM transactions WHERE stock_id = ?",
                    (stock_id,)
                )
                if transactions and transactions[0] > 0:
                    instruments_with_transactions.append((instrument_code, transactions[0]))
        
        warning_message = f"Are you sure you want to remove {len(selected_rows)} selected instruments?"
        
        if instruments_with_transactions:
            warning_message += "\n\nWARNING: The following instruments have existing transactions:\n"
            for instrument, count in instruments_with_transactions:
                warning_message += f"\n• {instrument}: {count} transactions"
            warning_message += "\n\nDeleting these stocks will also delete all their historical data and transactions."
        
        confirm = QMessageBox.question(
            self,
            "Confirm Removal",
            warning_message,
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            try:
                # Remove from database
                for row in reversed(selected_rows):
                    instrument_code = self.table.item(row, 0).text()
                    stock = self.db_manager.get_stock_by_instrument_code(instrument_code)
                    if stock:
                        stock_id = stock[0]
                        # Delete the stock (CASCADE will handle related records)
                        self.db_manager.execute(
                            "DELETE FROM stocks WHERE id = ?",
                            (stock_id,)
                        )
                    
                    # Remove from table
                    self.table.removeRow(row)
                
                self.db_manager.conn.commit()
                
            except Exception as e:
                self.db_manager.conn.rollback()
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to remove stocks: {str(e)}"
                )

    def _get_unverified_stocks(self):
        """
        Helper method to get list of unverified stocks.
        Returns list of row numbers for stocks that are neither verified nor delisted.
        """
        return [
            row for row, status in self.verification_status.items() 
            if status not in ["Verified", "Delisted"]
        ]

    def accept(self):
        # Check if all stocks have been verified or delisted
        unverified = self._get_unverified_stocks()
        
        if unverified:
            response = QMessageBox.question(
                self,
                "Unverified Stocks",
                "Some stocks haven't been verified or marked as delisted. Continue anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if response == QMessageBox.No:
                return
        
        # Emit verification results
        results = {
            'market_mappings': self.market_mappings,
            'stock_data': self.stock_data,
            'verification_status': self.verification_status,
            'transactions_df': self.transactions_data,
            'drp_settings': self.drp_settings
        }
        self.verification_completed.emit(results)
        super().accept()

    def save_and_update(self):
        """Get fresh Yahoo data, calculate metrics, save to db."""
        try:
            self.save_changes()
            
            progress = QProgressDialog(
                "Updating with fresh Yahoo data...",
                "Cancel",
                0,
                self.table.rowCount(),
                self
            )
            progress.setWindowModality(Qt.WindowModal)

            for row in range(self.table.rowCount()):
                if progress.wasCanceled():
                    break

                verification_status = self.table.item(row, 8).text()
                if verification_status == "Verified":
                    instrument_code = self.table.item(row, 0).text()
                    stock = self.db_manager.get_stock_by_instrument_code(instrument_code)
                    
                    if stock and stock[0]:
                        # stock[0] is id, stock[1] is yahoo_symbol
                        HistoricalDataCollector.process_and_store_historical_data(
                            db_manager=self.db_manager,
                            stock_id=stock[0],
                            yahoo_symbol=stock[1]
                        )

                progress.setValue(row + 1)

            progress.close()
            self.reject()

        except Exception as e:
            logger.error(f"Error in save_and_update: {str(e)}")
            logger.exception("Detailed traceback:")  # Add full traceback to log
            QMessageBox.warning(self, "Error", f"Failed to update with fresh data: {str(e)}")
            self.reject()

    def save_and_exit(self):
        """Use existing data, calculate metrics, save to db"""
        try:
            # 1. Save stock meta data
            self.save_changes()
            logger.info("Basic stock data saved")

            progress = QProgressDialog(
                "Calculating metrics with existing data...",
                "Cancel",
                0,
                self.table.rowCount(),
                self
            )
            progress.setWindowModality(Qt.WindowModal)

            for row in range(self.table.rowCount()):
                if progress.wasCanceled():
                    break

                instrument_code = self.table.item(row, 0).text()
                verification_status = self.table.item(row, 8).text()

                if verification_status == "Verified":
                    stock = self.db_manager.get_stock_by_instrument_code(instrument_code)
                    if stock and stock[0]:
                        stock_id = stock[0]
                        yahoo_symbol = stock[1]
                        transactions = self.db_manager.get_transactions_for_stock(stock_id)
                        if transactions:
                            # 2. Get existing Yahoo data from db
                            logger.info(f"Reading existing data for {yahoo_symbol}")
                            existing_yahoo_data = self.db_manager.get_existing_yahoo_data(
                                stock_id=stock_id
                            )

                            # 3. Calculate metrics using existing data
                            logger.info(f"Calculating metrics for {yahoo_symbol}")
                            metrics = HistoricalDataCollector.calculate_historical_metrics(
                                stock_id=stock_id,
                                transactions=transactions,
                                yahoo_data=existing_yahoo_data
                            )

                            # 4. Save updated metrics to db
                            if metrics:
                                logger.debug(f"About to insert {len(metrics)} records")
                                self.db_manager.bulk_insert_historical_prices(metrics)
                                logger.debug("Insert completed")

                progress.setValue(row + 1)

            progress.close()
            self.reject()

        except Exception as e:
            logger.error(f"Error in save_and_exit: {str(e)}")
            logger.exception("Detailed traceback:")
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to calculate metrics with existing data: {str(e)}"
            )
            self.reject()

    def save_changes(self):
        """
        Save the current state of all stocks to the database and update metrics.
        Handles stock data, DRP settings, splits, and metrics calculations.
        """
        try:
            metrics_manager = PortfolioMetricsManager(self.db_manager)
                
            for row in range(self.table.rowCount()):
                instrument_code = self.table.item(row, 0).text()
                market_combo = self.table.cellWidget(row, 1)
                yahoo_symbol = self.table.item(row, 2).text()
                name = self.table.item(row, 3).text()
                current_price = self.table.item(row, 4).text()
                trading_currency = self.table.item(row, 5).text()
                verification_status = self.table.item(row, 8).text()
                
                logging.info(f"Saving stock {instrument_code} with verification status: {verification_status}")
                
                # Get or create the stock
                stock = self.db_manager.get_stock_by_instrument_code(instrument_code)
                
                if stock:
                    stock_id = stock[0]
                    # Check if a valid market or index selection has been made an update existing stock .db if so
                    if market_combo.currentIndex() > 0:
                        market_or_index = market_combo.currentData()
                        self.db_manager.update_stock_market(instrument_code, market_or_index)
                    
                    # Convert price text box -> float
                    try:
                        price = float(current_price) if current_price else None
                    except ValueError:
                        price = None
                        logging.warning(f"Invalid price value for {instrument_code}: {current_price}")
                    
                    self.db_manager.execute("""
                        UPDATE stocks 
                        SET name = ?,
                            current_price = ?,
                            yahoo_symbol = ?,
                            verification_status = ?,
                            trading_currency = ?
                        WHERE id = ?
                    """, (
                        name if name else None,
                        price,
                        yahoo_symbol,
                        verification_status,
                        trading_currency,
                        stock_id
                    ))
                    
                    logging.info(f"Updated stock {instrument_code} (ID: {stock_id}) with status: {verification_status}")
                else:
                    # Create new stock
                    market_or_index = market_combo.currentData() if market_combo.currentIndex() > 0 else None
                    
                    try:
                        current_price_float = float(current_price) if current_price else None
                    except ValueError:
                        current_price_float = None
                        logging.warning(f"Invalid price value for new stock {instrument_code}: {current_price}")
                    
                    stock_id = self.db_manager.add_stock(
                        yahoo_symbol=yahoo_symbol,
                        instrument_code=instrument_code,
                        name=name if name else None,
                        current_price=current_price_float,
                        market_or_index=market_or_index,
                        verification_status=verification_status
                    )
                    
                    logging.info(f"Created new stock {instrument_code} (ID: {stock_id})")
                
                if stock_id:
                    
                    # Handle portfolio association
                    if self.portfolio_id:
                        self.db_manager.add_stock_to_portfolio(self.portfolio_id, stock_id)

                    # Process splits if available
                    if instrument_code in self.stock_data and 'splits' in self.stock_data[instrument_code]:
                        splits = self.stock_data[instrument_code]['splits']
                        split_records = [
                            (stock_id, date.strftime('%Y-%m-%d'), ratio, 'yahoo', datetime.now())
                            for date, ratio in splits.items()
                        ]
                        if split_records:
                            self.db_manager.bulk_insert_stock_splits(split_records)
                            logging.info(f"Saved {len(split_records)} splits for {instrument_code}")

                    # Update metrics for verified stocks
                    if verification_status == "Verified":
                        metrics_manager.update_metrics_for_stock(stock_id)
                        logging.info(f"Updated metrics for verified stock {instrument_code}")
            
            # Commit all changes
            self.db_manager.conn.commit()
            logging.info("Successfully saved all stock changes and updated metrics")
            
            # Emit verification results
            self.verification_completed.emit({
                'market_mappings': self.market_mappings,
                'stock_data': self.stock_data,
                'verification_status': self.verification_status,
                'transactions_df': self.transactions_data,
                'drp_settings': self.drp_settings
            })
                
        except Exception as e:
            self.db_manager.conn.rollback()
            logging.error(f"Error saving changes: {str(e)}")
            logging.exception("Detailed traceback:")
            QMessageBox.warning(
                self,
                "Error Saving Changes",
                f"Failed to save changes: {str(e)}"
            )

    def closeEvent(self, event):
        """Handle the window close event (X button)"""
        self.save_changes()
        event.accept()  # Allow the window to close

class StockSplitsDialog(QDialog):
    def __init__(self, db_manager, instrument_code, initial_splits=None, parent=None):
        """
        Dialog for managing stock splits.
        
        Args:
            db_manager: Database manager instance
            instrument_code: The stock's instrument code
            initial_splits: Dictionary of splits from Yahoo Finance (optional)
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_manager = db_manager
        self.instrument_code = instrument_code
        self.initial_splits = initial_splits or {}
        self.splits = {}  # Will store all splits (both manual and from Yahoo)
        self.init_ui()
        self.load_splits()

    def init_ui(self):
        """Initialise the user interface components."""
        self.setWindowTitle(f"Manage Stock Splits - {self.instrument_code}")
        layout = QVBoxLayout(self)

        # Add explanation with different coloured text for manual/yahoo splits
        explanation = QLabel(
            "Manage stock splits for this instrument.\n"
            "• Yahoo Finance splits are shown in blue\n"
            "• Manual splits are shown in black\n"
            "Note: Manual splits will be preserved during Yahoo updates."
        )
        explanation.setStyleSheet("color: #333;")
        layout.addWidget(explanation)

        # Table for existing splits
        self.splits_table = QTableWidget()
        self.splits_table.setColumnCount(4)  # Date, Ratio, Source, Delete button
        self.splits_table.setHorizontalHeaderLabels(["Date", "Ratio", "Source", ""])
        self.splits_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
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
        self.ratio_spin.setValue(2.00)
        self.ratio_spin.setDecimals(2)
        add_split_layout.addWidget(self.ratio_spin)

        # Add button
        self.add_button = QPushButton("Add Manual Split")
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
        """Load splits from both database and Yahoo Finance data."""
        try:
            # Get stock ID from database
            stock = self.db_manager.get_stock(self.instrument_code)
            if stock:
                # Fetch splits including the verified_source field
                db_splits = self.db_manager.fetch_all("""
                    SELECT date, ratio, verified_source
                    FROM stock_splits
                    WHERE stock_id = ?
                    ORDER BY date
                """, (stock[0],))

                # Load splits from database
                for split in db_splits:
                    date = datetime.strptime(split[0], '%Y-%m-%d').date()
                    self.splits[date] = {
                        'ratio': float(split[1]),
                        'source': split[2] if split[2] else 'manual'
                    }

            # Add any new Yahoo splits
            if self.initial_splits is not None:
                for date, ratio in self.initial_splits.items():
                    if isinstance(date, str):
                        date = datetime.strptime(date, '%Y-%m-%d').date()
                    self.splits[date] = {
                        'ratio': float(ratio),
                        'source': 'yahoo'
                    }

            self.refresh_table()

        except Exception as e:
            QMessageBox.warning(
                self,
                "Error Loading Splits",
                f"Failed to load stock splits: {str(e)}"
            )

    def refresh_table(self):
        """Refresh the splits table with current data."""
        self.splits_table.setRowCount(len(self.splits))
        
        # Sort splits by date
        sorted_splits = sorted(self.splits.items())
        
        for row, (date, split_info) in enumerate(sorted_splits):
            # Date column
            date_item = QTableWidgetItem(date.strftime('%Y-%m-%d'))
            self.splits_table.setItem(row, 0, date_item)
            
            # Ratio column (format to 2 decimal places)
            ratio_item = QTableWidgetItem(f"{split_info['ratio']:.2f}")
            self.splits_table.setItem(row, 1, ratio_item)
            
            # Source column
            source_item = QTableWidgetItem(split_info['source'])
            if split_info['source'] == 'yahoo':
                source_item.setForeground(Qt.blue)
            self.splits_table.setItem(row, 2, source_item)
            
            # Delete button (only for manual splits)
            if split_info['source'] != 'yahoo':
                delete_button = QPushButton("Delete")
                delete_button.clicked.connect(lambda checked, r=row: self.delete_split(r))
                self.splits_table.setCellWidget(row, 3, delete_button)

    def add_split(self):
        """Add a new manual split."""
        date = self.date_edit.date().toPython()
        ratio = self.ratio_spin.value()

        # Check if split already exists on this date
        if date in self.splits:
            QMessageBox.warning(
                self,
                "Split Exists",
                f"A split already exists for {date.strftime('%Y-%m-%d')}. "
                "Please choose a different date."
            )
            return

        # Add to splits dictionary
        self.splits[date] = {
            'ratio': ratio,
            'source': 'manual'
        }
        
        self.refresh_table()

    def delete_split(self, row):
        """Delete a manual split."""
        date_item = self.splits_table.item(row, 0)
        date_str = date_item.text()
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Confirm deletion
        confirm = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the stock split on {date_str}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            if date in self.splits:
                # Only delete if it's a manual split
                if self.splits[date]['source'] == 'manual':
                    del self.splits[date]
                    self.refresh_table()
                else:
                    QMessageBox.warning(
                        self,
                        "Cannot Delete",
                        "Yahoo Finance splits cannot be deleted."
                    )

    def get_splits(self):
        """Return the current splits dictionary."""
        return self.splits

    def accept(self):
        """Handle the OK button click."""
        try:
            # Get stock ID
            stock = self.db_manager.get_stock(self.instrument_code)
            if stock:
                stock_id = stock[0]
                
                # Clear existing manual splits (preserve Yahoo splits)
                self.db_manager.execute("""
                    DELETE FROM stock_splits 
                    WHERE stock_id = ? AND (verified_source IS NULL OR verified_source = 'manual')
                """, (stock_id,))
                
                # Insert all current splits
                for date, split_info in self.splits.items():
                    self.db_manager.execute("""
                        INSERT OR REPLACE INTO stock_splits 
                        (stock_id, date, ratio, verified_source, verification_date)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        stock_id,
                        date.strftime('%Y-%m-%d'),
                        split_info['ratio'],
                        split_info['source'],
                        datetime.now()
                    ))
                
                self.db_manager.conn.commit()
                super().accept()
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error Saving Splits",
                f"Failed to save stock splits: {str(e)}"
            )

class AddInstrumentDialog(QDialog):
    """
    Dialog for adding a new instrument code to the verification list.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Instrument")
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel(
            "Enter the instrument code for the stock you wish to add.\n"
            "You can verify and configure the stock details after adding it."
        )
        layout.addWidget(instructions)
        
        # Input field
        self.instrument_code = QLineEdit()
        self.instrument_code.setPlaceholderText("Enter Instrument Code")
        layout.addWidget(self.instrument_code)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_instrument_code(self):
        """Return the entered instrument code in uppercase."""
        return self.instrument_code.text().strip().upper()