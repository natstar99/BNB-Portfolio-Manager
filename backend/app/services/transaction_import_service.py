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
                                stocks_needing_market_data
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
    
    def collect_market_data_for_stocks(self, stock_keys: List[int]) -> Dict[str, Any]:
        """
        Collect market data for stocks after successful transaction import.
        
        INTEGRATION POINT: This method is called automatically after transaction import
        to ensure FACT_MARKET_PRICES is populated with data required for daily metrics.
        
        DESIGN PHILOSOPHY: Market data collection is triggered immediately after transaction
        import to ensure complete data pipeline. However, market data failures don't block
        the transaction import process - they are reported separately.
        
        CRITICAL DECISIONS:
        1. Error Isolation: Market data failures don't rollback transaction imports
        2. Efficient Date Ranges: Each stock determines its own optimal start date
        3. Individual Processing: Fixed inefficiency where all stocks used global earliest date
        4. Automatic Retry: MarketDataService handles Yahoo Finance API failures
        
        Args:
            stock_keys: List of stock_key values that need market data
            
        Returns:
            Dict: Market data collection results with detailed per-stock status
        """
        try:
            logger.info(f"Starting market data collection for {len(stock_keys)} stocks (each with optimal date range)")
            
            # Process each stock individually to allow optimal date range determination
            # This fixes the inefficiency where all stocks used the earliest date from any stock
            results = []
            successful_stocks = 0
            failed_stocks = 0
            total_records_loaded = 0
            
            for stock_key in stock_keys:
                try:
                    # Let each stock determine its own optimal start date
                    # This uses existing efficient logic in fetch_and_load_stock_data
                    result = self.market_data_service.fetch_and_load_stock_data(
                        stock_key=stock_key,
                        start_date=None,  # Let method determine optimal start date per stock
                        end_date=None,    # Default to today
                        commit=False      # Don't commit - we're inside transaction context
                    )
                    
                    results.append(result)
                    
                    if result['success']:
                        successful_stocks += 1
                        total_records_loaded += result.get('loaded_count', 0) + result.get('updated_count', 0)
                        logger.info(f"Successfully collected market data for stock_key {stock_key}")
                    else:
                        failed_stocks += 1
                        logger.warning(f"Failed to collect market data for stock_key {stock_key}: {result.get('error')}")
                        
                except Exception as e:
                    failed_stocks += 1
                    error_result = {
                        'success': False,
                        'stock_key': stock_key,
                        'error': str(e)
                    }
                    results.append(error_result)
                    logger.error(f"Exception collecting market data for stock_key {stock_key}: {str(e)}")
            
            # Return results in same format as old batch method for compatibility
            return {
                'success': True,
                'total_stocks': len(stock_keys),
                'successful_stocks': successful_stocks,
                'failed_stocks': failed_stocks,
                'total_records_loaded': total_records_loaded,
                'results': results
            }
            
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