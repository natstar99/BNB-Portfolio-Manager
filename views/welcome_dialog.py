# File: views/welcome_dialog.py

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QLineEdit, QPushButton, QWizard, QWizardPage,
                              QMessageBox, QWidget, QGroupBox, QComboBox,
                              QRadioButton)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap
from controllers.import_transactions_controller import ImportTransactionsController
import os
import yaml

class WelcomeDialog(QWizard):
    """
    A wizard-style welcome dialog that guides new users through initial setup.
    Includes portfolio creation and settings configuration.
    """

    # Add a signal to tell the future what to do
    import_requested = Signal(str)  # Will emit portfolio name


    def __init__(self, portfolio_controller, settings_controller, parent=None):
        super().__init__(parent)
        self.portfolio_controller = portfolio_controller
        self.settings_controller = settings_controller
        self.current_portfolio = None  # Store the created portfolio at wizard level
        self.init_ui()
        
    def init_ui(self):

        # Connect signals
        self.finished.connect(self.on_wizard_finished)

        # Initialise the wizard interface
        self.setWindowTitle("Welcome to BNB Portfolio Manager")
        self.setWizardStyle(QWizard.ModernStyle)
        
        # Configure wizard buttons
        self.setButtonText(QWizard.NextButton, "Continue")
        self.setButtonText(QWizard.FinishButton, "Get Started!")
        
        # Add pages
        self.welcome_page = WelcomePage()
        self.portfolio_page = CreatePortfolioPage(self.portfolio_controller)
        self.settings_page = SettingsPage(self.settings_controller)
        self.import_page = ImportOptionsPage()
        
        self.addPage(self.welcome_page)
        self.addPage(self.portfolio_page)
        self.addPage(self.settings_page)
        self.addPage(self.import_page)
        
        # Set minimum size
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

    def on_wizard_finished(self, result):
        """Handle wizard completion."""
        if result == QWizard.Accepted and self.import_page.should_import:
            # Emit signal with the portfolio name
            portfolio_name = self.current_portfolio.name
            self.import_requested.emit(portfolio_name)

class WelcomePage(QWizardPage):
    """
    The initial welcome page introducing users to the application.
    """
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """Initialise the welcome page interface."""
        layout = QVBoxLayout()
        
        # Add logo
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bnb_logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled_pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(logo_label)
        
        # Welcome title
        title = QLabel("Welcome to BNB Portfolio Manager!")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Welcome message
        message = QLabel(
            "Thank you for choosing BNB Portfolio Manager!\n\n"
            "This wizard will help you set up your first portfolio and configure "
            "your settings. We'll guide you through:\n\n"
            "• Creating your first portfolio\n"
            "• Setting up your preferred currency\n"
            "• Configuring profit/loss calculation methods\n\n"
            "Click 'Continue' to get started!"
        )
        message.setWordWrap(True)
        message.setAlignment(Qt.AlignCenter)
        layout.addWidget(message)
        
        layout.addStretch()
        self.setLayout(layout)

class CreatePortfolioPage(QWizardPage):
    """
    Page for creating the user's first portfolio.
    Reuses functionality from the PortfolioController.
    """
    def __init__(self, portfolio_controller):
        super().__init__()
        self.portfolio_controller = portfolio_controller
        self.init_ui()
        
    def init_ui(self):
        """Initialise the portfolio creation page interface."""
        self.setTitle("Create Your First Portfolio")
        self.setSubTitle("Enter a name for your portfolio to get started.")
        
        layout = QVBoxLayout()
        
        # Portfolio name input
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter Portfolio Name")
        layout.addWidget(self.name_input)
        
        # Register field for validation
        self.registerField("portfolio_name*", self.name_input)
        
        # Explanation text
        explanation = QLabel(
            "Your portfolio name should be something meaningful to you. "
            "You can create additional portfolios later if needed."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        
        layout.addStretch()
        self.setLayout(layout)

    def validatePage(self):
        """Validate and create the portfolio."""
        portfolio_name = self.name_input.text().strip()
        
        try:
            # Create the portfolio
            portfolio = self.portfolio_controller.create_portfolio(portfolio_name)
            # Store it in the wizard
            wizard = self.wizard()
            if wizard:
                wizard.current_portfolio = portfolio
                # Update settings controller with the new portfolio
                wizard.settings_controller.set_portfolio(portfolio)
            return True
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to create portfolio: {str(e)}"
            )
            return False

class SettingsPage(QWizardPage):
    """
    Page for configuring initial portfolio settings.
    Creates a similar interface to the main settings view.
    """
    def __init__(self, settings_controller):
        super().__init__()
        self.settings_controller = settings_controller
        self.init_ui()

    def init_ui(self):
        """Initialise the settings page interface."""
        self.setTitle("Configure Your Settings")
        self.setSubTitle("Set up your preferred currency and calculation methods.")
        
        layout = QVBoxLayout()

        # Currency Settings Section
        currency_group = QGroupBox("Currency Settings")
        currency_layout = QVBoxLayout()

        # Currency selection
        currency_box = QHBoxLayout()
        self.currency_label = QLabel("Default Currency:")
        self.currency_combo = QComboBox()
        
        # Load currencies immediately
        currencies = self.settings_controller.db_manager.fetch_all(
            "SELECT code, name, symbol FROM supported_currencies WHERE is_active = 1"
        )
        
        for code, name, symbol in currencies:
            self.currency_combo.addItem(f"{code} - {name} ({symbol})", code)
        
        # Set default currency to AUD
        aud_index = self.currency_combo.findData("AUD")
        if aud_index >= 0:
            self.currency_combo.setCurrentIndex(aud_index)
        
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
        currency_layout.addWidget(currency_info)

        currency_group.setLayout(currency_layout)
        layout.addWidget(currency_group)

        # Profit/Loss Settings Section
        pl_group = QGroupBox("Profit/Loss Settings")
        pl_layout = QVBoxLayout()

        pl_box = QHBoxLayout()
        self.pl_label = QLabel("Profit/Loss Calculation Method:")
        self.pl_combo = QComboBox()
        
        # Add the calculation methods
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

        # Info about methods
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
        pl_layout.addWidget(pl_info)

        pl_group.setLayout(pl_layout)
        layout.addWidget(pl_group)

        layout.addStretch()
        self.setLayout(layout)

    def validatePage(self):
        """Save settings when finishing the wizard."""
        try:
            # Get selected values
            currency_code = self.currency_combo.currentData()
            pl_method = self.pl_combo.currentData()
            
            # Get portfolio from wizard
            wizard = self.wizard()
            if wizard and wizard.current_portfolio:
                portfolio_id = wizard.current_portfolio.id
                
                # Update database currency setting
                self.settings_controller.db_manager.execute(
                    "UPDATE portfolios SET portfolio_currency = ? WHERE id = ?",
                    (currency_code, portfolio_id)
                )
                self.settings_controller.db_manager.conn.commit()  # Ensure changes are committed
                
            else:
                raise ValueError("No portfolio available for settings update")
            
            # Update config file for P/L method
            try:
                with open('config.yaml', 'r') as f:
                    config = yaml.safe_load(f) or {}
                
                if 'profit_loss_calculations' not in config:
                    config['profit_loss_calculations'] = {}
                
                config['profit_loss_calculations'].update({
                    'default_method': pl_method.lower(),
                    'available_methods': ['fifo', 'lifo', 'hifo']
                })
                
                with open('config.yaml', 'w') as f:
                    yaml.dump(config, f, default_flow_style=False, sort_keys=False)
                print("Updated config.yaml with P/L method")
                
            except Exception as e:
                print(f"Error updating config file: {str(e)}")
                raise
                
            return True
                
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to save settings: {str(e)}"
            )
            return False

class ImportOptionsPage(QWizardPage):
    """
    Page for asking users if they want to import transactions right away.
    Shown after settings configuration.
    """
    def __init__(self, import_controller=None):
        super().__init__()
        self.import_controller = import_controller
        self.should_import = False  # Flag to track user's choice
        self.init_ui()
        
    def init_ui(self):
        """Initialise the import options page interface."""
        self.setTitle("Import Transactions")
        self.setSubTitle("Would you like to import your transactions now?")
        
        layout = QVBoxLayout()
        
        # Explanation text
        explanation = QLabel(
            "You can import your transaction history from a CSV or Excel file.\n\n"
            "This will help you track your portfolio's performance from day one.\n"
            "You can always import transactions later if you prefer."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        
        # Yes/No radio buttons
        self.yes_radio = QRadioButton("Yes, import transactions now")
        self.no_radio = QRadioButton("No, I'll do it later")
        self.no_radio.setChecked(True)  # Default to "No"
        
        layout.addWidget(self.yes_radio)
        layout.addWidget(self.no_radio)
        
        layout.addStretch()
        self.setLayout(layout)

    def validatePage(self):
        """Handle the user's choice."""
        self.should_import = self.yes_radio.isChecked()
        return True