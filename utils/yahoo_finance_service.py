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
        2. If current_currency or trading_currency differs from portfolio_currency, conversion is performed
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
                    

            # Check if we need current market price
            today = datetime.now().date()
            today_data = data[data.index.date == today]

            if today_data.empty or pd.isna(today_data['Close'].iloc[-1]):
                # Get current market price
                current_price, is_live = YahooFinanceService.get_current_market_price(yahoo_symbol)
                
                if current_price > 0 and is_live:
                    logger.info(f"Adding live market price for {yahoo_symbol}: {current_price}")
                    
                    # Create a new row that matches the existing DataFrame structure
                    new_row = pd.DataFrame({
                        'Open': [current_price],
                        'High': [current_price],
                        'Low': [current_price],
                        'Close': [current_price],
                        'Volume': [0],
                        'Dividends': [0],
                        'Stock Splits': [1.0]
                    }, index=[pd.Timestamp(today)])
                    
                    # Add to our historical data
                    data = pd.concat([data, new_row])

            data = data.reset_index()
            data = data.rename(columns={'index': 'Date'})
            data['Date'] = data['Date'].apply(lambda x: DateUtils.to_database_date(
                DateUtils.normalise_yahoo_date(x)
            ))

            # Prepare records for database insertion
            records = []
            latest_close = None
            
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
                if row['Date'] == today.strftime('%Y-%m-%d'):
                    latest_close = row['Close']
            
            # Handle currency conversion if needed
            if (str(current_currency) != str(portfolio_currency)) or (str(trading_currency) != str(portfolio_currency)):
                logger.info(f"Currency conversion needed for stock {stock_id}:")
                logger.info(f"Either stock currency ({current_currency}) or trading_currency ({trading_currency}) is not equal to portfolio_currency ({portfolio_currency})") 
                logger.info(f"Therefore, fetching data to convert from {trading_currency} to {portfolio_currency}")
                
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
            

            # Update current price in stocks table if we have today's data
            if latest_close is not None:
                db_manager.execute("""
                    UPDATE stocks 
                    SET current_price = ?,
                        last_updated = ?
                    WHERE id = ?
                """, (
                    latest_close,
                    datetime.now().replace(microsecond=0),
                    stock_id
                ))
                db_manager.conn.commit()
            
            logger.info(f"Historical data and current price updated for stock {stock_id}")
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
            logger.info(f"Fetching conversion data for {yahoo_symbol}: {trading_currency} to {portfolio_currency}")
            
            # Try direct currency pair
            ticker = yf.Ticker(f"{trading_currency}{portfolio_currency}=X")
            data = ticker.history(start=start_date, auto_adjust=False)
            
            if not data.empty:
                logger.info(f"Found direct currency conversion for {trading_currency} to {portfolio_currency}")
                conversion_data = data['Close'].to_frame('conversion_rate')
                return conversion_data
                
            # If direct conversion fails, try via USD
            logger.info(f"Direct conversion not found, trying via USD for {yahoo_symbol}")
            
            # Get source currency to USD conversion
            source_usd = yf.Ticker(f"{trading_currency}USD=X")
            source_data = source_usd.history(start=start_date, auto_adjust=False)
            
            # Get USD to portfolio currency conversion
            portfolio_usd = yf.Ticker(f"{portfolio_currency}USD=X")
            portfolio_data = portfolio_usd.history(start=start_date, auto_adjust=False)
            
            if not source_data.empty and not portfolio_data.empty:
                # Calculate cross rate
                conversion_rate = portfolio_data['Close'] / source_data['Close']
                return conversion_rate.to_frame('conversion_rate')
                
            raise ValueError(f"Could not fetch conversion data from {trading_currency} to {portfolio_currency}")
            
        except Exception as e:
            logger.error(f"Error fetching currency conversion data for {yahoo_symbol}: {str(e)}")
            logger.exception("Detailed traceback:")
            return None


    @staticmethod
    def apply_currency_conversion(data: pd.DataFrame, records: list, conversion_data: pd.DataFrame):
        try:
            logger.info(f"Starting currency conversion")
            logger.info(f"Original records count: {len(records)}")
            logger.info(f"Conversion data shape: {conversion_data.shape}")
            logger.info(f"Conversion data index range: {conversion_data.index.min()} to {conversion_data.index.max()}")

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
            
            # Log merge details
            logger.info(f"Merged data shape: {merged_data.shape}")
            logger.info(f"Rows with missing conversion rate: {merged_data['conversion_rate'].isna().sum()}")
            
            # Log the specific rows with missing conversion rates
            missing_rate_rows = merged_data[merged_data['conversion_rate'].isna()]
            if not missing_rate_rows.empty:
                logger.warning("Rows with missing conversion rates:")
                logger.warning(missing_rate_rows[['date']])
            
            # Apply conversion to price columns
            price_columns = ['open', 'high', 'low', 'close', 'dividends']
            for col in price_columns:
                # Use the last known conversion rate for rows with missing rates
                merged_data['conversion_rate'] = merged_data['conversion_rate'].fillna(method='ffill')
                merged_data[col] *= merged_data['conversion_rate']
            
            # Convert back to list of tuples, excluding conversion_rate column
            # Convert dates back to strings in YYYY-MM-DD format
            merged_data['date'] = merged_data['date'].dt.strftime('%Y-%m-%d')
            converted_records = list(merged_data.drop('conversion_rate', axis=1).itertuples(index=False, name=None))
            
            logger.info(f"Converted records count: {len(converted_records)}")
            
            return converted_records
            
        except Exception as e:
            logger.error(f"Detailed error in apply_currency_conversion: {str(e)}")
            logger.exception("Full traceback:")
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
        
    @staticmethod
    def get_current_market_price(yahoo_symbol: str) -> tuple:
        """
        Fetches the most recent price for a stock, whether from current trading or last close.
        
        Args:
            yahoo_symbol: Yahoo Finance stock symbol
            
        Returns:
            tuple: (price, is_live_price) where is_live_price indicates if price is from current trading
        """
        try:
            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info
            
            # Try getting current trading price first
            live_price = (
                info.get('currentPrice', 0.0) or
                info.get('regularMarketPrice', 0.0)
            )
            
            # If we got a live price, return it with True flag
            if live_price > 0:
                return float(live_price), True
                
            # Otherwise fall back to previous close
            last_price = (
                info.get('previousClose', 0.0) or
                info.get('lastPrice', 0.0)
            )
            
            return float(last_price), False
                
        except Exception as e:
            logger.error(f"Error getting current price for {yahoo_symbol}: {str(e)}")
            return 0.0, False