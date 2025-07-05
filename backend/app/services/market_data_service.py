"""
Market Data Service - Yahoo Finance Integration
Handles all external market data operations with proper ETL separation
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, date
import logging
from typing import Dict, List, Optional, Tuple
from app.models import Stock, Transaction
from app import db
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


class MarketDataService:
    """
    Service for handling all market data operations including:
    - Yahoo Finance API integration
    - Currency conversion
    - Historical data extraction and loading
    - Real-time price updates
    """

    def __init__(self):
        self.timeout = 30
        self.retry_count = 3

    # ============= EXTRACT METHODS =============

    def extract_stock_data(self, yahoo_symbol: str, start_date: datetime) -> Optional[pd.DataFrame]:
        """
        Extract historical stock data from Yahoo Finance.
        
        Args:
            yahoo_symbol: Yahoo Finance stock symbol
            start_date: Start date for historical data
            
        Returns:
            pd.DataFrame or None: Raw historical data from Yahoo Finance
        """
        try:
            ticker = yf.Ticker(yahoo_symbol)
            data = ticker.history(start=start_date, auto_adjust=False)
            
            if data.empty:
                logger.warning(f"No data returned from Yahoo for {yahoo_symbol}")
                return None
            
            # Add current market price if not available in historical data
            today = datetime.now().date()
            today_data = data[data.index.date == today]
            
            if today_data.empty or pd.isna(today_data['Close'].iloc[-1]):
                current_price, is_live = self.get_current_market_price(yahoo_symbol)
                
                if current_price > 0 and is_live:
                    logger.info(f"Adding live market price for {yahoo_symbol}: {current_price}")
                    
                    new_row = pd.DataFrame({
                        'Open': [current_price],
                        'High': [current_price],
                        'Low': [current_price],
                        'Close': [current_price],
                        'Volume': [0],
                        'Dividends': [0],
                        'Stock Splits': [1.0]
                    }, index=[pd.Timestamp(today)])
                    
                    data = pd.concat([data, new_row])
            
            return data
            
        except Exception as e:
            logger.error(f"Error extracting Yahoo data for {yahoo_symbol}: {str(e)}")
            return None

    def extract_currency_conversion_data(self, from_currency: str, to_currency: str, 
                                       start_date: datetime) -> Optional[pd.DataFrame]:
        """
        Extract currency conversion rates from Yahoo Finance.
        
        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            start_date: Start date for conversion data
            
        Returns:
            pd.DataFrame or None: Currency conversion rates
        """
        try:
            if from_currency == to_currency:
                return None
                
            logger.info(f"Extracting conversion data: {from_currency} to {to_currency}")
            
            # Try direct currency pair first
            ticker = yf.Ticker(f"{from_currency}{to_currency}=X")
            data = ticker.history(start=start_date, auto_adjust=False)
            
            if not data.empty:
                logger.info(f"Found direct currency conversion for {from_currency} to {to_currency}")
                return data['Close'].to_frame('conversion_rate')
            
            # Fall back to USD cross-rate conversion
            logger.info(f"Direct conversion not found, trying via USD")
            
            source_usd = yf.Ticker(f"{from_currency}USD=X")
            source_data = source_usd.history(start=start_date, auto_adjust=False)
            
            target_usd = yf.Ticker(f"{to_currency}USD=X")
            target_data = target_usd.history(start=start_date, auto_adjust=False)
            
            if not source_data.empty and not target_data.empty:
                # Calculate cross rate: FROM -> USD -> TO
                conversion_rate = target_data['Close'] / source_data['Close']
                return conversion_rate.to_frame('conversion_rate')
            
            raise ValueError(f"Could not fetch conversion data from {from_currency} to {to_currency}")
            
        except Exception as e:
            logger.error(f"Error extracting currency conversion data: {str(e)}")
            return None

    def get_current_market_price(self, yahoo_symbol: str) -> Tuple[float, bool]:
        """
        Get the current market price for a stock.
        
        Args:
            yahoo_symbol: Yahoo Finance stock symbol
            
        Returns:
            Tuple[float, bool]: (price, is_live) where is_live indicates real-time data
        """
        try:
            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info
            
            # Try current trading price first
            live_price = (
                info.get('currentPrice', 0.0) or
                info.get('regularMarketPrice', 0.0)
            )
            
            if live_price > 0:
                return float(live_price), True
            
            # Fall back to previous close
            last_price = (
                info.get('previousClose', 0.0) or
                info.get('lastPrice', 0.0)
            )
            
            return float(last_price), False
            
        except Exception as e:
            logger.error(f"Error getting current price for {yahoo_symbol}: {str(e)}")
            return 0.0, False

    def get_current_conversion_rate(self, from_currency: str, to_currency: str) -> float:
        """
        Get current currency conversion rate.
        
        Args:
            from_currency: Source currency
            to_currency: Target currency
            
        Returns:
            float: Conversion rate (1.0 if same currency or error)
        """
        try:
            if not from_currency or not to_currency or from_currency == to_currency:
                return 1.0
            
            # Try direct conversion
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
            
            # Try via USD
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
            
            logger.warning(f"Could not find conversion rate for {from_currency} to {to_currency}")
            return 1.0
            
        except Exception as e:
            logger.error(f"Error getting conversion rate {from_currency} to {to_currency}: {str(e)}")
            return 1.0

    # ============= TRANSFORM METHODS =============

    def transform_stock_data(self, raw_data: pd.DataFrame, stock_id: int) -> List[Dict]:
        """
        Transform raw Yahoo Finance data into database-ready format.
        
        Args:
            raw_data: Raw pandas DataFrame from Yahoo Finance
            stock_id: Database stock ID
            
        Returns:
            List[Dict]: Transformed data ready for database insertion
        """
        try:
            data = raw_data.reset_index()
            data = data.rename(columns={'Date': 'date'})
            
            # Normalize dates to YYYY-MM-DD format
            data['date'] = pd.to_datetime(data['date']).dt.strftime('%Y-%m-%d')
            
            records = []
            for _, row in data.iterrows():
                record = {
                    'stock_id': stock_id,
                    'date': datetime.strptime(row['date'], '%Y-%m-%d').date(),
                    'open_price': float(row.get('Open', 0)) if pd.notna(row.get('Open')) else None,
                    'high_price': float(row.get('High', 0)) if pd.notna(row.get('High')) else None,
                    'low_price': float(row.get('Low', 0)) if pd.notna(row.get('Low')) else None,
                    'close_price': float(row.get('Close', 0)) if pd.notna(row.get('Close')) else None,
                    'volume': int(row.get('Volume', 0)) if pd.notna(row.get('Volume')) else None,
                    'dividend': float(row.get('Dividends', 0)) if pd.notna(row.get('Dividends')) else 0.0,
                    'split_ratio': float(row.get('Stock Splits', 1.0)) if pd.notna(row.get('Stock Splits')) else 1.0
                }
                records.append(record)
            
            return records
            
        except Exception as e:
            logger.error(f"Error transforming stock data: {str(e)}")
            return []

    def apply_currency_conversion(self, stock_data: List[Dict], 
                                conversion_data: pd.DataFrame) -> List[Dict]:
        """
        Apply currency conversion to stock price data.
        
        Args:
            stock_data: List of stock data records
            conversion_data: DataFrame with conversion rates
            
        Returns:
            List[Dict]: Stock data with converted prices
        """
        try:
            if conversion_data is None or conversion_data.empty:
                return stock_data
            
            # Convert dates in conversion data to match stock data format
            conversion_data.index = pd.to_datetime(conversion_data.index).date
            
            converted_data = []
            for record in stock_data:
                record_date = record['date']
                
                # Find conversion rate for this date
                conversion_rate = None
                if record_date in conversion_data.index:
                    conversion_rate = conversion_data.loc[record_date, 'conversion_rate']
                else:
                    # Use forward fill for missing dates
                    available_dates = [d for d in conversion_data.index if d <= record_date]
                    if available_dates:
                        latest_date = max(available_dates)
                        conversion_rate = conversion_data.loc[latest_date, 'conversion_rate']
                
                if conversion_rate and pd.notna(conversion_rate):
                    # Apply conversion to price fields
                    price_fields = ['open_price', 'high_price', 'low_price', 'close_price', 'dividend']
                    for field in price_fields:
                        if record[field] is not None:
                            record[field] = record[field] * conversion_rate
                    
                    # Add conversion rate to record for tracking
                    record['currency_conversion_rate'] = conversion_rate
                
                converted_data.append(record)
            
            return converted_data
            
        except Exception as e:
            logger.error(f"Error applying currency conversion: {str(e)}")
            return stock_data

    # ============= LOAD METHODS =============

    def load_historical_prices(self, price_data: List[Dict]) -> bool:
        """
        Load historical price data into the database.
        
        Args:
            price_data: List of transformed price records
            
        Returns:
            bool: Success status
        """
        try:
            for record in price_data:
                try:
                    historical_price = HistoricalPrice.create(**record)
                    logger.debug(f"Loaded price data for stock {record['stock_id']} on {record['date']}")
                except IntegrityError:
                    # Record already exists, update it
                    db.session.rollback()
                    existing = HistoricalPrice.query.filter_by(
                        stock_id=record['stock_id'],
                        date=record['date']
                    ).first()
                    if existing:
                        existing.update(**{k: v for k, v in record.items() if k not in ['stock_id', 'date']})
                        logger.debug(f"Updated existing price data for stock {record['stock_id']} on {record['date']}")
            
            db.session.commit()
            logger.info(f"Successfully loaded {len(price_data)} historical price records")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error loading historical prices: {str(e)}")
            return False

    def update_stock_current_price(self, stock_id: int, price: float) -> bool:
        """
        Update the current price for a stock.
        
        Args:
            stock_id: Database stock ID
            price: New current price
            
        Returns:
            bool: Success status
        """
        try:
            stock = Stock.get_by_id(stock_id)
            if stock:
                stock.update_price(price)
                logger.info(f"Updated current price for stock {stock_id}: {price}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error updating stock price: {str(e)}")
            return False

    # ============= HIGH-LEVEL ETL METHODS =============

    def fetch_and_update_stock_data(self, stock_id: int, start_date: datetime = None) -> bool:
        """
        Complete ETL process for a single stock's historical data.
        
        Args:
            stock_id: Database stock ID
            start_date: Start date for data fetch (optional)
            
        Returns:
            bool: Success status
        """
        try:
            stock = Stock.get_by_id(stock_id)
            if not stock:
                logger.error(f"Stock with ID {stock_id} not found")
                return False
            
            # Determine start date if not provided
            if start_date is None:
                # Get the latest date from historical data
                latest_price = HistoricalPrice.get_latest_price(stock_id)
                if latest_price:
                    start_date = latest_price.date
                else:
                    # Default to 1 year ago if no historical data
                    start_date = datetime.now().replace(year=datetime.now().year - 1)
            
            logger.info(f"Fetching data for stock {stock.yahoo_symbol} from {start_date}")
            
            # Extract raw data from Yahoo Finance
            raw_data = self.extract_stock_data(stock.yahoo_symbol, start_date)
            if raw_data is None:
                return False
            
            # Transform data to database format
            transformed_data = self.transform_stock_data(raw_data, stock_id)
            if not transformed_data:
                return False
            
            # Apply currency conversion if needed
            if stock.trading_currency and stock.current_currency and stock.trading_currency != stock.current_currency:
                conversion_data = self.extract_currency_conversion_data(
                    stock.trading_currency, 
                    stock.current_currency, 
                    start_date
                )
                if conversion_data is not None:
                    transformed_data = self.apply_currency_conversion(transformed_data, conversion_data)
            
            # Load data into database
            success = self.load_historical_prices(transformed_data)
            
            # Update current price if we have today's data
            today = datetime.now().date()
            today_record = next((r for r in transformed_data if r['date'] == today), None)
            if today_record and today_record['close_price']:
                self.update_stock_current_price(stock_id, today_record['close_price'])
            
            return success
            
        except Exception as e:
            logger.error(f"Error in ETL process for stock {stock_id}: {str(e)}")
            return False

    
    def verify_stock(self, yahoo_symbol: str) -> Dict:
        """
        Enhanced verification for stock assignment - gets comprehensive stock data.
        Used during market assignment to provide rich stock information.
        
        Args:
            yahoo_symbol: Yahoo Finance stock symbol
            
        Returns:
            Dict: Enhanced verification result with comprehensive stock data
        """
        try:
            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info
            
            # Get basic stock information
            name = info.get('longName') or info.get('shortName')
            
            # Basic existence check
            if not info or not name:
                return {
                    'success': False,
                    'error': f'Stock {yahoo_symbol} not found on Yahoo Finance'
                }
            
            # Get current price information
            current_price = (
                info.get('currentPrice', 0.0) or
                info.get('regularMarketPrice', 0.0) or
                info.get('previousClose', 0.0) or
                info.get('lastPrice', 0.0)
            )
            
            # If still no price, try from history
            if not current_price:
                try:
                    hist = ticker.history(period="1d", auto_adjust=False)
                    if not hist.empty:
                        current_price = float(hist['Close'].iloc[-1])
                except:
                    current_price = 0.0
            
            # Get currency information
            currency = info.get('currency', 'USD')
            
            # Get market information
            market_cap = info.get('marketCap')
            sector = info.get('sector')
            industry = info.get('industry')
            exchange = info.get('exchange')
            country = info.get('country')
            
            # Format market cap for display
            market_cap_formatted = None
            if market_cap:
                if market_cap >= 1e12:
                    market_cap_formatted = f"${market_cap/1e12:.2f}T"
                elif market_cap >= 1e9:
                    market_cap_formatted = f"${market_cap/1e9:.2f}B"
                elif market_cap >= 1e6:
                    market_cap_formatted = f"${market_cap/1e6:.2f}M"
                else:
                    market_cap_formatted = f"${market_cap:,.0f}"
            
            return {
                'success': True,
                'name': name,
                'currency': currency,
                'current_price': float(current_price) if current_price else 0.0,
                'market_cap': market_cap,
                'market_cap_formatted': market_cap_formatted,
                'sector': sector,
                'industry': industry,
                'exchange': exchange,
                'country': country,
                'exists': True
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced verification for {yahoo_symbol}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
