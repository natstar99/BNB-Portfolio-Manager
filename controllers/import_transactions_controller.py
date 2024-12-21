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
from database.portfolio_metrics_manager import PortfolioMetricsManager
from utils.fifo_hifo_lifo_calculator import RealisedPLCalculator, process_stock_matches, MatchingMethod
import yaml


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
        self.historical_collector = HistoricalDataCollector()
        self.config = self.load_config()

        self.view.import_transactions.connect(self.import_transactions)
        self.view.get_template.connect(self.provide_template)

    def load_config(self):
        """Load configuration from config.yaml."""
        try:
            with open('config.yaml', 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            return {"profit_loss_calculations": {"default_method": "fifo"}}

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
        Process verified transactions and update metrics.
        Imports all transactions regardless of verification status, but only collects
        historical data for verified stocks.
        
        Args:
            verification_results (dict): Contains verification data and transaction information
        """
        try:
            self.market_mappings = verification_results['market_mappings']
            self.stock_data = verification_results['stock_data']
            self.drp_settings = verification_results.get('drp_settings', {})
            df = verification_results['transactions_df']

            # Get calculation method from config
            pl_method = self.config.get('profit_loss_calculations', {}).get('default_method', 'fifo')
            calculation_method = MatchingMethod[pl_method.upper()]
            
            # Process each unique instrument
            unique_instruments = df['Instrument Code'].unique()
            
            for instrument_code in unique_instruments:
                # Get the stock to check its verification status
                stock = self.db_manager.get_stock_by_instrument_code(instrument_code)
                
                logger.info(f"Processing stock {instrument_code}")
                if stock:
                    stock_id = stock[0]  # ID
                    verification_status = stock[8]  # verification_status is at index 8
                    
                    # Add stock to portfolio regardless of verification
                    self.db_manager.add_stock_to_portfolio(self.portfolio.id, stock_id)
                    logger.info(f"Added stock {instrument_code} to portfolio {self.portfolio.id}")
                    
                    # Get transactions for this instrument
                    instrument_transactions = df[df['Instrument Code'] == instrument_code]

                    # Convert transactions to calculator format (for realised_pl calcuations)
                    calculator_transactions = []
                    for _, row in instrument_transactions.iterrows():
                        calc_trans = RealisedPLCalculator(
                            id=None,  # Will be set after database insert
                            stock_id=stock_id,
                            date=row['Trade Date'],
                            quantity=row['Quantity'],
                            price=row['Price'],
                            type=row['Transaction Type']
                        )
                        calculator_transactions.append(calc_trans)
                    
                    # Bulk insert transactions first
                    transactions = [
                        (stock_id, row['Trade Date'], row['Quantity'], row['Price'],
                        row['Transaction Type'])
                        for _, row in instrument_transactions.iterrows()
                    ]
                    self.db_manager.bulk_insert_transactions(transactions)
                    logger.info(f"Inserted {len(transactions)} transactions for {instrument_code}")

                    # Get all transactions for this stock (including existing ones)
                    all_transactions = self.db_manager.get_transactions_for_stock(stock_id)
                    all_calculator_transactions = [
                        RealisedPLCalculator(
                            id=trans[0],
                            stock_id=stock_id,
                            date=trans[1],
                            quantity=trans[2],
                            price=trans[3],
                            type=trans[4]
                        )
                        for trans in all_transactions
                    ]
                    
                    # Process matches using specified method
                    matches = process_stock_matches(all_calculator_transactions, calculation_method)
                    
                    # Clear existing matches for this stock
                    self.db_manager.execute(
                        "DELETE FROM realised_pl WHERE stock_id = ?",
                        (stock_id,)
                    )
                    
                    # Bulk insert new matches
                    self.db_manager.cursor.executemany("""
                        INSERT INTO realised_pl (
                            sell_id, buy_id, stock_id, matched_units,
                            buy_price, sell_price, realised_pl,
                            trade_date, method
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, [
                        (m['sell_id'], m['buy_id'], m['stock_id'], m['matched_units'],
                            m['buy_price'], m['sell_price'], m['realised_pl'],
                            m['trade_date'], m['method'])
                        for m in matches
                    ])
                    
                    # Update metrics for verified stocks only
                    if verification_status == "Verified":
                        metrics_manager = PortfolioMetricsManager(self.db_manager)
                        metrics_manager.update_metrics_for_stock(stock_id)
                        logger.info(f"Updated metrics for verified stock {instrument_code}")
                
            # Show completion message
            QMessageBox.information(
                self.view,
                "Import Successful", 
                f"Transactions have been imported for all stocks."
            )
            
            self.import_completed.emit()

        except Exception as e:
            logger.error(f"Failed to process transactions: {str(e)}")
            logger.exception("Detailed traceback:")
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