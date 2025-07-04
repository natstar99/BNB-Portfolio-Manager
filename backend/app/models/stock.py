from datetime import datetime
from app import db
from sqlalchemy import text


class Stock(db.Model):
    """Stock dimension model for Kimball star schema"""
    __tablename__ = 'DIM_STOCK'
    
    stock_key = db.Column(db.Integer, primary_key=True)
    instrument_code = db.Column(db.String(20), nullable=False, unique=True)
    yahoo_symbol = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    market_key = db.Column(db.Integer, db.ForeignKey('DIM_YAHOO_MARKET_CODES.market_key'))
    sector = db.Column(db.String(100))
    industry = db.Column(db.String(100))
    exchange = db.Column(db.String(50))
    currency = db.Column(db.String(10), default='USD')
    country = db.Column(db.String(50))
    market_cap = db.Column(db.Numeric(20, 2))
    verification_status = db.Column(db.String(20), default='pending')
    current_price = db.Column(db.Numeric(10, 4), default=0.0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    transactions = db.relationship('Transaction', back_populates='stock')
    positions = db.relationship('PortfolioPosition', back_populates='stock')
    
    def __repr__(self):
        return f'<Stock {self.instrument_code} - {self.name}>'
    
    def to_dict(self):
        return {
            'stock_key': self.stock_key,
            'instrument_code': self.instrument_code,
            'yahoo_symbol': self.yahoo_symbol,
            'name': self.name,
            'market_key': self.market_key,
            'sector': self.sector,
            'industry': self.industry,
            'exchange': self.exchange,
            'currency': self.currency,
            'country': self.country,
            'market_cap': float(self.market_cap) if self.market_cap else None,
            'verification_status': self.verification_status,
            'current_price': float(self.current_price) if self.current_price else 0.0,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active
        }
    
    @staticmethod
    def create(instrument_code: str, yahoo_symbol: str, name: str, **kwargs):
        """Create a new stock"""
        stock = Stock(
            instrument_code=instrument_code,
            yahoo_symbol=yahoo_symbol,
            name=name,
            **kwargs
        )
        db.session.add(stock)
        db.session.commit()
        return stock
    
    @staticmethod
    def get_all():
        """Get all active stocks"""
        return Stock.query.filter_by(is_active=True).all()
    
    @staticmethod
    def get_by_id(stock_key: int):
        """Get stock by stock_key"""
        return Stock.query.get(stock_key)
    
    @staticmethod
    def get_by_instrument_code(instrument_code: str):
        """Get stock by instrument code"""
        return Stock.query.filter_by(instrument_code=instrument_code, is_active=True).first()
    
    @staticmethod
    def get_by_yahoo_symbol(yahoo_symbol: str):
        """Get stock by Yahoo symbol"""
        return Stock.query.filter_by(yahoo_symbol=yahoo_symbol, is_active=True).first()
    
    def update(self, **kwargs):
        """Update stock fields"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.last_updated = datetime.utcnow()
        db.session.commit()
        return self
    
    def soft_delete(self):
        """Soft delete stock by setting is_active to False"""
        self.is_active = False
        self.last_updated = datetime.utcnow()
        db.session.commit()
    
    def update_price(self, price: float):
        """Update the current price of the stock"""
        self.current_price = price
        self.last_updated = datetime.utcnow()
        db.session.commit()
    
    def verify(self):
        """Mark stock as verified"""
        self.verification_status = 'verified'
        self.last_updated = datetime.utcnow()
        db.session.commit()
    
    def mark_failed(self):
        """Mark stock verification as failed"""
        self.verification_status = 'failed'
        self.last_updated = datetime.utcnow()
        db.session.commit()