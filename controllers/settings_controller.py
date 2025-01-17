# File: controllers/settings_controller.py

import logging
from views.settings_view import SettingsView

logger = logging.getLogger(__name__)

class SettingsController:
    """
    Controller for managing application settings.
    Handles currency settings for portfolios and interaction with the database.
    """
    
    def __init__(self, db_manager):
        """
        Initialize the settings controller.
        
        Args:
            db_manager: Database manager instance for data operations
        """
        self.db_manager = db_manager
        self.view = SettingsView()
        self.current_portfolio = None
        
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

    def save_changes(self):
        """Save the current currency settings to the database."""
        if not self.current_portfolio:
            return
            
        try:
            new_currency = self.view.get_selected_currency()
            self.db_manager.execute(
                "UPDATE portfolios SET portfolio_currency = ? WHERE id = ?",
                (new_currency, self.current_portfolio.id)
            )
            self.db_manager.conn.commit()
            
            logger.info(f"Updated portfolio {self.current_portfolio.id} currency to {new_currency}")
            self.view.save_button.setEnabled(False)
            self.view.show_success("Currency settings updated successfully")
            
        except Exception as e:
            logger.error(f"Error updating portfolio currency: {str(e)}")
            self.view.show_error("Failed to update currency setting")

    def get_view(self):
        """
        Get the settings view instance.
        
        Returns:
            SettingsView: The settings view instance
        """
        return self.view