from app import db


class SupportedCurrency(db.Model):
    __tablename__ = 'supported_currencies'
    
    code = db.Column(db.String(3), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    symbol = db.Column(db.String(5))
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<Currency {self.code} - {self.name}>'
    
    def to_dict(self):
        return {
            'code': self.code,
            'name': self.name,
            'symbol': self.symbol,
            'is_active': self.is_active
        }
    
    @staticmethod
    def create(code: str, name: str, symbol: str = None, is_active: bool = True):
        """Create a new supported currency"""
        currency = SupportedCurrency(
            code=code,
            name=name,
            symbol=symbol,
            is_active=is_active
        )
        db.session.add(currency)
        db.session.commit()
        return currency
    
    @staticmethod
    def get_all(active_only: bool = True):
        """Get all supported currencies"""
        query = SupportedCurrency.query
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(SupportedCurrency.code).all()
    
    @staticmethod
    def get_by_code(code: str):
        """Get currency by code"""
        return SupportedCurrency.query.get(code.upper())
    
    def activate(self):
        """Activate currency"""
        self.is_active = True
        db.session.commit()
    
    def deactivate(self):
        """Deactivate currency"""
        self.is_active = False
        db.session.commit()
    
    def update(self, **kwargs):
        """Update currency fields"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        db.session.commit()
        return self
    
    def delete(self):
        """Delete currency"""
        db.session.delete(self)
        db.session.commit()


class MarketCode(db.Model):
    __tablename__ = 'market_codes'
    
    market_or_index = db.Column(db.String(255), primary_key=True)
    market_suffix = db.Column(db.String(10))
    
    def __repr__(self):
        return f'<MarketCode {self.market_or_index} - {self.market_suffix}>'
    
    def to_dict(self):
        return {
            'market_or_index': self.market_or_index,
            'market_suffix': self.market_suffix
        }
    
    @staticmethod
    def create(market_or_index: str, market_suffix: str = None):
        """Create a new market code"""
        market_code = MarketCode(
            market_or_index=market_or_index,
            market_suffix=market_suffix
        )
        db.session.add(market_code)
        db.session.commit()
        return market_code
    
    @staticmethod
    def get_all():
        """Get all market codes"""
        return MarketCode.query.order_by(MarketCode.market_or_index).all()
    
    @staticmethod
    def get_by_name(market_or_index: str):
        """Get market code by name"""
        return MarketCode.query.get(market_or_index)
    
    @staticmethod
    def get_by_suffix(market_suffix: str):
        """Get market codes by suffix"""
        return MarketCode.query.filter_by(market_suffix=market_suffix).all()
    
    def update(self, **kwargs):
        """Update market code fields"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        db.session.commit()
        return self
    
    def delete(self):
        """Delete market code"""
        db.session.delete(self)
        db.session.commit()