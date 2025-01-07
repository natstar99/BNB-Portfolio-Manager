# File: views/settings_view.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QComboBox, QPushButton, QFrame, QGroupBox,
                              QMessageBox)
from PySide6.QtCore import Signal

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
        """Initialize the user interface components."""
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

    def show_error(self, message):
        """
        Display an error message to the user.
        
        Args:
            message: The error message to display
        """
        QMessageBox.warning(self, "Error", message)

    def show_success(self, message):
        """
        Display a success message to the user.
        
        Args:
            message: The success message to display
        """
