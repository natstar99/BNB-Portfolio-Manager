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
    def bulk_create(price_data: List[Dict[str, Any]]):
        """Bulk create market price records for efficiency"""
        market_prices = []
        for data in price_data:
            price = MarketPrice(**data)
            market_prices.append(price)
            db.session.add(price)
        
        db.session.commit()
        return market_prices
    
    @staticmethod
    def get_by_stock_and_date(stock_key: int, date_key: int):
        """Get market price for specific stock and date"""
        return MarketPrice.query.filter_by(
            stock_key=stock_key,
            date_key=date_key
        ).first()
    
    @staticmethod
    def get_price_range(stock_key: int, start_date_key: int, end_date_key: int):
        """Get market prices for stock within date range"""
        return MarketPrice.query.filter(
            MarketPrice.stock_key == stock_key,
            MarketPrice.date_key >= start_date_key,
            MarketPrice.date_key <= end_date_key
        ).order_by(MarketPrice.date_key).all()
    
    @staticmethod
    def get_missing_dates(stock_key: int, start_date_key: int, end_date_key: int) -> List[int]:
        """Get list of missing date keys for a stock in given range"""
        existing_dates = db.session.query(MarketPrice.date_key).filter(
            MarketPrice.stock_key == stock_key,
            MarketPrice.date_key >= start_date_key,
            MarketPrice.date_key <= end_date_key
        ).all()
        
        existing_date_keys = {date[0] for date in existing_dates}
        
        # Generate all trading days in range (excluding weekends)
        from app.models.date_dimension import DateDimension
        all_trading_days = DateDimension.get_trading_days_in_range(start_date_key, end_date_key)
        
        missing_dates = [date_key for date_key in all_trading_days if date_key not in existing_date_keys]
        return missing_dates
    
    @staticmethod
    def get_latest_price(stock_key: int) -> Optional['MarketPrice']:
        """Get the most recent market price for a stock"""
        return MarketPrice.query.filter_by(
            stock_key=stock_key
        ).order_by(MarketPrice.date_key.desc()).first()
    
    @staticmethod
    def get_stocks_needing_updates() -> List[int]:
        """Get list of stock_keys that need price updates (missing recent data)"""
        from datetime import date
        today_key = int(date.today().strftime('%Y%m%d'))
        yesterday_key = today_key - 1  # Simplified - should handle weekends properly
        
        # Find stocks that don't have yesterday's price
        stocks_with_recent_prices = db.session.query(MarketPrice.stock_key).filter(
            MarketPrice.date_key >= yesterday_key
        ).distinct().all()
        
        recent_stock_keys = {stock[0] for stock in stocks_with_recent_prices}
        
        # Get all active stocks
        from app.models.stock import Stock
        all_active_stocks = db.session.query(Stock.stock_key).filter(
            Stock.verification_status == 'verified'
        ).all()
        
        all_stock_keys = {stock[0] for stock in all_active_stocks}
        
        return list(all_stock_keys - recent_stock_keys)