from datetime import datetime
from app import db


class PortfolioPosition(db.Model):
    """Portfolio positions snapshot model"""
    __tablename__ = 'PORTFOLIO_POSITIONS'
    
    position_key = db.Column(db.Integer, primary_key=True)
    portfolio_key = db.Column(db.Integer, db.ForeignKey('DIM_PORTFOLIO.portfolio_key'), nullable=False)
    stock_key = db.Column(db.Integer, db.ForeignKey('DIM_STOCK.stock_key'), nullable=False)
    
    # Position details
    current_quantity = db.Column(db.Numeric(15, 6), nullable=False, default=0)
    average_cost = db.Column(db.Numeric(10, 4), nullable=False, default=0)
    total_cost = db.Column(db.Numeric(20, 2), nullable=False, default=0)
    current_price = db.Column(db.Numeric(10, 4), nullable=False, default=0)
    current_value = db.Column(db.Numeric(20, 2), nullable=False, default=0)
    
    # P&L information
    unrealized_pl = db.Column(db.Numeric(20, 2), nullable=False, default=0)
    unrealized_pl_percent = db.Column(db.Numeric(10, 4), nullable=False, default=0)
    
    # Audit fields
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    portfolio = db.relationship('Portfolio', back_populates='positions')
    stock = db.relationship('Stock', back_populates='positions')
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('portfolio_key', 'stock_key'),)
    
    def __repr__(self):
        return f'<Position {self.portfolio_key}:{self.stock_key} - {self.current_quantity}>'
    
    def to_dict(self):
        return {
            'position_key': self.position_key,
            'portfolio_key': self.portfolio_key,
            'stock_key': self.stock_key,
            'current_quantity': float(self.current_quantity) if self.current_quantity else 0.0,
            'average_cost': float(self.average_cost) if self.average_cost else 0.0,
            'total_cost': float(self.total_cost) if self.total_cost else 0.0,
            'current_price': float(self.current_price) if self.current_price else 0.0,
            'current_value': float(self.current_value) if self.current_value else 0.0,
            'unrealized_pl': float(self.unrealized_pl) if self.unrealized_pl else 0.0,
            'unrealized_pl_percent': float(self.unrealized_pl_percent) if self.unrealized_pl_percent else 0.0,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            # Include related data
            'portfolio': self.portfolio.to_dict() if self.portfolio else None,
            'stock': self.stock.to_dict() if self.stock else None
        }
    
    @staticmethod
    def get_or_create(portfolio_key: int, stock_key: int):
        """Get existing position or create new one"""
        position = PortfolioPosition.query.filter_by(
            portfolio_key=portfolio_key,
            stock_key=stock_key
        ).first()
        
        if not position:
            position = PortfolioPosition(
                portfolio_key=portfolio_key,
                stock_key=stock_key
            )
            db.session.add(position)
            db.session.commit()
        
        return position
    
    @staticmethod
    def get_by_portfolio(portfolio_key: int):
        """Get all positions for a portfolio"""
        return PortfolioPosition.query.filter_by(portfolio_key=portfolio_key).all()
    
    @staticmethod
    def get_by_stock(stock_key: int):
        """Get all positions for a stock"""
        return PortfolioPosition.query.filter_by(stock_key=stock_key).all()
    
    def update_position(self, quantity_change: float, price: float, is_buy: bool):
        """Update position based on transaction"""
        if is_buy:
            # Calculate new average cost for buy transactions
            if self.current_quantity > 0:
                total_cost = (self.current_quantity * self.average_cost) + (quantity_change * price)
                new_quantity = self.current_quantity + quantity_change
                self.average_cost = total_cost / new_quantity if new_quantity > 0 else 0
            else:
                self.average_cost = price
            
            self.current_quantity += quantity_change
            self.total_cost = self.current_quantity * self.average_cost
        else:
            # Sell transaction
            self.current_quantity -= quantity_change
            if self.current_quantity <= 0:
                self.current_quantity = 0
                self.average_cost = 0
                self.total_cost = 0
            else:
                self.total_cost = self.current_quantity * self.average_cost
        
        self.last_updated = datetime.utcnow()
        db.session.commit()
    
    def update_market_value(self, current_price: float):
        """Update current market value and P&L"""
        self.current_price = current_price
        self.current_value = self.current_quantity * current_price
        
        if self.total_cost > 0:
            self.unrealized_pl = self.current_value - self.total_cost
            self.unrealized_pl_percent = (self.unrealized_pl / self.total_cost) * 100
        else:
            self.unrealized_pl = 0
            self.unrealized_pl_percent = 0
        
        self.last_updated = datetime.utcnow()
        db.session.commit()
    
    def recalculate_from_transactions(self):
        """Recalculate position from all transactions"""
        from app.models.transaction import Transaction, TransactionType
        
        # Get all transactions for this position
        transactions = Transaction.query.filter_by(
            portfolio_key=self.portfolio_key,
            stock_key=self.stock_key
        ).order_by(Transaction.transaction_date, Transaction.created_at).all()
        
        # Reset position
        self.current_quantity = 0
        self.average_cost = 0
        self.total_cost = 0
        
        # Process each transaction
        for transaction in transactions:
            if transaction.transaction_type.is_buy_type:
                self.update_position(
                    float(transaction.quantity),
                    float(transaction.price),
                    True
                )
            elif transaction.transaction_type.is_sell_type:
                self.update_position(
                    float(transaction.quantity),
                    float(transaction.price),
                    False
                )
        
        db.session.commit()