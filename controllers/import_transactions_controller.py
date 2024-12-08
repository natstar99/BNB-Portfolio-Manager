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
from utils.historical_data_collector import HistoricalDataCollector

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
        self.market_mappings = {}
        self.historical_collector = HistoricalDataCollector(db_manager)

        self.view.import_transactions.connect(self.import_transactions)
        self.view.get_template.connect(self.provide_template)

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
        Process verified transactions and collect historical data for verified stocks.
        Imports all transactions regardless of verification status, but only collects
        historical data for verified stocks.
        
        Args:
            verification_results (dict): Contains verification data and transaction information
        """
        try:
            self.market_mappings = verification_results['market_mappings']
            stock_data = verification_results['stock_data']
            drp_settings = verification_results.get('drp_settings', {})
            df = verification_results['transactions_df']
            
            logger.info("Starting transaction processing")
            processed_stocks = set()

            # First, get all unique instrument codes from the transactions
            unique_instruments = df['Instrument Code'].unique()
            
            for instrument_code in unique_instruments:
                # Get the stock from database to check its verification status
                stock = self.db_manager.get_stock_by_instrument_code(instrument_code)
                
                logger.info(f"Processing stock {instrument_code}")
                if stock:
                    stock_id = stock[0]  # ID
                    yahoo_symbol = stock[1]  # Yahoo symbol
                    verification_status = stock[8]  # verification_status is at index 8
                    logger.info(f"Database record for {instrument_code}: {stock}")
                    logger.info(f"Verification status for {instrument_code}: {verification_status}")
                    
                    # Add stock to portfolio regardless of verification status
                    self.db_manager.add_stock_to_portfolio(self.portfolio.id, stock_id)
                    logger.info(f"Added stock {instrument_code} to portfolio {self.portfolio.id}")
                    
                    # Get transactions for this instrument
                    instrument_transactions = df[df['Instrument Code'] == instrument_code]
                    
                    # Update DRP setting
                    drp_status = drp_settings.get(instrument_code, False)
                    self.db_manager.update_stock_drp(stock_id, drp_status)
                    logger.info(f"Updated DRP setting for {instrument_code}: {drp_status}")

                    # Bulk insert transactions regardless of verification status
                    transactions = [
                        (stock_id, row['Trade Date'], row['Quantity'], row['Price'],
                        row['Transaction Type'], row['Quantity'], row['Price'])
                        for _, row in instrument_transactions.iterrows()
                    ]
                    self.db_manager.bulk_insert_transactions(transactions)
                    logger.info(f"Inserted {len(transactions)} transactions for {instrument_code}")
                    
                    # Only collect historical data for verified stocks
                    if verification_status == 'Verified' and stock_id not in processed_stocks:
                        logger.info(f"Collecting historical data for verified stock {instrument_code}")
                        if self.historical_collector.collect_historical_data(
                            stock_id, 
                            yahoo_symbol,
                            parent_widget=self.view
                        ):
                            processed_stocks.add(stock_id)
                    else:
                        logger.info(f"Skipping historical data for {instrument_code}: verification_status={verification_status}")
                else:
                    logger.warning(f"Stock not found in database: {instrument_code}")
                    continue

            # Show completion message with appropriate details
            if processed_stocks:
                verified_count = len(processed_stocks)
                total_count = len(unique_instruments)
                QMessageBox.information(
                    self.view,
                    "Import Successful", 
                    f"Transactions have been imported for all {total_count} stocks.\n"
                    f"Historical data has been collected for {verified_count} verified stocks."
                )
            else:
                QMessageBox.warning(
                    self.view,
                    "Import Completed", 
                    "Transactions have been imported, but no stocks were verified for historical data collection.\n"
                    "You can verify stocks later through the portfolio manager."
                )
                
            self.import_completed.emit()

        except Exception as e:
            logger.error(f"Failed to process transactions: {str(e)}")
            QMessageBox.warning(self.view, "Import Failed", str(e))


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