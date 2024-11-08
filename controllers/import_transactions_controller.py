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

logging.basicConfig(level=logging.DEBUG, filename='import_transactions.log', filemode='w',
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ImportTransactionsController(QObject):
    import_completed = Signal()

    def __init__(self, portfolio, db_manager):
        super().__init__()
        self.portfolio = portfolio
        self.db_manager = db_manager
        self.view = ImportTransactionsView()

        self.view.import_transactions.connect(self.import_transactions)
        self.view.get_template.connect(self.provide_template)

    def import_transactions(self, file_name, column_mapping):
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
            logger.exception(error_msg)
            QMessageBox.warning(self.view, "Import Failed", error_msg)

    def on_verification_completed(self, verification_results):
        try:
            market_mappings = verification_results['market_mappings']
            stock_data = verification_results['stock_data']
            df = verification_results['transactions_df']  # Get back the verified DataFrame

            # Ask about historical data
            response = QMessageBox.question(
                self.view,
                "Historical Data",
                "Would you like to collect historical price data for verified stocks?\n"
                "This process might take several minutes.",
                QMessageBox.Yes | QMessageBox.No
            )
            collect_history = response == QMessageBox.Yes

            # Group transactions by instrument_code for efficiency
            for instrument_code, group in df.groupby('Instrument Code'):
                # Get market suffix and create yahoo symbol
                market_suffix = market_mappings.get(instrument_code, '')
                yahoo_symbol = f"{instrument_code}{market_suffix}" if market_suffix else instrument_code

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

                # Bulk insert transactions for this stock
                transactions = []
                for _, row in group.iterrows():
                    transactions.append((
                        stock.id,
                        row['Trade Date'],
                        row['Quantity'],
                        row['Price'],
                        row['Transaction Type'],
                        row['Quantity'],  # original_quantity
                        row['Price']      # original_price
                    ))
                
                self.db_manager.bulk_insert_transactions(transactions)

                # Update stock splits if any
                if instrument_code in stock_data and 'splits' in stock_data[instrument_code]:
                    splits = stock_data[instrument_code]['splits']
                    split_data = [
                        (stock.id, date.strftime('%Y-%m-%d'), ratio, 'yahoo', datetime.now())
                        for date, ratio in splits.items()
                    ]
                    self.db_manager.bulk_insert_stock_splits(split_data)

            if collect_history:
                self.collect_historical_data(df)

            QMessageBox.information(self.view, "Import Successful", 
                                  "Transactions have been imported successfully.")
            self.import_completed.emit()

        except Exception as e:
            error_msg = f"Failed to process verified transactions: {str(e)}"
            logger.exception(error_msg)
            QMessageBox.warning(self.view, "Import Failed", error_msg)

    def collect_historical_data(self, df):
        # Group by instrument code and get date ranges
        date_ranges = df.groupby('Instrument Code').agg({
            'Trade Date': ['min', 'max']
        }).reset_index()
        date_ranges.columns = ['instrument_code', 'start_date', 'end_date']

        # Collect and store historical data for each stock
        for _, row in date_ranges.iterrows():
            try:
                stock = self.portfolio.get_stock(row['instrument_code'])
                if stock:
                    ticker = yf.Ticker(stock.yahoo_symbol)
                    history = ticker.history(
                        start=row['start_date'],
                        end=row['end_date'],
                        interval='1d'
                    )
                    
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
                    
                    self.db_manager.bulk_insert_historical_prices(historical_prices)
                    
            except Exception as e:
                logger.error(f"Failed to collect historical data for {row['instrument_code']}: {str(e)}")

    def provide_template(self):
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
        self.view.show()