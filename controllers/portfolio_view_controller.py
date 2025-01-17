# File: controllers/portfolio_view_controller.py

from PySide6.QtWidgets import QMessageBox, QProgressDialog
from PySide6.QtCore import Qt
from views.my_portfolio_view import MyPortfolioView
from models.portfolio import Portfolio
from models.stock import Stock
from models.transaction import Transaction
from datetime import datetime
import yfinance as yf
import logging
import pandas as pd
from views.verify_transactions_view import VerifyTransactionsDialog
from views.historical_data_view import HistoricalDataDialog
from utils.historical_data_collector import HistoricalDataCollector
from utils.yahoo_finance_service import YahooFinanceService
logger = logging.getLogger(__name__)

class PortfolioViewController:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.view = MyPortfolioView()
        self.current_portfolio = None
        self.historical_collector = HistoricalDataCollector()
        
        # Connect signals
        self.view.view_history.connect(self.show_history)
        self.view.refresh_data.connect(self.refresh_data)
        self.view.manage_portfolio.connect(self.show_portfolio_manager)

    def set_portfolio(self, portfolio: Portfolio):
        """Set the current portfolio and load its data"""
        self.current_portfolio = portfolio
        self.current_portfolio.load_stocks()
        self.update_view()

    def update_view(self):
        """Update the view with current portfolio data"""
        if self.current_portfolio:
            self.view.update_portfolio(self.current_portfolio)

    def show_history(self, yahoo_symbol):
        """Display historical data for a selected stock"""
        if self.current_portfolio:
            stock = self.current_portfolio.get_stock(yahoo_symbol)
            if stock:
                dialog = HistoricalDataDialog(stock, self.db_manager, self.view)
                dialog.exec_()

    def refresh_data(self):
        """Update current prices for all stocks"""
        if not self.current_portfolio:
            return

        # Create progress dialog
        progress = QProgressDialog(
            "Updating stock prices...", 
            "Cancel",
            0, 
            len(self.current_portfolio.stocks),
            self.view
        )
        progress.setWindowModality(Qt.WindowModal)

        for i, stock in enumerate(self.current_portfolio.stocks.values()):
            if progress.wasCanceled():
                break

            try:
                # Use YahooFinanceService to verify stock and get info
                result = YahooFinanceService.verify_stock(stock.yahoo_symbol)
                
                if result['error']:
                    raise Exception(result['error'])
                    
                # Update stock price and currency in database
                self.db_manager.execute("""
                    UPDATE stocks 
                    SET current_price = ?,
                        currency = ?,
                        last_updated = ?
                    WHERE id = ?
                """, (
                    result['current_price'],
                    result['currency'],
                    datetime.now().replace(microsecond=0),
                    stock.id
                ))
                
                # Update stock object
                stock.current_price = result['current_price']
                
            except Exception as e:
                logger.error(f"Failed to update price for {stock.yahoo_symbol}: {str(e)}")
                QMessageBox.warning(
                    self.view,
                    "Update Failed",
                    f"Failed to update price for {stock.yahoo_symbol}: {str(e)}"
                )

            progress.setValue(i + 1)

        progress.close()

        # Refresh portfolio after updates
        self.current_portfolio.load_stocks()
        self.update_view()
        QMessageBox.information(self.view, "Update Complete", "Portfolio prices have been updated.")

    def show_portfolio_manager(self):
        """Open the verification dialog for the portfolio and refresh view after"""
        if not self.current_portfolio:
            return
                
        # Get just the instrument codes
        instruments = self.db_manager.fetch_all("""
            SELECT DISTINCT instrument_code 
            FROM stocks 
            JOIN portfolio_stocks ps ON stocks.id = ps.stock_id
            WHERE ps.portfolio_id = ?
        """, (self.current_portfolio.id,))
                
        if instruments:
            # Create DataFrame with just instrument codes
            holdings_data = pd.DataFrame({
                'Instrument Code': [code[0] for code in instruments]
            })
            dialog = VerifyTransactionsDialog(
                transactions_data=holdings_data, 
                db_manager=self.db_manager,
                parent=self.view,
                portfolio_id=self.current_portfolio.id
            )
            dialog.portfolio_id = self.current_portfolio.id
            dialog.verification_completed.connect(self.on_verification_completed)
            if dialog.exec_():
                # Refresh the portfolio data after dialog closes
                self.current_portfolio.load_stocks()
                self.update_view()

    def get_view(self):
        """Return the view instance"""
        return self.view
    
    def on_verification_completed(self, verification_results):
        """Handle verification results and collect historical data."""
        self.historical_collector.process_verification_results(
            verification_results, 
            parent_widget=self.view
        )
        self.current_portfolio.load_stocks()
        self.update_view()