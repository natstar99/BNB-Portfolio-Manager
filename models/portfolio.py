# File: models/portfolio.py

from typing import Dict
from .stock import Stock

class Portfolio:
    def __init__(self, id: int, name: str, db_manager):
        self.id = id
        self.name = name
        self.db_manager = db_manager
        self.stocks: Dict[str, Stock] = {}

    def load_stocks(self):
        """Load all stocks in the portfolio with their current data."""
        stocks_data = self.db_manager.get_stocks_for_portfolio(self.id)
        for stock_data in stocks_data:
            stock = Stock(
                id=stock_data[0],
                yahoo_symbol=stock_data[1],
                instrument_code=stock_data[2],
                name=stock_data[3],
                current_price=stock_data[4],
                last_updated=stock_data[5],
                db_manager=self.db_manager
            )
            self.stocks[stock.yahoo_symbol] = stock

    def add_stock(self, stock: Stock):
        self.db_manager.add_stock_to_portfolio(self.id, stock.id)
        self.stocks[stock.yahoo_symbol] = stock

    def remove_stock(self, yahoo_symbol: str):
        if yahoo_symbol in self.stocks:
            stock = self.stocks[yahoo_symbol]
            self.db_manager.remove_stock_from_portfolio(self.id, stock.id)
            del self.stocks[yahoo_symbol]

    def get_stock(self, yahoo_symbol: str) -> Stock:
        return self.stocks.get(yahoo_symbol)

    def update_prices(self):
        for stock in self.stocks.values():
            stock.update_price()

    def calculate_total_value(self) -> float:
        return sum(stock.calculate_market_value() for stock in self.stocks.values())

    def calculate_total_profit_loss(self) -> float:
        return sum(stock.calculate_profit_loss() for stock in self.stocks.values())

    @classmethod
    def create(cls, name: str, db_manager):
        portfolio_id = db_manager.create_portfolio(name)
        return cls(id=portfolio_id, name=name, db_manager=db_manager)

    @classmethod
    def get_all(cls, db_manager):
        portfolios_data = db_manager.get_all_portfolios()
        return [cls(id=data[0], name=data[1], db_manager=db_manager) for data in portfolios_data]

    @classmethod
    def get_by_id(cls, portfolio_id: int, db_manager):
        portfolio_data = db_manager.get_portfolio(portfolio_id)
        if portfolio_data:
            return cls(id=portfolio_data[0], name=portfolio_data[1], db_manager=db_manager)
        return None