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
        """
        Updates all stock data in the current portfolio using historical data collector.
        This method provides a comprehensive update including:
        - Historical price data from earliest transaction
        - Current prices
        - Currency conversions if needed
        - Portfolio metrics recalculation
        """
        if not self.current_portfolio:
            return

        # Create progress dialog for user feedback
        progress = QProgressDialog(
            "Updating portfolio data...", 
            "Cancel",
            0, 
            len(self.current_portfolio.stocks),
            self.view
        )
        progress.setWindowModality(Qt.WindowModal)

        # Track any failures for summary message
        failed_updates = []

        for i, stock in enumerate(self.current_portfolio.stocks.values()):
            if progress.wasCanceled():
                break

            try:
                # Update progress dialog with current stock
                progress.setLabelText(f"Updating {stock.yahoo_symbol}...")
                
                # Process historical data using existing collector
                success = HistoricalDataCollector.process_and_store_historical_data(
                    db_manager=self.db_manager,
                    stock_id=stock.id,
                    yahoo_symbol=stock.yahoo_symbol,
                    progress_callback=progress.setLabelText
                )

                if not success:
                    failed_updates.append(stock.yahoo_symbol)

            except Exception as e:
                logger.error(f"Failed to update data for {stock.yahoo_symbol}: {str(e)}")
                logger.exception("Detailed traceback:")
                failed_updates.append(stock.yahoo_symbol)

            progress.setValue(i + 1)

        progress.close()

        # Refresh portfolio view with updated data
        self.current_portfolio.load_stocks()
        self.update_view()

        # Show completion message with any failures
        if failed_updates:
            QMessageBox.warning(
                self.view,
                "Update Complete with Errors",
                f"Portfolio updated, but failed to update: {', '.join(failed_updates)}"
            )
        else:
            QMessageBox.information(
                self.view,
                "Update Complete",
                "Portfolio has been successfully updated with latest data."
            )
            
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
            
            # Connect signals for portfolio updates
            dialog.update_portfolio_requested.connect(self.update_after_verification)
            dialog.verification_completed.connect(self.on_verification_completed)
            
            # Just show the dialog - updates will happen through signals
            dialog.exec_()

    def get_view(self):
        """Return the view instance"""
        return self.view
        
    def update_after_verification(self):
        """Handler for when verification dialog requests a portfolio update"""
        self.current_portfolio.load_stocks()
        self.update_view()
    
    def on_verification_completed(self, verification_results):
        """Handle verification results and collect historical data."""
        self.historical_collector.process_verification_results(
            verification_results, 
            parent_widget=self.view
        )
        self.current_portfolio.load_stocks()
        self.update_view()