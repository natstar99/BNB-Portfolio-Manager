# File: utils/yahoo_finance_service.py

import yfinance as yf
import pandas as pd
from datetime import datetime
import logging
from utils.date_utils import DateUtils
from database.final_metrics_manager import PortfolioMetricsManager

logger = logging.getLogger(__name__)

class YahooFinanceService:
    """Handles all Yahoo Finance API interactions."""
    
    @staticmethod
    def fetch_stock_data(db_manager, stock_id: int, yahoo_symbol: str, start_date: datetime, 
                        trading_currency: str, portfolio_currency: str) -> pd.DataFrame:
        """
        Fetch historical data from Yahoo Finance and handle currency conversions.
        Downloads OHLCV data, dividends, and splits while managing currency conversions.
        
        The method follows a specific currency handling process:
        1. If current_currency is NULL, it's set to trading_currency
        2. If current_currency differs from portfolio_currency, conversion is performed
        3. Original prices are preserved before any conversion
        
        Args:
            db_manager: Database manager instance
            stock_id: The database ID of the stock
            yahoo_symbol: Yahoo Finance stock symbol
            start_date: Start date for historical data
            trading_currency: Currency stock is traded in (native currency)
            portfolio_currency: Default currency of the selected portfolio
                
        Returns:
            pd.DataFrame: DataFrame containing historical data, or None if fetch fails
        """
        try:
            # First, handle currency status
            result = db_manager.fetch_one(
                "SELECT current_currency FROM stocks WHERE id = ?",
                (stock_id,)
            )
            current_currency = result[0] if result else None
            
            # If current_currency is NULL, set it to trading_currency
            if current_currency is None:
                db_manager.execute("""
                    UPDATE stocks 
                    SET current_currency = trading_currency 
                    WHERE id = ? AND current_currency IS NULL
                """, (stock_id,))
                db_manager.conn.commit()
                current_currency = trading_currency
                logger.info(f"Set initial current_currency to {trading_currency} for stock {stock_id}")

            # Download raw data from Yahoo Finance
            ticker = yf.Ticker(yahoo_symbol)
            data = ticker.history(start=start_date, auto_adjust=False)
            
            if data.empty:
                logger.warning(f"No data returned from Yahoo for {yahoo_symbol}")
                return None
                    
            # Reset index and format dates
            data = data.reset_index()
            data['Date'] = data['Date'].apply(lambda x: DateUtils.to_database_date(
                DateUtils.normalise_yahoo_date(x)
            ))
            
            # Prepare records for database insertion
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
            
            # Handle currency conversion if needed
            if str(current_currency) != str(portfolio_currency):
                logger.info(f"Currency conversion needed for stock {stock_id}: {current_currency} to {portfolio_currency}")
                
                conversion_data = YahooFinanceService.fetch_currency_conversion_data(
                    yahoo_symbol, 
                    start_date, 
                    trading_currency, 
                    portfolio_currency,
                    current_currency
                )
                
                if conversion_data is not None:
                    # Convert historical prices
                    records = YahooFinanceService.apply_currency_conversion(
                        data, records, conversion_data
                    )
                    
                    # Update transaction prices using original prices
                    db_manager.update_transaction_prices_with_conversion(
                        stock_id, conversion_data, trading_currency, portfolio_currency
                    )
                    
                    logger.info(f"Currency conversion completed for stock {stock_id}")
                else:
                    logger.warning(f"Failed to get conversion data for stock {stock_id}")
                    return None

            # Bulk insert historical prices
            db_manager.bulk_insert_historical_prices(records)
            logger.info(f"Historical data saved for stock {stock_id}")
            
            # Update metrics after new data
            metrics_manager = PortfolioMetricsManager(db_manager)
            metrics_manager.update_metrics_for_stock(stock_id)
            logger.info(f"Metrics updated for stock {stock_id}")
            
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
    def fetch_currency_conversion_data(yahoo_symbol: str, start_date: datetime, trading_currency: str,
                                       portfolio_currency: str, current_currency: str = None) -> pd.DataFrame:
        """
        Fetch currency conversion data from Yahoo Finance.
        Converts FROM the stock's current processing currency (or native currency if not yet processed)
        TO the portfolio currency. Attempts direct currency pair first, falls back to USD conversion if needed.
        
        Args:
            yahoo_symbol: Stock's Yahoo Finance symbol (for logging)
            start_date: Start date for conversion data
            trading_currency: Currency we're converting FROM (either current_currency or native currency)
            portfolio_currency: Portfolio's default currency (currency we're converting TO)
            current_currency: Current processing currency of the stock (if any)
            
        Returns:
            pd.DataFrame: DataFrame with dates and conversion rates
            """
        try:
            # Determine source currency for conversion
            source_currency = current_currency if current_currency else trading_currency
            logger.info(f"Fetching conversion data for {yahoo_symbol}: {source_currency} to {portfolio_currency}")
            
            # Try direct currency pair
            ticker = yf.Ticker(f"{source_currency}{portfolio_currency}=X")
            data = ticker.history(start=start_date, auto_adjust=False)
            
            if not data.empty:
                logger.info(f"Found direct currency conversion for {source_currency} to {portfolio_currency}")
                conversion_data = data['Close'].to_frame('conversion_rate')
                return conversion_data
                
            # If direct conversion fails, try via USD
            logger.info(f"Direct conversion not found, trying via USD for {yahoo_symbol}")
            
            # Get source currency to USD conversion
            source_usd = yf.Ticker(f"{source_currency}USD=X")
            source_data = source_usd.history(start=start_date, auto_adjust=False)
            
            # Get USD to portfolio currency conversion
            portfolio_usd = yf.Ticker(f"{portfolio_currency}USD=X")
            portfolio_data = portfolio_usd.history(start=start_date, auto_adjust=False)
            
            if not source_data.empty and not portfolio_data.empty:
                # Calculate cross rate
                conversion_rate = portfolio_data['Close'] / source_data['Close']
                return conversion_rate.to_frame('conversion_rate')
                
            raise ValueError(f"Could not fetch conversion data from {source_currency} to {portfolio_currency}")
            
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

    @staticmethod
    def get_current_conversion_rate(from_currency: str, to_currency: str) -> float:
        """
        Get the current currency conversion rate with fallback options.
        
        Args:
            from_currency (str): The currency to convert from (stock's native currency)
            to_currency (str): The currency to convert to (portfolio currency)
            
        Returns:
            float: The conversion rate (1.0 if currencies are same or conversion fails)
        """
        try:
            # Return 1.0 if currencies are the same or invalid
            if not from_currency or not to_currency or from_currency == to_currency:
                return 1.0
                
            # Try direct conversion first
            conversion_symbol = f"{from_currency}{to_currency}=X"
            ticker = yf.Ticker(conversion_symbol)
            info = ticker.info
            
            rate = (
                info.get('currentPrice', 0.0) or
                info.get('regularMarketPrice', 0.0) or
                info.get('previousClose', 0.0) or
                info.get('lastPrice', 0.0)
            )
            
            if rate:
                return float(rate)
                
            # If direct conversion fails, try via USD
            from_usd = yf.Ticker(f"{from_currency}USD=X")
            to_usd = yf.Ticker(f"{to_currency}USD=X")
            
            from_info = from_usd.info
            to_info = to_usd.info
            
            from_rate = (
                from_info.get('currentPrice', 0.0) or
                from_info.get('regularMarketPrice', 0.0) or
                from_info.get('previousClose', 0.0) or
                from_info.get('lastPrice', 0.0)
            )
            
            to_rate = (
                to_info.get('currentPrice', 0.0) or
                to_info.get('regularMarketPrice', 0.0) or
                to_info.get('previousClose', 0.0) or
                to_info.get('lastPrice', 0.0)
            )
            
            if from_rate and to_rate:
                return float(to_rate) / float(from_rate)
                    
            # Log warning if no valid price found
            logger.warning(
                f"Could not find valid conversion rate for {from_currency} to {to_currency}"
            )
            return 1.0  # Fallback if all conversions fail
                
        except Exception as e:
            logger.error(f"Error getting conversion rate {from_currency} to {to_currency}: {str(e)}")
            return 1.0