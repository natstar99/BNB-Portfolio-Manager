"""
Date Dimension Model for Kimball Star Schema
Handles date dimension table operations with automatic population
"""

from datetime import datetime, date, timedelta
import calendar
import logging
from typing import List
from app import db
from sqlalchemy import text

logger = logging.getLogger(__name__)


class DateDimension(db.Model):
    """Date dimension model for analytics and star schema"""
    __tablename__ = 'DIM_DATE'
    
    date_key = db.Column(db.Integer, primary_key=True)
    date_value = db.Column(db.Date, nullable=False, unique=True)
    year = db.Column(db.Integer, nullable=False)
    quarter = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    day = db.Column(db.Integer, nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 1=Monday, 7=Sunday
    day_name = db.Column(db.String(20), nullable=False)
    month_name = db.Column(db.String(20), nullable=False)
    is_weekend = db.Column(db.Boolean, default=False)
    is_holiday = db.Column(db.Boolean, default=False)  # Default false - market-specific logic needed
    is_leap_year = db.Column(db.Boolean, default=False)
    fiscal_year = db.Column(db.Integer)  # Defaults to calendar year
    fiscal_quarter = db.Column(db.Integer)  # Defaults to calendar quarter
    
    def __repr__(self):
        return f'<DateDimension {self.date_key}: {self.date_value}>'
    
    def to_dict(self):
        return {
            'date_key': self.date_key,
            'date_value': self.date_value.isoformat() if self.date_value else None,
            'year': self.year,
            'quarter': self.quarter,
            'month': self.month,
            'day': self.day,
            'day_of_week': self.day_of_week,
            'day_name': self.day_name,
            'month_name': self.month_name,
            'is_weekend': self.is_weekend,
            'is_holiday': self.is_holiday,
            'is_leap_year': self.is_leap_year,
            'fiscal_year': self.fiscal_year,
            'fiscal_quarter': self.fiscal_quarter
        }
    
    @staticmethod
    def get_or_create_date_entry(target_date: date, commit: bool = True):
        """
        Get existing date dimension entry or create new one
        
        Args:
            target_date: The date to get/create entry for
            commit: Whether to commit the transaction (default True for backward compatibility)
            
        Returns:
            DateDimension: The date dimension entry
        """
        date_key = int(target_date.strftime('%Y%m%d'))
        
        # Check if entry already exists
        existing_entry = DateDimension.query.filter_by(date_key=date_key).first()
        if existing_entry:
            return existing_entry
        
        # Create new entry
        return DateDimension.create_date_entry(target_date, commit=commit)
    
    @staticmethod
    def create_date_entry(target_date: date, commit: bool = True):
        """
        Create a single date dimension entry
        
        Args:
            target_date: The date to create entry for
            commit: Whether to commit the transaction (default True for backward compatibility)
            
        Returns:
            DateDimension: The created date dimension entry
        """
        date_key = int(target_date.strftime('%Y%m%d'))
        
        # Calculate derived fields
        year = target_date.year
        month = target_date.month
        day = target_date.day
        quarter = (month - 1) // 3 + 1
        
        # Day of week (1=Monday, 7=Sunday)
        day_of_week = target_date.isoweekday()
        day_name = target_date.strftime('%A')
        month_name = target_date.strftime('%B')
        
        # Weekend check (Saturday=6, Sunday=7)
        is_weekend = day_of_week in [6, 7]
        
        # Leap year check
        is_leap_year = calendar.isleap(year)
        
        # Fiscal year defaults to calendar year
        fiscal_year = year
        fiscal_quarter = quarter
        
        date_entry = DateDimension(
            date_key=date_key,
            date_value=target_date,
            year=year,
            quarter=quarter,
            month=month,
            day=day,
            day_of_week=day_of_week,
            day_name=day_name,
            month_name=month_name,
            is_weekend=is_weekend,
            is_holiday=False,  # Default to false - requires market-specific logic
            is_leap_year=is_leap_year,
            fiscal_year=fiscal_year,
            fiscal_quarter=fiscal_quarter
        )
        
        db.session.add(date_entry)
        if commit:
            db.session.commit()
        
        return date_entry
    
    @staticmethod
    def ensure_date_range_exists(start_date: date, end_date: date = None, commit: bool = True):
        """
        Efficiently ensure all dates exist in the dimension between start_date and end_date.
        Only creates missing dates to avoid duplicates.
        
        Args:
            start_date: Start date for the range
            end_date: End date for the range (defaults to today)
            commit: Whether to commit the transaction (default True for backward compatibility)
            
        Returns:
            int: Number of date entries created
        """
        if end_date is None:
            end_date = date.today()
        
        if start_date > end_date:
            return 0
        
        # Get existing date keys in the range to avoid duplicates
        start_key = int(start_date.strftime('%Y%m%d'))
        end_key = int(end_date.strftime('%Y%m%d'))
        
        existing_keys = set()
        existing_entries = db.session.execute(
            text("SELECT date_key FROM DIM_DATE WHERE date_key BETWEEN :start_key AND :end_key"),
            {'start_key': start_key, 'end_key': end_key}
        ).fetchall()
        existing_keys = {row[0] for row in existing_entries}
        
        # Batch create missing dates
        missing_dates = []
        current_date = start_date
        
        while current_date <= end_date:
            date_key = int(current_date.strftime('%Y%m%d'))
            
            if date_key not in existing_keys:
                missing_dates.append(current_date)
            
            current_date += timedelta(days=1)
        
        # Bulk insert missing dates
        created_count = 0
        if missing_dates:
            date_entries = []
            for missing_date in missing_dates:
                date_entry_data = DateDimension._prepare_date_entry_data(missing_date)
                date_entries.append(date_entry_data)
                created_count += 1
            
            # Bulk insert using SQLAlchemy
            if date_entries:
                db.session.execute(
                    text("""
                    INSERT OR IGNORE INTO DIM_DATE (
                        date_key, date_value, year, quarter, month, day, 
                        day_of_week, day_name, month_name, is_weekend, 
                        is_holiday, is_leap_year, fiscal_year, fiscal_quarter
                    ) VALUES (
                        :date_key, :date_value, :year, :quarter, :month, :day,
                        :day_of_week, :day_name, :month_name, :is_weekend,
                        :is_holiday, :is_leap_year, :fiscal_year, :fiscal_quarter
                    )
                    """),
                    date_entries
                )
                if commit:
                    db.session.commit()
        
        logger.info(f"Created {created_count} missing date dimension entries from {start_date} to {end_date}")
        return created_count
    
    @staticmethod
    def _prepare_date_entry_data(target_date: date):
        """
        Prepare date entry data for bulk insertion
        
        Args:
            target_date: The date to prepare data for
            
        Returns:
            dict: Date entry data ready for insertion
        """
        date_key = int(target_date.strftime('%Y%m%d'))
        
        # Calculate derived fields
        year = target_date.year
        month = target_date.month
        day = target_date.day
        quarter = (month - 1) // 3 + 1
        
        # Day of week (1=Monday, 7=Sunday)
        day_of_week = target_date.isoweekday()
        day_name = target_date.strftime('%A')
        month_name = target_date.strftime('%B')
        
        # Weekend check (Saturday=6, Sunday=7)
        is_weekend = day_of_week in [6, 7]
        
        # Leap year check
        is_leap_year = calendar.isleap(year)
        
        # Fiscal year defaults to calendar year
        fiscal_year = year
        fiscal_quarter = quarter
        
        return {
            'date_key': date_key,
            'date_value': target_date,
            'year': year,
            'quarter': quarter,
            'month': month,
            'day': day,
            'day_of_week': day_of_week,
            'day_name': day_name,
            'month_name': month_name,
            'is_weekend': is_weekend,
            'is_holiday': False,  # Default to false - requires market-specific logic
            'is_leap_year': is_leap_year,
            'fiscal_year': fiscal_year,
            'fiscal_quarter': fiscal_quarter
        }
    
    @staticmethod
    def get_date_range_info():
        """
        Get information about the date range in the dimension
        
        Returns:
            dict: Information about date range, leap years, etc.
        """
        try:
            result = db.session.execute(
                text("""
                SELECT 
                    MIN(date_key) as min_date_key,
                    MAX(date_key) as max_date_key,
                    COUNT(*) as total_dates,
                    COUNT(CASE WHEN is_leap_year = 1 THEN 1 END) as leap_year_dates,
                    COUNT(CASE WHEN is_weekend = 1 THEN 1 END) as weekend_dates
                FROM DIM_DATE
                """)
            ).fetchone()
            
            if result and result[0]:
                return {
                    'min_date': str(result[0]),
                    'max_date': str(result[1]),
                    'total_dates': result[2],
                    'leap_year_dates': result[3],
                    'weekend_dates': result[4]
                }
            else:
                return {
                    'min_date': None,
                    'max_date': None,
                    'total_dates': 0,
                    'leap_year_dates': 0,
                    'weekend_dates': 0
                }
        except Exception:
            return {
                'error': 'Could not retrieve date range information'
            }
    
    @staticmethod
    def get_trading_days_in_range(start_date_key: int, end_date_key: int) -> List[int]:
        """
        Get all trading days (non-weekend days) in the specified date range.
        
        This method is critical for metrics calculation performance. It returns only
        business days (Monday-Friday) to avoid calculating metrics for weekends
        when markets are closed.
        
        Args:
            start_date_key: Start date in YYYYMMDD format
            end_date_key: End date in YYYYMMDD format
            
        Returns:
            List[int]: List of date_keys for trading days in the range
            
        Performance Note:
            Uses database query to leverage indexes rather than generating 
            dates in Python for better performance with large date ranges.
        """
        try:
            # Query database for trading days (weekdays only)
            result = db.session.execute(
                text("""
                SELECT date_key 
                FROM DIM_DATE 
                WHERE date_key BETWEEN :start_key AND :end_key 
                  AND is_weekend = 0
                  AND is_holiday = 0
                ORDER BY date_key
                """),
                {'start_key': start_date_key, 'end_key': end_date_key}
            ).fetchall()
            
            return [row[0] for row in result]
            
        except Exception as e:
            logger.error(f"Error getting trading days in range {start_date_key} to {end_date_key}: {str(e)}")
            return []