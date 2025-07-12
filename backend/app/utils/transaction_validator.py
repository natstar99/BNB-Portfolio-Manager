"""
Centralized transaction validation utility to eliminate DRY violations.

This utility consolidates validation logic that was previously duplicated in:
- transaction_import_service.py (confirm_raw_data method, lines 136-173)
- import_transactions.py (/validate endpoint, lines 274-293)

DESIGN DECISION: Single responsibility for transaction validation with comprehensive error reporting.
BUG FIXES INCLUDED: Consistent validation rules, proper error formatting, type checking.
"""

import pandas as pd
from typing import Dict, List, Any, Tuple
from datetime import date
import logging
from decimal import Decimal

from .date_parser import DateParser

logger = logging.getLogger(__name__)


class TransactionValidator:
    """
    Centralized validation utility for transaction data.
    
    Provides consistent validation across all transaction import components.
    """
    
    # Valid transaction types
    VALID_TRANSACTION_TYPES = ['BUY', 'SELL', 'DIVIDEND', 'SPLIT', 'BONUS', 'RIGHTS']
    
    # Required fields for transaction validation
    REQUIRED_FIELDS = ['date', 'instrument_code', 'quantity', 'price', 'transaction_type']
    
    @classmethod
    def validate_dataframe_structure(cls, df: pd.DataFrame, required_fields: List[str] = None) -> List[str]:
        """
        Validate that DataFrame has required columns and basic structure.
        
        Args:
            df: DataFrame to validate
            required_fields: List of required field names (defaults to REQUIRED_FIELDS)
            
        Returns:
            List[str]: List of structural validation errors
        """
        if required_fields is None:
            required_fields = cls.REQUIRED_FIELDS
            
        errors = []
        
        if df.empty:
            errors.append("DataFrame is empty")
            return errors
            
        # Check for required columns
        missing_columns = [col for col in required_fields if col not in df.columns]
        if missing_columns:
            errors.append(f"Missing required columns: {missing_columns}")
            
        return errors
    
    @classmethod
    def validate_transaction_rows(cls, df: pd.DataFrame, date_format: str = 'YYYY-MM-DD') -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Validate individual transaction rows and return valid transactions + errors.
        
        Args:
            df: DataFrame with transaction data (must have standard column names)
            date_format: Expected date format for parsing
            
        Returns:
            Tuple[List[Dict], List[str]]: (valid_transactions, validation_errors)
        """
        valid_transactions = []
        validation_errors = []
        
        for index, row in df.iterrows():
            row_number = index + 1
            row_errors = []
            
            try:
                # Validate and parse date
                try:
                    parsed_date = DateParser.parse_date(row['date'], date_format)
                except Exception as e:
                    row_errors.append(f"Row {row_number}: Invalid date format '{row['date']}' - {str(e)}")
                    parsed_date = None
                
                # Validate instrument code
                instrument_code = str(row['instrument_code']).strip().upper()
                if not instrument_code or instrument_code == 'NAN':
                    row_errors.append(f"Row {row_number}: Missing or invalid instrument code")
                
                # Validate transaction type
                transaction_type = str(row['transaction_type']).strip().upper()
                if transaction_type not in cls.VALID_TRANSACTION_TYPES:
                    row_errors.append(f"Row {row_number}: Invalid transaction type '{transaction_type}'. Must be one of: {cls.VALID_TRANSACTION_TYPES}")
                
                # Validate quantity
                try:
                    quantity = float(row['quantity'])
                    if quantity <= 0:
                        row_errors.append(f"Row {row_number}: Quantity must be positive, got {quantity}")
                except (ValueError, TypeError):
                    row_errors.append(f"Row {row_number}: Invalid quantity '{row['quantity']}' - must be a number")
                    quantity = None
                
                # Validate price
                try:
                    price = float(row['price'])
                    if price <= 0:
                        row_errors.append(f"Row {row_number}: Price must be positive, got {price}")
                except (ValueError, TypeError):
                    row_errors.append(f"Row {row_number}: Invalid price '{row['price']}' - must be a number")
                    price = None
                
                # Validate total_value if present
                total_value = None
                if 'total_value' in row and pd.notna(row['total_value']):
                    try:
                        total_value = float(row['total_value'])
                    except (ValueError, TypeError):
                        row_errors.append(f"Row {row_number}: Invalid total_value '{row['total_value']}' - must be a number")
                
                # If no errors, add to valid transactions
                if not row_errors:
                    valid_transaction = {
                        'row_number': row_number,
                        'date': parsed_date,
                        'instrument_code': instrument_code,
                        'transaction_type': transaction_type,
                        'quantity': quantity,
                        'price': price
                    }
                    
                    # Add total_value if available
                    if total_value is not None:
                        valid_transaction['total_value'] = total_value
                    else:
                        # Calculate total_value if not provided
                        valid_transaction['total_value'] = quantity * price
                        
                    valid_transactions.append(valid_transaction)
                else:
                    validation_errors.extend(row_errors)
                    
            except Exception as e:
                validation_errors.append(f"Row {row_number}: Unexpected validation error - {str(e)}")
        
        logger.info(f"Validation complete: {len(valid_transactions)} valid, {len(validation_errors)} errors")
        return valid_transactions, validation_errors
    
    @classmethod
    def check_for_duplicates(cls, valid_transactions: List[Dict[str, Any]], 
                           portfolio_id: int) -> Tuple[List[Dict[str, Any]], int]:
        """
        Check for duplicate transactions against existing STG_RAW_TRANSACTIONS.
        
        Args:
            valid_transactions: List of validated transaction dictionaries
            portfolio_id: Portfolio ID to check duplicates against
            
        Returns:
            Tuple[List[Dict], int]: (new_transactions, duplicate_count)
        """
        from app.models.transaction import RawTransaction
        
        # Check what exists in database first
        existing_count = RawTransaction.query.filter_by(portfolio_id=portfolio_id).count()
        logger.debug(f"Portfolio {portfolio_id} has {existing_count} existing transactions in STG_RAW_TRANSACTIONS")
        logger.debug(f"Checking {len(valid_transactions)} transactions for duplicates")
        
        new_transactions = []
        duplicate_count = 0
        
        for trans in valid_transactions:
            try:
                # Convert date to YYYYMMDD format for comparison with raw_date
                raw_date_int = DateParser.date_to_raw_int(trans['date'])
                
                # Check if this exact raw transaction already exists in STG_RAW_TRANSACTIONS
                # Include transaction_type in duplicate check for better accuracy
                # 
                # BUG FIX: Use Decimal comparison instead of float to avoid precision issues
                quantity_decimal = Decimal(str(trans['quantity']))
                price_decimal = Decimal(str(trans['price']))
                
                existing = RawTransaction.query.filter(
                    RawTransaction.portfolio_id == portfolio_id,
                    RawTransaction.raw_instrument_code == trans['instrument_code'],
                    RawTransaction.raw_date == raw_date_int,
                    RawTransaction.raw_transaction_type == trans['transaction_type'],
                    RawTransaction.raw_quantity == quantity_decimal,
                    RawTransaction.raw_price == price_decimal
                ).first()
                
                if existing:
                    duplicate_count += 1
                    logger.debug(f"Duplicate found: {trans['instrument_code']} on {trans['date']} (ID: {existing.id})")
                else:
                    logger.debug(f"No duplicate for: {trans['instrument_code']} {trans['date']} qty={quantity_decimal} price={price_decimal}")
                    new_transactions.append(trans)
                    
            except Exception as e:
                logger.error(f"Error checking duplicates for transaction {trans}: {str(e)}")
                # Include transaction anyway to avoid data loss
                new_transactions.append(trans)
        
        logger.debug(f"Duplicate check result: {len(new_transactions)} new, {duplicate_count} duplicates")
        
        # If no duplicates found but data exists, show sample data for debugging
        if duplicate_count == 0 and existing_count > 0 and len(valid_transactions) > 0:
            sample_existing = RawTransaction.query.filter_by(portfolio_id=portfolio_id).first()
            sample_import = valid_transactions[0]
            logger.debug(f"No duplicates found but data exists - Sample DB: {sample_existing.raw_instrument_code} {sample_existing.raw_date}")
            logger.debug(f"Sample Import: {sample_import['instrument_code']} {DateParser.date_to_raw_int(sample_import['date'])}")
        
        return new_transactions, duplicate_count
    
    @classmethod
    def analyze_unique_instruments(cls, valid_transactions: List[Dict[str, Any]], portfolio_id: int) -> Dict[str, Any]:
        """
        Analyze unique instruments in transaction data and categorize as new/existing FOR THIS PORTFOLIO.
        
        Args:
            valid_transactions: List of validated transaction dictionaries
            portfolio_id: Portfolio ID to check stocks against (portfolio-specific check)
            
        Returns:
            Dict: Analysis results with unique instruments, new vs existing categorization
        """
        from app.models.stock import Stock
        
        # Get unique instruments
        unique_instruments = list(set([t['instrument_code'] for t in valid_transactions]))
        
        # Check which stocks are new vs existing FOR THIS PORTFOLIO ONLY
        new_stocks = []
        existing_stocks = []
        
        for instrument in unique_instruments:
            # Check if stock with this instrument code exists in THIS portfolio only
            existing_stock = Stock.get_by_portfolio_and_instrument(portfolio_id, instrument)
            if existing_stock:
                existing_stocks.append(instrument)
            else:
                new_stocks.append(instrument)
        
        # Create transaction breakdown by instrument
        transaction_breakdown = {}
        for transaction in valid_transactions:
            instrument_code = transaction['instrument_code']
            transaction_type = transaction['transaction_type'].upper()
            
            if instrument_code not in transaction_breakdown:
                transaction_breakdown[instrument_code] = {
                    'BUY': 0, 'SELL': 0, 'DIVIDEND': 0, 'SPLIT': 0, 'BONUS': 0, 'RIGHTS': 0, 'total': 0
                }
            
            if transaction_type in transaction_breakdown[instrument_code]:
                transaction_breakdown[instrument_code][transaction_type] += 1
            transaction_breakdown[instrument_code]['total'] += 1
        
        return {
            'unique_instruments': unique_instruments,
            'new_stocks': new_stocks,
            'existing_stocks': existing_stocks,
            'transaction_breakdown': transaction_breakdown,
            'unique_stock_count': len(unique_instruments),
            'new_stock_count': len(new_stocks),
            'existing_stock_count': len(existing_stocks)
        }
    
    @classmethod
    def validate_complete_dataset(cls, df: pd.DataFrame, portfolio_id: int, 
                                date_format: str = 'YYYY-MM-DD') -> Dict[str, Any]:
        """
        Perform complete validation of transaction dataset.
        
        This is the main validation method that combines all validation steps.
        
        Args:
            df: DataFrame with transaction data (standard column names)
            portfolio_id: Portfolio ID for duplicate checking
            date_format: Expected date format
            
        Returns:
            Dict: Complete validation results including errors, valid data, and analysis
        """
        results = {
            'total_rows': len(df),
            'valid_rows': 0,
            'validation_errors': [],
            'new_transactions': 0,
            'duplicate_transactions': 0,
            'valid_transactions': [],
            'instrument_analysis': {}
        }
        
        try:
            # Step 1: Validate DataFrame structure
            structural_errors = cls.validate_dataframe_structure(df)
            if structural_errors:
                results['validation_errors'].extend(structural_errors)
                return results
            
            # Step 2: Validate individual rows
            valid_transactions, validation_errors = cls.validate_transaction_rows(df, date_format)
            results['valid_rows'] = len(valid_transactions)
            results['validation_errors'] = validation_errors
            results['valid_transactions'] = valid_transactions
            
            if not valid_transactions:
                return results
            
            # Step 3: Check for duplicates
            new_transactions, duplicate_count = cls.check_for_duplicates(valid_transactions, portfolio_id)
            results['new_transactions'] = len(new_transactions)
            results['duplicate_transactions'] = duplicate_count
            results['new_transaction_data'] = new_transactions  # Store actual new transactions
            
            # Step 4: Analyze unique instruments (portfolio-specific)
            instrument_analysis = cls.analyze_unique_instruments(valid_transactions, portfolio_id)
            results['instrument_analysis'] = instrument_analysis
            
            logger.info(f"Complete validation: {results['valid_rows']} valid, {len(validation_errors)} errors, "
                       f"{results['new_transactions']} new, {duplicate_count} duplicates")
            
        except Exception as e:
            logger.error(f"Error during complete validation: {str(e)}")
            results['validation_errors'].append(f"Validation system error: {str(e)}")
        
        return results