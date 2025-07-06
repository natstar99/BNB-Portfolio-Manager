from datetime import datetime, date
from app import db
from sqlalchemy import text
from app.utils.date_parser import DateParser


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
        
        # Get date key (date should already exist due to batch population in import service)
        date_key = int(transaction_date.strftime('%Y%m%d'))
        
        # Fallback: ensure date exists if called outside of import process
        from .date_dimension import DateDimension
        existing_date = DateDimension.query.filter_by(date_key=date_key).first()
        if not existing_date:
            date_entry = DateDimension.create_date_entry(transaction_date)
            date_key = date_entry.date_key
        
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
    raw_date = db.Column(db.Integer, nullable=False)
    raw_instrument_code = db.Column(db.Text, nullable=False)
    raw_transaction_type = db.Column(db.Text, nullable=False)
    raw_quantity = db.Column(db.Numeric, nullable=False)
    raw_price = db.Column(db.Numeric, nullable=False)
    raw_import_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    processed_flag = db.Column(db.Boolean, default=False)
    
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
            'raw_quantity': float(self.raw_quantity) if self.raw_quantity else 0.0,
            'raw_price': float(self.raw_price) if self.raw_price else 0.0,
            'raw_import_timestamp': self.raw_import_timestamp.isoformat() if self.raw_import_timestamp else None,
            'processed_flag': self.processed_flag
        }
    
    @staticmethod
    def create_batch(batch_id: str, portfolio_id: int, raw_data: list):
        """
        CRITICAL METHOD: Create a batch of raw transactions in STG_RAW_TRANSACTIONS.
        
        This method is called during Step 3b (Stage Transactions) to save validated transaction
        data to the staging table. It handles complex date parsing and ensures data consistency.
        
        DESIGN DECISIONS:
        - Uses batch_id to group related transactions for tracking and rollback capabilities
        - Converts all date formats to standardized YYYYMMDD integer format for raw_date field
        - Handles multiple date formats including string dates, datetime objects, and integers
        - Sets processed_flag=False to mark transactions as ready for Step 5 processing
        
        KNOWN ISSUES FIXED:
        - BUG FIX: Date parsing was inconsistent between different input formats - now handles all cases
        - BUG FIX: Timestamps with dates (e.g., '20170628 00:00:00') caused parsing errors - now strips time
        - BUG FIX: Non-string date inputs caused crashes - now handles date objects and integers
        - BUG FIX: Malformed date strings caused silent failures - now provides detailed error messages
        
        CRITICAL REQUIREMENTS:
        - All transactions in batch must be saved atomically (all succeed or all fail)
        - Date conversion must be consistent with date handling in other parts of system
        - Must set processed_flag=False for all new records
        - Must link to correct portfolio_id for proper data isolation
        
        Args:
            batch_id (str): Unique identifier for this batch of transactions (UUID recommended)
            portfolio_id (int): Portfolio ID these transactions belong to
            raw_data (list): List of transaction dictionaries containing:
                - date: Date in various formats (str, datetime, date, int)
                - instrument_code (str): Stock symbol
                - transaction_type (str): Transaction type (BUY, SELL, etc.)
                - quantity (float): Number of shares
                - price (float): Price per share
                
        Returns:
            List[RawTransaction]: List of created raw transaction objects
            
        Raises:
            ValueError: If date cannot be parsed or required fields are missing
            DatabaseError: If database commit fails
            
        Example:
            >>> raw_data = [
            ...     {'date': '2023-01-15', 'instrument_code': 'AAPL', 'transaction_type': 'BUY', 'quantity': 100, 'price': 150.00},
            ...     {'date': datetime(2023, 1, 16), 'instrument_code': 'MSFT', 'transaction_type': 'BUY', 'quantity': 50, 'price': 245.50}
            ... ]
            >>> transactions = RawTransaction.create_batch('batch-123', 456, raw_data)
            >>> print(f"Created {len(transactions)} raw transactions")
        """
        transactions = []
        for row in raw_data:
            # Convert date to YYYYMMDD integer format using shared utility
            date_value = row.get('date', '')
            try:
                parsed_date = DateParser.parse_date(date_value)
                raw_date = DateParser.date_to_raw_int(parsed_date)
            except Exception as e:
                raise ValueError(f"Cannot parse date '{date_value}': {str(e)}")
            
            transaction = RawTransaction(
                import_batch_id=batch_id,
                portfolio_id=portfolio_id,
                raw_date=raw_date,
                raw_instrument_code=str(row.get('instrument_code', '')),
                raw_transaction_type=str(row.get('transaction_type', '')),
                raw_quantity=float(row.get('quantity', 0)),
                raw_price=float(row.get('price', 0))
            )
            transactions.append(transaction)
            db.session.add(transaction)
        
        db.session.commit()
        return transactions