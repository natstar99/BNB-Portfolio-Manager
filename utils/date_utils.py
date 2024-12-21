from datetime import datetime, timezone, date
from typing import Union, Optional
import logging

logger = logging.getLogger(__name__)

class DateUtils:
    """
    Centralised utility class for handling dates throughout the application.
    Ensures consistent date handling between user transactions and external data.
    """
    
    @staticmethod
    def parse_date(date_input: Union[str, datetime, date]) -> datetime:
        """
        Parse various date formats into a timezone-naive datetime object.
        
        Args:
            date_input: Date string, datetime, or date object to parse
            
        Returns:
            datetime: Timezone-naive datetime object
            
        Raises:
            ValueError: If date cannot be parsed
        """
        try:
            if isinstance(date_input, datetime):
                # Convert timezone-aware to naive
                if date_input.tzinfo is not None:
                    date_input = date_input.replace(tzinfo=None)
                return date_input
                
            if isinstance(date_input, date):
                return datetime.combine(date_input, datetime.min.time())
            
            # Try various string formats
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
                try:
                    return datetime.strptime(date_input, fmt)
                except ValueError:
                    continue
                    
            raise ValueError(f"Unable to parse date: {date_input}")
            
        except Exception as e:
            logger.error(f"Error parsing date {date_input}: {str(e)}")
            raise
    
    @staticmethod
    def format_date(date_obj: Union[datetime, date], fmt: str = '%Y-%m-%d') -> str:
        """
        Format a date object into a consistent string format.
        
        Args:
            date_obj: Date or datetime object to format
            fmt: Output format string (default: YYYY-MM-DD)
            
        Returns:
            str: Formatted date string
        """
        if isinstance(date_obj, datetime):
            return date_obj.strftime(fmt)
        return date_obj.strftime(fmt)
    
    @staticmethod
    def to_database_date(date_obj: Union[datetime, date]) -> str:
        """
        Convert a date object to the standard database date format (YYYY-MM-DD).
        
        Args:
            date_obj: Date or datetime object to convert
            
        Returns:
            str: Date string in YYYY-MM-DD format
        """
        if isinstance(date_obj, datetime):
            return date_obj.date().isoformat()
        return date_obj.isoformat()
    
    @staticmethod
    def normalise_yahoo_date(yahoo_date: datetime) -> datetime:
        """
        Normalise a Yahoo Finance datetime to timezone-naive datetime.
        Handles both Timestamp and datetime objects from Yahoo Finance.
        
        Args:
            yahoo_date: Datetime object from Yahoo Finance (potentially timezone-aware)
            
        Returns:
            datetime: Timezone-naive datetime object
        """
        try:
            # Handle pandas Timestamp objects
            if hasattr(yahoo_date, 'to_pydatetime'):
                yahoo_date = yahoo_date.to_pydatetime()
                
            # Remove timezone if present
            if yahoo_date.tzinfo is not None:
                yahoo_date = yahoo_date.replace(tzinfo=None)
                
            return yahoo_date
            
        except Exception as e:
            logger.error(f"Error normalising Yahoo date: {str(e)}")
            logger.debug(f"Input date type: {type(yahoo_date)}")
            raise ValueError(f"Failed to normalise Yahoo date: {str(e)}")