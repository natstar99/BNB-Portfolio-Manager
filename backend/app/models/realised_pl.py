from datetime import datetime
from app import db


class RealisedPL(db.Model):
    __tablename__ = 'realised_pl'
    
    id = db.Column(db.Integer, primary_key=True)
    sell_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=False)
    buy_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stocks.id'), nullable=False)
    matched_units = db.Column(db.Float, nullable=False)
    buy_price = db.Column(db.Float, nullable=False)
    sell_price = db.Column(db.Float, nullable=False)
    purchase_price = db.Column(db.Float, nullable=False)
    realised_pl = db.Column(db.Float, nullable=False)
    trade_date = db.Column(db.DateTime, nullable=False)
    method = db.Column(db.String(10), nullable=False)  # 'fifo', 'lifo', 'hifo'
    
    # Relationships
    sell_transaction = db.relationship('Transaction', foreign_keys=[sell_id], back_populates='realised_pl_sell')
    buy_transaction = db.relationship('Transaction', foreign_keys=[buy_id], back_populates='realised_pl_buy')
    stock = db.relationship('Stock')
    
    # Check constraint for method
    __table_args__ = (db.CheckConstraint(method.in_(['fifo', 'lifo', 'hifo'])),)
    
    def __repr__(self):
        return f'<RealisedPL {self.stock.yahoo_symbol if self.stock else "Unknown"} {self.matched_units} units: ${self.realised_pl}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'sell_id': self.sell_id,
            'buy_id': self.buy_id,
            'stock_id': self.stock_id,
            'matched_units': self.matched_units,
            'buy_price': self.buy_price,
            'sell_price': self.sell_price,
            'purchase_price': self.purchase_price,
            'realised_pl': self.realised_pl,
            'trade_date': self.trade_date.isoformat() if self.trade_date else None,
            'method': self.method,
            'stock': self.stock.to_dict() if self.stock else None
        }
    
    @staticmethod
    def create(sell_id: int, buy_id: int, stock_id: int, matched_units: float,
               buy_price: float, sell_price: float, purchase_price: float,
               realised_pl: float, trade_date: datetime, method: str):
        """Create a new realised P&L record"""
        realised_pl_record = RealisedPL(
            sell_id=sell_id,
            buy_id=buy_id,
            stock_id=stock_id,
            matched_units=matched_units,
            buy_price=buy_price,
            sell_price=sell_price,
            purchase_price=purchase_price,
            realised_pl=realised_pl,
            trade_date=trade_date,
            method=method
        )
        db.session.add(realised_pl_record)
        db.session.commit()
        return realised_pl_record
    
    @staticmethod
    def get_by_stock(stock_id: int):
        """Get all realised P&L records for a stock"""
        return RealisedPL.query.filter_by(stock_id=stock_id).all()
    
    @staticmethod
    def get_by_method(method: str):
        """Get all realised P&L records for a specific calculation method"""
        return RealisedPL.query.filter_by(method=method).all()
    
    @staticmethod
    def get_total_realised_pl(stock_id: int = None, method: str = None):
        """Calculate total realised P&L"""
        query = RealisedPL.query
        
        if stock_id:
            query = query.filter_by(stock_id=stock_id)
        if method:
            query = query.filter_by(method=method)
            
        records = query.all()
        return sum(record.realised_pl for record in records)
    
    def delete(self):
        """Delete realised P&L record"""
        db.session.delete(self)
        db.session.commit()