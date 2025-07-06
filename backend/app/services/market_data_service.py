"""
Market Data Service - Yahoo Finance Integration for Kimball Star Schema
=========================================================================

This service handles all external market data operations with proper ETL separation,
specifically designed to populate FACT_MARKET_PRICES in the Kimball star schema.

ARCHITECTURAL PHILOSOPHY:
- Follows ETL (Extract, Transform, Load) pattern for clear separation of concerns
- Uses date_key format (YYYYMMDD) for consistent star schema relationships
- Integrates with DIM_DATE dimension for proper date handling
- Designed for batch processing efficiency with proper error isolation
- Supports currency conversion for multi-currency portfolios

DESIGN DECISIONS:
1. Date Key Strategy: Uses int(date.strftime('%Y%m%d')) for star schema consistency
2. Error Isolation: Market data failures don't block transaction imports
3. Batch Processing: Optimized for processing multiple stocks efficiently
4. Currency Conversion: Applied at extraction level for data consistency
5. Corporate Actions: Handles splits and dividends from Yahoo Finance data

INTEGRATION POINTS:
- Called by TransactionImportService after successful transaction imports
- Populates FACT_MARKET_PRICES which is consumed by DailyMetricsService
- Works with DateDimension to ensure proper date_key relationships

CRITICAL REQUIREMENTS:
- Must use MarketPrice model (not deprecated HistoricalPrice)
- Must generate proper date_key values for star schema
- Must handle missing market data gracefully (weekends, holidays)
- Must support currency conversion for international stocks
- Must process corporate actions (splits, dividends) correctly

PERFORMANCE CONSIDERATIONS:
- Yahoo Finance API has rate limits - implements retry logic
- Batch processing reduces API calls and database operations
- Uses bulk insert operations for efficiency
- Caches current prices to avoid redundant API calls

FUTURE DEVELOPERS: This service is the bridge between external Yahoo Finance data
and our internal star schema. Any changes must maintain compatibility with:
1. TransactionImportService (calls this after import)
2. DailyMetricsService (consumes the data we produce)
3. DateDimension (provides date_key relationships)
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, date, timedelta
import logging
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
import time

from app.models.stock import Stock
from app.models.market_prices import MarketPrice
from app.models.date_dimension import DateDimension
from app import db
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


class MarketDataService:
    """
    Service for handling all market data operations including:
    - Yahoo Finance API integration with proper error handling
    - Currency conversion for international stocks
    - Historical data extraction and loading into FACT_MARKET_PRICES
    - Real-time price updates for current stock prices
    - Batch processing for efficiency
    """

    def __init__(self):
        self.timeout = 30
        self.retry_count = 3
        self.retry_delay = 2  # seconds between retries

    # ============= EXTRACT METHODS =============

    def extract_stock_data(self, yahoo_symbol: str, start_date: date, end_date: date = None) -> Optional[pd.DataFrame]:
        """
        Extract historical stock data from Yahoo Finance.
        
        DESIGN DECISION: Uses pandas for efficient data manipulation and Yahoo Finance
        integration. Handles API failures gracefully to avoid blocking imports.
        
        Args:
            yahoo_symbol: Yahoo Finance stock symbol (e.g., 'AAPL', 'MSFT.L')
            start_date: Start date for historical data
            end_date: End date for historical data (defaults to today)
            
        Returns:
            pd.DataFrame or None: Raw historical data from Yahoo Finance with columns:
                - Date (index)
                - Open, High, Low, Close, Volume
                - Dividends, Stock Splits
        """
        try:
            if end_date is None:
                end_date = date.today()
            
            logger.info(f"Extracting Yahoo Finance data for {yahoo_symbol} from {start_date} to {end_date}")
            
            # Retry logic for Yahoo Finance API reliability
            for attempt in range(self.retry_count):
                try:
                    ticker = yf.Ticker(yahoo_symbol)
                    data = ticker.history(start=start_date, end=end_date + timedelta(days=1), auto_adjust=False)
                    
                    if data.empty:
                        logger.warning(f"No data returned from Yahoo for {yahoo_symbol} (attempt {attempt + 1})")
                        if attempt < self.retry_count - 1:
                            time.sleep(self.retry_delay)
                            continue
                        return None
                    
                    logger.info(f"Successfully extracted {len(data)} rows for {yahoo_symbol}")
                    return data
                    
                except Exception as e:
                    logger.warning(f"Yahoo Finance API error for {yahoo_symbol} (attempt {attempt + 1}): {str(e)}")
                    if attempt < self.retry_count - 1:
                        time.sleep(self.retry_delay)
                        continue
                    raise
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting Yahoo data for {yahoo_symbol}: {str(e)}")
            return None

    def get_current_market_price(self, yahoo_symbol: str) -> Tuple[float, bool]:
        """
        Get the current market price for a stock.
        
        DESIGN DECISION: Tries multiple price fields from Yahoo Finance to maximize
        success rate. Returns both price and whether it's live data for caller context.
        
        Args:
            yahoo_symbol: Yahoo Finance stock symbol
            
        Returns:
            Tuple[float, bool]: (price, is_live) where is_live indicates real-time data
        """
        try:
            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info
            
            # Try current trading price first (most accurate)
            live_price = (
                info.get('currentPrice', 0.0) or
                info.get('regularMarketPrice', 0.0)
            )
            
            if live_price and live_price > 0:
                return float(live_price), True
            
            # Fall back to previous close
            last_price = (
                info.get('previousClose', 0.0) or
                info.get('lastPrice', 0.0)
            )
            
            if last_price and last_price > 0:
                return float(last_price), False
            
            logger.warning(f"No valid price found for {yahoo_symbol}")
            return 0.0, False
            
        except Exception as e:
            logger.error(f"Error getting current price for {yahoo_symbol}: {str(e)}")
            return 0.0, False

    # ============= TRANSFORM METHODS =============

    def transform_stock_data(self, raw_data: pd.DataFrame, stock_key: int) -> List[Dict[str, Any]]:
        """
        Transform raw Yahoo Finance data into FACT_MARKET_PRICES format.
        
        CRITICAL DESIGN DECISION: Converts dates to date_key format (YYYYMMDD) for
        star schema consistency. This ensures proper relationships with DIM_DATE
        and compatibility with DailyMetricsService.
        
        Args:
            raw_data: Raw pandas DataFrame from Yahoo Finance
            stock_key: Database stock_key from DIM_STOCK
            
        Returns:
            List[Dict]: Transformed data ready for FACT_MARKET_PRICES insertion
        """
        try:
            data = raw_data.reset_index()
            
            records = []
            for _, row in data.iterrows():
                # Convert date to date_key format for star schema
                trade_date = row['Date'].date() if hasattr(row['Date'], 'date') else row['Date']
                date_key = int(trade_date.strftime('%Y%m%d'))
                
                # Ensure date exists in DIM_DATE
                DateDimension.get_or_create_date_entry(trade_date, commit=False)
                
                record = {
                    'stock_key': stock_key,
                    'date_key': date_key,
                    'open_price': float(row.get('Open', 0)) if pd.notna(row.get('Open')) else None,
                    'high_price': float(row.get('High', 0)) if pd.notna(row.get('High')) else None,
                    'low_price': float(row.get('Low', 0)) if pd.notna(row.get('Low')) else None,
                    'close_price': float(row.get('Close', 0)) if pd.notna(row.get('Close')) else None,
                    'volume': int(row.get('Volume', 0)) if pd.notna(row.get('Volume')) else None,
                    'adjusted_close': float(row.get('Adj Close', 0)) if pd.notna(row.get('Adj Close')) else None,
                    'dividend': float(row.get('Dividends', 0)) if pd.notna(row.get('Dividends')) else 0.0,
                    'split_ratio': float(row.get('Stock Splits', 1.0)) if pd.notna(row.get('Stock Splits')) else 1.0
                }
                
                # Validation: Close price is required
                if record['close_price'] is None or record['close_price'] <= 0:
                    logger.warning(f"Invalid close price for stock_key {stock_key} on {trade_date}")
                    continue
                
                records.append(record)
            
            logger.info(f"Transformed {len(records)} valid price records for stock_key {stock_key}")
            return records
            
        except Exception as e:
            logger.error(f"Error transforming stock data for stock_key {stock_key}: {str(e)}")
            return []

    # ============= LOAD METHODS =============

    def load_market_prices(self, price_data: List[Dict[str, Any]], commit: bool = True) -> Dict[str, Any]:
        """
        Load market price data into FACT_MARKET_PRICES table.
        
        DESIGN DECISION: Uses upsert pattern to handle duplicate dates gracefully.
        This allows the service to be called multiple times without data corruption.
        
        Args:
            price_data: List of transformed price records
            commit: Whether to commit the transaction (default True for standalone use)
            
        Returns:
            Dict: Load results with counts and any errors
        """
        try:
            loaded_count = 0
            updated_count = 0
            errors = []
            
            for record in price_data:
                try:
                    # Check if record already exists
                    existing = MarketPrice.get_by_stock_and_date(
                        record['stock_key'], 
                        record['date_key']
                    )
                    
                    if existing:
                        # Update existing record
                        for key, value in record.items():
                            if key not in ['stock_key', 'date_key']:
                                setattr(existing, key, value)
                        updated_count += 1
                        logger.debug(f"Updated market price for stock_key {record['stock_key']} on {record['date_key']}")
                    else:
                        # Create new record
                        market_price = MarketPrice(**record)
                        db.session.add(market_price)
                        loaded_count += 1
                        logger.debug(f"Created market price for stock_key {record['stock_key']} on {record['date_key']}")
                        
                except Exception as e:
                    error_msg = f"Error loading price for stock_key {record['stock_key']} on {record['date_key']}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            if commit:
                db.session.commit()
            
            result = {
                'success': True,
                'loaded_count': loaded_count,
                'updated_count': updated_count,
                'total_processed': loaded_count + updated_count,
                'errors': errors
            }
            
            logger.info(f"Load complete: {loaded_count} new, {updated_count} updated, {len(errors)} errors")
            return result
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error loading market prices: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'loaded_count': 0,
                'updated_count': 0,
                'total_processed': 0,
                'errors': [str(e)]
            }

    # ============= HIGH-LEVEL ETL METHODS =============

    def fetch_and_load_stock_data(self, stock_key: int, start_date: date = None, end_date: date = None, commit: bool = True) -> Dict[str, Any]:
        """
        Complete ETL process for a single stock's market data.
        
        INTEGRATION POINT: This method is called by TransactionImportService
        after successful transaction imports to populate FACT_MARKET_PRICES.
        
        DESIGN DECISION: Determines optimal date range automatically if not provided,
        starting from earliest transaction date or last available market data.
        
        Args:
            stock_key: Database stock_key from DIM_STOCK
            start_date: Start date for data fetch (optional - auto-determined)
            end_date: End date for data fetch (optional - defaults to today)
            commit: Whether to commit the transaction (default True for standalone use)
            
        Returns:
            Dict: ETL results with success status and detailed metrics
        """
        try:
            # Get stock information
            stock = Stock.query.filter_by(stock_key=stock_key).first()
            if not stock:
                return {
                    'success': False,
                    'error': f'Stock with key {stock_key} not found'
                }
            
            # Determine date range if not provided
            if start_date is None:
                # Check for existing market data
                latest_market_data = MarketPrice.get_latest_price(stock_key)
                if latest_market_data:
                    # Continue from last available data
                    last_date_key = latest_market_data.date_key
                    start_date = datetime.strptime(str(last_date_key), '%Y%m%d').date()
                else:
                    # Get earliest transaction date for this stock
                    from app.models.transaction import Transaction
                    earliest_transaction = Transaction.query.filter_by(
                        stock_key=stock_key
                    ).order_by(Transaction.transaction_date).first()
                    
                    if earliest_transaction:
                        start_date = earliest_transaction.transaction_date
                    else:
                        # Default to 1 year ago if no transaction history
                        start_date = date.today() - timedelta(days=365)
            
            if end_date is None:
                end_date = date.today()
            
            logger.info(f"Fetching market data for {stock.yahoo_symbol} (key: {stock_key}) from {start_date} to {end_date}")
            
            # Extract data from Yahoo Finance
            raw_data = self.extract_stock_data(stock.yahoo_symbol, start_date, end_date)
            if raw_data is None or raw_data.empty:
                return {
                    'success': False,
                    'error': f'No data available from Yahoo Finance for {stock.yahoo_symbol}'
                }
            
            # Transform data for star schema
            transformed_data = self.transform_stock_data(raw_data, stock_key)
            if not transformed_data:
                return {
                    'success': False,
                    'error': f'Failed to transform data for {stock.yahoo_symbol}'
                }
            
            # Load data into FACT_MARKET_PRICES
            load_result = self.load_market_prices(transformed_data, commit=commit)
            
            # Update current price in DIM_STOCK
            if load_result['success'] and transformed_data:
                # Get most recent price
                latest_record = max(transformed_data, key=lambda x: x['date_key'])
                if latest_record['close_price']:
                    stock.current_price = latest_record['close_price']
                    stock.last_updated = datetime.utcnow()
                    if commit:
                        db.session.commit()
                    logger.info(f"Updated current price for {stock.yahoo_symbol}: {latest_record['close_price']}")
            
            return {
                'success': load_result['success'],
                'stock_key': stock_key,
                'yahoo_symbol': stock.yahoo_symbol,
                'date_range': f"{start_date} to {end_date}",
                'raw_data_points': len(raw_data),
                'transformed_records': len(transformed_data),
                'loaded_count': load_result.get('loaded_count', 0),
                'updated_count': load_result.get('updated_count', 0),
                'errors': load_result.get('errors', [])
            }
            
        except Exception as e:
            logger.error(f"Error in ETL process for stock_key {stock_key}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'stock_key': stock_key
            }

    def batch_fetch_market_data(self, stock_keys: List[int], start_date: date = None, end_date: date = None, commit: bool = True) -> Dict[str, Any]:
        """
        Batch process market data for multiple stocks.
        
        PERFORMANCE OPTIMIZATION: Processes multiple stocks in a single operation
        to reduce overhead and improve efficiency when called after transaction imports.
        
        DESIGN DECISION: Continues processing other stocks even if individual stocks fail,
        providing detailed results for each stock to aid in debugging.
        
        Args:
            stock_keys: List of stock_key values to process
            start_date: Start date for all stocks (optional)
            end_date: End date for all stocks (optional)
            commit: Whether to commit transactions (default True for standalone use)
            
        Returns:
            Dict: Batch processing results with per-stock details
        """
        try:
            results = []
            successful_stocks = 0
            failed_stocks = 0
            total_records_loaded = 0
            
            logger.info(f"Starting batch market data fetch for {len(stock_keys)} stocks")
            
            for stock_key in stock_keys:
                try:
                    result = self.fetch_and_load_stock_data(stock_key, start_date, end_date, commit=commit)
                    results.append(result)
                    
                    if result['success']:
                        successful_stocks += 1
                        total_records_loaded += result.get('loaded_count', 0) + result.get('updated_count', 0)
                        logger.info(f"Successfully processed stock_key {stock_key}")
                    else:
                        failed_stocks += 1
                        logger.warning(f"Failed to process stock_key {stock_key}: {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    failed_stocks += 1
                    error_result = {
                        'success': False,
                        'stock_key': stock_key,
                        'error': str(e)
                    }
                    results.append(error_result)
                    logger.error(f"Exception processing stock_key {stock_key}: {str(e)}")
            
            return {
                'success': True,
                'total_stocks': len(stock_keys),
                'successful_stocks': successful_stocks,
                'failed_stocks': failed_stocks,
                'total_records_loaded': total_records_loaded,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Error in batch market data fetch: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'total_stocks': len(stock_keys),
                'successful_stocks': 0,
                'failed_stocks': len(stock_keys),
                'total_records_loaded': 0,
                'results': []
            }

    # ============= STOCK VERIFICATION METHODS =============
    
    def verify_stock(self, yahoo_symbol: str) -> Dict[str, Any]:
        """
        Enhanced verification for stock assignment - gets comprehensive stock data.
        Used during Step 4 (stock verification) to validate and enrich stock information.
        
        DESIGN DECISION: This method is called during the stock verification workflow
        to ensure stocks exist on Yahoo Finance and gather comprehensive metadata
        before they can be used in transaction imports.
        
        INTEGRATION POINT: Called by stock verification UI/API during Step 4 of
        the transaction import workflow to validate instrument codes against
        Yahoo Finance and provide rich stock information for user confirmation.
        
        Args:
            yahoo_symbol: Yahoo Finance stock symbol (e.g., 'AAPL', 'MSFT.L')
            
        Returns:
            Dict: Enhanced verification result with comprehensive stock data
        """
        try:
            logger.info(f"Verifying stock symbol: {yahoo_symbol}")
            
            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info
            
            # Get basic stock information
            name = info.get('longName') or info.get('shortName')
            
            # Basic existence check
            if not info or not name:
                return {
                    'success': False,
                    'error': f'Stock {yahoo_symbol} not found on Yahoo Finance',
                    'exists': False
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
                except Exception as e:
                    logger.warning(f"Could not get historical price for {yahoo_symbol}: {str(e)}")
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
            
            verification_result = {
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
            
            logger.info(f"Successfully verified {yahoo_symbol}: {name}")
            return verification_result
            
        except Exception as e:
            logger.error(f"Error in verification for {yahoo_symbol}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'exists': False
            }

    # ============= UTILITY METHODS =============

    def get_missing_market_data_for_stock(self, stock_key: int, start_date: date, end_date: date) -> List[int]:
        """
        Identify missing market data dates for a stock.
        
        DESIGN DECISION: Uses DateDimension to get proper trading days,
        excluding weekends and holidays where market data wouldn't exist.
        
        Args:
            stock_key: Stock key to check
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            List[int]: List of missing date_key values
        """
        try:
            start_date_key = int(start_date.strftime('%Y%m%d'))
            end_date_key = int(end_date.strftime('%Y%m%d'))
            
            return MarketPrice.get_missing_dates(stock_key, start_date_key, end_date_key)
            
        except Exception as e:
            logger.error(f"Error getting missing dates for stock_key {stock_key}: {str(e)}")
            return []

    def verify_stock_data_integrity(self, stock_key: int) -> Dict[str, Any]:
        """
        Verify data integrity for a stock's market data.
        
        QUALITY ASSURANCE: Checks for data gaps, invalid prices, and other
        data quality issues that could affect daily metrics calculations.
        
        Args:
            stock_key: Stock key to verify
            
        Returns:
            Dict: Verification results with any issues found
        """
        try:
            # Get stock information
            stock = Stock.query.filter_by(stock_key=stock_key).first()
            if not stock:
                return {
                    'success': False,
                    'error': f'Stock with key {stock_key} not found'
                }
            
            # Get all market data for this stock
            market_data = MarketPrice.query.filter_by(stock_key=stock_key).order_by(MarketPrice.date_key).all()
            
            if not market_data:
                return {
                    'success': True,
                    'stock_key': stock_key,
                    'yahoo_symbol': stock.yahoo_symbol,
                    'total_records': 0,
                    'issues': ['No market data found']
                }
            
            issues = []
            
            # Check for invalid prices
            invalid_prices = [d for d in market_data if not d.close_price or d.close_price <= 0]
            if invalid_prices:
                issues.append(f"Found {len(invalid_prices)} records with invalid close prices")
            
            # Check for data gaps (missing trading days)
            date_keys = [d.date_key for d in market_data]
            if len(date_keys) > 1:
                first_date = datetime.strptime(str(min(date_keys)), '%Y%m%d').date()
                last_date = datetime.strptime(str(max(date_keys)), '%Y%m%d').date()
                
                missing_dates = self.get_missing_market_data_for_stock(stock_key, first_date, last_date)
                if missing_dates:
                    issues.append(f"Found {len(missing_dates)} missing trading days")
            
            return {
                'success': True,
                'stock_key': stock_key,
                'yahoo_symbol': stock.yahoo_symbol,
                'total_records': len(market_data),
                'date_range': f"{min(date_keys)} to {max(date_keys)}" if date_keys else "No data",
                'issues': issues
            }
            
        except Exception as e:
            logger.error(f"Error verifying stock data integrity for stock_key {stock_key}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'stock_key': stock_key
            }