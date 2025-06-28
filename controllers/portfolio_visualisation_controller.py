# File: controllers/portfolio_visualisation_controller.py

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from PySide6.QtWidgets import QMessageBox
import logging

logger = logging.getLogger(__name__)

class PortfoliovisualisationController:
    """
    Controller for portfolio profitability comparison against market indices.
    Integrates with final_metrics database for portfolio data and Yahoo Finance for index data.
    """
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.view = None
        self.current_portfolio = None
    
    def set_view(self, view):
        """Set the view and connect signals."""
        self.view = view
        self.view.plot_portfolio_vs_indices.connect(self.compare_portfolio_vs_indices)
    
    def set_portfolio(self, portfolio):
        """Set the current portfolio and update the view."""
        self.current_portfolio = portfolio
        if self.view:
            self.view.update_portfolio_stocks(portfolio.stocks.values())
    
    def compare_portfolio_vs_indices(self, params):
        """
        Compare portfolio profitability against selected market indices.
        
        Args:
            params: Dict containing comparison parameters
        """
        try:
            period = params['period']
            metric = params['metric']
            normalize = params['normalize']
            selected_indices = params['indices']
            
            if not self.current_portfolio:
                QMessageBox.warning(
                    self.view,
                    "No Portfolio",
                    "Please select a portfolio first."
                )
                return
            
            if not selected_indices:
                QMessageBox.warning(
                    self.view,
                    "No Indices Selected",
                    "Please select at least one market index for comparison."
                )
                return
            
            # Get date range for analysis
            start_date, end_date = self._get_date_range(period)
            
            # Get portfolio profitability data from final_metrics
            portfolio_data = self._get_portfolio_profitability_data(start_date, end_date, metric)
            
            # Get index data from Yahoo Finance
            indices_data = self._get_indices_data(selected_indices, start_date, end_date, metric)
            
            # Normalize data if requested
            if normalize:
                portfolio_data = self._normalize_to_zero_start(portfolio_data)
                for symbol in indices_data:
                    indices_data[symbol] = self._normalize_to_zero_start(indices_data[symbol])
            
            # Plot the results
            self.view.plot_results(portfolio_data, indices_data, params)
            
        except Exception as e:
            logger.error(f"Error in portfolio vs indices comparison: {str(e)}")
            logger.exception("Detailed traceback:")
            QMessageBox.warning(
                self.view,
                "Analysis Error",
                f"Failed to compare portfolio vs indices: {str(e)}"
            )
    
    def _get_date_range(self, period):
        """Convert period string to start and end dates."""
        end_date = datetime.now()
        
        period_mapping = {
            "1 Month": 30,
            "3 Months": 90,
            "6 Months": 180,
            "1 Year": 365,
            "2 Years": 730,
            "3 Years": 1095,
            "5 Years": 1825,
            "All Time": 3650  # 10 years as proxy for "all time"
        }
        
        days = period_mapping.get(period, 365)
        start_date = end_date - timedelta(days=days)
        
        return start_date, end_date
    
    def _get_portfolio_profitability_data(self, start_date, end_date, metric):
        """
        Get portfolio profitability data from final_metrics table.
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            metric: Profitability metric to retrieve
            
        Returns:
            pandas.Series: Portfolio profitability data indexed by date
        """
        # Map metric to database column
        metric_mapping = {
            "Total Return (%)": "total_return_pct",
            "Daily P&L (%)": "daily_pl_pct",
            "Cumulative Return (%)": "cumulative_return_pct"
        }
        
        db_column = metric_mapping.get(metric, "total_return_pct")
        
        # Use the exact same approach as Study Portfolio controller
        data_frames = []
        
        for stock in self.current_portfolio.stocks.values():
            query = f"""
            SELECT date, {db_column}
            FROM final_metrics 
            WHERE stock_id = ?
            AND date BETWEEN ? AND ?
            AND {db_column} IS NOT NULL
            ORDER BY date
            """
            
            params = [stock.id, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')]
            
            try:
                results = self.db_manager.fetch_all(query, params)
                
                if results:
                    df = pd.DataFrame(results, columns=['date', db_column])
                    df['stock'] = stock.yahoo_symbol
                    data_frames.append(df)
                    
            except Exception as e:
                logger.error(f"Error retrieving data for stock {stock.yahoo_symbol}: {str(e)}")
                continue
        
        if not data_frames:
            logger.warning("No portfolio data found for the selected period")
            return pd.Series(dtype=float)
            
        # Combine all stock data
        combined_data = pd.concat(data_frames, ignore_index=True)
        combined_data['date'] = pd.to_datetime(combined_data['date'])
        
        # Apply the exact same pattern as Study Portfolio profitability plotting
        plot_data = combined_data.copy()
        plot_data.set_index(['date', 'stock'], inplace=True)
        plot_data = plot_data[db_column].unstack()
        plot_data = plot_data.asfreq('D').ffill()
        
        # Calculate portfolio total (all metrics are now percentages)
        portfolio_series = plot_data.mean(axis=1)
            
        logger.info(f"Created portfolio series with {len(portfolio_series)} data points")
        return portfolio_series
    
    def _get_indices_data(self, index_symbols, start_date, end_date, metric):
        """
        Get market indices data from Yahoo Finance.
        
        Args:
            index_symbols: List of index symbols
            start_date: Start date for analysis
            end_date: End date for analysis
            metric: Metric type to calculate
            
        Returns:
            dict: Dictionary of pandas.Series indexed by symbol
        """
        indices_data = {}
        
        for symbol in index_symbols:
            try:
                # Download index data
                data = yf.download(
                    symbol,
                    start=start_date,
                    end=end_date,
                    interval='1d'
                )
                
                if data.empty:
                    logger.warning(f"No data available for index {symbol}")
                    continue
                
                # Calculate the appropriate metric (all percentage based)
                prices = data['Close']
                
                if "Total Return" in metric or "Cumulative Return" in metric:
                    # Calculate total/cumulative return from start
                    values = 100 * (prices / prices.iloc[0] - 1)
                elif "Daily P&L" in metric:
                    # Calculate daily percentage changes
                    daily_returns = prices.pct_change().fillna(0)
                    values = daily_returns * 100
                else:
                    # Default to total return percentage
                    values = 100 * (prices / prices.iloc[0] - 1)
                
                # Apply weekend/holiday handling using the same pattern as portfolio study
                # Forward fill to handle weekends and holidays
                values = values.asfreq('D').ffill()
                
                indices_data[symbol] = values
                
            except Exception as e:
                logger.error(f"Error retrieving data for index {symbol}: {str(e)}")
                continue
        
        return indices_data
    
    def _normalize_to_zero_start(self, data):
        """
        Normalize data to start from zero for relative performance comparison.
        
        Args:
            data: pandas.Series with time series data
            
        Returns:
            pandas.Series: Normalized data starting from zero
        """
        if data.empty:
            return data
        
        # Subtract the first value to start from zero
        first_value = data.iloc[0]
        normalized_data = data - first_value
        
        # Ensure forward fill is maintained after normalization
        normalized_data = normalized_data.asfreq('D').ffill()
        
        return normalized_data
    
    def get_view(self):
        """Return the view instance."""
        return self.view