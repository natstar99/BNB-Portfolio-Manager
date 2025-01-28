# File: controllers/settings_controller.py

import logging
from views.settings_view import SettingsView
import yaml

logger = logging.getLogger(__name__)

class SettingsController:
    """
    Controller for managing application settings.
    Handles currency settings for portfolios and interaction with the database.
    """
    
    def __init__(self, db_manager):
        """
        Initialise the settings controller.
        
        Args:
            db_manager: Database manager instance for data operations
        """
        self.db_manager = db_manager
        self.view = SettingsView()
        self.current_portfolio = None
        self._load_config()
        self._set_initial_pl_method()
        
        # Connect signals
        self.view.save_button.clicked.connect(self.save_changes)
        
        # Load supported currencies immediately
        self._load_supported_currencies()

    def set_portfolio(self, portfolio):
        """
        Set the current portfolio and update the view.
        
        Args:
            portfolio: The portfolio instance to manage settings for
        """
        self.current_portfolio = portfolio
        if portfolio:
            # Load current currency setting
            result = self.db_manager.fetch_one(
                "SELECT portfolio_currency FROM portfolios WHERE id = ?",
                (portfolio.id,)
            )
            if result:
                self.view.set_current_currency(result[0])
        else:
            self.view.save_button.setEnabled(False)

    def _load_supported_currencies(self):
        """Load and display the list of supported currencies."""
        try:
            currencies = self.db_manager.fetch_all(
                "SELECT code, name, symbol FROM supported_currencies WHERE is_active = 1"
            )
            self.view.set_supported_currencies(currencies)
            
        except Exception as e:
            logger.error(f"Error loading supported currencies: {str(e)}")
            self.view.show_error("Failed to load supported currencies")

    def _load_config(self):
        """Load configuration from config.yaml"""
        try:
            with open('config.yaml', 'r') as f:
                self.config = yaml.safe_load(f) or {}
            if 'profit_loss_calculations' not in self.config:
                self.config['profit_loss_calculations'] = {
                    'default_method': 'fifo',
                    'available_methods': ['fifo', 'lifo', 'hifo']
                }
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            self.config = {
                "profit_loss_calculations": {
                    "default_method": "fifo",
                    "available_methods": ['fifo', 'lifo', 'hifo']
                }
            }

    def _set_initial_pl_method(self):
        """Set initial P/L calculation method from config"""
        method = self.config['profit_loss_calculations']['default_method']
        self.view.set_current_pl_method(method)

    def save_changes(self):
        """Save currency and P/L method settings"""
        if not self.current_portfolio:
            return
            
        try:
            # Save currency settings
            new_currency = self.view.get_selected_currency()
            self.db_manager.execute(
                "UPDATE portfolios SET portfolio_currency = ? WHERE id = ?",
                (new_currency, self.current_portfolio.id)
            )
            
            # Save P/L method while preserving other config
            new_method = self.view.get_selected_pl_method().lower()
            
            # Load existing config
            with open('config.yaml', 'r') as f:
                config = yaml.safe_load(f) or {}
                
            # Only update the profit_loss_calculations section
            if 'profit_loss_calculations' not in config:
                config['profit_loss_calculations'] = {}
                
            config['profit_loss_calculations']['default_method'] = new_method
            
            # Write back the config preserving order and style
            with open('config.yaml', 'w') as f:
                yaml.dump(
                    config, 
                    f, 
                    sort_keys=False,  # Don't sort the keys
                    default_flow_style=False,  # Use block style for main structure
                    allow_unicode=True,  # Preserve unicode characters
                    width=float("inf"),  # Prevent line wrapping
                    indent=2  # Maintain indentation
                )
            
            self.db_manager.conn.commit()
            self.view.save_button.setEnabled(False)
            self.view.show_success("Settings updated successfully")
            
        except Exception as e:
            logger.error(f"Error updating settings: {str(e)}")
            self.view.show_error("Failed to update settings")

    def get_view(self):
        """
        Get the settings view instance.
        
        Returns:
            SettingsView: The settings view instance
        """
        return self.view