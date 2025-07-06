"""
Centralized date parsing utility to eliminate DRY violations across transaction import system.

This utility consolidates all date parsing logic that was previously duplicated in:
- transaction_import_service.py (lines 220-235)
- transaction.py (lines 220-261) 
- Various other locations

DESIGN DECISION: Single responsibility for date parsing with comprehensive format support.
BUG FIXES INCLUDED: Handles edge cases like timestamps with dates, malformed strings, etc.
"""

from datetime import datetime, date
from typing import Union, Optional
import logging

logger = logging.getLogger(__name__)


class DateParser:
    """
    Centralized date parsing utility for transaction import system.
    
    Supports multiple date formats and provides consistent parsing across all import components.
    """
    
    # Date format mapping from frontend format to pandas format
    FRONTEND_TO_PANDAS_FORMAT = {
        'YYYY-MM-DD': '%Y-%m-%d',
        'MM/DD/YYYY': '%m/%d/%Y',
        'DD/MM/YYYY': '%d/%m/%Y',
        'DD-MM-YYYY': '%d-%m-%Y',
        'MM-DD-YYYY': '%m-%d-%Y',
        'YYYYMMDD': '%Y%m%d',
        'DD-MMM-YYYY': '%d-%b-%Y',
        'MMM DD, YYYY': '%b %d, %Y'
    }
    
    # Common date formats to try when auto-detecting format
    AUTO_DETECT_FORMATS = [
        '%Y%m%d',      # YYYYMMDD
        '%Y-%m-%d',    # YYYY-MM-DD
        '%m/%d/%Y',    # MM/DD/YYYY
        '%d/%m/%Y',    # DD/MM/YYYY
        '%d-%m-%Y',    # DD-MM-YYYY
        '%m-%d-%Y',    # MM-DD-YYYY
        '%d-%b-%Y',    # DD-MMM-YYYY
        '%b %d, %Y'    # MMM DD, YYYY
    ]
    
    @classmethod
    def parse_date(cls, date_value: Union[str, date, datetime, int], 
                   format_hint: Optional[str] = None) -> date:
        """
        Parse a date value into a Python date object.
        
        Args:
            date_value: The date value to parse (string, date, datetime, or int)
            format_hint: Optional hint about the expected format (frontend format)
            
        Returns:
            date: Parsed date object
            
        Raises:
            ValueError: If date cannot be parsed in any supported format
        """
        if date_value is None:
            raise ValueError("Date value cannot be None")
            
        # Handle date objects directly
        if isinstance(date_value, date):
            return date_value
            
        # Handle datetime objects
        if isinstance(date_value, datetime):
            return date_value.date()
            
        # Handle integer dates (YYYYMMDD format)
        if isinstance(date_value, int):
            return cls._parse_int_date(date_value)
            
        # Handle string dates
        if isinstance(date_value, str):
            return cls._parse_string_date(date_value.strip(), format_hint)
            
        # Fallback: try to convert to string and parse
        try:
            return cls._parse_string_date(str(date_value).strip(), format_hint)
        except Exception as e:
            raise ValueError(f"Cannot parse date value '{date_value}' of type {type(date_value)}: {str(e)}")
    
    @classmethod
    def _parse_int_date(cls, date_int: int) -> date:
        """Parse integer date in YYYYMMDD format."""
        try:
            date_str = str(date_int)
            if len(date_str) != 8:
                raise ValueError(f"Integer date must be 8 digits (YYYYMMDD), got {len(date_str)} digits")
            return datetime.strptime(date_str, '%Y%m%d').date()
        except Exception as e:
            raise ValueError(f"Cannot parse integer date {date_int}: {str(e)}")
    
    @classmethod
    def _parse_string_date(cls, date_str: str, format_hint: Optional[str] = None) -> date:
        """Parse string date with optional format hint."""
        if not date_str:
            raise ValueError("Date string cannot be empty")
            
        # Remove time portion if present (e.g., '20170628 00:00:00' -> '20170628')
        if ' ' in date_str:
            date_str = date_str.split(' ')[0]
            
        # Try format hint first if provided
        if format_hint and format_hint in cls.FRONTEND_TO_PANDAS_FORMAT:
            pandas_format = cls.FRONTEND_TO_PANDAS_FORMAT[format_hint]
            try:
                return datetime.strptime(date_str, pandas_format).date()
            except ValueError:
                logger.warning(f"Format hint '{format_hint}' failed for date '{date_str}', trying auto-detection")
        
        # Try all supported formats
        for fmt in cls.AUTO_DETECT_FORMATS:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
                
        # Last resort: try to extract digits and assume YYYYMMDD
        digits_only = ''.join(filter(str.isdigit, date_str))
        if len(digits_only) >= 8:
            try:
                return cls._parse_int_date(int(digits_only[:8]))
            except ValueError:
                pass
                
        raise ValueError(f"Cannot parse date string '{date_str}' in any supported format")
    
    @classmethod
    def date_to_raw_int(cls, date_obj: Union[date, datetime]) -> int:
        """
        Convert a date object to raw integer format (YYYYMMDD) for database storage.
        
        Args:
            date_obj: Date or datetime object
            
        Returns:
            int: Date in YYYYMMDD format
        """
        if isinstance(date_obj, datetime):
            date_obj = date_obj.date()
        elif not isinstance(date_obj, date):
            raise ValueError(f"Expected date or datetime object, got {type(date_obj)}")
            
        return int(date_obj.strftime('%Y%m%d'))
    
    @classmethod
    def raw_int_to_date(cls, raw_int: int) -> date:
        """
        Convert raw integer format (YYYYMMDD) back to date object.
        
        Args:
            raw_int: Date in YYYYMMDD format
            
        Returns:
            date: Parsed date object
        """
        return cls._parse_int_date(raw_int)
    
    @classmethod
    def get_pandas_format(cls, frontend_format: str) -> str:
        """
        Get pandas format string for a given frontend format.
        
        Args:
            frontend_format: Frontend format (e.g., 'YYYY-MM-DD')
            
        Returns:
            str: Pandas format string (e.g., '%Y-%m-%d')
            
        Raises:
            ValueError: If frontend format is not supported
        """
        if frontend_format not in cls.FRONTEND_TO_PANDAS_FORMAT:
            raise ValueError(f"Unsupported frontend format: {frontend_format}")
        return cls.FRONTEND_TO_PANDAS_FORMAT[frontend_format]