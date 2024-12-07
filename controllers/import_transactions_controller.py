# File: controllers/import_transactions_controller.py

import pandas as pd
import os
import shutil
import logging
from datetime import datetime
import yfinance as yf
from PySide6.QtWidgets import QFileDialog, QMessageBox
from PySide6.QtCore import QObject, Signal
from models.transaction import Transaction
from models.stock import Stock
from views.import_transactions_view import ImportTransactionsView
from views.verify_transactions_view import VerifyTransactionsDialog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImportTransactionsController(QObject):
    import_completed = Signal()

    def __init__(self, portfolio, db_manager):
        super().__init__()
        self.portfolio = portfolio
        self.db_manager = db_manager
        self.view = ImportTransactionsView()
        self.market_mappings = {}

        self.view.import_transactions.connect(self.import_transactions)
        self.view.get_template.connect(self.provide_template)

    def collect_historical_data(self, stock_id, yahoo_symbol, force_refresh=False):
        """
        Collect historical data for a stock.
        
        Args:
            stock_id (int): The database ID of the stock
            yahoo_symbol (str): The Yahoo Finance symbol for the stock
            force_refresh (bool): If True, re-fetch all data. If False, only fetch new data.
        """
        try:
            logger.info(f"Starting historical data collection for {yahoo_symbol}")
            
            if force_refresh:
                # Get earliest transaction date for full refresh
                earliest_transaction = self.db_manager.fetch_one(
                    "SELECT MIN(date) FROM transactions WHERE stock_id = ?", 
                    (stock_id,)
                )
                start_date = pd.to_datetime(earliest_transaction[0])
                logger.info(f"Forcing full refresh from {start_date}")
            else:
                # Get latest historical date if any
                latest_date = self.db_manager.fetch_one(
                    "SELECT MAX(date) FROM historical_prices WHERE stock_id = ?", 
                    (stock_id,)
                )

                if latest_date and latest_date[0]:
                    # We have some data - get start date for new data collection
                    start_date = pd.to_datetime(latest_date[0]) + pd.Timedelta(days=1)
                    logger.info(f"Found existing data, collecting from {start_date}")
                else:
                    # No data - get earliest transaction date
                    earliest_transaction = self.db_manager.fetch_one(
                        "SELECT MIN(date) FROM transactions WHERE stock_id = ?", 
                        (stock_id,)
                    )
                    start_date = pd.to_datetime(earliest_transaction[0])
                    logger.info(f"No existing data, collecting from {start_date}")

            # Only collect if we need new data
            if start_date < pd.Timestamp.today():
                ticker = yf.Ticker(yahoo_symbol)
                
                if force_refresh:
                    # Clear existing data first if doing a full refresh
                    self.db_manager.execute(
                        "DELETE FROM historical_prices WHERE stock_id = ?",
                        (stock_id,)
                    )
                    self.db_manager.conn.commit()
                
                # Get historical data
                history = ticker.history(
                    start=start_date,
                    end=pd.Timestamp.today(),
                    interval='1d'
                )

                if not history.empty:
                    logger.info(f"Retrieved {len(history)} new data points")
                    
                    # Prepare bulk insert data
                    historical_prices = []
                    for index, row in history.iterrows():
                        historical_prices.append((
                            stock_id,
                            index.strftime('%Y-%m-%d'),
                            row['Open'],
                            row['High'],
                            row['Low'],
                            row['Close'],
                            row['Volume'],
                            row['Close'],  # adjusted_close
                            row['Close'],  # original_close
                            False,         # split_adjusted
                            0.0           # dividend
                        ))
                    
                    # Insert new historical data
                    self.db_manager.bulk_insert_historical_prices(historical_prices)
                    logger.info(f"Successfully stored historical data")
                else:
                    logger.warning(f"No new historical data found")
            else:
                logger.info("Historical data is up to date")

        except Exception as e:
            logger.error(f"Failed to collect historical data: {str(e)}")
            raise

    def import_transactions(self, file_name, column_mapping):
        """
        Import transactions from a file and collect historical data.
        
        Args:
            file_name (str): Path to the import file
            column_mapping (dict): Mapping of file columns to database columns
        """
        try:
            logger.info(f"Starting import from file: {file_name}")
            # Read the file
            if file_name.endswith('.xlsx'):
                df = pd.read_excel(file_name, parse_dates=['Trade Date'])
            elif file_name.endswith('.csv'):
                df = pd.read_csv(file_name, parse_dates=['Trade Date'])
            else:
                raise ValueError("Unsupported file format")

            if column_mapping:
                df = df.rename(columns=column_mapping)

            # Convert 'Trade Date' to date only (no time information)
            df['Trade Date'] = df['Trade Date'].dt.date

            # Show verification dialog
            dialog = VerifyTransactionsDialog(df, self.db_manager, self.view)
            dialog.verification_completed.connect(self.on_verification_completed)
            
            if dialog.exec_():
                logger.info("Transaction verification completed successfully")
            else:
                logger.info("Transaction verification cancelled by user")
                return

        except Exception as e:
            error_msg = f"Failed to import transactions: {str(e)}"
            logger.error(error_msg)
            QMessageBox.warning(self.view, "Import Failed", error_msg)

    def on_verification_completed(self, verification_results):
        """
        Process verified transactions and collect historical data only for verified stocks.
        Uses verification status from the verification dialog.
        """
        try:
            self.market_mappings = verification_results['market_mappings']
            stock_data = verification_results['stock_data']
            drp_settings = verification_results.get('drp_settings', {})
            df = verification_results['transactions_df']
            verification_status = verification_results['verification_status']

            processed_stocks = set()
            for instrument_code, group in df.groupby('Instrument Code'):
                # Get market suffix and create yahoo symbol
                market_suffix = self.market_mappings.get(instrument_code, '')
                yahoo_symbol = f"{instrument_code}{market_suffix}" if market_suffix else instrument_code

                # Only process verified stocks
                row_index = df[df['Instrument Code'] == instrument_code].index[0]
                if verification_status.get(row_index) == "Verified":
                    # Create or get stock
                    stock = Stock.get_by_yahoo_symbol(yahoo_symbol, self.db_manager)
                    if not stock:
                        stock_info = stock_data.get(instrument_code, {})
                        stock = Stock.create(
                            yahoo_symbol=yahoo_symbol,
                            instrument_code=instrument_code,
                            name=stock_info.get('name', ''),
                            current_price=stock_info.get('price', 0.0),
                            db_manager=self.db_manager
                        )
                        self.portfolio.add_stock(stock)

                    # Update DRP setting
                    drp_status = drp_settings.get(instrument_code, False)
                    self.db_manager.update_stock_drp(stock.id, drp_status)

                    # Bulk insert transactions
                    transactions = [
                        (stock.id, row['Trade Date'], row['Quantity'], row['Price'],
                        row['Transaction Type'], row['Quantity'], row['Price'])
                        for _, row in group.iterrows()
                    ]
                    self.db_manager.bulk_insert_transactions(transactions)
                    
                    # Collect historical data
                    if stock.id not in processed_stocks:
                        self.collect_historical_data(stock.id, yahoo_symbol)
                        processed_stocks.add(stock.id)

            QMessageBox.information(
                self.view,
                "Import Successful", 
                "Transactions and historical data have been imported for verified stocks."
            )
            self.import_completed.emit()

        except Exception as e:
            error_msg = f"Failed to process verified transactions: {str(e)}"
            logger.error(error_msg)
            QMessageBox.warning(self.view, "Import Failed", error_msg)


    def provide_template(self):
        """Provide a template file for transaction import."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(current_dir, "..", "Transaction_Data_Template.xlsx")
        
        if not os.path.exists(template_path):
            QMessageBox.warning(self.view, "Template Not Found", 
                              "The template file is missing from the application directory.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self.view,
            "Save Template",
            "Transaction_Data_Template.xlsx",
            "Excel Files (*.xlsx)"
        )
        if save_path:
            shutil.copy2(template_path, save_path)
            QMessageBox.information(self.view, "Template Saved", 
                                  f"Template has been saved to {save_path}")

    def show_view(self):
        """Show the import transactions view."""
        self.view.show()