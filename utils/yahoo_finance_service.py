# File: utils/yahoo_finance_service.py

import yfinance as yf
import pandas as pd
from datetime import datetime
import logging
from utils.date_utils import DateUtils
from database.portfolio_metrics_manager import PortfolioMetricsManager

logger = logging.getLogger(__name__)

class YahooFinanceService:
    """Handles all Yahoo Finance API interactions."""
    
    @staticmethod
    def fetch_stock_data(db_manager, stock_id: int, yahoo_symbol: str, start_date: datetime, stock_currency: str, portfolio_currency: str) -> pd.DataFrame:
        """
        Fetch historical data from Yahoo Finance.
        Only gets raw OHLCV data, dividends and splits.
        
        Args:
            db_manager: Database manager instance
            stock_id: The database ID of the stock
            yahoo_symbol: Yahoo Finance stock symbol
            start_date: Start date for historical data
            stock_currency: Currency of stock
            default_currency: Default currency of the selected portfolio
            
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
            
            # Check if currency is correct
            if str(stock_currency) != str(portfolio_currency):
                conversion_data = YahooFinanceService.fetch_currency_conversion_data(
                    yahoo_symbol, start_date, stock_currency, portfolio_currency
                )
                
                if conversion_data is not None:
                    # Convert historical prices
                    records = YahooFinanceService.apply_currency_conversion(
                        data, records, conversion_data
                    )
                    
                    # Update transaction prices using database manager
                    db_manager.update_transaction_prices_with_conversion(
                        stock_id, conversion_data, stock_currency, portfolio_currency
                    )

            # Bulk insert historical prices
            db_manager.bulk_insert_historical_prices(records)
            
            # Update metrics after new data
            
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

    
    @staticmethod
    def fetch_currency_conversion_data(yahoo_symbol: str, start_date: datetime, stock_currency: str, portfolio_currency: str) -> pd.DataFrame:
        """
        Fetch currency conversion data from Yahoo Finance.
        Attempts direct currency pair first, falls back to USD conversion if needed.
        
        Args:
            yahoo_symbol: Stock's Yahoo Finance symbol (for logging)
            start_date: Start date for conversion data
            stock_currency: Currency of the stock
            portfolio_currency: Portfolio's default currency
            
        Returns:
            pd.DataFrame: DataFrame with dates and conversion rates
        """
        try:
            # Try direct currency pair
            ticker = yf.Ticker(f"{stock_currency}{portfolio_currency}=X")
            data = ticker.history(start=start_date, auto_adjust=False)
            
            if not data.empty:
                logger.info(f"Found direct currency conversion for {stock_currency} to {portfolio_currency}")
                conversion_data = data['Close'].to_frame('conversion_rate')
                return conversion_data
                
            # If direct conversion fails, try via USD
            logger.info(f"Direct conversion not found, trying via USD for {yahoo_symbol}")
            
            # Get stock currency to USD conversion
            stock_usd = yf.Ticker(f"{stock_currency}=X")
            stock_data = stock_usd.history(start=start_date, auto_adjust=False)
            
            # Get portfolio currency to USD conversion
            portfolio_usd = yf.Ticker(f"{portfolio_currency}=X")
            portfolio_data = portfolio_usd.history(start=start_date, auto_adjust=False)
            
            if not stock_data.empty and not portfolio_data.empty:
                # Calculate cross rate
                conversion_rate = portfolio_data['Close'] / stock_data['Close']
                return conversion_rate.to_frame('conversion_rate')
                
            raise ValueError("Could not fetch required currency conversion data")
            
        except Exception as e:
            logger.error(f"Error fetching currency conversion data for {yahoo_symbol}: {str(e)}")
            logger.exception("Detailed traceback:")
            return None

    @staticmethod
    def apply_currency_conversion(data: pd.DataFrame, records: list, conversion_data: pd.DataFrame):
        """
        Apply currency conversion to historical price records.
        
        Args:
            data: Original Yahoo Finance data DataFrame
            records: List of tuples containing historical price records
            conversion_data: DataFrame containing currency conversion rates
            
        Returns:
            list: Updated records with converted values
        """
        try:
            # Convert records to DataFrame for easier manipulation
            records_df = pd.DataFrame(records, columns=[
                'stock_id', 'date', 'open', 'high', 'low', 'close', 
                'volume', 'dividends', 'splits'
            ])

            # Convert date columns to datetime with no timezone
            records_df['date'] = pd.to_datetime(records_df['date']).dt.tz_localize(None)
            conversion_data.index = pd.to_datetime(conversion_data.index).tz_localize(None)
            
            # Merge conversion rates with records
            merged_data = pd.merge(
                records_df,
                conversion_data,
                left_on='date',
                right_index=True,
                how='left'
            )
            
            # Apply conversion to price columns
            price_columns = ['open', 'high', 'low', 'close', 'dividends']
            for col in price_columns:
                merged_data[col] *= merged_data['conversion_rate']
            
            # Convert back to list of tuples, excluding conversion_rate column
            # Convert dates back to strings in YYYY-MM-DD format
            merged_data['date'] = merged_data['date'].dt.strftime('%Y-%m-%d')
            converted_records = list(merged_data.drop('conversion_rate', axis=1).itertuples(index=False, name=None))
            
            return converted_records
            
        except Exception as e:
            logger.error(f"Error applying currency conversion: {str(e)}")
            logger.exception("Detailed traceback:")
            return records  # Return original records if conversion fails