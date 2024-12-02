# File: views/verify_transactions_view.py

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QComboBox, QMessageBox, QLabel, QProgressDialog,
                              QDateEdit, QDoubleSpinBox, QMenu, QDialogButtonBox,
                              QCheckBox)
from PySide6.QtCore import Qt, Signal
from datetime import datetime
import yfinance as yf
import logging

class VerifyTransactionsDialog(QDialog):
    verification_completed = Signal(dict)  # Emits final verification results

    def __init__(self, transactions_data, db_manager, parent=None):
        self.market_names = {}
        super().__init__(parent)
        self.db_manager = db_manager
        self.transactions_data = transactions_data
        self.market_mappings = {}
        self.stock_data = {}
        self.verification_status = {}
        self.drp_settings = {}
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Verify Imported Transactions")
        self.setMinimumWidth(1350)
        self.setMinimumHeight(600)
        
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
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Instrument Code",
            "Market",
            "Yahoo Symbol",
            "Stock Name",
            "Latest Price",
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
        self.table.cellChanged.connect(self.on_cell_changed) # Connect table item changes (used for manual yahoo code declaration)
        
        # Buttons bar
        button_layout = QHBoxLayout()
        
        # Left side buttons
        self.verify_all_btn = QPushButton("Verify All with Yahoo")
        self.verify_all_btn.clicked.connect(self.verify_all_stocks)
        button_layout.addWidget(self.verify_all_btn)
        
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
        Populate the verification table with stock data from the transactions.
        This method initialises the table and handles existing stock data and verification status.
        """
        # Get unique instrument codes from transactions
        instrument_codes = self.transactions_data['Instrument Code'].unique()
        self.table.setRowCount(len(instrument_codes))
        
        # Get market codes for the dropdown
        market_codes = self.db_manager.get_all_market_codes()
        
        for row, instrument_code in enumerate(instrument_codes):
            # Initialise all table items first to prevent NoneType errors
            for col in range(self.table.columnCount()):
                self.table.setItem(row, col, QTableWidgetItem(""))
                
            # Set Instrument Code (Column 0)
            self.table.item(row, 0).setText(instrument_code)
            
            # Get existing stock data from database if it exists
            existing_stock = self.db_manager.get_stock_by_instrument_code(instrument_code)
            
            # Create and setup Market Combo Box (Column 1)
            market_combo = QComboBox()
            market_combo.addItem("Select Market", "")
            for market_or_index, suffix in market_codes:
                market_combo.addItem(market_or_index, market_or_index)  # Store the market_or_index
            self.table.setCellWidget(row, 1, market_combo)
            
            if existing_stock:
                stock_id, yahoo_symbol, _, name, current_price, _, market_or_index, drp, market_suffix = existing_stock
                
                # Set the market combo box value if we have one
                if market_or_index:
                    index = market_combo.findText(market_or_index)
                    if index >= 0:
                        market_combo.setCurrentIndex(index)
                
                # Set Yahoo Symbol (Column 2)
                self.table.setItem(row, 2, QTableWidgetItem(yahoo_symbol if yahoo_symbol else ""))
                
                # Set Stock Name (Column 3)
                self.table.item(row, 3).setText(name or "")
                
                # Set Current Price (Column 4)
                if current_price:
                    self.table.item(row, 4).setText(f"{current_price:.2f}")
                
                # Check for splits and set indicator (Column 5)
                splits = self.db_manager.get_stock_splits(stock_id)
                split_indicator = "✓" if splits else ""
                self.table.item(row, 5).setText(split_indicator)
                
                # Set DRP checkbox (Column 6)
                drp_checkbox = QCheckBox()
                drp_checkbox.setChecked(bool(drp))
                drp_checkbox.stateChanged.connect(lambda state, r=row: self.on_drp_changed(r))
                self.table.setCellWidget(row, 6, drp_checkbox)
                self.drp_settings[instrument_code] = bool(drp)
                
                # Set verification status (Column 7)
                if name:
                    if name == "N/A":
                        self.update_status(row, "Not Found", Qt.red)
                    else:
                        self.update_status(row, "Verified", Qt.green)
                else:
                    self.update_status(row, "Pending", Qt.gray)
                        
            else:
                # Handle new stock
                # Set empty Yahoo Symbol (will be updated when market is selected)
                self.table.item(row, 2).setText(instrument_code)
                
                # Initialise other columns as empty
                self.table.item(row, 3).setText("")  # Name
                self.table.item(row, 4).setText("")  # Price
                self.table.item(row, 5).setText("")  # Splits
                
                # Add DRP checkbox for new stock (Column 6)
                drp_checkbox = QCheckBox()
                drp_checkbox.setChecked(False)
                drp_checkbox.stateChanged.connect(lambda state, r=row: self.on_drp_changed(r))
                self.table.setCellWidget(row, 6, drp_checkbox)
                self.drp_settings[instrument_code] = False
                
                # Set initial verification status as Pending (Column 7)
                self.update_status(row, "Pending", Qt.gray)
            
            # Connect market combo box signal
            # Important: Connect after setting initial value to avoid triggering updates
            market_combo.currentIndexChanged.connect(
                lambda idx, r=row: self.on_market_changed(r)
            )
            
            # Create Actions Button (Column 8)
            actions_btn = QPushButton("Actions ▼")
            actions_btn.clicked.connect(lambda _, r=row: self.show_actions_menu(r))
            self.table.setCellWidget(row, 8, actions_btn)

            # Store the initial verification status
            if row not in self.verification_status:
                self.verification_status[row] = "Pending"

    def on_market_changed(self, row):
        """Handle changes to the market selection dropdown."""
        try:
            instrument_code = self.table.item(row, 0).text()
            market_combo = self.table.cellWidget(row, 1)
            market_or_index = market_combo.currentData()  # Now returns the market_or_index directly
            yahoo_symbol_item = self.table.item(row, 2)
            
            if market_combo.currentText() == "Manually Declare Market Code":
                # Enable editing for manual yahoo symbol entry
                yahoo_symbol_item.setFlags(yahoo_symbol_item.flags() | Qt.ItemIsEditable)
                if not yahoo_symbol_item.text():
                    yahoo_symbol_item.setText(instrument_code)
            else:
                # Disable editing and use standard market suffix
                yahoo_symbol_item.setFlags(yahoo_symbol_item.flags() & ~Qt.ItemIsEditable)
                
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
            
            # Reset verification status
            self.update_status(row, "Pending", Qt.gray)
            
        except Exception as e:
            logging.error(f"Error in on_market_changed: {str(e)}")

    def on_cell_changed(self, row, column):
        """Handle changes to cells in the table."""
        if column == 2:  # Yahoo Symbol column
            instrument_code = self.table.item(row, 0).text()
            yahoo_symbol = self.table.item(row, 2).text()
            
            # Save the manual override to the database
            self.db_manager.update_stock_yahoo_override(instrument_code, yahoo_symbol)
            
            # Update the verification status
            self.update_status(row, "Pending", Qt.gray)

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
            if progress.wasCanceled():
                break
                
            self.verify_stock(row)
            progress.setValue(row + 1)
        
        progress.close()

    def on_drp_changed(self, row):
        """Handle changes to the DRP checkbox."""
        drp_checkbox = self.table.cellWidget(row, 6)  # Column 6 is DRP
        instrument_code = self.table.item(row, 0).text()
        stock = self.db_manager.get_stock_by_instrument_code(instrument_code)
        if stock:
            stock_id = stock[0]
            is_checked = drp_checkbox.isChecked()
            self.db_manager.update_stock_drp(stock_id, is_checked)
            self.drp_settings[instrument_code] = is_checked

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
            
            # Update verification status based on name
            if name and name != "N/A":
                self.update_status(row, "Verified", Qt.green)
            else:
                self.update_status(row, "Not Found", Qt.red)
            
            # Update latest price
            price = (
                info.get('currentPrice', 0.0) or           # Try currentPrice first
                info.get('regularMarketPrice', 0.0) or     # Then regularMarketPrice
                info.get('previousClose', 0.0) or          # Then previousClose
                info.get('lastPrice', 0.0) or              # Then lastPrice
                info.get('regularMarketPreviousClose', 0.0) # Finally try regularMarketPreviousClose

            )
            # If we still don't have a price, try getting it from history
            if price == 0:
                try:
                    # Get the most recent day's data
                    hist = ticker.history(period="1d")
                    if not hist.empty:
                        price = hist['Close'].iloc[-1]  # Get the last closing price
                except Exception as e:
                    print(f"Error getting historical price for {yahoo_symbol}: {str(e)}")

            # If we still don't have a price, log it
            if price == 0:
                print(f"Warning: Could not get price for {yahoo_symbol}")

            self.table.item(row, 4).setText(str(price))

            # Get current market settings from the combo box
            market_combo = self.table.cellWidget(row, 1)
            market_or_index = market_combo.currentData()
            
            # Store the verified data
            self.stock_data[instrument_code] = {
                'name': name,
                'price': price,
                'symbol': yahoo_symbol,
                'market_or_index': market_or_index,
                'drp': self.drp_settings.get(instrument_code, False)
            }

            # Get splits and update indicator
            splits = ticker.splits
            if not splits.empty:
                self.table.item(row, 5).setText("✓")
                self.stock_data[instrument_code]['splits'] = splits
            else:
                self.table.item(row, 5).setText("")
                
        except Exception as e:
            self.update_status(row, "Failed", Qt.red)
            print(f"Error verifying {yahoo_symbol}: {str(e)}")

    def update_status(self, row, status, color):
        """Update the verification status for a given row."""
        # Ensure the status cell exists, create it if it doesn't
        status_item = self.table.item(row, 7)  # Status is column 7
        if status_item is None:
            status_item = QTableWidgetItem("")
            self.table.setItem(row, 7, status_item)
        
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
        button = self.table.cellWidget(row, 8)
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
            self.table.item(row, 5).setText("✓" if has_splits else "")

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
            'transactions_df': self.transactions_data,
            'drp_settings': self.drp_settings
        }
        self.verification_completed.emit(results)
        super().accept()

    def save_and_update(self):
        """Save all changes and update stock data"""
        self.save_changes()  # Save current state
        self.accept()  # Close dialog with accept (will trigger verification)

    def save_and_exit(self):
        """Save all changes without updating stock data"""
        self.save_changes()  # Save current state
        self.reject()  # Close dialog with reject (won't trigger verification)

    def save_changes(self):
        """Save the current state of all stocks"""
        try:
            for row in range(self.table.rowCount()):
                instrument_code = self.table.item(row, 0).text()
                market_combo = self.table.cellWidget(row, 1)
                yahoo_symbol = self.table.item(row, 2).text()
                
                selected_index = market_combo.currentIndex()
                if selected_index > 0:  # If something other than "Select Market" is chosen
                    market_or_index = market_combo.currentData()
                    if market_combo.currentText() == "Manually Declare Market Code":
                        # Save as manual override
                        self.db_manager.update_stock_yahoo_override(instrument_code, yahoo_symbol)
                    elif market_or_index:
                        # Save with market_or_index
                        self.db_manager.update_stock_market(instrument_code, market_or_index)
                
                # Save DRP setting
                drp_checkbox = self.table.cellWidget(row, 6)
                if drp_checkbox:
                    stock = self.db_manager.get_stock_by_instrument_code(instrument_code)
                    if stock:
                        self.db_manager.update_stock_drp(stock[0], drp_checkbox.isChecked())
            
            # Commit all changes
            self.db_manager.conn.commit()
            
        except Exception as e:
            logging.error(f"Error saving changes: {str(e)}")
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
        """Initialize the user interface components."""
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