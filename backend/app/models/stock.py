from datetime import datetime
from app import db
from sqlalchemy import text


class Stock(db.Model):
    """Stock dimension model for Kimball star schema"""
    __tablename__ = 'DIM_STOCK'
    
    stock_key = db.Column(db.Integer, primary_key=True)
    portfolio_key = db.Column(db.Integer, db.ForeignKey('DIM_PORTFOLIO.portfolio_key'), nullable=False)
    market_key = db.Column(db.Integer, db.ForeignKey('DIM_YAHOO_MARKET_CODES.market_key'))
    instrument_code = db.Column(db.String(20), nullable=False)
    yahoo_symbol = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    sector = db.Column(db.String(100))
    industry = db.Column(db.String(100))
    exchange = db.Column(db.String(50))
    country = db.Column(db.String(50))
    market_cap = db.Column(db.Numeric(20, 2))
    verification_status = db.Column(db.String(20), default='pending')
    drp_enabled = db.Column(db.Boolean, default=False)
    current_price = db.Column(db.Numeric(10, 4), default=0.0)
    currency = db.Column(db.String(10))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    portfolio = db.relationship('Portfolio', backref='stocks')
    transactions = db.relationship('Transaction', back_populates='stock')
    market_prices = db.relationship('MarketPrice', back_populates='stock')
    daily_metrics = db.relationship('DailyPortfolioMetric', back_populates='stock')
    
    # Table constraints
    __table_args__ = (
        db.UniqueConstraint('portfolio_key', 'instrument_code', name='uq_portfolio_instrument'),
    )
    
    def __repr__(self):
        return f'<Stock {self.instrument_code} - {self.name}>'
    
    def to_dict(self):
        return {
            'stock_key': self.stock_key,
            'portfolio_key': self.portfolio_key,
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
            'drp_enabled': self.drp_enabled,
            'current_price': float(self.current_price) if self.current_price else 0.0,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }
    
    @staticmethod
    def create(portfolio_key: int, instrument_code: str, yahoo_symbol: str, name: str, **kwargs):
        """Create a new stock"""
        stock = Stock(
            portfolio_key=portfolio_key,
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
        """Get all stocks"""
        return Stock.query.all()
    
    @staticmethod
    def get_by_id(stock_key: int):
        """Get stock by stock_key"""
        return Stock.query.get(stock_key)
    
    @staticmethod
    def get_by_portfolio_and_instrument(portfolio_key: int, instrument_code: str):
        """Get stock by portfolio and instrument code"""
        return Stock.query.filter_by(
            portfolio_key=portfolio_key, 
            instrument_code=instrument_code
        ).first()
    
    @staticmethod
    def get_by_instrument_code(instrument_code: str):
        """Get stock by instrument code (returns first match - consider using get_by_portfolio_and_instrument instead)"""
        return Stock.query.filter_by(instrument_code=instrument_code).first()
    
    @staticmethod
    def get_by_portfolio(portfolio_key: int):
        """Get all stocks for a portfolio"""
        return Stock.query.filter_by(portfolio_key=portfolio_key).all()
    
    @staticmethod
    def get_by_yahoo_symbol(yahoo_symbol: str):
        """Get stock by Yahoo symbol (returns first match)"""
        return Stock.query.filter_by(yahoo_symbol=yahoo_symbol).first()
    
    def update(self, **kwargs):
        """Update stock fields"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.last_updated = datetime.utcnow()
        db.session.commit()
        return self
    
    def delete(self):
        """Delete stock"""
        db.session.delete(self)
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