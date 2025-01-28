# File: controllers/portfolio_controller.py

from typing import List
from models.portfolio import Portfolio
from views.manage_portfolios_view import ManagePortfoliosView
from controllers.import_transactions_controller import ImportTransactionsController
from PySide6.QtCore import QObject, Signal

class PortfolioController(QObject):
    portfolio_selected = Signal(object)

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.portfolios: List[Portfolio] = []
        self.view = ManagePortfoliosView()
        self.import_controller = None

        # Connect view signals to controller methods
        self.view.create_portfolio.connect(self.create_portfolio)
        self.view.select_portfolio.connect(self.select_portfolio)
        self.view.delete_portfolio.connect(self.delete_portfolio)
        self.view.import_transactions.connect(self.import_transactions)

    def load_portfolios(self):
        """Load all portfolios from the database."""
        self.portfolios = Portfolio.get_all(self.db_manager)
        self.update_view()

    def create_portfolio(self, name: str):
        """Create a new portfolio in the database."""
        new_portfolio = Portfolio.create(name, self.db_manager)
        self.portfolios.append(new_portfolio)
        self.update_view()
        return new_portfolio

    def select_portfolio(self, portfolio_name, import_transactions=False):
        portfolio = self.get_portfolio_by_name(portfolio_name)
        if portfolio:
            self.current_portfolio = portfolio
            self.portfolio_selected.emit(portfolio)
            if import_transactions:
                self.import_transactions(portfolio_name)
        else:
            raise ValueError(f"No portfolio found with name '{portfolio_name}'")

    def delete_portfolio(self, name: str):
        portfolio_to_delete = next((p for p in self.portfolios if p.name == name), None)
        if portfolio_to_delete:
            self.db_manager.delete_portfolio(portfolio_to_delete.id)
            self.portfolios = [p for p in self.portfolios if p.name != name]
            self.update_view()

    def import_transactions(self, portfolio_name: str):
        portfolio = next((p for p in self.portfolios if p.name == portfolio_name), None)
        if portfolio:
            self.import_controller = ImportTransactionsController(portfolio, self.db_manager)
            self.import_controller.import_completed.connect(self.on_import_completed)
            self.import_controller.show_view()
            return self.import_controller
        else:
            print(f"Portfolio '{portfolio_name}' not found")
            return None

    def on_import_completed(self):
        self.load_portfolios()

    def update_view(self):
        self.view.update_portfolios(self.portfolios)

    def get_view(self):
        return self.view
    
    def get_portfolio_by_name(self, name: str) -> Portfolio:
        return next((p for p in self.portfolios if p.name == name), None)