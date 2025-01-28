# File: views/settings_view.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QComboBox, QPushButton, QFrame, QGroupBox,
                              QMessageBox)
from PySide6.QtCore import Signal
import yaml

class SettingsView(QWidget):
    """
    Settings view for managing portfolio currency settings.
    Allows users to view and change the default currency for their portfolio.
    """
    currency_changed = Signal(str)  # Emits when currency is changed

    def __init__(self):
        super().__init__()
        self.init_ui()
        self._setup_connections()

    def init_ui(self):
        """Initialise the user interface components."""
        layout = QVBoxLayout(self)
        
        # Title and description
        title_label = QLabel("Portfolio Settings")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)
        
        description = QLabel("Manage currency settings for your portfolio.")
        description.setWordWrap(True)
        layout.addWidget(description)

        # Currency Settings Section
        currency_group = QGroupBox("Currency Settings")
        currency_layout = QVBoxLayout()

        # Currency selection
        currency_box = QHBoxLayout()
        self.currency_label = QLabel("Default Currency:")
        self.currency_combo = QComboBox()
        currency_box.addWidget(self.currency_label)
        currency_box.addWidget(self.currency_combo)
        currency_box.addStretch()
        currency_layout.addLayout(currency_box)

        # Info about currency
        currency_info = QLabel(
            "The default currency will be used for all portfolio calculations. "
            "Values from stocks in different currencies will be converted automatically."
        )
        currency_info.setWordWrap(True)
        currency_info.setStyleSheet("color: #666;")
        currency_layout.addWidget(currency_info)

        # Supported currencies section
        currency_layout.addWidget(QLabel("Supported Currencies:"))
        self.currency_list = QLabel()
        self.currency_list.setWordWrap(True)
        self.currency_list.setStyleSheet("padding: 10px; background-color: #f0f0f0;")
        currency_layout.addWidget(self.currency_list)

        currency_group.setLayout(currency_layout)
        layout.addWidget(currency_group)

        # Profit/Loss Settings Section
        pl_group = QGroupBox("Profit/Loss Settings")
        pl_layout = QVBoxLayout()

        # Profit/Loss calculation method selection
        pl_box = QHBoxLayout()
        self.pl_label = QLabel("Profit/Loss Calculation Method:")
        self.pl_combo = QComboBox()
        
        # Add the calculation methods to the combo box
        pl_methods = [
            ("FIFO", "First In, First Out"),
            ("LIFO", "Last In, First Out"),
            ("HIFO", "Highest In, First Out")
        ]
        for code, name in pl_methods:
            self.pl_combo.addItem(f"{code} - {name}", code)
        
        pl_box.addWidget(self.pl_label)
        pl_box.addWidget(self.pl_combo)
        pl_box.addStretch()
        pl_layout.addLayout(pl_box)

        # Info about profit/loss calculation methods
        pl_info = QLabel(
            "Select your preferred method for calculating realised profit/loss:\n\n"
            "FIFO (First In, First Out):\n"
            "• Assumes the first shares you bought are the first ones sold\n"
            "• Best for long-term investors and most common tax reporting method\n"
            "• Generally accepted by tax authorities in many jurisdictions\n\n"
            "LIFO (Last In, First Out):\n"
            "• Assumes the most recently purchased shares are sold first\n"
            "• Useful for analysing short-term trading performance\n"
            "• May not be accepted for tax purposes in some jurisdictions\n\n"
            "HIFO (Highest In, First Out):\n"
            "• Sells shares with the highest purchase price first\n"
            "• Minimises capital gains in taxable accounts\n"
            "• Useful for tax-loss harvesting strategies"
        )
        pl_info.setWordWrap(True)
        pl_info.setStyleSheet("color: #666; padding: 10px; background-color: #f0f0f0;")
        pl_layout.addWidget(pl_info)

        pl_group.setLayout(pl_layout)
        layout.addWidget(pl_group)

        # Save button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.save_button = QPushButton("Save Changes")
        self.save_button.setEnabled(False)
        button_layout.addWidget(self.save_button)
        layout.addLayout(button_layout)

        layout.addStretch()

    def _setup_connections(self):
        """Setup signal connections."""
        self.currency_combo.currentIndexChanged.connect(self._on_currency_changed)
        self.pl_combo.currentIndexChanged.connect(self._on_pl_method_changed)

    def _on_currency_changed(self):
        """Handle currency selection changes."""
        self.save_button.setEnabled(True)

    def set_supported_currencies(self, currencies):
        """
        Update the list of supported currencies.
        
        Args:
            currencies: List of tuples [(code, name, symbol), ...]
        """
        self.currency_combo.clear()
        currency_texts = []
        
        for code, name, symbol in currencies:
            self.currency_combo.addItem(f"{code} - {name} ({symbol})", code)
            currency_texts.append(f"{code} - {name} ({symbol})")
        
        self.currency_list.setText("\n".join(currency_texts))

    def set_current_currency(self, currency_code):
        """
        Set the currently selected currency.
        
        Args:
            currency_code: The currency code to select
        """
        index = self.currency_combo.findData(currency_code)
        if index >= 0:
            self.currency_combo.setCurrentIndex(index)
            self.save_button.setEnabled(False)

    def get_selected_currency(self):
        """
        Get the currently selected currency code.
        
        Returns:
            str: The selected currency code
        """
        return self.currency_combo.currentData()
    
    def _on_pl_method_changed(self):
        """
        Handle profit/loss calculation method changes.
        Enables the save button and validates against current config.
        """
        try:
            with open('config.yaml', 'r') as f:
                config = yaml.safe_load(f)
                pl_config = config.get('profit_loss_calculations', {})
                current_method = pl_config.get('default_method', 'fifo')
                available_methods = pl_config.get('available_methods', ['fifo', 'lifo', 'hifo'])
                
                selected_method = self.get_selected_pl_method().lower()
                
                # Validate selected method is available
                if selected_method not in available_methods:
                    self.show_error(f"Selected method {selected_method} is not in available methods")
                    return
                
                # Only enable save button if the selection has changed
                if current_method != selected_method:
                    self.save_button.setEnabled(True)
                    
                    # Show warning if changing from existing method
                    if current_method:
                        self.show_warning(
                            "Changing the profit/loss calculation method will affect "
                            "how future transactions are calculated. Existing calculations "
                            "will not be automatically updated."
                        )
        except FileNotFoundError:
            self.show_error("Configuration file not found. Using default settings.")
        except yaml.YAMLError as e:
            self.show_error(f"Error reading configuration: {str(e)}")


    def set_current_pl_method(self, method_code, silent=True):
        """
        Set the currently selected profit/loss calculation method.
        
        Args:
            method_code (str): The method code to select (FIFO, LIFO, or HIFO)
            silent (bool): If True, don't show any messages during initial setup
        """
        try:
            # Convert method_code to lowercase for consistency
            method_code = method_code.lower()
            
            # Update the combo box selection
            index = self.pl_combo.findData(method_code.upper())
            if index >= 0:
                self.pl_combo.blockSignals(True)  # Temporarily block signals
                self.pl_combo.setCurrentIndex(index)
                self.pl_combo.blockSignals(False)  # Re-enable signals
                self.save_button.setEnabled(False)
            
            # Only update config file if not in silent mode
            if not silent:
                # Update the configuration file
                with open('config.yaml', 'r') as f:
                    config = yaml.safe_load(f) or {}
                
                if 'profit_loss_calculations' not in config:
                    config['profit_loss_calculations'] = {
                        'default_method': 'fifo',
                        'available_methods': ['fifo', 'lifo', 'hifo']
                    }
                
                # Validate method is in available methods
                available_methods = config['profit_loss_calculations'].get('available_methods', ['fifo', 'lifo', 'hifo'])
                if method_code not in available_methods:
                    self.show_error(f"Method {method_code} is not in available methods: {available_methods}")
                    return
                
                # Update default method while preserving available_methods
                config['profit_loss_calculations']['default_method'] = method_code
                
                with open('config.yaml', 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)  # Use block style for YAML
                    
                self.show_success(f"Profit/Loss calculation method updated to {method_code.upper()}")
                
        except FileNotFoundError:
            if not silent:
                self.show_error("Configuration file not found. Cannot save settings.")
        except yaml.YAMLError as e:
            if not silent:
                self.show_error(f"Error updating configuration: {str(e)}")
        except Exception as e:
            if not silent:
                self.show_error(f"Unexpected error: {str(e)}")

    def get_selected_pl_method(self):
        """
        Get the currently selected profit/loss calculation method code.
        
        Returns:
            str: The selected method code (FIFO, LIFO, or HIFO)
        """
        return self.pl_combo.currentData()

    def show_warning(self, message):
        """
        Display a warning message to the user.
        
        Args:
            message (str): The warning message to display
        """
        QMessageBox.warning(self, "Warning", message)

    def show_success(self, message):
        """
        Display a success message to the user.
        
        Args:
            message (str): The success message to display
        """
        QMessageBox.information(self, "Success", message)

    def show_error(self, message):
        """
        Display an error message using QMessageBox.
        
        Args:
            message (str): The error message to display
        """
        QMessageBox.warning(self, "Error", message)