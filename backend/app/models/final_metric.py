from datetime import datetime
from app import db


class FinalMetric(db.Model):
    __tablename__ = 'final_metrics'
    
    metric_index = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stocks.id'), nullable=False)
    yahoo_symbol = db.Column(db.String(50))
    date = db.Column(db.Date)
    close_price = db.Column(db.Float)
    dividend = db.Column(db.Float, default=0.0)
    cash_dividend = db.Column(db.Float, default=0.0)
    cash_dividends_total = db.Column(db.Float, default=0.0)
    drp_flag = db.Column(db.Boolean, default=False)
    drp_share = db.Column(db.Float, default=0.0)
    drp_shares_total = db.Column(db.Float, default=0.0)
    split_ratio = db.Column(db.Float, default=1.0)
    cumulative_split_ratio = db.Column(db.Float, default=1.0)
    transaction_type = db.Column(db.String(20))
    adjusted_quantity = db.Column(db.Float)
    adjusted_price = db.Column(db.Float)
    net_transaction_quantity = db.Column(db.Float)
    total_investment_amount = db.Column(db.Float, default=0.0)
    cost_basis_variation = db.Column(db.Float, default=0.0)
    cumulative_cost_basis_variation = db.Column(db.Float, default=0.0)
    current_cost_basis = db.Column(db.Float, default=0.0)
    total_shares_owned = db.Column(db.Float)
    market_value = db.Column(db.Float, default=0.0)
    realised_pl = db.Column(db.Float, default=0.0)
    unrealised_pl = db.Column(db.Float, default=0.0)
    daily_pl = db.Column(db.Float, default=0.0)
    daily_pl_pct = db.Column(db.Float, default=0.0)
    total_return = db.Column(db.Float, default=0.0)
    total_return_pct = db.Column(db.Float, default=0.0)
    cumulative_return_pct = db.Column(db.Float, default=0.0)
    last_updated = db.Column(db.DateTime)
    
    # Relationships
    stock = db.relationship('Stock', back_populates='final_metrics')
    
    # Unique constraint on stock_id and date
    __table_args__ = (
        db.UniqueConstraint('stock_id', 'date'),
        db.Index('idx_final_metrics_stock_date', 'stock_id', 'date'),
        db.Index('idx_final_metrics_date', 'date')
    )
    
    def __repr__(self):
        return f'<FinalMetric {self.yahoo_symbol} {self.date} Value: ${self.market_value}>'
    
    def to_dict(self):
        return {
            'metric_index': self.metric_index,
            'stock_id': self.stock_id,
            'yahoo_symbol': self.yahoo_symbol,
            'date': self.date.isoformat() if self.date else None,
            'close_price': self.close_price,
            'dividend': self.dividend,
            'cash_dividend': self.cash_dividend,
            'cash_dividends_total': self.cash_dividends_total,
            'drp_flag': self.drp_flag,
            'drp_share': self.drp_share,
            'drp_shares_total': self.drp_shares_total,
            'split_ratio': self.split_ratio,
            'cumulative_split_ratio': self.cumulative_split_ratio,
            'transaction_type': self.transaction_type,
            'adjusted_quantity': self.adjusted_quantity,
            'adjusted_price': self.adjusted_price,
            'net_transaction_quantity': self.net_transaction_quantity,
            'total_investment_amount': self.total_investment_amount,
            'cost_basis_variation': self.cost_basis_variation,
            'cumulative_cost_basis_variation': self.cumulative_cost_basis_variation,
            'current_cost_basis': self.current_cost_basis,
            'total_shares_owned': self.total_shares_owned,
            'market_value': self.market_value,
            'realised_pl': self.realised_pl,
            'unrealised_pl': self.unrealised_pl,
            'daily_pl': self.daily_pl,
            'daily_pl_pct': self.daily_pl_pct,
            'total_return': self.total_return,
            'total_return_pct': self.total_return_pct,
            'cumulative_return_pct': self.cumulative_return_pct,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }
    
    @staticmethod
    def create(**kwargs):
        """Create a new final metric record"""
        final_metric = FinalMetric(**kwargs)
        db.session.add(final_metric)
        db.session.commit()
        return final_metric
    
    @staticmethod
    def get_by_stock(stock_id: int, start_date: datetime = None, end_date: datetime = None):
        """Get final metrics for a specific stock"""
        query = FinalMetric.query.filter_by(stock_id=stock_id)
        
        if start_date:
            query = query.filter(FinalMetric.date >= start_date)
        if end_date:
            query = query.filter(FinalMetric.date <= end_date)
            
        return query.order_by(FinalMetric.date).all()
    
    @staticmethod
    def get_latest_by_stock(stock_id: int):
        """Get the most recent metric for a stock"""
        return FinalMetric.query.filter_by(stock_id=stock_id)\
            .order_by(FinalMetric.date.desc()).first()
    
    @staticmethod
    def get_portfolio_summary(stock_ids: list, date: datetime = None):
        """Get aggregated metrics for a portfolio"""
        query = FinalMetric.query.filter(FinalMetric.stock_id.in_(stock_ids))
        
        if date:
            query = query.filter(FinalMetric.date == date)
        else:
            # Get latest metrics for each stock
            subquery = db.session.query(
                FinalMetric.stock_id,
                db.func.max(FinalMetric.date).label('max_date')
            ).filter(FinalMetric.stock_id.in_(stock_ids)).group_by(FinalMetric.stock_id).subquery()
            
            query = query.join(
                subquery,
                db.and_(
                    FinalMetric.stock_id == subquery.c.stock_id,
                    FinalMetric.date == subquery.c.max_date
                )
            )
        
        return query.all()
    
    @staticmethod
    def bulk_create(metrics_data_list):
        """Bulk create final metric records"""
        db.session.bulk_insert_mappings(FinalMetric, metrics_data_list)
        db.session.commit()
    
    def update(self, **kwargs):
        """Update final metric record"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.last_updated = datetime.utcnow()
        db.session.commit()
        return self
    
    def delete(self):
        """Delete final metric record"""
        db.session.delete(self)
        db.session.commit()