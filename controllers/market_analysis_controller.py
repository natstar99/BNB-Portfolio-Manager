# File: controllers/market_analysis_controller.py

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from PySide6.QtWidgets import QMessageBox
import logging
from controllers.portfolio_optimisation_controller import PortfolioOptimisationController
from controllers.portfolio_visualisation_controller import PortfoliovisualisationController

logger = logging.getLogger(__name__)

class MarketAnalysisController:
    """
    Controller for market analysis functionality.
    Handles data retrieval and processing for market analysis tools.
    """
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.view = None
        self.current_portfolio = None
        self.optimisation_controller = PortfolioOptimisationController(db_manager)
        self.visualisation_controller = PortfoliovisualisationController(db_manager)
    
    def set_view(self, view):
        """Set the view and connect signals."""
        self.view = view
        self.view.analyse_correlation.connect(self.generate_correlation_matrix)
        self.optimisation_controller.set_view(self.view.optimisation_view)
        self.visualisation_controller.set_view(self.view.visualisation_view)
    
    def set_portfolio(self, portfolio):
        """Set the current portfolio and update the views."""
        self.current_portfolio = portfolio
        if self.view:
            self.view.update_portfolio_stocks(portfolio.stocks.values())
            self.optimisation_controller.set_portfolio(portfolio)
            self.visualisation_controller.set_portfolio(portfolio)
    
    def generate_correlation_matrix(self, params):
        """
        Generate a correlation matrix for the selected stocks.
        
        Args:
            params: List containing [selected_tickers, period_text]
        """
        try:
            selected_tickers, period_text = params
            
            # Convert period text to datetime
            period_mapping = {
                "1 Month": 30,
                "3 Months": 90,
                "6 Months": 180,
                "1 Year": 365,
                "3 Years": 1095,
                "5 Years": 1825
            }
            days = period_mapping.get(period_text, 365)
            start_date = datetime.now() - timedelta(days=days)
            
            # Download data
            data = yf.download(
                selected_tickers,
                start=start_date,
                end=datetime.now(),
                interval='1d',
                group_by='ticker'
            )
            
            # Calculate returns
            if len(selected_tickers) == 1:
                prices = pd.DataFrame(data['Close'])
                prices.columns = selected_tickers
            else:
                prices = pd.DataFrame({ticker: data[ticker]['Close'] 
                                    for ticker in selected_tickers})
            
            returns = prices.pct_change().dropna()
            correlation_matrix = returns.corr()
            
            # Update the plot
            self.view.plot_correlation_matrix(correlation_matrix)
            
        except Exception as e:
            logger.error(f"Error generating correlation matrix: {str(e)}")
            QMessageBox.warning(
                self.view,
                "Analysis Error",
                f"Failed to generate correlation matrix: {str(e)}"
            )
    
    def get_view(self):
        """Return the view instance."""
        return self.view