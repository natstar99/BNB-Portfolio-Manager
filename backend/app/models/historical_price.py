from datetime import datetime
from app import db


class HistoricalPrice(db.Model):
    __tablename__ = 'historical_prices'
    
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stocks.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    open_price = db.Column(db.Float)
    high_price = db.Column(db.Float)
    low_price = db.Column(db.Float)
    close_price = db.Column(db.Float)
    volume = db.Column(db.Integer)
    dividend = db.Column(db.Float)
    split_ratio = db.Column(db.Float)
    currency_conversion_rate = db.Column(db.Float, default=1.0)
    
    # Relationships
    stock = db.relationship('Stock', back_populates='historical_prices')
    
    # Unique constraint on stock_id and date
    __table_args__ = (db.UniqueConstraint('stock_id', 'date'),)
    
    def __repr__(self):
        return f'<HistoricalPrice {self.stock.yahoo_symbol if self.stock else "Unknown"} {self.date} Close: {self.close_price}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'stock_id': self.stock_id,
            'date': self.date.isoformat() if self.date else None,
            'open_price': self.open_price,
            'high_price': self.high_price,
            'low_price': self.low_price,
            'close_price': self.close_price,
            'volume': self.volume,
            'dividend': self.dividend,
            'split_ratio': self.split_ratio,
            'currency_conversion_rate': self.currency_conversion_rate,
            'stock': self.stock.to_dict() if self.stock else None
        }
    
    @staticmethod
    def create(stock_id: int, date: datetime, **kwargs):
        """Create a new historical price record"""
        historical_price = HistoricalPrice(
            stock_id=stock_id,
            date=date,
            **kwargs
        )
        db.session.add(historical_price)
        db.session.commit()
        return historical_price
    
    @staticmethod
    def get_by_stock(stock_id: int, start_date: datetime = None, end_date: datetime = None):
        """Get historical prices for a specific stock"""
        query = HistoricalPrice.query.filter_by(stock_id=stock_id)
        
        if start_date:
            query = query.filter(HistoricalPrice.date >= start_date)
        if end_date:
            query = query.filter(HistoricalPrice.date <= end_date)
            
        return query.order_by(HistoricalPrice.date).all()
    
    @staticmethod
    def get_latest_price(stock_id: int):
        """Get the most recent price for a stock"""
        return HistoricalPrice.query.filter_by(stock_id=stock_id)\
            .order_by(HistoricalPrice.date.desc()).first()
    
    @staticmethod
    def bulk_create(price_data_list):
        """Bulk create historical price records"""
        db.session.bulk_insert_mappings(HistoricalPrice, price_data_list)
        db.session.commit()
    
    def update(self, **kwargs):
        """Update historical price record"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        db.session.commit()
        return self
    
    def delete(self):
        """Delete historical price record"""
        db.session.delete(self)
        db.session.commit()
    
    @property
    def price_change(self):
        """Calculate price change from open to close"""
        if self.open_price and self.close_price:
            return self.close_price - self.open_price
        return None
    
    @property
    def price_change_percentage(self):
        """Calculate percentage price change from open to close"""
        if self.open_price and self.close_price and self.open_price != 0:
            return ((self.close_price - self.open_price) / self.open_price) * 100
        return None