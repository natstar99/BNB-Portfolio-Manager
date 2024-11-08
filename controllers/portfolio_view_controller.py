# File: controllers/portfolio_view_controller.py

from PySide6.QtWidgets import QInputDialog, QMessageBox
from views.my_portfolio_view import MyPortfolioView
from models.portfolio import Portfolio
from models.stock import Stock
from models.transaction import Transaction
from datetime import datetime
import yfinance as yf
from views.historical_data_view import HistoricalDataDialog

class PortfolioViewController:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.view = MyPortfolioView()
        self.current_portfolio = None
        self.view.view_history.connect(self.show_history)

        # Connect view signals to controller methods
        self.view.add_stock.connect(self.add_stock)
        self.view.remove_stock.connect(self.remove_stock)
        self.view.refresh_data.connect(self.refresh_data)

    def set_portfolio(self, portfolio: Portfolio):
        self.current_portfolio = portfolio
        self.current_portfolio.load_stocks()
        self.refresh_data()

    def update_view(self):
        if self.current_portfolio:
            self.view.update_portfolio(self.current_portfolio)

    def show_history(self, yahoo_symbol):
        if self.current_portfolio:
            stock = self.current_portfolio.get_stock(yahoo_symbol)
            if stock:
                dialog = HistoricalDataDialog(stock, self.db_manager, self.view)
                dialog.exec_()

    def add_stock(self):
        if not self.current_portfolio:
            return

        instrument_code, ok = QInputDialog.getText(self.view, "Add Stock", "Enter stock symbol:")
        if ok and instrument_code:
            quantity, ok = QInputDialog.getInt(self.view, "Add Stock", f"Enter quantity for {instrument_code}:", min=1)
            if ok:
                try:
                    # Fetch basic stock info
                    ticker = yf.Ticker(instrument_code)
                    info = ticker.info
                    yahoo_symbol = info['symbol']
                    stock_name = info.get('longName', instrument_code)
                    current_price = info.get('currentPrice', 0.0)

                    # Create new stock and add to portfolio
                    new_stock = Stock.create(yahoo_symbol, instrument_code, stock_name, current_price, self.db_manager)
                    self.current_portfolio.add_stock(new_stock)
                    
                    # Add transaction
                    Transaction.create(new_stock.id, datetime.now(), quantity, current_price, "BUY", self.db_manager)
                    
                    self.update_view()
                except Exception as e:
                    QMessageBox.warning(self.view, "Error", f"Failed to add stock: {str(e)}")

    def remove_stock(self, yahoo_symbol: str):
        if not self.current_portfolio:
            return

        confirm = QMessageBox.question(self.view, "Confirm Removal",
                                       f"Are you sure you want to remove {yahoo_symbol} from the portfolio?",
                                       QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            self.current_portfolio.remove_stock(yahoo_symbol)
            self.update_view()

    def refresh_data(self):
        if not self.current_portfolio:
            return

        for stock in self.current_portfolio.stocks.values():
            try:
                # In a real application, you would fetch the current price from an API
                # For now, we'll just update the last_updated timestamp
                stock.update_price()
            except Exception as e:
                print(f"Failed to update price for {stock.yahoo_symbol}: {str(e)}")
        self.update_view()

    def get_view(self):
        return self.view