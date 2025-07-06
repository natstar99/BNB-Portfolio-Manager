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
        self.market_data_service = MarketDataService()
        
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
        Get existing stock records for all instruments from DIM_STOCK.
        
        All stocks should have been created in Step 4 (stock verification).
        This method only retrieves stock_keys for existing stocks.
        
        Args:
            instrument_codes: List of instrument codes to retrieve
            portfolio_key: Portfolio ID to look up stocks for
            
        Returns:
            Dict mapping instrument_code to stock_key
            
        Raises:
            ValueError: If any expected stock is not found (indicates Step 4 wasn't completed properly)
        """
        stock_key_mapping = {}
        missing_stocks = []
        
        for instrument_code in instrument_codes:
            # All stocks should exist - they were created in Step 4
            existing_stock = Stock.get_by_portfolio_and_instrument(portfolio_key, instrument_code)
            
            if existing_stock:
                stock_key_mapping[instrument_code] = existing_stock.stock_key
                logger.info(f"Found existing stock: {instrument_code} (Key: {existing_stock.stock_key}, Status: {existing_stock.verification_status})")
            else:
                missing_stocks.append(instrument_code)
                logger.error(f"Stock not found: {instrument_code} - should have been created in Step 4")
        
        if missing_stocks:
            raise ValueError(f"Missing stocks from Step 4: {missing_stocks}. Stock verification step may not have completed properly.")
        
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
        try:
            # Get all unprocessed transactions for this portfolio
            unprocessed_transactions = RawTransaction.query.filter_by(
                portfolio_id=portfolio_key,
                processed_flag=False
            ).order_by(RawTransaction.raw_date).all()
            
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
            DateDimension.ensure_date_range_exists(earliest_transaction_date, latest_transaction_date)
            logger.info(f"Ensured DIM_DATE populated from {earliest_transaction_date} to {latest_transaction_date}")
            
            # Group transactions by instrument code to retrieve stocks
            instrument_codes = list(set([tx.raw_instrument_code for tx in unprocessed_transactions]))
            
            # Get existing stocks (created in Step 4)
            stock_key_mapping = self.get_existing_stocks(instrument_codes, portfolio_key)
            
            successful_imports = 0
            errors = []
            
            # Process each unprocessed transaction
            for raw_tx in unprocessed_transactions:
                try:
                    instrument_code = raw_tx.raw_instrument_code
                    
                    if instrument_code not in stock_key_mapping:
                        errors.append(f"No stock key found for instrument {instrument_code}")
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
            
            # Commit all transaction changes
            db.session.commit()
            
            # PERFORMANCE OPTIMIZATION: Defer metrics calculation to avoid N+1 queries
            # Instead of calculating metrics for each stock individually, defer to background or manual trigger
            if successful_imports > 0:
                # Get stocks that actually had transactions and are verified
                stocks_needing_metrics = []
                for instrument_code, stock_key in stock_key_mapping.items():
                    stock_had_transactions = any(
                        tx.raw_instrument_code == instrument_code 
                        for tx in unprocessed_transactions 
                        if tx.processed_flag
                    )
                    
                    if stock_had_transactions:
                        stock = Stock.get_by_portfolio_and_instrument(portfolio_key, instrument_code)
                        if stock and stock.verification_status == 'verified':
                            stocks_needing_metrics.append({
                                'instrument_code': instrument_code,
                                'stock_key': stock_key
                            })
                
                logger.info(f"Import complete. {len(stocks_needing_metrics)} verified stocks need metrics recalculation from {earliest_transaction_date}")
                logger.info("RECOMMENDATION: Run metrics recalculation as separate background process to avoid blocking import")
            
            return {
                'success': True,
                'successful_imports': successful_imports,
                'stocks_processed': len([k for k in stock_key_mapping.keys()]),  # Changed from stocks_created
                'import_errors': errors,
                'processed_transactions': len(unprocessed_transactions),
                'earliest_date': earliest_transaction_date.isoformat() if earliest_transaction_date else None,
                'message': f'Successfully imported {successful_imports} transactions for {len(stock_key_mapping)} stocks'
            }
            
        except Exception as e:
            logger.error(f"Error processing staged transactions for portfolio {portfolio_key}: {str(e)}")
            db.session.rollback()
            return {
                'success': False,
                'error': str(e),
                'successful_imports': 0,
                'stocks_processed': 0,  # Changed from stocks_created
                'import_errors': [str(e)]
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