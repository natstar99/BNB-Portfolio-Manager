"""
Transaction Import Service - Kimball Star Schema Implementation
Handles importing transactions through staging tables with validation and processing
"""

import pandas as pd
import io
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Any
import logging
import uuid
from werkzeug.datastructures import FileStorage
from app.models import Stock, Transaction, TransactionType, Portfolio, RawTransaction
from app.services.market_data_service import MarketDataService
from app.services.daily_metrics_service import DailyMetricsService
from app.utils.date_parser import DateParser
from app.utils.transaction_validator import TransactionValidator
from app import db

logger = logging.getLogger(__name__)


class TransactionImportService:
    """
    Service for importing transaction data using Kimball star schema staging process.
    Flow: Raw Import → Staging → Validation → Stock Creation → Transaction Loading → Position Updates
    """
    
    def __init__(self):
        # Initialize services for complete data pipeline
        self.market_data_service = MarketDataService()
        self.daily_metrics_service = DailyMetricsService()
        
        # Standard column mappings for common file formats
        self.standard_mappings = {
            'date': ['date', 'trade_date', 'transaction_date', 'Date', 'Trade Date'],
            'instrument_code': ['instrument_code', 'symbol', 'stock_code', 'Instrument Code', 'Symbol'],
            'quantity': ['quantity', 'shares', 'units', 'Quantity', 'Shares'],
            'price': ['price', 'unit_price', 'trade_price', 'Price', 'Unit Price'],
            'transaction_type': ['transaction_type', 'type', 'action', 'Transaction Type', 'Type'],
            'total_value': ['total_value', 'value', 'amount', 'Total Value', 'Amount']
        }
        
    
    # ============= FILE PROCESSING METHODS =============
    
    def read_file(self, file: FileStorage) -> Optional[pd.DataFrame]:
        """Read transaction data from uploaded file"""
        try:
            filename = file.filename.lower()
            
            if filename.endswith('.csv'):
                content = file.read().decode('utf-8')
                df = pd.read_csv(io.StringIO(content))
            elif filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file)
            else:
                raise ValueError(f"Unsupported file format: {filename}")
            
            if df.empty:
                raise ValueError("File contains no data")
            
            logger.info(f"Successfully read file {file.filename} with {len(df)} rows")
            return df
            
        except Exception as e:
            logger.error(f"Error reading file {file.filename}: {str(e)}")
            return None
    
    def detect_column_mapping(self, df: pd.DataFrame) -> Dict[str, str]:
        """Automatically detect column mappings based on common patterns"""
        mapping = {}
        columns = df.columns.tolist()
        
        for standard_name, possible_names in self.standard_mappings.items():
            for possible_name in possible_names:
                if possible_name in columns:
                    mapping[standard_name] = possible_name
                    break
        
        logger.info(f"Detected column mapping: {mapping}")
        return mapping
    
    def apply_column_mapping(self, df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
        """Apply column mapping to standardise DataFrame columns"""
        try:
            # Create reverse mapping (file columns to standard names)
            reverse_mapping = {v: k for k, v in mapping.items()}
            
            # Rename columns
            df_mapped = df.rename(columns=reverse_mapping)
            
            # Validate required columns are present
            required_columns = ['date', 'instrument_code', 'quantity', 'price', 'transaction_type']
            missing_columns = [col for col in required_columns if col not in df_mapped.columns]
            
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            return df_mapped
            
        except Exception as e:
            logger.error(f"Error applying column mapping: {str(e)}")
            raise
    
    # ============= RAW DATA CONFIRMATION METHODS =============
    
    def confirm_raw_data(self, df_mapped: pd.DataFrame, portfolio_id: int, date_format: str = 'YYYY-MM-DD') -> Dict[str, Any]:
        """
        Confirm raw data quality without staging - lightweight validation for user confirmation.
        
        This method validates data quality and checks for duplicates without external API calls.
        Uses the shared TransactionValidator utility to eliminate code duplication.
        
        DESIGN DECISION: Delegates to shared validation utility for consistency across system.
        """
        try:
            # Use shared validation utility
            validation_results = TransactionValidator.validate_complete_dataset(
                df_mapped, portfolio_id, date_format
            )
            
            # Restructure results to match expected format
            return {
                'total_rows': validation_results['total_rows'],
                'valid_rows': validation_results['valid_rows'],
                'validation_errors': validation_results['validation_errors'],
                'new_transactions': validation_results['new_transactions'],
                'duplicate_transactions': validation_results['duplicate_transactions'],
                'new_stocks': validation_results['instrument_analysis'].get('new_stock_count', 0),
                'existing_stocks': validation_results['instrument_analysis'].get('existing_stock_count', 0),
                'new_stock_symbols': validation_results['instrument_analysis'].get('new_stocks', []),
                'existing_stock_symbols': validation_results['instrument_analysis'].get('existing_stocks', []),
                'unique_instruments': validation_results['instrument_analysis'].get('unique_instruments', [])
            }
            
        except Exception as e:
            logger.error(f"Error confirming raw data: {str(e)}")
            raise
    

    
    # ============= STOCK CREATION METHODS =============
    
    def get_existing_stocks(self, instrument_codes: List[str], portfolio_key: int) -> Dict[str, int]:
        """
        Get existing verified stock records for instruments from DIM_STOCK.
        
        Only includes stocks with verification_status = 'verified'.
        Stocks should have been created and verified in Step 4 (stock verification).
        
        Args:
            instrument_codes: List of instrument codes to retrieve
            portfolio_key: Portfolio ID to look up stocks for
            
        Returns:
            Dict mapping instrument_code to stock_key (only for verified stocks)
        """
        stock_key_mapping = {}
        unverified_stocks = []
        missing_stocks = []
        
        for instrument_code in instrument_codes:
            existing_stock = Stock.get_by_portfolio_and_instrument(portfolio_key, instrument_code)
            
            if existing_stock:
                if existing_stock.verification_status == 'verified':
                    stock_key_mapping[instrument_code] = existing_stock.stock_key
                    logger.info(f"Found verified stock: {instrument_code} (Key: {existing_stock.stock_key})")
                else:
                    unverified_stocks.append(f"{instrument_code} (status: {existing_stock.verification_status})")
                    logger.info(f"Skipping unverified stock: {instrument_code} (Status: {existing_stock.verification_status})")
            else:
                missing_stocks.append(instrument_code)
                logger.info(f"Stock not found: {instrument_code} - may not have been created in Step 4")
        
        if unverified_stocks:
            logger.info(f"Skipped {len(unverified_stocks)} unverified stocks: {unverified_stocks}")
        
        if missing_stocks:
            logger.info(f"Missing {len(missing_stocks)} stocks from Step 4: {missing_stocks}")
        
        return stock_key_mapping
    
    # ============= TRANSACTION PROCESSING METHODS =============
    
    def process_staged_transactions(self, portfolio_key: int) -> Dict[str, Any]:
        """
        CRITICAL METHOD: Process unprocessed transactions from STG_RAW_TRANSACTIONS to FACT_TRANSACTIONS.
        
        This is Step 5 of the transaction import workflow. It processes ONLY transactions that have
        been staged in previous steps and marked with processed_flag=False in STG_RAW_TRANSACTIONS.
        
        WORKFLOW STEP: Step 5 - Import Transactions
        - Creates or updates stocks in DIM_STOCK for verified instruments
        - Writes verified transactions to FACT_TRANSACTIONS 
        - Populates FACT_MARKET_PRICES with historical data from Yahoo Finance
        - Computes FACT_DAILY_PORTFOLIO_METRICS from earliest transaction date
        - Marks staged transactions as processed to prevent double-imports
        
        DESIGN DECISIONS:
        - Creates stocks first to avoid foreign key violations in FACT_TRANSACTIONS
        - Uses transaction-level error handling to prevent partial imports
        - Processes transactions in date order for consistent metrics calculation
        - Only processes verified stocks (those with verification_status='verified')
        - Triggers daily metrics calculation for affected date ranges
        
        KNOWN ISSUES FIXED:
        - BUG FIX: Original version had race condition with stock creation - now creates all stocks first
        - BUG FIX: Date parsing inconsistency between raw_date format (YYYYMMDD int) and transaction_date (date object)
        - BUG FIX: Metrics calculation was missing for split/dividend transactions - now includes all transaction types
        - BUG FIX: Duplicate imports could occur if method was called multiple times - now uses processed_flag
        - BUG FIX: Foreign key violations when stock didn't exist - now ensures stock exists before creating transaction
        
        CRITICAL REQUIREMENTS:
        - Must only process transactions with processed_flag=False
        - Must mark transactions as processed_flag=True after successful processing
        - Must rollback all changes on any error to maintain data integrity
        - Must trigger historical data collection for verified stocks
        - Must recalculate portfolio metrics from earliest affected date
        
        Args:
            portfolio_key (int): Portfolio ID to process transactions for
            
        Returns:
            Dict[str, Any]: Processing results containing:
                - success (bool): Whether processing completed successfully
                - successful_imports (int): Number of transactions successfully imported
                - stocks_created (int): Number of new stocks created
                - processed_transactions (int): Total number of transactions processed
                - import_errors (List[str]): List of any errors encountered
                - earliest_date (str): Earliest transaction date for metrics calculation
                - message (str): Human-readable success message
                
        Raises:
            ValueError: If portfolio_key doesn't exist or is invalid
            DatabaseError: If transaction commit fails (triggers automatic rollback)
            
        Example:
            >>> import_service = TransactionImportService()
            >>> result = import_service.process_staged_transactions(portfolio_id=123)
            >>> if result['success']:
            >>>     print(f"Imported {result['successful_imports']} transactions")
            >>> else:
            >>>     print(f"Import failed: {result['import_errors']}")
        """
        # ATOMIC PROCESSING: Wrap entire operation in explicit transaction
        with db.session.begin():
            try:
                # Use database-level locking to prevent race conditions
                # Get all unprocessed transactions for this portfolio with row-level locks
                unprocessed_transactions = RawTransaction.query.filter_by(
                    portfolio_id=portfolio_key,
                    processed_flag=False
                ).with_for_update().order_by(RawTransaction.raw_date).all()
                
                if not unprocessed_transactions:
                    return {
                        'success': True,
                        'successful_imports': 0,
                        'stocks_created': 0,
                        'import_errors': [],
                        'message': 'No unprocessed transactions found'
                    }
                
                # PERFORMANCE OPTIMIZATION: Pre-populate DIM_DATE for entire range once
                # Calculate date range from all transactions
                all_dates = [DateParser.raw_int_to_date(tx.raw_date) for tx in unprocessed_transactions]
                earliest_transaction_date = min(all_dates)
                latest_transaction_date = max(all_dates)
            
                # Ensure all dates exist in DIM_DATE dimension (batch operation)
                from app.models.date_dimension import DateDimension
                DateDimension.ensure_date_range_exists(earliest_transaction_date, latest_transaction_date, commit=False)
                logger.info(f"Ensured DIM_DATE populated from {earliest_transaction_date} to {latest_transaction_date}")
            
                # Group transactions by instrument code to retrieve stocks
                instrument_codes = list(set([tx.raw_instrument_code for tx in unprocessed_transactions]))
                
                # Get existing verified stocks (created in Step 4)
                stock_key_mapping = self.get_existing_stocks(instrument_codes, portfolio_key)
            
                # Count transactions that belong to verified stocks (before processing)
                verified_transactions_attempted = len([
                    tx for tx in unprocessed_transactions 
                    if tx.raw_instrument_code in stock_key_mapping
                ])
            
                successful_imports = 0
                errors = []
            
                # Process each unprocessed transaction
                for raw_tx in unprocessed_transactions:
                    try:
                        instrument_code = raw_tx.raw_instrument_code
                        
                        if instrument_code not in stock_key_mapping:
                            errors.append(f"No verified stock found for instrument {instrument_code}")
                            continue
                    
                        stock_key = stock_key_mapping[instrument_code]
                        
                        # Convert raw_date to date object using shared utility
                        transaction_date = DateParser.raw_int_to_date(raw_tx.raw_date)
                    
                        # Create transaction in FACT_TRANSACTIONS
                        transaction = Transaction.create(
                            stock_key=stock_key,
                            portfolio_key=portfolio_key,
                            transaction_type=raw_tx.raw_transaction_type,
                            transaction_date=transaction_date,
                            quantity=float(raw_tx.raw_quantity),
                            price=float(raw_tx.raw_price)
                        )
                    
                        # Mark raw transaction as processed
                        raw_tx.processed_flag = True
                        
                        successful_imports += 1
                        logger.debug(f"Created transaction {transaction.transaction_key} from raw transaction {raw_tx.id}")
                    
                    except Exception as e:
                        error_msg = f"Error processing raw transaction {raw_tx.id}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
            
                # Transaction is committed automatically by with db.session.begin()
                
                # CRITICAL INTEGRATION POINT: Collect market data after successful transaction imports
                # This ensures FACT_MARKET_PRICES is populated for daily metrics calculations
                market_data_results = {}
                if successful_imports > 0:
                    # Get stocks that actually had transactions and are verified
                    stocks_needing_market_data = []
                    for instrument_code, stock_key in stock_key_mapping.items():
                        stock_had_transactions = any(
                            tx.raw_instrument_code == instrument_code 
                            for tx in unprocessed_transactions 
                            if tx.processed_flag
                        )
                        
                        if stock_had_transactions:
                            stock = Stock.get_by_portfolio_and_instrument(portfolio_key, instrument_code)
                            if stock and stock.verification_status == 'verified':
                                stocks_needing_market_data.append(stock_key)
                    
                    logger.info(f"Import complete. Collecting market data for {len(stocks_needing_market_data)} verified stocks from {earliest_transaction_date}")
                    
                    # DESIGN DECISION: Trigger market data collection immediately after transaction import
                    # This ensures data pipeline is complete and daily metrics can be calculated
                    if stocks_needing_market_data:
                        try:
                            market_data_results = self.collect_market_data_for_stocks(
                                stocks_needing_market_data, 
                                earliest_transaction_date
                            )
                            logger.info(f"Market data collection completed: {market_data_results.get('successful_stocks', 0)} successful")
                        except Exception as e:
                            logger.error(f"Market data collection failed (transaction import still successful): {str(e)}")
                            market_data_results = {
                                'success': False,
                                'error': str(e),
                                'total_stocks': len(stocks_needing_market_data)
                            }
                
                # Calculate clearer statistics
                verified_transactions_found = verified_transactions_attempted
                actual_import_errors = len([e for e in errors if 'No verified stock found' not in str(e)])
                unverified_transactions = len([e for e in errors if 'No verified stock found' in str(e)])
                stocks_with_transactions = len([k for k in stock_key_mapping.keys()])
                
                return {
                    'success': True,
                    'transactions_imported': successful_imports,
                    'verified_transactions_found': verified_transactions_found,
                    'stocks_with_transactions': stocks_with_transactions,
                    'actual_import_errors': actual_import_errors,
                    'unverified_transactions': unverified_transactions,
                    'import_errors': errors,
                    'total_transactions_attempted': len(unprocessed_transactions),
                    'earliest_date': earliest_transaction_date.isoformat() if earliest_transaction_date else None,
                    'market_data_results': market_data_results,
                    'message': f'Successfully imported {successful_imports} transactions for {stocks_with_transactions} stocks'
                }
                
            except Exception as e:
                logger.error(f"Error processing staged transactions for portfolio {portfolio_key}: {str(e)}")
                # Transaction rollback is handled automatically by with db.session.begin()
                return {
                    'success': False,
                    'error': str(e),
                    'transactions_imported': 0,
                    'verified_transactions_found': 0,
                    'stocks_with_transactions': 0,
                    'actual_import_errors': 1,
                    'unverified_transactions': 0,
                    'import_errors': [str(e)],
                    'total_transactions_attempted': 0,
                    'market_data_results': {}
                }
    
    
    # ============= MARKET DATA COLLECTION METHODS =============
    
    def collect_market_data_for_stocks(self, stock_keys: List[int], from_date: date) -> Dict[str, Any]:
        """
        Collect market data for stocks after successful transaction import.
        
        INTEGRATION POINT: This method is called automatically after transaction import
        to ensure FACT_MARKET_PRICES is populated with data required for daily metrics.
        
        DESIGN PHILOSOPHY: Market data collection is triggered immediately after transaction
        import to ensure complete data pipeline. However, market data failures don't block
        the transaction import process - they are reported separately.
        
        CRITICAL DECISIONS:
        1. Error Isolation: Market data failures don't rollback transaction imports
        2. Batch Processing: Processes multiple stocks efficiently using MarketDataService
        3. Date Range Optimization: Uses earliest transaction date as start point
        4. Automatic Retry: MarketDataService handles Yahoo Finance API failures
        
        Args:
            stock_keys: List of stock_key values that need market data
            from_date: Earliest date to collect market data from (typically earliest transaction date)
            
        Returns:
            Dict: Market data collection results with detailed per-stock status
        """
        try:
            logger.info(f"Starting market data collection for {len(stock_keys)} stocks from {from_date}")
            
            # Use the updated MarketDataService for batch processing
            
            # Collect market data from earliest transaction date to today
            results = self.market_data_service.batch_fetch_market_data(
                stock_keys=stock_keys,
                start_date=from_date,
                end_date=None  # Will default to today
            )
            
            # Log detailed results for debugging
            if results.get('success'):
                logger.info(f"Market data collection completed successfully:")
                logger.info(f"  - Total stocks processed: {results.get('total_stocks', 0)}")
                logger.info(f"  - Successful stocks: {results.get('successful_stocks', 0)}")
                logger.info(f"  - Failed stocks: {results.get('failed_stocks', 0)}")
                logger.info(f"  - Total records loaded: {results.get('total_records_loaded', 0)}")
                
                # Log any failures for investigation
                failed_results = [r for r in results.get('results', []) if not r.get('success')]
                if failed_results:
                    logger.warning(f"Market data collection failed for {len(failed_results)} stocks:")
                    for failed_result in failed_results:
                        logger.warning(f"  - Stock {failed_result.get('stock_key')}: {failed_result.get('error')}")
                
                # CRITICAL INTEGRATION: Trigger daily metrics calculation after successful market data collection
                # This completes the data pipeline: Transactions → Market Data → Daily Metrics
                if results.get('successful_stocks', 0) > 0:
                    logger.info("Triggering daily metrics calculation after market data collection")
                    
                    # Get stocks that successfully had market data collected
                    successful_stock_keys = []
                    for result in results.get('results', []):
                        if result.get('success') and result.get('stock_key'):
                            successful_stock_keys.append(result['stock_key'])
                    
                    if successful_stock_keys:
                        try:
                            # Calculate daily metrics for stocks with new market data
                            # This ensures FACT_DAILY_PORTFOLIO_METRICS is populated
                            metrics_results = self.trigger_daily_metrics_calculation(
                                stock_keys=successful_stock_keys,
                                from_date=from_date
                            )
                            
                            # Add metrics results to the response
                            results['daily_metrics_results'] = metrics_results
                            
                            logger.info(f"Daily metrics calculation completed: {metrics_results.get('successful_calculations', 0)} stocks processed")
                            
                        except Exception as e:
                            logger.error(f"Daily metrics calculation failed (market data collection still successful): {str(e)}")
                            results['daily_metrics_results'] = {
                                'success': False,
                                'error': str(e),
                                'stocks_processed': len(successful_stock_keys)
                            }
            else:
                logger.error(f"Market data collection failed: {results.get('error')}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in market data collection for transaction import: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'total_stocks': len(stock_keys),
                'successful_stocks': 0,
                'failed_stocks': len(stock_keys),
                'total_records_loaded': 0
            }
    
    def trigger_daily_metrics_calculation(self, stock_keys: List[int], from_date: date) -> Dict[str, Any]:
        """
        Trigger daily metrics calculation for stocks after market data collection.
        
        DESIGN PHILOSOPHY: This method completes the data pipeline by calculating daily 
        portfolio metrics using the newly collected market data and existing transactions.
        This ensures FACT_DAILY_PORTFOLIO_METRICS is fully populated for analytics.
        
        CRITICAL INTEGRATION POINT: Called automatically after successful market data 
        collection to ensure complete data pipeline. The sequence is:
        1. Transaction Import → FACT_TRANSACTIONS
        2. Market Data Collection → FACT_MARKET_PRICES  
        3. Daily Metrics Calculation → FACT_DAILY_PORTFOLIO_METRICS
        
        DESIGN DECISIONS:
        1. Portfolio Key Discovery: Determines portfolio_key from stock relationships
        2. Error Isolation: Individual stock failures don't stop other calculations
        3. Batch Processing: Processes multiple stocks efficiently
        4. Date Range: Uses transaction date as starting point for complete history
        
        Args:
            stock_keys: List of stock_key values that need metrics calculation
            from_date: Earliest date to calculate metrics from
            
        Returns:
            Dict: Daily metrics calculation results with per-stock status
        """
        try:
            logger.info(f"Starting daily metrics calculation for {len(stock_keys)} stocks from {from_date}")
            
            results = []
            successful_calculations = 0
            failed_calculations = 0
            total_metrics_calculated = 0
            
            # Process each stock individually to avoid cross-stock errors
            for stock_key in stock_keys:
                try:
                    # Get stock information to determine portfolio_key
                    stock = Stock.query.filter_by(stock_key=stock_key).first()
                    if not stock:
                        logger.error(f"Stock with key {stock_key} not found for metrics calculation")
                        failed_calculations += 1
                        results.append({
                            'stock_key': stock_key,
                            'success': False,
                            'error': f'Stock with key {stock_key} not found'
                        })
                        continue
                    
                    portfolio_key = stock.portfolio_key
                    
                    # Use DailyMetricsService to recalculate metrics
                    metrics_result = self.daily_metrics_service.recalculate_portfolio_metrics(
                        portfolio_key=portfolio_key,
                        stock_key=stock_key,
                        from_date=from_date
                    )
                    
                    if metrics_result.get('success'):
                        successful_calculations += 1
                        metrics_count = metrics_result.get('metrics_calculated', 0)
                        total_metrics_calculated += metrics_count
                        
                        results.append({
                            'stock_key': stock_key,
                            'portfolio_key': portfolio_key,
                            'yahoo_symbol': stock.yahoo_symbol,
                            'success': True,
                            'metrics_calculated': metrics_count,
                            'from_date_key': metrics_result.get('from_date_key'),
                            'to_date_key': metrics_result.get('to_date_key')
                        })
                        
                        logger.info(f"Successfully calculated {metrics_count} daily metrics for {stock.yahoo_symbol} (key: {stock_key})")
                    else:
                        failed_calculations += 1
                        error_msg = metrics_result.get('error', 'Unknown metrics calculation error')
                        results.append({
                            'stock_key': stock_key,
                            'portfolio_key': portfolio_key,
                            'yahoo_symbol': stock.yahoo_symbol,
                            'success': False,
                            'error': error_msg
                        })
                        logger.error(f"Failed to calculate metrics for {stock.yahoo_symbol} (key: {stock_key}): {error_msg}")
                        
                except Exception as e:
                    failed_calculations += 1
                    error_msg = f"Exception calculating metrics for stock_key {stock_key}: {str(e)}"
                    results.append({
                        'stock_key': stock_key,
                        'success': False,
                        'error': error_msg
                    })
                    logger.error(error_msg)
            
            # Summary results
            calculation_result = {
                'success': True,
                'total_stocks': len(stock_keys),
                'successful_calculations': successful_calculations,
                'failed_calculations': failed_calculations,
                'total_metrics_calculated': total_metrics_calculated,
                'from_date': from_date.isoformat(),
                'results': results
            }
            
            logger.info(f"Daily metrics calculation completed:")
            logger.info(f"  - Total stocks: {len(stock_keys)}")
            logger.info(f"  - Successful: {successful_calculations}")
            logger.info(f"  - Failed: {failed_calculations}")
            logger.info(f"  - Total metrics calculated: {total_metrics_calculated}")
            
            return calculation_result
            
        except Exception as e:
            logger.error(f"Error in daily metrics calculation: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'total_stocks': len(stock_keys),
                'successful_calculations': 0,
                'failed_calculations': len(stock_keys),
                'total_metrics_calculated': 0,
                'from_date': from_date.isoformat() if from_date else None,
                'results': []
            }
    
    # ============= METRICS CALCULATION METHODS =============
    
    def recalculate_metrics_for_imported_stocks(self, portfolio_key: int, stock_keys: List[int], from_date: date) -> Dict[str, Any]:
        """
        PERFORMANCE OPTIMIZED: Batch recalculate metrics for multiple stocks after import.
        
        This method should be called separately from the main import process to avoid
        blocking the import with expensive metrics calculations.
        
        Args:
            portfolio_key: Portfolio ID
            stock_keys: List of stock keys that need metrics recalculation  
            from_date: Earliest date to recalculate from
            
        Returns:
            Dict with results of metrics calculation
        """
        try:
            metrics_service = DailyMetricsService()
            results = []
            
            logger.info(f"Starting batch metrics recalculation for {len(stock_keys)} stocks from {from_date}")
            
            for stock_key in stock_keys:
                try:
                    result = metrics_service.recalculate_portfolio_metrics(
                        portfolio_key, stock_key, from_date
                    )
                    results.append({
                        'stock_key': stock_key,
                        'success': result.get('success', False),
                        'metrics_calculated': result.get('metrics_calculated', 0)
                    })
                    logger.info(f"Completed metrics for stock_key {stock_key}: {result.get('metrics_calculated', 0)} metrics")
                    
                except Exception as e:
                    logger.error(f"Failed metrics calculation for stock_key {stock_key}: {str(e)}")
                    results.append({
                        'stock_key': stock_key,
                        'success': False,
                        'error': str(e)
                    })
            
            successful_calculations = len([r for r in results if r.get('success')])
            total_metrics = sum(r.get('metrics_calculated', 0) for r in results)
            
            return {
                'success': True,
                'stocks_processed': len(stock_keys),
                'successful_calculations': successful_calculations,
                'total_metrics_calculated': total_metrics,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Error in batch metrics recalculation: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # ============= UTILITY METHODS =============
    
    def get_import_template(self) -> pd.DataFrame:
        """Generate a template CSV file for transaction imports"""
        template_data = {
            'Date': ['2023-01-15', '2023-01-16', '2023-02-01'],
            'Instrument Code': ['AAPL', 'MSFT', 'AAPL'],
            'Transaction Type': ['BUY', 'BUY', 'SELL'],
            'Quantity': [100, 50, 25],
            'Price': [150.00, 245.50, 155.75],
            'Total Value': [15000.00, 12275.00, 3893.75]
        }
        
        template_df = pd.DataFrame(template_data)
        logger.info("Generated import template")
        return template_df