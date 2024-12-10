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
        """Load all transactions for this stock from the database."""
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

    def calculate_total_shares(self) -> float:
        """Calculate the current total number of shares held."""
        return sum(t.quantity if t.transaction_type == 'BUY' else -t.quantity 
                  for t in self.transactions)

    def calculate_cost_basis(self) -> float:
        """
        Calculate the total cost basis of current holdings.
        This represents the total amount spent on purchases, adjusted for sales.
        """
        total_cost = 0
        remaining_shares = 0
        
        # Sort transactions by date to process them chronologically
        sorted_transactions = sorted(self.transactions, key=lambda x: x.date)
        
        for transaction in sorted_transactions:
            if transaction.transaction_type == 'BUY':
                total_cost += transaction.quantity * transaction.price
                remaining_shares += transaction.quantity
            elif transaction.transaction_type == 'SELL':
                # Calculate the proportion of cost basis to remove
                if remaining_shares > 0:
                    cost_per_share = total_cost / remaining_shares
                    total_cost -= transaction.quantity * cost_per_share
                    remaining_shares -= transaction.quantity
        
        return total_cost

    def calculate_average_cost(self) -> float:
        """
        Calculate the average cost per share of current holdings.
        Returns 0 if no shares are held.
        """
        total_shares = self.calculate_total_shares()
        if total_shares > 0:
            return self.calculate_cost_basis() / total_shares
        return 0

    def calculate_market_value(self) -> float:
        """Calculate the current market value of holdings."""
        return self.calculate_total_shares() * self.current_price

    def calculate_realised_pl(self) -> float:
        """
        Calculate realised profit/loss from completed sales.
        Uses FIFO (First In, First Out) method for calculating cost basis of sold shares.
        """
        realised_pl = 0
        buy_queue = []  # [(quantity, price)]
        
        # Sort transactions by date
        sorted_transactions = sorted(self.transactions, key=lambda x: x.date)
        
        for transaction in sorted_transactions:
            if transaction.transaction_type == 'BUY':
                buy_queue.append((transaction.quantity, transaction.price))
            elif transaction.transaction_type == 'SELL':
                remaining_to_sell = transaction.quantity
                while remaining_to_sell > 0 and buy_queue:
                    buy_quantity, buy_price = buy_queue[0]
                    
                    # Calculate how many shares we can sell from this buy lot
                    shares_sold = min(remaining_to_sell, buy_quantity)
                    
                    # Calculate P/L for this portion
                    pl = shares_sold * (transaction.price - buy_price)
                    realised_pl += pl
                    
                    # Update the buy queue
                    if shares_sold == buy_quantity:
                        buy_queue.pop(0)
                    else:
                        buy_queue[0] = (buy_quantity - shares_sold, buy_price)
                    
                    remaining_to_sell -= shares_sold
        
        return realised_pl

    def calculate_unrealised_pl(self) -> float:
        """Calculate unrealised profit/loss based on current market price."""
        return self.calculate_market_value() - self.calculate_cost_basis()

    def calculate_total_pl(self) -> float:
        """Calculate total profit/loss (realised + unrealised)."""
        return self.calculate_realised_pl() + self.calculate_unrealised_pl()

    def calculate_percentage_change(self) -> float:
        """
        Calculate the total percentage change including realised and unrealised P/L.
        Returns 0 if there's no cost basis to avoid division by zero.
        """
        cost_basis = self.calculate_cost_basis()
        if cost_basis > 0:
            total_pl = self.calculate_total_pl()
            return (total_pl / cost_basis) * 100
        return 0

    def update_price(self):
        """Update the current price in the database."""
        self.last_updated = datetime.now().replace(microsecond=0)
        self.db_manager.update_stock_price(self.yahoo_symbol, self.current_price)

    def add_transaction(self, transaction: Transaction):
        """Add a new transaction to this stock."""
        self.db_manager.add_transaction(
            stock_id=self.id,
            date=transaction.date,
            quantity=transaction.quantity,
            price=transaction.price,
            transaction_type=transaction.transaction_type
        )
        self.transactions.append(transaction)

    @classmethod
    def create(cls, yahoo_symbol: str, instrument_code: str, name: str, current_price: float, db_manager):
        """Create a new stock instance."""
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
        """Get a stock instance by its Yahoo symbol."""
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