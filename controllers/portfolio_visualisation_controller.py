# File: controllers/portfolio_visualisation_controller.py

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from PySide6.QtWidgets import QMessageBox
import logging

logger = logging.getLogger(__name__)

class PortfoliovisualisationController:
    """
    Controller for portfolio visualisation functionality.
    Handles data retrieval and processing for portfolio performance visualisation.
    """
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.view = None
        self.current_portfolio = None
    
    def set_view(self, view):
        """Set the view and connect signals."""
        self.view = view
        self.view.plot_portfolio.connect(self.visualise_portfolio)
    
    def set_portfolio(self, portfolio):
        """Set the current portfolio and update the view."""
        self.current_portfolio = portfolio
        if self.view:
            self.view.update_portfolio_stocks(portfolio.stocks.values())
    
    def visualise_portfolio(self, params):
        """
        Generate portfolio visualisation based on selected stocks and weights.
        
        Args:
            params: Dict containing plot parameters
        """
        try:
            weights = params['weights']
            period_text = params['period']
            base_amount = params['base_amount']
            normalise = params['normalise']
            show_mode = params['show_mode']
            
            # Convert period text to datetime
            period_mapping = {
                "1 Month": 30,
                "3 Months": 90,
                "6 Months": 180,
                "1 Year": 365,
                "3 Years": 1095,
                "5 Years": 1825,
                "10 Years": 3650
            }
            days = period_mapping.get(period_text, 365)
            start_date = datetime.now() - timedelta(days=days)
            
            # Download data
            data = yf.download(
                list(weights.keys()),
                start=start_date,
                end=datetime.now(),
                interval='1d'
            )
            
            # Extract adjusted close prices
            prices = pd.DataFrame()
            if len(weights) == 1:
                # Single stock case
                ticker = list(weights.keys())[0]
                prices[ticker] = data['Adj Close']
            else:
                # Multiple stocks case
                for ticker in weights.keys():
                    prices[ticker] = data['Adj Close'][ticker]
            
            # Calculate portfolio and individual stock performances
            portfolio_values = pd.DataFrame(index=prices.index)
            
            # Process each stock
            for ticker, weight in weights.items():
                stock_prices = prices[ticker]
                
                if normalise == "normalise to 100":
                    stock_values = 100 * stock_prices / stock_prices.iloc[0]
                elif normalise == "Percent Change":
                    stock_values = 100 * (stock_prices / stock_prices.iloc[0] - 1)
                else:  # Absolute Prices
                    stock_values = stock_prices * (base_amount * weight)
                
                portfolio_values[ticker] = stock_values
            
            # Calculate combined portfolio value
            if normalise == "normalise to 100":
                portfolio_values['Portfolio'] = 100
                for ticker, weight in weights.items():
                    norm_return = (prices[ticker] / prices[ticker].iloc[0] - 1)
                    portfolio_values['Portfolio'] += weight * 100 * norm_return
            elif normalise == "Percent Change":
                portfolio_values['Portfolio'] = 0
                for ticker, weight in weights.items():
                    pct_change = (prices[ticker] / prices[ticker].iloc[0] - 1) * 100
                    portfolio_values['Portfolio'] += weight * pct_change
            else:
                portfolio_values['Portfolio'] = base_amount
                for ticker, weight in weights.items():
                    stock_contribution = base_amount * weight * (prices[ticker] / prices[ticker].iloc[0])
                    portfolio_values['Portfolio'] += stock_contribution - (base_amount * weight)
            
            # Plot the results
            self.view.figure.clear()
            ax = self.view.figure.add_subplot(111)
            
            # Determine what to plot based on show_mode
            if show_mode != "Portfolio Only":
                # Plot individual stocks
                for ticker in weights.keys():
                    ax.plot(portfolio_values.index, portfolio_values[ticker],
                        label=ticker, alpha=0.5)
            
            if show_mode != "Individual Only":
                # Plot portfolio
                ax.plot(portfolio_values.index, portfolio_values['Portfolio'],
                    label='Portfolio', linewidth=2, color='black')
            
            # Customize plot
            ax.set_title("Portfolio Performance Comparison")
            ax.set_xlabel("Date")
            
            if normalise == "normalise to 100":
                ax.set_ylabel("normalised Value (Base=100)")
            elif normalise == "Percent Change":
                ax.set_ylabel("Percent Change (%)")
            else:
                ax.set_ylabel("Value ($)")
            
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Format x-axis dates
            self.view.figure.autofmt_xdate()
            
            # Adjust layout and display
            self.view.figure.tight_layout()
            self.view.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error in portfolio visualisation: {str(e)}")
            logger.exception("Detailed traceback:")  # This will log the full traceback
            QMessageBox.warning(
                self.view,
                "visualisation Error",
                f"Failed to generate portfolio visualisation: {str(e)}"
            )
    
    def get_view(self):
        """Return the view instance."""
        return self.view