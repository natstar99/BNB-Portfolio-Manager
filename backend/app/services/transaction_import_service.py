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
from app.models import Stock, Transaction, TransactionType, Portfolio, RawTransaction, PortfolioPosition
from app.services.market_data_service import MarketDataService
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
        
        # Date format mapping from frontend format to pandas format
        self.date_format_mapping = {
            'YYYY-MM-DD': '%Y-%m-%d',
            'MM/DD/YYYY': '%m/%d/%Y',
            'DD/MM/YYYY': '%d/%m/%Y',
            'DD-MM-YYYY': '%d-%m-%Y',
            'MM-DD-YYYY': '%m-%d-%Y',
            'YYYYMMDD': '%Y%m%d',
            'DD-MMM-YYYY': '%d-%b-%Y',
            'MMM DD, YYYY': '%b %d, %Y'
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
        """
        try:
            validation_results = {
                'total_rows': len(df_mapped),
                'valid_rows': 0,
                'validation_errors': [],
                'new_transactions': 0,
                'duplicate_transactions': 0,
                'new_stocks': 0,
                'existing_stocks': 0,
                'unique_instruments': []
            }
            
            valid_transactions = []
            pandas_format = self.date_format_mapping.get(date_format, '%Y-%m-%d')
            
            # Validate each row
            for index, row in df_mapped.iterrows():
                row_errors = []
                
                # Validate date
                try:
                    parsed_date = datetime.strptime(str(row['date']), pandas_format).date()
                except Exception:
                    row_errors.append(f"Row {index + 1}: Invalid date format '{row['date']}'")
                
                # Validate instrument code
                instrument_code = str(row['instrument_code']).strip().upper()
                if not instrument_code:
                    row_errors.append(f"Row {index + 1}: Missing instrument code")
                
                # Validate transaction type
                transaction_type = str(row['transaction_type']).strip().upper()
                if transaction_type not in ['BUY', 'SELL', 'DIVIDEND', 'SPLIT', 'BONUS', 'RIGHTS']:
                    row_errors.append(f"Row {index + 1}: Invalid transaction type '{transaction_type}'")
                
                # Validate quantity
                try:
                    quantity = float(row['quantity'])
                    if quantity <= 0:
                        row_errors.append(f"Row {index + 1}: Quantity must be positive")
                except Exception:
                    row_errors.append(f"Row {index + 1}: Invalid quantity '{row['quantity']}'")
                
                # Validate price
                try:
                    price = float(row['price'])
                    if price <= 0:
                        row_errors.append(f"Row {index + 1}: Price must be positive")
                except Exception:
                    row_errors.append(f"Row {index + 1}: Invalid price '{row['price']}'")
                
                if row_errors:
                    validation_results['validation_errors'].extend(row_errors)
                else:
                    # Valid transaction
                    valid_transactions.append({
                        'date': parsed_date,
                        'instrument_code': instrument_code,
                        'transaction_type': transaction_type,
                        'quantity': quantity,
                        'price': price
                    })
            
            validation_results['valid_rows'] = len(valid_transactions)
            
            if not valid_transactions:
                return validation_results
            
            # Check for duplicates against existing transactions
            duplicate_count = 0
            new_transaction_count = 0
            
            for trans in valid_transactions:
                # Check if this exact transaction already exists
                from app.models.transaction import Transaction
                existing = Transaction.query.join(
                    Stock, Transaction.stock_key == Stock.stock_key
                ).filter(
                    Transaction.portfolio_key == portfolio_id,
                    Stock.instrument_code == trans['instrument_code'],
                    Transaction.transaction_date == trans['date'],
                    Transaction.quantity == trans['quantity'],
                    Transaction.price == trans['price']
                ).first()
                
                if existing:
                    duplicate_count += 1
                else:
                    new_transaction_count += 1
            
            validation_results['new_transactions'] = new_transaction_count
            validation_results['duplicate_transactions'] = duplicate_count
            
            # Analyze unique instruments (stocks)
            unique_instruments = list(set([t['instrument_code'] for t in valid_transactions]))
            validation_results['unique_instruments'] = unique_instruments
            
            # Check which stocks are new vs existing
            new_stocks = []
            existing_stocks = []
            
            for instrument in unique_instruments:
                existing_stock = Stock.get_by_instrument_code(instrument)
                if existing_stock:
                    existing_stocks.append(instrument)
                else:
                    new_stocks.append(instrument)
            
            validation_results['new_stocks'] = len(new_stocks)
            validation_results['existing_stocks'] = len(existing_stocks)
            validation_results['new_stock_symbols'] = new_stocks
            validation_results['existing_stock_symbols'] = existing_stocks
            
            logger.info(f"Raw data confirmation: {validation_results['valid_rows']} valid, {len(validation_results['validation_errors'])} errors, {validation_results['new_stocks']} new stocks")
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Error confirming raw data: {str(e)}")
            raise

    # ============= STAGING METHODS =============
    
    def stage_raw_data(self, df: pd.DataFrame, portfolio_key: int) -> Tuple[str, List[RawTransaction]]:
        """Stage raw data into STG_RAW_TRANSACTIONS table"""
        try:
            # Generate unique batch ID
            batch_id = str(uuid.uuid4())
            
            # Convert DataFrame to raw transaction format
            raw_data = []
            for _, row in df.iterrows():
                raw_data.append({
                    'date': str(row.get('date', '')),
                    'instrument_code': str(row.get('instrument_code', '')),
                    'transaction_type': str(row.get('transaction_type', '')),
                    'quantity': str(row.get('quantity', '')),
                    'price': str(row.get('price', '')),
                    'total_value': str(row.get('total_value', '')),
                    'currency': str(row.get('currency', ''))
                })
            
            # Create batch of raw transactions
            raw_transactions = RawTransaction.create_batch(batch_id, portfolio_key, raw_data)
            
            logger.info(f"Staged {len(raw_transactions)} raw transactions with batch ID {batch_id}")
            return batch_id, raw_transactions
            
        except Exception as e:
            logger.error(f"Error staging raw data: {str(e)}")
            raise
    
    def validate_staged_data(self, batch_id: str, date_format: str = 'YYYY-MM-DD') -> Tuple[List[Dict], List[str]]:
        """Validate staged data and prepare for processing"""
        try:
            # Get all raw transactions for this batch
            raw_transactions = RawTransaction.query.filter_by(import_batch_id=batch_id).all()
            
            validated_data = []
            errors = []
            
            for raw_tx in raw_transactions:
                validation_errors = []
                validated_row = {}
                
                # Validate and convert date
                try:
                    pandas_format = self.date_format_mapping.get(date_format)
                    if pandas_format:
                        validated_row['date'] = datetime.strptime(raw_tx.raw_date, pandas_format).date()
                    else:
                        validated_row['date'] = pd.to_datetime(raw_tx.raw_date).date()
                except Exception as e:
                    validation_errors.append(f"Invalid date format: {raw_tx.raw_date}")
                
                # Validate instrument code
                if raw_tx.raw_instrument_code.strip():
                    validated_row['instrument_code'] = raw_tx.raw_instrument_code.strip().upper()
                else:
                    validation_errors.append("Missing instrument code")
                
                # Validate transaction type
                transaction_type = raw_tx.raw_transaction_type.strip().upper()
                if transaction_type in ['BUY', 'SELL', 'DIVIDEND', 'SPLIT', 'BONUS', 'RIGHTS']:
                    validated_row['transaction_type'] = transaction_type
                else:
                    validation_errors.append(f"Invalid transaction type: {transaction_type}")
                
                # Validate quantity
                try:
                    validated_row['quantity'] = float(raw_tx.raw_quantity)
                    if validated_row['quantity'] <= 0:
                        validation_errors.append("Quantity must be positive")
                except Exception:
                    validation_errors.append(f"Invalid quantity: {raw_tx.raw_quantity}")
                
                # Validate price
                try:
                    validated_row['price'] = float(raw_tx.raw_price)
                    if validated_row['price'] <= 0:
                        validation_errors.append("Price must be positive")
                except Exception:
                    validation_errors.append(f"Invalid price: {raw_tx.raw_price}")
                
                # Store validation results
                if validation_errors:
                    raw_tx.validation_errors = "; ".join(validation_errors)
                    errors.extend([f"Row {raw_tx.id}: {err}" for err in validation_errors])
                else:
                    validated_row['raw_tx_id'] = raw_tx.id
                    validated_row['portfolio_key'] = raw_tx.portfolio_id
                    validated_data.append(validated_row)
            
            db.session.commit()
            logger.info(f"Validated {len(validated_data)} transactions, {len(errors)} errors")
            return validated_data, errors
            
        except Exception as e:
            logger.error(f"Error validating staged data: {str(e)}")
            raise
    
    # ============= STOCK CREATION METHODS =============
    
    def create_stocks_for_instruments(self, instrument_codes: List[str]) -> Dict[str, int]:
        """Create or get stock records for all instruments"""
        stock_key_mapping = {}
        
        for instrument_code in instrument_codes:
            # Check if stock already exists
            existing_stock = Stock.get_by_instrument_code(instrument_code)
            
            if existing_stock:
                stock_key_mapping[instrument_code] = existing_stock.stock_key
                logger.info(f"Found existing stock: {instrument_code} (Key: {existing_stock.stock_key})")
            else:
                # Create new stock without verification (to avoid rate limits)
                try:
                    stock = Stock.create(
                        instrument_code=instrument_code,
                        yahoo_symbol=instrument_code,
                        name=instrument_code,  # Use symbol as name for now
                        verification_status='pending'
                    )
                    stock_key_mapping[instrument_code] = stock.stock_key
                    logger.info(f"Created new stock: {instrument_code} (Key: {stock.stock_key})")
                    
                except Exception as e:
                    logger.error(f"Error creating stock {instrument_code}: {str(e)}")
        
        return stock_key_mapping
    
    # ============= TRANSACTION PROCESSING METHODS =============
    
    def process_validated_transactions(self, validated_data: List[Dict], stock_key_mapping: Dict[str, int]) -> Tuple[int, List[str]]:
        """Process validated transactions into FACT_TRANSACTIONS table"""
        successful_imports = 0
        errors = []
        
        for row in validated_data:
            try:
                instrument_code = row['instrument_code']
                
                if instrument_code not in stock_key_mapping:
                    errors.append(f"No stock key found for instrument {instrument_code}")
                    continue
                
                stock_key = stock_key_mapping[instrument_code]
                
                # Create transaction
                transaction = Transaction.create(
                    stock_key=stock_key,
                    portfolio_key=row['portfolio_key'],
                    transaction_type=row['transaction_type'],
                    transaction_date=row['date'],
                    quantity=row['quantity'],
                    price=row['price']
                )
                
                # Update portfolio position
                self.update_portfolio_position(
                    portfolio_key=row['portfolio_key'],
                    stock_key=stock_key,
                    transaction_type=row['transaction_type'],
                    quantity=row['quantity'],
                    price=row['price']
                )
                
                # Mark raw transaction as processed
                if 'raw_tx_id' in row:
                    raw_tx = RawTransaction.query.get(row['raw_tx_id'])
                    if raw_tx:
                        raw_tx.processed_flag = True
                
                successful_imports += 1
                logger.debug(f"Created transaction {transaction.transaction_key}")
                
            except Exception as e:
                error_msg = f"Error creating transaction: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        db.session.commit()
        logger.info(f"Successfully processed {successful_imports} transactions, {len(errors)} errors")
        return successful_imports, errors
    
    def update_portfolio_position(self, portfolio_key: int, stock_key: int, 
                                transaction_type: str, quantity: float, price: float):
        """Update portfolio position based on transaction"""
        try:
            # Get or create position
            position = PortfolioPosition.get_or_create(portfolio_key, stock_key)
            
            # Get transaction type details
            trans_type = TransactionType.get_by_type(transaction_type)
            
            if trans_type and trans_type.affects_quantity:
                # Update position based on transaction type
                position.update_position(quantity, price, trans_type.is_buy_type)
            
        except Exception as e:
            logger.error(f"Error updating portfolio position: {str(e)}")
            raise
    
    # ============= HIGH-LEVEL IMPORT METHODS =============
    
    def process_file_import(self, file: FileStorage, portfolio_key: int, 
                          custom_mapping: Optional[Dict[str, str]] = None,
                          date_format: str = 'YYYY-MM-DD') -> Dict[str, Any]:
        """Complete process for importing transactions using staging approach"""
        try:
            # Step 1: Read file
            df = self.read_file(file)
            if df is None:
                return {
                    'success': False,
                    'error': 'Failed to read file',
                    'details': 'Could not parse the uploaded file'
                }
            
            # Step 2: Detect or apply column mapping
            if custom_mapping:
                mapping = custom_mapping
            else:
                mapping = self.detect_column_mapping(df)
            
            if not mapping:
                return {
                    'success': False,
                    'error': 'Could not detect column mapping',
                    'details': 'Please provide custom column mapping',
                    'available_columns': df.columns.tolist()
                }
            
            df_mapped = self.apply_column_mapping(df, mapping)
            
            # Step 3: Stage raw data
            batch_id, raw_transactions = self.stage_raw_data(df_mapped, portfolio_key)
            
            # Step 4: Validate staged data
            validated_data, validation_errors = self.validate_staged_data(batch_id, date_format)
            
            if not validated_data:
                return {
                    'success': False,
                    'error': 'No valid transactions found after validation',
                    'validation_errors': validation_errors,
                    'batch_id': batch_id
                }
            
            # Step 5: Create stocks for all instruments
            unique_instruments = list(set([row['instrument_code'] for row in validated_data]))
            stock_key_mapping = self.create_stocks_for_instruments(unique_instruments)
            
            # Step 6: Process validated transactions
            successful_imports, import_errors = self.process_validated_transactions(
                validated_data, stock_key_mapping
            )
            
            return {
                'success': True,
                'summary': {
                    'total_rows_processed': len(df),
                    'raw_transactions_staged': len(raw_transactions),
                    'valid_rows_after_validation': len(validated_data),
                    'successful_imports': successful_imports,
                    'validation_errors': len(validation_errors),
                    'import_errors': len(import_errors),
                    'stocks_created': len([k for k in stock_key_mapping.keys() 
                                         if k not in [s.instrument_code for s in Stock.get_all()]]),
                    'batch_id': batch_id
                },
                'details': {
                    'column_mapping': mapping,
                    'validation_errors': validation_errors,
                    'import_errors': import_errors,
                    'stock_key_mapping': stock_key_mapping
                }
            }
            
        except Exception as e:
            logger.error(f"Error in file import process: {str(e)}")
            return {
                'success': False,
                'error': 'Import process failed',
                'details': str(e)
            }
    
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