# File: views/historical_data_view.py

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QTableWidget, QTableWidgetItem, QGroupBox, 
                              QLabel, QDateEdit, QDialogButtonBox, QCheckBox,
                              QAbstractItemView, QComboBox, QMessageBox,
                              QDoubleSpinBox, QFormLayout, QSpinBox, QHeaderView,
                              QApplication)
from PySide6.QtCore import Qt, QDate
from datetime import datetime
import logging
from utils.historical_data_collector import HistoricalDataCollector
import yaml
import os

logger = logging.getLogger(__name__)

class HistoricalDataDialog(QDialog):
    def __init__(self, stock, db_manager, parent=None):
        super().__init__(parent)
        self.stock = stock
        self.db_manager = db_manager
        self.config = self.load_view_config()  # Load configuration
        self.current_view_mode = "Simple"  # Default to Simple view
        self.visible_columns = self.get_columns_for_view_mode(self.current_view_mode)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        """Initialise the user interface components."""
        self.setWindowTitle("View Historical Data")
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(0.1*screen.width(), 0.1*screen.height(), 0.8*screen.width(), 0.8*screen.height())

        layout = QVBoxLayout(self)
        
        # Add title with stock information
        title = QLabel(f"Historical Data - {self.stock.name} ({self.stock.yahoo_symbol})")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        # Create toolbar
        toolbar = QHBoxLayout()
        
        # View mode selector
        toolbar.addWidget(QLabel("View Mode:"))
        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItems(["Simple", "Detailed", "Custom"])
        self.view_mode_combo.currentTextChanged.connect(self.on_view_mode_changed)
        toolbar.addWidget(self.view_mode_combo)
        
        # Group visibility toggles
        self.group_toggles = {}
        for group_name in self.config['column_groups'].keys():
            display_name = group_name.replace('_', ' ').title()
            checkbox = QCheckBox(display_name)
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(self.on_group_visibility_changed)
            self.group_toggles[group_name] = checkbox
            toolbar.addWidget(checkbox)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Transaction management buttons
        button_bar = QHBoxLayout()
        
        # Left side buttons
        self.manage_data_btn = QPushButton("Manage Historical Data")
        self.manage_data_btn.clicked.connect(self.show_manage_dialog)
        button_bar.addWidget(self.manage_data_btn)

        # Right side buttons
        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self.show_settings_dialog)
        button_bar.addWidget(settings_btn)
        
        layout.addLayout(button_bar)

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

        # Apply filters button
        self.apply_filter_btn = QPushButton("Apply Filters")
        self.apply_filter_btn.clicked.connect(self.apply_filters)
        filter_layout.addWidget(self.apply_filter_btn)

        # Reset filters button
        self.reset_filter_btn = QPushButton("Reset Filters")
        self.reset_filter_btn.clicked.connect(self.reset_filters)
        filter_layout.addWidget(self.reset_filter_btn)

        layout.addLayout(filter_layout)

        # Main table
        self.table = QTableWidget()
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.resize(1200, 800)

    def load_data(self):
        """Fetch and display historical data combining prices, transactions and metrics."""
        try:
            # First, let's get the ordered fields from our visible columns
            fields = []
            for col in self.visible_columns:
                field = col['field']
                # Determine table prefix based on the field
                if field in ['open_price', 'high_price', 'low_price', 'close_price', 'volume']:
                    fields.append(f"hp.{field}")
                elif field in ['transaction_type', 'price', 'quantity']:
                    fields.append(f"t.{field}")
                else:
                    fields.append(f"pm.{field}")

            logger.debug(f"Selected fields in order: {fields}")

            # Build query using the ordered fields
            query = f"""
                SELECT 
                    {', '.join(fields)}
                FROM historical_prices hp
                LEFT JOIN transactions t 
                    ON hp.stock_id = t.stock_id 
                    AND date(hp.date) = date(t.date)
                LEFT JOIN portfolio_metrics pm 
                    ON hp.stock_id = pm.stock_id 
                    AND hp.date = pm.date
                WHERE hp.stock_id = ?
                ORDER BY hp.date DESC
            """

            logger.debug(f"Executing query with fields: {fields}")
            data = self.db_manager.fetch_all(query, (self.stock.id,))

            if data:
                # Log first row of data for debugging
                logger.debug(f"First row of data: {data[0]}")
                logger.debug(f"Number of columns in data: {len(data[0])}")
                logger.debug(f"Number of visible columns: {len(self.visible_columns)}")
                self.populate_table(data)
            else:
                logger.warning(f"No historical data found for stock_id {self.stock.id}")
                QMessageBox.warning(
                    self,
                    "No Data",
                    "No historical data available for this stock."
                )

        except Exception as e:
            logger.error(f"Error loading historical data: {str(e)}")
            logger.exception("Detailed traceback:")
            QMessageBox.warning(
                self,
                "Error Loading Data",
                f"Failed to load historical data: {str(e)}"
            )

    def load_view_config(self):
        """Load view configuration from YAML file."""
        try:
            import yaml
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
            print(config_path)
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)['historical_data_view']
        except Exception as e:
            logger.error(f"Error loading view configuration: {str(e)}")
            return None

    def get_columns_for_view_mode(self, mode):
        """Get list of visible columns based on view mode."""
        columns = []
        for group in self.config['column_groups'].values():
            for column in group:
                if mode == "Detailed" or (mode == "Simple" and column['simple_view']):
                    columns.append(column)
        return columns

    def apply_filters(self):
        """Apply date and view mode filters to the data."""
        try:
            date_from = self.date_from.date().toString("yyyy-MM-dd")
            date_to = self.date_to.date().toString("yyyy-MM-dd")
            
            # Build column list based on visible columns
            visible_columns = []
            for column in self.visible_columns:
                field = column['field']
                # Determine which table the field comes from
                if field in ['open_price', 'high_price', 'low_price', 'close_price', 'volume']:
                    visible_columns.append(f"hp.{field}")
                elif field in ['transaction_type', 'price', 'quantity']:
                    visible_columns.append(f"t.{field}")
                else:
                    visible_columns.append(f"pm.{field}")

            # Build query dynamically
            query = f"""
                SELECT {', '.join(visible_columns)}
                FROM historical_prices hp
                LEFT JOIN transactions t 
                    ON hp.stock_id = t.stock_id 
                    AND date(hp.date) = date(t.date)
                LEFT JOIN portfolio_metrics pm 
                    ON hp.stock_id = pm.stock_id 
                    AND hp.date = pm.date
                WHERE hp.stock_id = ? 
                AND hp.date BETWEEN ? AND ?
                ORDER BY hp.date DESC
            """

            data = self.db_manager.fetch_all(query, (self.stock.id, date_from, date_to))
            self.populate_table(data)

        except Exception as e:
            logger.error(f"Error applying filters: {str(e)}")
            QMessageBox.warning(
                self,
                "Filter Error",
                f"Failed to apply filters: {str(e)}"
            )

    def populate_table(self, data):
        """
        Populate the table with formatted data.
        
        Args:
            data: Raw data to display in the table
        """
        try:
            self.table.clear()
            self.table.setColumnCount(len(self.visible_columns))
            headers = [col['name'] for col in self.visible_columns]
            self.table.setHorizontalHeaderLabels(headers)

            if not data:
                self.table.setRowCount(0)
                return

            self.table.setRowCount(len(data))
            
            for row in range(len(data)):
                for col in range(len(self.visible_columns)):
                    if col < len(data[row]):
                        value = data[row][col]
                        if value is not None:
                            column_info = self.visible_columns[col]
                            formatted_value = self.format_value(value, column_info)
                            item = QTableWidgetItem(formatted_value)
                            
                            # Set alignment for numeric values
                            if isinstance(value, (int, float)):
                                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                            
                            # Set colors for P/L and Return values
                            if isinstance(value, (int, float)) and ('P/L' in column_info['name'] or 'Return' in column_info['name']):
                                color = Qt.darkGreen if value >= 0 else Qt.red
                                item.setForeground(color)
                            
                            self.table.setItem(row, col, item)

            # Auto-hide empty columns if enabled
            if self.config.get('auto_hide_empty_columns', True):
                self.hide_empty_columns()

            # Resize columns to content
            self.table.resizeColumnsToContents()

        except Exception as e:
            logger.error(f"Error populating table: {str(e)}")
            logger.error(f"Visible columns: {len(self.visible_columns)}, Data columns: {len(data[0]) if data else 0}")
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to populate table: {str(e)}"
            )

    def format_value(self, value, column_info):
        """
        Format a value based on column type and settings.
        
        Args:
            value: The value to format
            column_info: Dictionary containing column information
            
        Returns:
            str: Formatted value string
        """
        if value is None:
            return ""

        # Handle non-numeric values
        if isinstance(value, bool):
            return "Yes" if value else "No"
        
        if not isinstance(value, (int, float)):
            return str(value)

        try:
            # Determine column type and get corresponding format
            column_name = column_info['name']
            
            # Get format settings - add debug logging
            formats = self.config.get('column_formats', {})
            logger.debug(f"Current formats config: {formats}")
            
            # Determine format type and apply formatting
            if any(text in column_name for text in ['Open', 'High', 'Low', 'Close', 'Price',
                                                'Value', 'P/L', 'Cost', 'Dividend', 'DRP',
                                                'Total Return']):
                format_config = formats.get('price_formats', {'default': '.2f'})
                decimals = int(format_config['default'].split('.')[1][0])
                return f"${value:.{decimals}f}"
                
            elif '%' in column_name:
                format_config = formats.get('percentage_formats', {'default': '.2f'})
                decimals = int(format_config['default'].split('.')[1][0])
                return f"{value:.{decimals}f}%"
                
            else:  # Quantity format for all other numeric values
                format_config = formats.get('quantity_formats', {'default': '.4f'})
                decimals = int(format_config['default'].split('.')[1][0])
                return f"{value:.{decimals}f}"
                
        except Exception as e:
            logger.error(f"Error formatting value {value} for column {column_info['name']}: {str(e)}")
            logger.exception("Detailed traceback:")  # Add full traceback
            return str(value)

    def hide_empty_columns(self):
        """Hide columns that are empty or contain all zeros/ones based on settings."""
        for col in range(self.table.columnCount()):
            hide_column = True
            has_non_zero = False
            has_non_one = False
            
            for row in range(self.table.rowCount()):
                item = self.table.item(row, col)
                if item and item.text().strip():
                    hide_column = False
                    value_str = item.text().replace('$', '').replace(',', '').replace('%', '')
                    try:
                        value = float(value_str)
                        if value != 0:
                            has_non_zero = True
                        if value != 1:
                            has_non_one = True
                    except ValueError:
                        has_non_zero = True
                        has_non_one = True

            # Apply hiding rules
            if (hide_column or 
                (self.config.get('hide_all_zero_columns', True) and not has_non_zero) or
                (self.config.get('hide_all_one_columns', True) and not has_non_one)):
                self.table.hideColumn(col)

    def on_view_mode_changed(self, mode):
        """Handle changes to the view mode."""
        try:
            self.current_view_mode = mode
            self.visible_columns = self.get_columns_for_view_mode(mode)
            
            # If switching to custom mode, show the column selector dialog
            if mode == "Custom":
                self.show_column_selector()
            else:
                # Refresh the table with new column configuration
                self.apply_filters()
                
        except Exception as e:
            logger.error(f"Error changing view mode: {str(e)}")
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to change view mode: {str(e)}"
            )

    def on_group_visibility_changed(self):
        """Handle changes to group visibility toggles."""
        try:
            visible_groups = [
                group_name for group_name, checkbox in self.group_toggles.items()
                if checkbox.isChecked()
            ]
            
            # Update visible columns based on checked groups
            if self.current_view_mode != "Custom":
                self.visible_columns = [
                    column for group_name in visible_groups 
                    for column in self.config['column_groups'][group_name]
                    if self.current_view_mode == "Detailed" or column['simple_view']
                ]
                
                # Refresh the table
                self.apply_filters()
                
        except Exception as e:
            logger.error(f"Error updating group visibility: {str(e)}")

    def show_manage_dialog(self):
        """Show the manage historical data dialog."""
        dialog = ManageHistoricalDataDialog(self.stock, self.db_manager, self)
        if dialog.exec_():
            self.load_data()  # Refresh main view after managing data

    def show_settings_dialog(self):
        """Show dialog for configuring view settings."""
        try:
            dialog = ColumnSettingsDialog(self.config, self.visible_columns, self)
            if dialog.exec_():
                if dialog.save_settings_to_config():
                    # Update settings
                    self.config.update(dialog.get_settings())
                    # Refresh the view
                    self.apply_filters()
                    QMessageBox.information(
                        self,
                        "Success",
                        "Settings have been saved and applied."
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Warning",
                        "Failed to save settings to config file."
                    )
        except Exception as e:
            logger.error(f"Error showing settings dialog: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to update settings: {str(e)}"
            )

    def reset_filters(self):
        """Reset all filters to default values."""
        try:
            # Reset date range to defaults
            min_date = self.get_earliest_date()
            if min_date:
                self.date_from.setDate(min_date)
            self.date_to.setDate(QDate.currentDate())

            # Reset view mode to Simple
            self.view_mode_combo.setCurrentText("Simple")

            # Reset all group toggles to checked
            for checkbox in self.group_toggles.values():
                checkbox.setChecked(True)

            # Refresh the data
            self.apply_filters()

        except Exception as e:
            logger.error(f"Error resetting filters: {str(e)}")
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to reset filters: {str(e)}"
            )

    def get_earliest_date(self):
        """Get the earliest date from transactions or historical data."""
        try:
            result = self.db_manager.fetch_one("""
                SELECT MIN(date) FROM (
                    SELECT MIN(date) as date FROM transactions WHERE stock_id = ?
                    UNION
                    SELECT MIN(date) FROM historical_prices WHERE stock_id = ?
                )
            """, (self.stock.id, self.stock.id))
            
            if result and result[0]:
                return QDate.fromString(result[0].split()[0], "yyyy-MM-dd")
            return QDate.currentDate()

        except Exception as e:
            logger.error(f"Error getting earliest date: {str(e)}")
            return QDate.currentDate()
    
    def show_column_selector(self):
        """Show dialog for selecting custom columns."""
        try:
            dialog = ColumnSelectorDialog(self.config, self.visible_columns, self)
            if dialog.exec_():
                self.visible_columns = dialog.get_selected_columns()
                self.apply_filters()
                
        except Exception as e:
            logger.error(f"Error showing column selector: {str(e)}")

class ColumnSettingsDialog(QDialog):
    """
    Dialog for managing column display settings and formats.
    Combines both general settings and column-specific format settings in one dialog.
    """
    def __init__(self, config, visible_columns, parent=None):
        super().__init__(parent)
        self.config = config.copy()
        self.visible_columns = visible_columns
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Column Settings")
        self.setMinimumWidth(800)
        layout = QVBoxLayout(self)

        # Auto-hide settings
        auto_hide_group = QGroupBox("Display Settings")
        auto_hide_layout = QVBoxLayout()
        
        self.hide_empty = QCheckBox("Hide empty columns")
        self.hide_empty.setChecked(self.config.get('auto_hide_empty_columns', True))
        
        self.hide_zeros = QCheckBox("Hide columns with all zeros")
        self.hide_zeros.setChecked(self.config.get('hide_all_zero_columns', True))
        
        self.hide_ones = QCheckBox("Hide columns with all ones")
        self.hide_ones.setChecked(self.config.get('hide_all_one_columns', True))
        
        auto_hide_layout.addWidget(self.hide_empty)
        auto_hide_layout.addWidget(self.hide_zeros)
        auto_hide_layout.addWidget(self.hide_ones)
        auto_hide_group.setLayout(auto_hide_layout)
        layout.addWidget(auto_hide_group)

        # Column formats table
        format_group = QGroupBox("Column Format Settings")
        format_layout = QVBoxLayout()
        
        # Help text
        help_text = QLabel("Set decimal places for each column type. Changes apply to all columns of the same type.")
        help_text.setWordWrap(True)
        format_layout.addWidget(help_text)
        
        # Simple format settings table
        self.format_table = QTableWidget()
        self.format_table.setColumnCount(2)
        self.format_table.setHorizontalHeaderLabels(["Column Type", "Decimal Places"])
        
        # Add rows for each format type
        self.format_table.setRowCount(3)
        types = ["Price", "Percentage", "Quantity"]
        
        for i, type_name in enumerate(types):
            # Column type
            type_item = QTableWidgetItem(type_name)
            self.format_table.setItem(i, 0, type_item)
            
            # Decimal places spinbox
            decimals = QSpinBox()
            decimals.setRange(0, 8)
            
            # Get current default format
            format_key = f"{type_name.lower()}_formats"
            current_format = self.config.get('column_formats', {}).get(format_key, {}).get('default', '.2f')
            current_decimals = int(current_format.split('.')[1][0])
            decimals.setValue(current_decimals)
            
            self.format_table.setCellWidget(i, 1, decimals)
        
        self.format_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        format_layout.addWidget(self.format_table)
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)

        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_settings(self):
        """Return the current settings."""
        # General settings
        settings = {
            'auto_hide_empty_columns': self.hide_empty.isChecked(),
            'hide_all_zero_columns': self.hide_zeros.isChecked(),
            'hide_all_one_columns': self.hide_ones.isChecked()
        }
        
        # Format settings
        column_formats = {}
        format_types = ["price", "percentage", "quantity"]
        
        for i, format_type in enumerate(format_types):
            decimals = self.format_table.cellWidget(i, 1).value()
            column_formats[f"{format_type}_formats"] = {
                'default': f".{decimals}f",
                'custom': {}  # Simplified to use only default formats
            }
        
        settings['column_formats'] = column_formats
        return settings

    def save_settings_to_config(self):
        """Save settings directly to config file."""
        try:
            settings = self.get_settings()
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
            
            # Load existing config
            with open(config_path, 'r') as f:
                full_config = yaml.safe_load(f)
            
            # Update historical_data_view settings
            full_config['historical_data_view'].update(settings)
            
            # Write back to file
            with open(config_path, 'w') as f:
                yaml.dump(full_config, f, default_flow_style=False, sort_keys=False)
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving settings to config: {str(e)}")
            return False

class ColumnSelectorDialog(QDialog):
    """Dialog for selecting custom columns."""
    def __init__(self, config, current_columns, parent=None):
        super().__init__(parent)
        self.config = config
        self.current_columns = current_columns
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Select Columns")
        layout = QVBoxLayout(self)
        
        # Create a group box for each column group
        self.column_checks = {}
        for group_name, columns in self.config['column_groups'].items():
            group = QGroupBox(group_name.replace('_', ' ').title())
            group_layout = QVBoxLayout()
            
            for column in columns:
                checkbox = QCheckBox(column['name'])
                checkbox.setChecked(column in self.current_columns)
                self.column_checks[column['name']] = (checkbox, column)
                group_layout.addWidget(checkbox)
                
            group.setLayout(group_layout)
            layout.addWidget(group)
        
        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def get_selected_columns(self):
        """Return the list of selected columns."""
        return [
            column for _, (checkbox, column) in self.column_checks.items()
            if checkbox.isChecked()
        ]

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


class ManageHistoricalDataDialog(QDialog):
    """
    Dialog for managing historical data including transactions and data updates.
    Provides functionality to add/delete transactions and update historical data.
    """
    def __init__(self, stock, db_manager, parent=None):
        super().__init__(parent)
        self.stock = stock
        self.db_manager = db_manager
        self.init_ui()
        self.load_data()

    def init_ui(self):
        """Initialise the user interface."""
        self.setWindowTitle(f"Manage Historical Data - {self.stock.yahoo_symbol}")
        self.setMinimumWidth(800)
        layout = QVBoxLayout(self)

        # Instructions
        instructions = QLabel(
            "Manage historical data and transactions for this stock.\n"
            "• Add or delete transactions\n"
            "• Update historical price data from Yahoo Finance\n"
            "• View transaction history"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Transactions section
        trans_group = QGroupBox("Transactions")
        trans_layout = QVBoxLayout()

        # Transactions table
        self.trans_table = QTableWidget()
        self.trans_table.setColumnCount(5)
        self.trans_table.setHorizontalHeaderLabels([
            "Date", "Type", "Quantity", "Price", "Value"
        ])
        self.trans_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.trans_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.trans_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.trans_table.itemSelectionChanged.connect(self.update_button_states)
        trans_layout.addWidget(self.trans_table)

        # Transaction buttons
        button_layout = QHBoxLayout()
        
        self.add_trans_btn = QPushButton("Add Transaction")
        self.add_trans_btn.clicked.connect(self.add_transaction)
        button_layout.addWidget(self.add_trans_btn)

        self.delete_trans_btn = QPushButton("Delete Transaction")
        self.delete_trans_btn.clicked.connect(self.delete_transaction)
        self.delete_trans_btn.setEnabled(False)
        button_layout.addWidget(self.delete_trans_btn)

        trans_layout.addLayout(button_layout)
        trans_group.setLayout(trans_layout)
        layout.addWidget(trans_group)

        # Historical data section
        data_group = QGroupBox("Historical Data")
        data_layout = QVBoxLayout()

        # Last update info
        self.last_update_label = QLabel()
        data_layout.addWidget(self.last_update_label)

        # Update button
        self.update_data_btn = QPushButton("Update Historical Data from Yahoo")
        self.update_data_btn.clicked.connect(self.update_historical_data)
        data_layout.addWidget(self.update_data_btn)

        data_group.setLayout(data_layout)
        layout.addWidget(data_group)

        # Dialog buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Close)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def load_data(self):
        """Load transaction data into the table."""
        try:
            transactions = self.db_manager.get_transactions_for_stock(self.stock.id)
            self.trans_table.setRowCount(len(transactions))

            for row, trans in enumerate(transactions):
                # Date
                date_item = QTableWidgetItem(trans[1].split()[0])  # Get date part only
                self.trans_table.setItem(row, 0, date_item)

                # Type
                type_item = QTableWidgetItem(trans[4])
                self.trans_table.setItem(row, 1, type_item)

                # Quantity
                quantity = float(trans[2])
                quantity_item = QTableWidgetItem(f"{quantity:,.4f}")
                quantity_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.trans_table.setItem(row, 2, quantity_item)

                # Price
                price = float(trans[3])
                price_item = QTableWidgetItem(f"${price:,.2f}")
                price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.trans_table.setItem(row, 3, price_item)

                # Value
                value = quantity * price
                value_item = QTableWidgetItem(f"${value:,.2f}")
                value_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.trans_table.setItem(row, 4, value_item)

            # Update last update info
            last_price = self.db_manager.fetch_one("""
                SELECT date FROM historical_prices 
                WHERE stock_id = ? 
                ORDER BY date DESC LIMIT 1
            """, (self.stock.id,))
            
            if last_price:
                self.last_update_label.setText(f"Last data update: {last_price[0]}")
            else:
                self.last_update_label.setText("No historical data available")

        except Exception as e:
            logger.error(f"Error loading transaction data: {str(e)}")
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to load transaction data: {str(e)}"
            )

    def update_button_states(self):
        """Enable/disable buttons based on selection state."""
        self.delete_trans_btn.setEnabled(bool(self.trans_table.selectedItems()))

    def show_add_transaction_dialog(self):
        """Show dialog to add a new transaction."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Transaction")
        layout = QFormLayout(dialog)

        # Date input
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDate(datetime.now().date())
        layout.addRow("Date:", date_edit)

        # Transaction type
        type_combo = QComboBox()
        type_combo.addItems(["BUY", "SELL"])
        layout.addRow("Type:", type_combo)

        # Quantity input
        quantity_spin = QDoubleSpinBox()
        quantity_spin.setRange(0.0001, 1000000)
        quantity_spin.setDecimals(4)
        quantity_spin.setValue(1)
        layout.addRow("Quantity:", quantity_spin)

        # Price input
        price_spin = QDoubleSpinBox()
        price_spin.setRange(0.01, 1000000)
        price_spin.setDecimals(2)
        price_spin.setPrefix("$")
        price_spin.setValue(1.00)
        layout.addRow("Price:", price_spin)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec_():
            return (
                date_edit.date().toPython(),
                type_combo.currentText(),
                quantity_spin.value(),
                price_spin.value()
            )
        return None
    
    def add_transaction(self):
        """Handle adding a new transaction."""
        result = self.show_add_transaction_dialog()
        if result:
            date, trans_type, quantity, price = result
            try:
                # Verify sufficient shares for sells
                if trans_type == "SELL":
                    shares_owned = self.db_manager.fetch_one("""
                        SELECT SUM(CASE 
                            WHEN transaction_type = 'BUY' THEN quantity 
                            WHEN transaction_type = 'SELL' THEN -quantity 
                        END)
                        FROM transactions
                        WHERE stock_id = ? AND date <= ?
                    """, (self.stock.id, date))
                    
                    total_shares = shares_owned[0] if shares_owned[0] else 0
                    
                    if quantity > total_shares:
                        QMessageBox.warning(
                            self,
                            "Invalid Transaction",
                            f"Cannot sell {quantity} shares. Only {total_shares:.4f} shares owned on {date}."
                        )
                        return

                # Add transaction
                transaction = [(self.stock.id, date, quantity, price, trans_type)]
                self.db_manager.bulk_insert_transactions(transaction)
                
                # Refresh display
                self.load_data()
                QMessageBox.information(self, "Success", "Transaction added successfully.")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add transaction: {str(e)}")

    def delete_transaction(self):
        """Delete the selected transaction."""
        selected_row = self.trans_table.currentRow()
        if selected_row < 0:
            return

        try:
            date = self.trans_table.item(selected_row, 0).text()
            trans_type = self.trans_table.item(selected_row, 1).text()
            quantity = float(self.trans_table.item(selected_row, 2).text().replace(',', ''))
            price = float(self.trans_table.item(selected_row, 3).text().replace('$', '').replace(',', ''))

            confirm = QMessageBox.question(
                self,
                "Confirm Deletion",
                f"Delete this transaction?\n\n"
                f"Date: {date}\n"
                f"Type: {trans_type}\n"
                f"Quantity: {quantity:,.4f}\n"
                f"Price: ${price:,.2f}",
                QMessageBox.Yes | QMessageBox.No
            )

            if confirm == QMessageBox.Yes:
                self.db_manager.execute("""
                    DELETE FROM transactions 
                    WHERE stock_id = ? AND date = ? AND transaction_type = ?
                    AND quantity = ? AND price = ?
                """, (self.stock.id, date, trans_type, quantity, price))
                
                self.db_manager.conn.commit()
                self.load_data()
                QMessageBox.information(self, "Success", "Transaction deleted successfully.")

        except Exception as e:
            self.db_manager.conn.rollback()
            QMessageBox.critical(self, "Error", f"Failed to delete transaction: {str(e)}")

    def update_historical_data(self):
        """Update historical price data from Yahoo Finance."""
        try:
            result = HistoricalDataCollector.process_and_store_historical_data(
                self.db_manager,
                self.stock.id,
                self.stock.yahoo_symbol
            )
            
            if result:
                self.load_data()
                QMessageBox.information(
                    self,
                    "Success",
                    "Historical data updated successfully."
                )
            else:
                QMessageBox.warning(
                    self,
                    "No Updates",
                    "No new historical data was available."
                )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to update historical data: {str(e)}"
            )