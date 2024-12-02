# File: models/stock.py

from datetime import datetime
from typing import List
from .transaction import Transaction

class Stock:
    def __init__(self, id: int, yahoo_symbol: str, instrument_code: str, name: str, current_price: float, last_updated: datetime, db_manager):
        self.id = id
        self.yahoo_symbol = yahoo_symbol
        self.instrument_code = instrument_code
        self.name = name
        self.current_price = current_price
        self.last_updated = last_updated
        self.db_manager = db_manager
        self.transactions: List[Transaction] = []

    def load_transactions(self):
        transactions_data = self.db_manager.get_transactions_for_stock(self.id)
        self.transactions = [
            Transaction(
                id=t[0],
                date=self.parse_date(t[1]),
                quantity=t[2],
                price=t[3],
                transaction_type=t[4],
                db_manager=self.db_manager
            ) for t in transactions_data
        ]

    @staticmethod
    def parse_date(date_string: str) -> datetime:
        try:
            return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                return datetime.strptime(date_string, '%Y-%m-%d')
            except ValueError:
                raise ValueError(f"Unable to parse date string: {date_string}")

    def add_transaction(self, transaction: Transaction):
        self.db_manager.add_transaction(
            stock_id=self.id,
            date=transaction.date,
            quantity=transaction.quantity,
            price=transaction.price,
            transaction_type=transaction.transaction_type
        )
        self.transactions.append(transaction)
        
    def update_price(self):
        self.last_updated = datetime.now().replace(microsecond=0)
        self.db_manager.update_stock_price(self.yahoo_symbol, self.current_price)

    def calculate_average_cost(self) -> float:
        total_cost = 0
        total_shares = 0
        for transaction in self.transactions:
            if transaction.transaction_type == 'BUY':
                total_cost += transaction.quantity * transaction.price
                total_shares += transaction.quantity
            elif transaction.transaction_type == 'SELL':
                total_shares -= transaction.quantity
        return total_cost / total_shares if total_shares > 0 else 0

    def calculate_total_shares(self) -> float:
        return sum(t.quantity if t.transaction_type == 'BUY' else -t.quantity for t in self.transactions)

    def calculate_market_value(self) -> float:
        return self.calculate_total_shares() * self.current_price

    def calculate_profit_loss(self) -> float:
        return self.calculate_market_value() - sum(t.quantity * t.price for t in self.transactions if t.transaction_type == 'BUY')

    @classmethod
    def create(cls, yahoo_symbol: str, instrument_code: str, name: str, current_price: float, db_manager):
        # First check if stock exists and get its market data
        existing_stock = db_manager.get_stock_by_instrument_code(instrument_code)
        market_or_index = None
        if existing_stock:
            _, _, _, _, _, _, market_or_index, _, market_suffix = existing_stock

        # Create or update the stock, preserving market data
        stock_id = db_manager.add_stock(
            yahoo_symbol=yahoo_symbol,
            instrument_code=instrument_code,
            name=name,
            current_price=current_price,
            market_or_index=market_or_index
        )
        
        return cls(
            id=stock_id,
            yahoo_symbol=yahoo_symbol,
            instrument_code=instrument_code,
            name=name,
            current_price=current_price,
            last_updated=datetime.now().replace(microsecond=0),
            db_manager=db_manager
        )

    @classmethod
    def get_by_yahoo_symbol(cls, yahoo_symbol: str, db_manager):
        stock_data = db_manager.get_stock(yahoo_symbol)
        if stock_data:
            return cls(
                id=stock_data[0],
                yahoo_symbol=stock_data[1],
                instrument_code=stock_data[2],
                name=stock_data[3],
                current_price=stock_data[4],
                last_updated=cls.parse_date(stock_data[5]),
                db_manager=db_manager
            )
        return None