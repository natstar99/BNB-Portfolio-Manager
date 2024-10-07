# File: controllers/portfolio_controller.py

from typing import List
from models.portfolio import Portfolio
from views.manage_portfolios_view import ManagePortfoliosView
from controllers.import_transactions_controller import ImportTransactionsController

class PortfolioController:
    def __init__(self, db_manager):
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
        self.portfolios = Portfolio.get_all(self.db_manager)
        self.update_view()

    def create_portfolio(self, name: str):
        new_portfolio = Portfolio.create(name, self.db_manager)
        self.portfolios.append(new_portfolio)
        self.update_view()

    def select_portfolio(self, name: str):
        selected_portfolio = next((p for p in self.portfolios if p.name == name), None)
        if selected_portfolio:
            # Here you would typically switch to a detailed view of the selected portfolio
            print(f"Selected portfolio: {selected_portfolio.name}")
            # You might emit a signal here to tell the main window to switch views
        else:
            print(f"Portfolio '{name}' not found")

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
        else:
            print(f"Portfolio '{portfolio_name}' not found")

    def on_import_completed(self):
        # This method will be called when the import is completed
        self.load_portfolios()  # Reload all portfolios to reflect changes
        # You might want to emit a signal here to update other views

    def update_view(self):
        self.view.update_portfolios(self.portfolios)

    def get_view(self):
        return self.view
    
    def get_portfolio_by_name(self, name: str) -> Portfolio:
        return next((p for p in self.portfolios if p.name == name), None)