# File: models/transaction.py

from datetime import datetime

class Transaction:
    def __init__(self, id: int, date: datetime, quantity: float, price: float, transaction_type: str, db_manager):
        self.id = id
        self.date = date
        self.quantity = quantity
        self.price = price
        self.transaction_type = transaction_type
        self.db_manager = db_manager

    @classmethod
    def create(cls, stock_id: int, date: datetime, quantity: float, price: float, transaction_type: str, db_manager):
        transaction_id = db_manager.add_transaction(stock_id, date, quantity, price, transaction_type)
        return cls(
            id=transaction_id,
            date=date,
            quantity=quantity,
            price=price,
            transaction_type=transaction_type,
            db_manager=db_manager
        )