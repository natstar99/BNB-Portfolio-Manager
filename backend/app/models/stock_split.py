from datetime import datetime
from app import db


class StockSplit(db.Model):
    __tablename__ = 'stock_splits'
    
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stocks.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    ratio = db.Column(db.Float, nullable=False)
    verified_source = db.Column(db.String(50))  # 'yahoo', 'manual', etc.
    verification_date = db.Column(db.DateTime)
    
    # Relationships
    stock = db.relationship('Stock', back_populates='stock_splits')
    
    def __repr__(self):
        return f'<StockSplit {self.stock.yahoo_symbol if self.stock else "Unknown"} {self.ratio}:1 on {self.date}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'stock_id': self.stock_id,
            'date': self.date.isoformat() if self.date else None,
            'ratio': self.ratio,
            'verified_source': self.verified_source,
            'verification_date': self.verification_date.isoformat() if self.verification_date else None,
            'stock': self.stock.to_dict() if self.stock else None
        }
    
    @staticmethod
    def create(stock_id: int, date: datetime, ratio: float, **kwargs):
        """Create a new stock split record"""
        stock_split = StockSplit(
            stock_id=stock_id,
            date=date,
            ratio=ratio,
            **kwargs
        )
        db.session.add(stock_split)
        db.session.commit()
        return stock_split
    
    @staticmethod
    def get_by_stock(stock_id: int):
        """Get all stock splits for a specific stock"""
        return StockSplit.query.filter_by(stock_id=stock_id).order_by(StockSplit.date).all()
    
    @staticmethod
    def get_by_date_range(start_date: datetime, end_date: datetime):
        """Get stock splits within a date range"""
        return StockSplit.query.filter(
            StockSplit.date >= start_date,
            StockSplit.date <= end_date
        ).order_by(StockSplit.date).all()
    
    def verify(self, source: str):
        """Mark the stock split as verified"""
        self.verified_source = source
        self.verification_date = datetime.utcnow()
        db.session.commit()
    
    def delete(self):
        """Delete stock split record"""
        db.session.delete(self)
        db.session.commit()