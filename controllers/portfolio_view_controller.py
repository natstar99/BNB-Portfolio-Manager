# File: controllers/portfolio_view_controller.py

from PySide6.QtWidgets import QInputDialog, QMessageBox
from views.my_portfolio_view import MyPortfolioView
from models.portfolio import Portfolio
from models.stock import Stock
from models.transaction import Transaction
from datetime import datetime, timedelta
import yfinance as yf
import logging
import pandas as pd
from views.verify_transactions_view import VerifyTransactionsDialog
from views.historical_data_view import HistoricalDataDialog

logger = logging.getLogger(__name__)

class PortfolioViewController:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.view = MyPortfolioView()
        self.current_portfolio = None
        
        # Connect signals
        self.view.view_history.connect(self.show_history)
        self.view.add_stock.connect(self.add_stock)
        self.view.remove_stock.connect(self.remove_stock)
        self.view.refresh_data.connect(self.refresh_data)
        self.view.manage_portfolio.connect(self.show_portfolio_manager)

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

    def show_portfolio_manager(self):
        if not self.current_portfolio:
            return
            
        # Create dataframe of current holdings for the verification dialog
        holdings_data = []
        for stock in self.current_portfolio.stocks.values():
            holdings_data.append({
                'Instrument Code': stock.instrument_code,
                'Trade Date': datetime.now().date(),  # Current date as reference
                'Quantity': stock.calculate_total_shares(),
                'Price': stock.current_price,
                'Transaction Type': 'HOLD'  # New type to indicate existing holding
            })
            
        if holdings_data:
            df = pd.DataFrame(holdings_data)
            dialog = VerifyTransactionsDialog(df, self.db_manager, self.view)
            dialog.verification_completed.connect(self.on_verification_completed)
            dialog.exec_()

    def on_verification_completed(self, verification_results):
        """Handle the results of stock verification"""
        try:
            # Update market mappings and stock data
            for instrument_code, market_suffix in verification_results['market_mappings'].items():
                # Update the database
                self.db_manager.update_stock_market(instrument_code, market_suffix)
                
                # If we have additional stock data, update it
                if instrument_code in verification_results['stock_data']:
                    stock_info = verification_results['stock_data'][instrument_code]
                    
                    # Get the stock from portfolio
                    yahoo_symbol = f"{instrument_code}{market_suffix}" if market_suffix else instrument_code
                    stock = self.current_portfolio.get_stock(yahoo_symbol)
                    
                    if stock:
                        # Update stock information in both object and database
                        stock.name = stock_info.get('name', stock.name)
                        stock.current_price = stock_info.get('price', stock.current_price)
                        
                        # Update the database with all stock information
                        self.db_manager.execute("""
                            UPDATE stocks 
                            SET name = ?,
                                current_price = ?,
                                last_updated = ?,
                                yahoo_symbol = ?
                            WHERE id = ?
                        """, (
                            stock_info.get('name'),
                            stock_info.get('price'),
                            datetime.now().replace(microsecond=0),
                            yahoo_symbol,
                            stock.id
                        ))
                        
                        # Handle splits if any
                        if 'splits' in stock_info:
                            splits = stock_info['splits']
                            split_data = [
                                (stock.id, date.strftime('%Y-%m-%d'), ratio, 'yahoo', datetime.now())
                                for date, ratio in splits.items()
                            ]
                            self.db_manager.bulk_insert_stock_splits(split_data)
            
            # Commit the database changes
            self.db_manager.conn.commit()
            
            # Reload the portfolio data to ensure we have fresh data
            self.current_portfolio.load_stocks()
            
            # Refresh the view
            self.refresh_data()
                
        except Exception as e:
            QMessageBox.warning(
                self.view,
                "Update Failed",
                f"Failed to update portfolio data: {str(e)}"
            )

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