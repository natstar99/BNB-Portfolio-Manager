# File: controllers/import_transactions_controller.py

import pandas as pd
import os
import shutil
import logging
from datetime import datetime
from PySide6.QtWidgets import QFileDialog, QMessageBox
from PySide6.QtCore import QObject, Signal
from models.transaction import Transaction
from models.stock import Stock
from views.import_transactions_view import ImportTransactionsView

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

            logger.debug(f"DataFrame head:\n{df.head()}")
            logger.debug(f"DataFrame info:\n{df.info()}")

            for index, row in df.iterrows():
                try:
                    logger.debug(f"Processing row {index}:\n{row}")
                    trade_date = row['Trade Date'].isoformat()  # Convert to 'YYYY-MM-DD' string
                    logger.debug(f"Parsed trade date: {trade_date}")
                    
                    self.process_transaction(
                        trade_date, row['Instrument Code'],
                        row['Quantity'], row['Price'], row['Transaction Type']
                    )
                except Exception as row_error:
                    logger.error(f"Error processing row {index}: {str(row_error)}")
                    raise

            QMessageBox.information(self.view, "Import Successful", "Transactions have been imported successfully.")
            self.import_completed.emit()
        except Exception as e:
            error_msg = f"Failed to import transactions: {str(e)}"
            logger.exception(error_msg)
            QMessageBox.warning(self.view, "Import Failed", error_msg)

    def process_transaction(self, date, instrument_code, quantity, price, transaction_type):
        logger.debug(f"Processing transaction: date={date}, instrument_code={instrument_code}, "
                     f"quantity={quantity}, price={price}, transaction_type={transaction_type}")
        stock = Stock.get_by_yahoo_symbol(instrument_code, self.db_manager)
        if not stock:
            stock = Stock.create(instrument_code, instrument_code, "", price, self.db_manager)
            self.portfolio.add_stock(stock)

        Transaction.create(stock.id, date, float(quantity), float(price), transaction_type, self.db_manager)

    def provide_template(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(current_dir, "..", "Transaction_Data_Template.xlsx")
        
        if not os.path.exists(template_path):
            QMessageBox.warning(self.view, "Template Not Found", "The template file is missing from the application directory.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self.view, "Save Template", "Transaction_Data_Template.xlsx", "Excel Files (*.xlsx)"
        )
        if save_path:
            shutil.copy2(template_path, save_path)
            QMessageBox.information(self.view, "Template Saved", f"Template has been saved to {save_path}")

    def show_view(self):
        self.view.show()