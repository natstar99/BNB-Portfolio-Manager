from datetime import datetime, date
from app import db
from sqlalchemy import text
from typing import List, Optional, Dict, Any


class MarketPrice(db.Model):
    """Market price fact model for historical stock prices from Yahoo Finance"""
    __tablename__ = 'FACT_MARKET_PRICES'
    
    id = db.Column(db.Integer, primary_key=True)
    stock_key = db.Column(db.Integer, db.ForeignKey('DIM_STOCK.stock_key'), nullable=False)
    date_key = db.Column(db.Integer, nullable=False)
    
    # Price data
    open_price = db.Column(db.Numeric(10, 4))
    high_price = db.Column(db.Numeric(10, 4))
    low_price = db.Column(db.Numeric(10, 4))
    close_price = db.Column(db.Numeric(10, 4), nullable=False)
    volume = db.Column(db.Integer)
    adjusted_close = db.Column(db.Numeric(10, 4))
    
    # Corporate actions
    dividend = db.Column(db.Numeric(10, 4), default=0)
    split_ratio = db.Column(db.Numeric(10, 6), default=1.0)
    
    # Audit fields
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    stock = db.relationship('Stock', back_populates='market_prices')
    
    def __repr__(self):
        return f'<MarketPrice {self.stock_key} on {self.date_key}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'stock_key': self.stock_key,
            'date_key': self.date_key,
            'open_price': float(self.open_price) if self.open_price else None,
            'high_price': float(self.high_price) if self.high_price else None,
            'low_price': float(self.low_price) if self.low_price else None,
            'close_price': float(self.close_price) if self.close_price else 0.0,
            'volume': self.volume,
            'adjusted_close': float(self.adjusted_close) if self.adjusted_close else None,
            'dividend': float(self.dividend) if self.dividend else 0.0,
            'split_ratio': float(self.split_ratio) if self.split_ratio else 1.0,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @staticmethod
    def create(stock_key: int, date_key: int, close_price: float, **kwargs):
        """Create a new market price record"""
        market_price = MarketPrice(
            stock_key=stock_key,
            date_key=date_key,
            close_price=close_price,
            **kwargs
        )
        
        db.session.add(market_price)
        db.session.commit()
        return market_price
    
    @staticmethod
    def get_by_stock_and_date(stock_key: int, date_key: int):
        """Get market price for specific stock and date"""
        return MarketPrice.query.filter_by(
            stock_key=stock_key,
            date_key=date_key
        ).first()
    
    @staticmethod
    def get_latest_price(stock_key: int) -> Optional['MarketPrice']:
        """Get the most recent market price for a stock"""
        return MarketPrice.query.filter_by(
            stock_key=stock_key
        ).order_by(MarketPrice.date_key.desc()).first()

    @staticmethod
    def get_price_with_forward_fill(stock_key: int, date_key: int) -> tuple[Optional['MarketPrice'], bool]:
        """
        Get market price for a date, with forward-fill for missing dates.

        This method implements forward-filling to handle market holidays and data gaps.
        When market data doesn't exist for a specific date (e.g., Christmas, Thanksgiving,
        or data provider outages), it returns the most recent previous market price.

        This ensures continuous daily portfolio metrics calculation even when markets
        are closed or data is unavailable, preventing portfolio value gaps that would
        cause aggregation issues in analytics views.

        Args:
            stock_key: Stock identifier
            date_key: Date in YYYYMMDD format

        Returns:
            Tuple[Optional[MarketPrice], bool]:
                - (MarketPrice, False) if actual data exists for the requested date
                - (MarketPrice, True) if forward-filled from a previous date
                - (None, False) if no historical data exists at all

        Example:
            # Dec 25 (Christmas) - market closed, no data
            price, is_filled = get_price_with_forward_fill(stock_key, 20241225)
            # Returns: (MarketPrice from Dec 24, True)

            # Dec 26 - market open, data available
            price, is_filled = get_price_with_forward_fill(stock_key, 20241226)
            # Returns: (MarketPrice from Dec 26, False)
        """
        # Try to get actual market price for this date
        market_price = MarketPrice.query.filter_by(
            stock_key=stock_key,
            date_key=date_key
        ).first()

        if market_price:
            # Actual data exists for this date
            return market_price, False

        # No data for this date - forward-fill from most recent previous date
        previous_price = MarketPrice.query.filter(
            MarketPrice.stock_key == stock_key,
            MarketPrice.date_key < date_key
        ).order_by(MarketPrice.date_key.desc()).first()

        if previous_price:
            # Found historical data to forward-fill from
            return previous_price, True

        # No historical data exists at all (shouldn't happen in normal operation)
        return None, False