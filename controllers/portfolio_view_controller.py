# File: controllers/portfolio_view_controller.py

from PySide6.QtWidgets import QInputDialog, QMessageBox
from views.my_portfolio_view import MyPortfolioView
from models.portfolio import Portfolio
from models.stock import Stock
from models.transaction import Transaction
from datetime import datetime, timedelta
import yfinance as yf
import logging
from views.historical_data_view import HistoricalDataDialog

logger = logging.getLogger(__name__)

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

        # Ask if user wants to update historical data
        response = QMessageBox.question(
            self.view,
            "Update Historical Data",
            "Would you like to update historical price data for all stocks?\n"
            "This process might take several minutes.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        collect_history = response == QMessageBox.Yes

        for stock in self.current_portfolio.stocks.values():
            try:
                # Update current price
                ticker = yf.Ticker(stock.yahoo_symbol)
                info = ticker.info
                stock.current_price = info.get('currentPrice', stock.current_price)
                stock.update_price()

                if collect_history:
                    logger.info(f"Collecting historical data for {stock.yahoo_symbol}")
                    
                    # Get data for the last year or since the earliest transaction
                    earliest_transaction = min(t.date for t in stock.transactions) if stock.transactions else None
                    start_date = earliest_transaction if earliest_transaction else (datetime.now() - timedelta(days=365))
                    end_date = datetime.now()
                    
                    history = ticker.history(
                        start=start_date,
                        end=end_date,
                        interval='1d'
                    )
                    
                    if not history.empty:
                        logger.info(f"Retrieved {len(history)} data points for {stock.yahoo_symbol}")
                        
                        # Prepare bulk insert data
                        historical_prices = [
                            (
                                stock.id,
                                index.strftime('%Y-%m-%d'),
                                row_data['Open'],
                                row_data['High'],
                                row_data['Low'],
                                row_data['Close'],
                                row_data['Volume'],
                                row_data['Close'],  # adjusted_close
                                row_data['Close'],  # original_close
                                False               # split_adjusted
                            )
                            for index, row_data in history.iterrows()
                        ]
                        
                        # Clear existing historical data for this stock
                        self.db_manager.execute(
                            "DELETE FROM historical_prices WHERE stock_id = ? AND date >= ?",
                            (stock.id, start_date.strftime('%Y-%m-%d'))
                        )
                        
                        # Insert new historical data
                        self.db_manager.bulk_insert_historical_prices(historical_prices)
                        logger.info(f"Successfully updated historical data for {stock.yahoo_symbol}")
                    else:
                        logger.warning(f"No historical data found for {stock.yahoo_symbol}")
                        
            except Exception as e:
                logger.error(f"Failed to update data for {stock.yahoo_symbol}: {str(e)}")
                QMessageBox.warning(
                    self.view,
                    "Update Failed",
                    f"Failed to update data for {stock.yahoo_symbol}: {str(e)}"
                )

        self.update_view()
        
        if collect_history:
            QMessageBox.information(
                self.view,
                "Update Complete",
                "Portfolio data and historical prices have been updated."
            )
        else:
            QMessageBox.information(
                self.view,
                "Update Complete",
                "Portfolio data has been updated."
            )

    def get_view(self):
        return self.view