from app import db


class YahooMarketCode(db.Model):
    """Yahoo Market Codes dimension model"""
    __tablename__ = 'DIM_YAHOO_MARKET_CODES'
    
    market_key = db.Column(db.Integer, primary_key=True)
    market_or_index = db.Column(db.Text, nullable=False, unique=True)
    market_suffix = db.Column(db.Text)
    
    def __repr__(self):
        return f'<YahooMarketCode {self.market_or_index} ({self.market_suffix})>'
    
    def to_dict(self):
        return {
            'market_key': self.market_key,
            'market_or_index': self.market_or_index,
            'market_suffix': self.market_suffix
        }
    
    @staticmethod
    def get_all():
        """Get all market codes"""
        return YahooMarketCode.query.all()
    
    @staticmethod
    def get_by_key(market_key: int):
        """Get market code by key"""
        return YahooMarketCode.query.get(market_key)
    
    @staticmethod
    def get_by_suffix(market_suffix: str):
        """Get market code by suffix"""
        return YahooMarketCode.query.filter_by(market_suffix=market_suffix).first()