# File: utils/yahoo_finance_service.py

import yfinance as yf
import pandas as pd
from datetime import datetime
import logging
from utils.date_utils import DateUtils

logger = logging.getLogger(__name__)

class YahooFinanceService:
    """Handles all Yahoo Finance API interactions."""
    
    @staticmethod
    def fetch_stock_data(db_manager, stock_id: int, yahoo_symbol: str, start_date: datetime) -> pd.DataFrame:
        """
        Fetch historical data from Yahoo Finance.
        Only gets raw OHLCV data, dividends and splits.
        
        Args:
            db_manager: Database manager instance
            stock_id: The database ID of the stock
            yahoo_symbol: Yahoo Finance stock symbol
            start_date: Start date for historical data
            
        Returns:
            pd.DataFrame: DataFrame containing historical data, or None if fetch fails
        """
        try:
            ticker = yf.Ticker(yahoo_symbol)
            data = ticker.history(start=start_date, auto_adjust=False)
            
            if data.empty:
                logger.warning(f"No data returned from Yahoo for {yahoo_symbol}")
                return None
                    
            # Reset index and format dates
            data = data.reset_index()
            # Use DateUtils to normalise and format the dates
            data['Date'] = data['Date'].apply(lambda x: DateUtils.to_database_date(
                DateUtils.normalise_yahoo_date(x)
            ))
            
            # Store basic historical data
            records = []
            for _, row in data.iterrows():
                records.append((
                    stock_id,
                    row['Date'],
                    row['Open'],
                    row['High'],
                    row['Low'],
                    row['Close'],
                    row['Volume'],
                    row.get('Dividends', 0.0),
                    row.get('Stock Splits', 1.0)
                ))
            
            # Bulk insert historical prices
            db_manager.bulk_insert_historical_prices(records)
            
            # Update metrics after new data
            from database.portfolio_metrics_manager import PortfolioMetricsManager
            metrics_manager = PortfolioMetricsManager(db_manager)
            metrics_manager.update_metrics_for_stock(stock_id)
            
            return data
                
        except Exception as e:
            logger.error(f"Error fetching Yahoo data for {yahoo_symbol}: {str(e)}")
            logger.exception("Detailed traceback:")
            return None

    @staticmethod
    def verify_stock(symbol: str) -> dict:
        """
        Verifies stock exists and returns basic info.
        
        Args:
            symbol: Yahoo Finance stock symbol
            
        Returns:
            Dictionary containing stock information
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Get current price trying different fields
            price = (
                info.get('currentPrice', 0.0) or
                info.get('regularMarketPrice', 0.0) or
                info.get('previousClose', 0.0) or
                info.get('lastPrice', 0.0)
            )
            
            # Get currency information
            currency = ticker.info['currency']

            # If still no price, try getting from history
            if price == 0:
                hist = ticker.history(period="1d", auto_adjust=False)
                if not hist.empty:
                    price = hist['Close'].iloc[-1]
            
            # Get splits and normalise dates
            splits = ticker.splits
            if not splits.empty:
                splits.index = splits.index.map(DateUtils.normalise_yahoo_date)
            
            return {
                'name': info.get('longName', 'N/A'),
                'current_price': price,
                'currency': currency,
                'exists': bool(info.get('longName')),
                'splits': splits if not splits.empty else None,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Error verifying stock {symbol}: {str(e)}")
            return {
                'name': 'N/A',
                'current_price': 0.0,
                'currency': 'N/A',
                'exists': False,
                'splits': None,
                'error': str(e)
            }