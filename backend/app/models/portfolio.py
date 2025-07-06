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
    
    def _format_date(self, date_value):
        """Helper method to format dates consistently"""
        if date_value is None:
            return None
        if isinstance(date_value, str):
            return date_value  # Already formatted
        if hasattr(date_value, 'isoformat'):
            return date_value.isoformat()
        return str(date_value)
    
    def to_dict(self, include_metrics=False):
        """Convert portfolio to dictionary with optional dashboard metrics"""
        base_dict = {
            'id': self.portfolio_key,  # Use 'id' for frontend consistency
            'name': self.portfolio_name,  # Use 'name' for frontend consistency
            'description': self.description,
            'currency': self.base_currency,  # Use 'currency' for frontend consistency
            'portfolio_type': self.portfolio_type,
            'created_by': self.created_by,
            'created_at': self._format_date(self.created_at),
            'updated_at': self._format_date(self.last_updated),
            'is_active': self.is_active
        }
        
        if include_metrics:
            # Get calculated metrics from the dashboard view
            metrics = self.get_dashboard_metrics()
            if metrics:
                base_dict.update({
                    'stock_count': metrics['stock_count'],
                    'total_value': metrics['total_value'],
                    'total_cost': metrics['total_cost'],
                    'gain_loss': metrics['gain_loss'],
                    'gain_loss_percent': metrics['gain_loss_percent'],
                    'day_change': metrics['day_change'],
                    'day_change_percent': metrics['day_change_percent'],
                    'realized_pl': metrics['realized_pl']
                })
            else:
                # Default values if no metrics available
                base_dict.update({
                    'stock_count': 0,
                    'total_value': 0.0,
                    'total_cost': 0.0,
                    'gain_loss': 0.0,
                    'gain_loss_percent': 0.0,
                    'day_change': 0.0,
                    'day_change_percent': 0.0,
                    'realized_pl': 0.0
                })
        else:
            # Basic portfolio info only
            base_dict['stock_count'] = 0
        
        return base_dict
    
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
    
    def get_dashboard_metrics(self):
        """Get comprehensive portfolio dashboard metrics using the new view"""
        from sqlalchemy import text
        try:
            result = db.session.execute(
                text("SELECT * FROM V_PORTFOLIO_DASHBOARD_SUMMARY WHERE portfolio_key = :portfolio_key"),
                {"portfolio_key": self.portfolio_key}
            ).fetchone()
            
            if result:
                return {
                    'portfolio_key': result.portfolio_key,
                    'portfolio_name': result.portfolio_name,
                    'base_currency': result.base_currency,
                    'created_at': self._format_date(result.created_at),
                    'stock_count': int(result.stock_count) if result.stock_count is not None else 0,
                    'total_value': float(result.total_value) if result.total_value is not None else 0.0,
                    'total_cost': float(result.total_cost) if result.total_cost is not None else 0.0,
                    'gain_loss': float(result.gain_loss) if result.gain_loss is not None else 0.0,
                    'gain_loss_percent': float(result.gain_loss_percent) if result.gain_loss_percent is not None else 0.0,
                    'day_change': float(result.day_change) if result.day_change is not None else 0.0,
                    'day_change_percent': float(result.day_change_percent) if result.day_change_percent is not None else 0.0,
                    'realized_pl': float(result.realized_pl) if result.realized_pl is not None else 0.0
                }
            else:
                # Return zero values if no data found for this portfolio
                return {
                    'portfolio_key': self.portfolio_key,
                    'portfolio_name': self.portfolio_name,
                    'base_currency': self.base_currency,
                    'created_at': self._format_date(self.created_at),
                    'stock_count': 0,
                    'total_value': 0.0,
                    'total_cost': 0.0,
                    'gain_loss': 0.0,
                    'gain_loss_percent': 0.0,
                    'day_change': 0.0,
                    'day_change_percent': 0.0,
                    'realized_pl': 0.0
                }
        except Exception as e:
            print(f"Error fetching dashboard metrics for portfolio {self.portfolio_key}: {str(e)}")
            # Return zero values if there's an error
            return {
                'portfolio_key': self.portfolio_key,
                'portfolio_name': self.portfolio_name,
                'base_currency': self.base_currency,
                'created_at': self._format_date(self.created_at),
                'stock_count': 0,
                'total_value': 0.0,
                'total_cost': 0.0,
                'gain_loss': 0.0,
                'gain_loss_percent': 0.0,
                'day_change': 0.0,
                'day_change_percent': 0.0,
                'realized_pl': 0.0
            }
    
    def get_current_positions(self):
        """Get current portfolio positions using the new view"""
        from sqlalchemy import text
        try:
            results = db.session.execute(
                text("SELECT * FROM V_CURRENT_POSITIONS WHERE portfolio_key = :portfolio_key"),
                {"portfolio_key": self.portfolio_key}
            ).fetchall()
            
            positions = []
            for row in results:
                positions.append({
                    'id': row.stock_key,
                    'symbol': row.symbol if row.symbol else '',
                    'company_name': row.company_name if row.company_name else '',
                    'quantity': float(row.quantity) if row.quantity is not None else 0.0,
                    'avg_cost': float(row.avg_cost) if row.avg_cost is not None else 0.0,
                    'current_price': float(row.current_price) if row.current_price is not None else 0.0,
                    'market_value': float(row.market_value) if row.market_value is not None else 0.0,
                    'total_cost': float(row.total_cost) if row.total_cost is not None else 0.0,
                    'gain_loss': float(row.gain_loss) if row.gain_loss is not None else 0.0,
                    'gain_loss_percent': float(row.gain_loss_percent) if row.gain_loss_percent is not None else 0.0,
                    'day_change': float(row.day_change) if row.day_change is not None else 0.0,
                    'day_change_percent': float(row.day_change_percent) if row.day_change_percent is not None else 0.0,
                    'cumulative_dividends': float(row.cumulative_dividends) if row.cumulative_dividends is not None else 0.0,
                    'currency': row.currency if row.currency else 'USD',
                    'exchange': row.exchange if row.exchange else '',
                    'sector': row.sector if row.sector else '',
                    'industry': row.industry if row.industry else '',
                    'last_updated_date': self._format_date(row.last_updated_date)
                })
            
            return positions
        except Exception as e:
            print(f"Error fetching positions for portfolio {self.portfolio_key}: {str(e)}")
            return []
    
    def get_recent_transactions(self, limit=10):
        """Get recent transactions for this portfolio"""
        from sqlalchemy import text
        try:
            results = db.session.execute(
                text("""
                    SELECT * FROM V_RECENT_TRANSACTIONS 
                    WHERE portfolio_key = :portfolio_key 
                    ORDER BY date DESC, created_at DESC 
                    LIMIT :limit
                """),
                {"portfolio_key": self.portfolio_key, "limit": limit}
            ).fetchall()
            
            transactions = []
            for row in results:
                transactions.append({
                    'id': row.id,
                    'symbol': row.symbol if row.symbol else '',
                    'company_name': row.company_name if row.company_name else '',
                    'action': row.action if row.action else '',
                    'quantity': float(row.quantity) if row.quantity is not None else 0.0,
                    'price': float(row.price) if row.price is not None else 0.0,
                    'total_value': float(row.total_value) if row.total_value is not None else 0.0,
                    'date': self._format_date(row.date),
                    'currency': row.original_currency if row.original_currency else 'USD',
                    'exchange_rate': float(row.exchange_rate) if row.exchange_rate is not None else 1.0
                })
            
            return transactions
        except Exception as e:
            print(f"Error fetching transactions for portfolio {self.portfolio_key}: {str(e)}")
            return []