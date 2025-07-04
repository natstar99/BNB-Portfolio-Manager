from datetime import datetime, date
from app import db
from sqlalchemy import text


class TransactionType(db.Model):
    """Transaction type dimension model"""
    __tablename__ = 'DIM_TRANSACTION_TYPE'
    
    transaction_type_key = db.Column(db.Integer, primary_key=True)
    transaction_type = db.Column(db.String(20), nullable=False, unique=True)
    description = db.Column(db.String(255))
    is_buy_type = db.Column(db.Boolean, default=False)
    is_sell_type = db.Column(db.Boolean, default=False)
    affects_quantity = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    transactions = db.relationship('Transaction', back_populates='transaction_type')
    
    def __repr__(self):
        return f'<TransactionType {self.transaction_type}>'
    
    def to_dict(self):
        return {
            'transaction_type_key': self.transaction_type_key,
            'transaction_type': self.transaction_type,
            'description': self.description,
            'is_buy_type': self.is_buy_type,
            'is_sell_type': self.is_sell_type,
            'affects_quantity': self.affects_quantity,
            'is_active': self.is_active
        }
    
    @staticmethod
    def get_by_type(transaction_type: str):
        """Get transaction type by type string"""
        return TransactionType.query.filter_by(
            transaction_type=transaction_type.upper(),
            is_active=True
        ).first()


class Transaction(db.Model):
    """Transaction fact model for Kimball star schema"""
    __tablename__ = 'FACT_TRANSACTIONS'
    
    transaction_key = db.Column(db.Integer, primary_key=True)
    stock_key = db.Column(db.Integer, db.ForeignKey('DIM_STOCK.stock_key'), nullable=False)
    portfolio_key = db.Column(db.Integer, db.ForeignKey('DIM_PORTFOLIO.portfolio_key'), nullable=False)
    transaction_type_key = db.Column(db.Integer, db.ForeignKey('DIM_TRANSACTION_TYPE.transaction_type_key'), nullable=False)
    date_key = db.Column(db.Integer, db.ForeignKey('DIM_DATE.date_key'), nullable=False)
    
    # Transaction details
    transaction_date = db.Column(db.Date, nullable=False)
    quantity = db.Column(db.Numeric(15, 6), nullable=False)
    price = db.Column(db.Numeric(10, 4), nullable=False)
    total_value = db.Column(db.Numeric(20, 2), nullable=False)
    
    # Currency information
    original_currency = db.Column(db.String(10), default='USD')
    base_currency = db.Column(db.String(10), default='USD')
    exchange_rate = db.Column(db.Numeric(10, 6), default=1.0)
    
    # Calculated fields
    total_value_base = db.Column(db.Numeric(20, 2), nullable=False)
    
    # Audit fields
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    stock = db.relationship('Stock', back_populates='transactions')
    portfolio = db.relationship('Portfolio', back_populates='transactions')
    transaction_type = db.relationship('TransactionType', back_populates='transactions')
    
    def __repr__(self):
        return f'<Transaction {self.transaction_key}: {self.quantity} of {self.stock.instrument_code if self.stock else "Unknown"}>'
    
    def to_dict(self):
        return {
            'transaction_key': self.transaction_key,
            'stock_key': self.stock_key,
            'portfolio_key': self.portfolio_key,
            'transaction_type_key': self.transaction_type_key,
            'date_key': self.date_key,
            'transaction_date': self.transaction_date.isoformat() if self.transaction_date else None,
            'quantity': float(self.quantity) if self.quantity else 0.0,
            'price': float(self.price) if self.price else 0.0,
            'total_value': float(self.total_value) if self.total_value else 0.0,
            'original_currency': self.original_currency,
            'base_currency': self.base_currency,
            'exchange_rate': float(self.exchange_rate) if self.exchange_rate else 1.0,
            'total_value_base': float(self.total_value_base) if self.total_value_base else 0.0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            # Include related data
            'stock': self.stock.to_dict() if self.stock else None,
            'portfolio': self.portfolio.to_dict() if self.portfolio else None,
            'transaction_type': self.transaction_type.to_dict() if self.transaction_type else None
        }
    
    @staticmethod
    def create(stock_key: int, portfolio_key: int, transaction_type: str, 
               transaction_date: date, quantity: float, price: float, **kwargs):
        """Create a new transaction"""
        # Get transaction type
        trans_type = TransactionType.get_by_type(transaction_type)
        if not trans_type:
            raise ValueError(f"Invalid transaction type: {transaction_type}")
        
        # Generate date key (YYYYMMDD format)
        date_key = int(transaction_date.strftime('%Y%m%d'))
        
        # Calculate total value
        total_value = quantity * price
        
        # Calculate base currency value (assuming USD for now)
        exchange_rate = kwargs.get('exchange_rate', 1.0)
        total_value_base = total_value * exchange_rate
        
        transaction = Transaction(
            stock_key=stock_key,
            portfolio_key=portfolio_key,
            transaction_type_key=trans_type.transaction_type_key,
            date_key=date_key,
            transaction_date=transaction_date,
            quantity=quantity,
            price=price,
            total_value=total_value,
            total_value_base=total_value_base,
            exchange_rate=exchange_rate,
            **kwargs
        )
        
        db.session.add(transaction)
        db.session.commit()
        return transaction
    
    @staticmethod
    def get_all():
        """Get all transactions"""
        return Transaction.query.all()
    
    @staticmethod
    def get_by_portfolio(portfolio_key: int):
        """Get transactions by portfolio"""
        return Transaction.query.filter_by(portfolio_key=portfolio_key).all()
    
    @staticmethod
    def get_by_stock(stock_key: int):
        """Get transactions by stock"""
        return Transaction.query.filter_by(stock_key=stock_key).all()
    
    @staticmethod
    def get_recent(limit: int = 50):
        """Get recent transactions"""
        return Transaction.query.order_by(
            Transaction.transaction_date.desc(),
            Transaction.created_at.desc()
        ).limit(limit).all()


class RawTransaction(db.Model):
    """Raw transaction staging model"""
    __tablename__ = 'STG_RAW_TRANSACTIONS'
    
    id = db.Column(db.Integer, primary_key=True)
    import_batch_id = db.Column(db.String(50), nullable=False)
    portfolio_id = db.Column(db.Integer, nullable=False)
    raw_date = db.Column(db.Text, nullable=False)
    raw_instrument_code = db.Column(db.Text, nullable=False)
    raw_transaction_type = db.Column(db.Text, nullable=False)
    raw_quantity = db.Column(db.Text, nullable=False)
    raw_price = db.Column(db.Text, nullable=False)
    raw_total_value = db.Column(db.Text)
    raw_currency = db.Column(db.Text)
    import_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    processed_flag = db.Column(db.Boolean, default=False)
    validation_errors = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<RawTransaction {self.id}: {self.raw_instrument_code}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'import_batch_id': self.import_batch_id,
            'portfolio_id': self.portfolio_id,
            'raw_date': self.raw_date,
            'raw_instrument_code': self.raw_instrument_code,
            'raw_transaction_type': self.raw_transaction_type,
            'raw_quantity': self.raw_quantity,
            'raw_price': self.raw_price,
            'raw_total_value': self.raw_total_value,
            'raw_currency': self.raw_currency,
            'import_timestamp': self.import_timestamp.isoformat() if self.import_timestamp else None,
            'processed_flag': self.processed_flag,
            'validation_errors': self.validation_errors,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @staticmethod
    def create_batch(batch_id: str, portfolio_id: int, raw_data: list):
        """Create a batch of raw transactions"""
        transactions = []
        for row in raw_data:
            transaction = RawTransaction(
                import_batch_id=batch_id,
                portfolio_id=portfolio_id,
                raw_date=str(row.get('date', '')),
                raw_instrument_code=str(row.get('instrument_code', '')),
                raw_transaction_type=str(row.get('transaction_type', '')),
                raw_quantity=str(row.get('quantity', '')),
                raw_price=str(row.get('price', '')),
                raw_total_value=str(row.get('total_value', '')),
                raw_currency=str(row.get('currency', ''))
            )
            transactions.append(transaction)
            db.session.add(transaction)
        
        db.session.commit()
        return transactions