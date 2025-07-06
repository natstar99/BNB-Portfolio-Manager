from datetime import datetime
from app import db


class Portfolio(db.Model):
    """Portfolio dimension model for Kimball star schema"""
    __tablename__ = 'DIM_PORTFOLIO'
    
    portfolio_key = db.Column(db.Integer, primary_key=True)
    portfolio_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    base_currency = db.Column(db.String(10), default='USD')
    portfolio_type = db.Column(db.String(50), default='INVESTMENT')
    created_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    transactions = db.relationship('Transaction', back_populates='portfolio')
    daily_metrics = db.relationship('DailyPortfolioMetric', back_populates='portfolio')
    
    def __repr__(self):
        return f'<Portfolio {self.portfolio_name}>'
    
    def to_dict(self):
        return {
            'id': self.portfolio_key,  # Use 'id' for frontend consistency
            'name': self.portfolio_name,  # Use 'name' for frontend consistency
            'description': self.description,
            'currency': self.base_currency,  # Use 'currency' for frontend consistency
            'portfolio_type': self.portfolio_type,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.last_updated.isoformat() if self.last_updated else None,
            'is_active': self.is_active,
            'stock_count': 0  # TODO: Calculate from actual positions
        }
    
    @staticmethod
    def create(portfolio_name: str, **kwargs):
        """Create a new portfolio"""
        portfolio = Portfolio(portfolio_name=portfolio_name, **kwargs)
        db.session.add(portfolio)
        db.session.commit()
        return portfolio
    
    @staticmethod
    def get_all():
        """Get all active portfolios"""
        return Portfolio.query.filter_by(is_active=True).all()
    
    @staticmethod
    def get_by_id(portfolio_key: int):
        """Get portfolio by portfolio_key"""
        return Portfolio.query.get(portfolio_key)
    
    @staticmethod
    def get_by_name(portfolio_name: str):
        """Get portfolio by name"""
        return Portfolio.query.filter_by(portfolio_name=portfolio_name, is_active=True).first()
    
    def update(self, **kwargs):
        """Update portfolio fields"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.last_updated = datetime.utcnow()
        db.session.commit()
        return self
    
    def soft_delete(self):
        """Soft delete portfolio by setting is_active to False"""
        self.is_active = False
        self.last_updated = datetime.utcnow()
        db.session.commit()
    
    def get_summary(self):
        """Get portfolio summary using the view"""
        from sqlalchemy import text
        result = db.session.execute(
            text("SELECT * FROM V_PORTFOLIO_SUMMARY WHERE portfolio_key = :portfolio_key"),
            {"portfolio_key": self.portfolio_key}
        ).fetchone()
        
        if result:
            return {
                'portfolio_key': result.portfolio_key,
                'portfolio_name': result.portfolio_name,
                'total_stocks': result.total_stocks,
                'total_value': float(result.total_value) if result.total_value else 0.0,
                'total_cost': float(result.total_cost) if result.total_cost else 0.0,
                'total_unrealized_pl': float(result.total_unrealized_pl) if result.total_unrealized_pl else 0.0,
                'unrealized_pl_percent': float(result.unrealized_pl_percent) if result.unrealized_pl_percent else 0.0
            }
        return None