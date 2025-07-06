from datetime import datetime, date
from app import db
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from decimal import Decimal


class DailyPortfolioMetric(db.Model):
    """Daily portfolio metrics fact model for pre-calculated performance data"""
    __tablename__ = 'FACT_DAILY_PORTFOLIO_METRICS'
    
    id = db.Column(db.Integer, primary_key=True)
    portfolio_key = db.Column(db.Integer, db.ForeignKey('DIM_PORTFOLIO.portfolio_key'), nullable=False)
    stock_key = db.Column(db.Integer, db.ForeignKey('DIM_STOCK.stock_key'), nullable=False)
    date_key = db.Column(db.Integer, nullable=False)
    
    # Market data (from FACT_MARKET_PRICES)
    close_price = db.Column(db.Numeric(10, 4), nullable=False)
    dividend = db.Column(db.Numeric(10, 4), default=0)
    split_ratio = db.Column(db.Numeric(10, 6), default=1.0)
    
    # Transaction data (if any transaction this date)
    transaction_type = db.Column(db.String(20))
    transaction_quantity = db.Column(db.Numeric(15, 6))
    transaction_value = db.Column(db.Numeric(20, 2))
    
    # Cumulative position metrics
    cumulative_shares = db.Column(db.Numeric(15, 6), nullable=False)
    cumulative_split_ratio = db.Column(db.Numeric(10, 6), nullable=False)
    average_cost_basis = db.Column(db.Numeric(10, 4), nullable=False)
    total_cost_basis = db.Column(db.Numeric(20, 2), nullable=False)
    
    # Performance metrics
    market_value = db.Column(db.Numeric(20, 2), nullable=False)
    unrealized_pl = db.Column(db.Numeric(20, 2), nullable=False)
    realized_pl = db.Column(db.Numeric(20, 2), nullable=False)
    daily_pl = db.Column(db.Numeric(20, 2), nullable=False)
    daily_pl_pct = db.Column(db.Numeric(8, 4), nullable=False)
    total_return_pct = db.Column(db.Numeric(8, 4), nullable=False)
    
    # DRP and dividend tracking
    cash_dividend = db.Column(db.Numeric(10, 4), default=0)
    drp_shares = db.Column(db.Numeric(15, 6), default=0)
    cumulative_dividends = db.Column(db.Numeric(20, 2), default=0)
    
    # Audit fields
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    portfolio = db.relationship('Portfolio', back_populates='daily_metrics')
    stock = db.relationship('Stock', back_populates='daily_metrics')
    
    def __repr__(self):
        return f'<DailyPortfolioMetric Portfolio:{self.portfolio_key} Stock:{self.stock_key} Date:{self.date_key}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'portfolio_key': self.portfolio_key,
            'stock_key': self.stock_key,
            'date_key': self.date_key,
            'close_price': float(self.close_price) if self.close_price else 0.0,
            'dividend': float(self.dividend) if self.dividend else 0.0,
            'split_ratio': float(self.split_ratio) if self.split_ratio else 1.0,
            'transaction_type': self.transaction_type,
            'transaction_quantity': float(self.transaction_quantity) if self.transaction_quantity else None,
            'transaction_value': float(self.transaction_value) if self.transaction_value else None,
            'cumulative_shares': float(self.cumulative_shares) if self.cumulative_shares else 0.0,
            'cumulative_split_ratio': float(self.cumulative_split_ratio) if self.cumulative_split_ratio else 1.0,
            'average_cost_basis': float(self.average_cost_basis) if self.average_cost_basis else 0.0,
            'total_cost_basis': float(self.total_cost_basis) if self.total_cost_basis else 0.0,
            'market_value': float(self.market_value) if self.market_value else 0.0,
            'unrealized_pl': float(self.unrealized_pl) if self.unrealized_pl else 0.0,
            'realized_pl': float(self.realized_pl) if self.realized_pl else 0.0,
            'daily_pl': float(self.daily_pl) if self.daily_pl else 0.0,
            'daily_pl_pct': float(self.daily_pl_pct) if self.daily_pl_pct else 0.0,
            'total_return_pct': float(self.total_return_pct) if self.total_return_pct else 0.0,
            'cash_dividend': float(self.cash_dividend) if self.cash_dividend else 0.0,
            'drp_shares': float(self.drp_shares) if self.drp_shares else 0.0,
            'cumulative_dividends': float(self.cumulative_dividends) if self.cumulative_dividends else 0.0,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @staticmethod
    def create(portfolio_key: int, stock_key: int, date_key: int, **kwargs):
        """Create a new daily metric record"""
        metric = DailyPortfolioMetric(
            portfolio_key=portfolio_key,
            stock_key=stock_key,
            date_key=date_key,
            **kwargs
        )
        
        db.session.add(metric)
        db.session.commit()
        return metric
    
    @staticmethod
    def get_latest_metric(portfolio_key: int, stock_key: int) -> Optional['DailyPortfolioMetric']:
        """Get the most recent metric for a portfolio/stock combination"""
        return DailyPortfolioMetric.query.filter_by(
            portfolio_key=portfolio_key,
            stock_key=stock_key
        ).order_by(DailyPortfolioMetric.date_key.desc()).first()
    
    @staticmethod
    def get_metric_by_date(portfolio_key: int, stock_key: int, date_key: int) -> Optional['DailyPortfolioMetric']:
        """Get metric for specific portfolio/stock/date"""
        return DailyPortfolioMetric.query.filter_by(
            portfolio_key=portfolio_key,
            stock_key=stock_key,
            date_key=date_key
        ).first()
    
    @staticmethod
    def get_portfolio_metrics_range(portfolio_key: int, start_date_key: int, end_date_key: int) -> List['DailyPortfolioMetric']:
        """Get all metrics for a portfolio within date range"""
        return DailyPortfolioMetric.query.filter(
            DailyPortfolioMetric.portfolio_key == portfolio_key,
            DailyPortfolioMetric.date_key >= start_date_key,
            DailyPortfolioMetric.date_key <= end_date_key
        ).order_by(DailyPortfolioMetric.date_key).all()
    
    @staticmethod
    def get_stock_metrics_range(portfolio_key: int, stock_key: int, start_date_key: int, end_date_key: int) -> List['DailyPortfolioMetric']:
        """Get metrics for specific stock within date range"""
        return DailyPortfolioMetric.query.filter(
            DailyPortfolioMetric.portfolio_key == portfolio_key,
            DailyPortfolioMetric.stock_key == stock_key,
            DailyPortfolioMetric.date_key >= start_date_key,
            DailyPortfolioMetric.date_key <= end_date_key
        ).order_by(DailyPortfolioMetric.date_key).all()
    
    @staticmethod
    def delete_metrics_from_date(portfolio_key: int, stock_key: int, from_date_key: int):
        """Delete metrics from specified date forward (for recalculation)"""
        DailyPortfolioMetric.query.filter(
            DailyPortfolioMetric.portfolio_key == portfolio_key,
            DailyPortfolioMetric.stock_key == stock_key,
            DailyPortfolioMetric.date_key >= from_date_key
        ).delete()
        db.session.commit()
    
    @staticmethod
    def get_portfolio_summary(portfolio_key: int, date_key: int) -> Dict[str, Any]:
        """Get portfolio summary for specific date"""
        metrics = DailyPortfolioMetric.query.filter_by(
            portfolio_key=portfolio_key,
            date_key=date_key
        ).all()
        
        if not metrics:
            return {
                'total_market_value': 0.0,
                'total_cost_basis': 0.0,
                'total_unrealized_pl': 0.0,
                'total_realized_pl': 0.0,
                'total_return_pct': 0.0,
                'stock_count': 0
            }
        
        total_market_value = sum(float(m.market_value) for m in metrics)
        total_cost_basis = sum(float(m.total_cost_basis) for m in metrics)
        total_unrealized_pl = sum(float(m.unrealized_pl) for m in metrics)
        total_realized_pl = sum(float(m.realized_pl) for m in metrics)
        
        total_return_pct = 0.0
        if total_cost_basis > 0:
            total_return_pct = ((total_market_value + total_realized_pl - total_cost_basis) / total_cost_basis) * 100
        
        return {
            'total_market_value': total_market_value,
            'total_cost_basis': total_cost_basis,
            'total_unrealized_pl': total_unrealized_pl,
            'total_realized_pl': total_realized_pl,
            'total_return_pct': total_return_pct,
            'stock_count': len(metrics)
        }
    
    @staticmethod
    def get_current_portfolio_holdings(portfolio_key: int) -> List['DailyPortfolioMetric']:
        """Get current holdings for portfolio (latest metrics for each stock with shares > 0)"""
        # Get the latest date_key for this portfolio
        latest_date_subquery = db.session.query(
            DailyPortfolioMetric.stock_key,
            db.func.max(DailyPortfolioMetric.date_key).label('max_date')
        ).filter_by(portfolio_key=portfolio_key).group_by(DailyPortfolioMetric.stock_key).subquery()
        
        # Get the latest metrics for each stock
        latest_metrics = DailyPortfolioMetric.query.join(
            latest_date_subquery,
            (DailyPortfolioMetric.stock_key == latest_date_subquery.c.stock_key) &
            (DailyPortfolioMetric.date_key == latest_date_subquery.c.max_date)
        ).filter(
            DailyPortfolioMetric.portfolio_key == portfolio_key,
            DailyPortfolioMetric.cumulative_shares > 0
        ).all()
        
        return latest_metrics