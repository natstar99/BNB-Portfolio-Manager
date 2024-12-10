# File: utils/historical_data_collector.py

import logging
import pandas as pd
import yfinance as yf
from PySide6.QtWidgets import QMessageBox, QProgressDialog
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)

class HistoricalDataCollector:
    """
    Centralised utility class for collecting and managing historical price and dividend data.
    Provides consistent historical data collection across different parts of the application.
    """
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def collect_historical_data(self, stock_id, yahoo_symbol, force_refresh=False, parent_widget=None):
        """
        Collect historical price and dividend data for a stock.
        
        Args:
            stock_id (int): The database ID of the stock
            yahoo_symbol (str): The Yahoo Finance symbol for the stock
            force_refresh (bool): If True, re-fetch all data. If False, only fetch new data.
            parent_widget (QWidget): Optional parent widget for progress dialog
            
        Returns:
            bool: True if collection was successful, False otherwise
        """
        try:
            logger.info(f"Starting historical data collection for {yahoo_symbol}")
            
            # Create progress dialog if parent widget provided
            progress_dialog = None
            if parent_widget:
                progress_dialog = QProgressDialog(
                    f"Collecting historical data for {yahoo_symbol}...",
                    "Cancel",
                    0,
                    100,
                    parent_widget
                )
                progress_dialog.setWindowModality(Qt.WindowModal)
                progress_dialog.setValue(0)
                progress_dialog.show()
            
            if force_refresh:
                # Get earliest transaction date for full refresh
                earliest_transaction = self.db_manager.fetch_one(
                    "SELECT MIN(date) FROM transactions WHERE stock_id = ?", 
                    (stock_id,)
                )
                start_date = pd.to_datetime(earliest_transaction[0])
                logger.info(f"Forcing full refresh from {start_date}")
                
                # Update progress
                if progress_dialog:
                    progress_dialog.setValue(20)
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

                # Update progress
                if progress_dialog:
                    progress_dialog.setValue(20)

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
                
                # Update progress
                if progress_dialog:
                    progress_dialog.setValue(40)
                
                # Get historical data
                history = ticker.history(
                    start=start_date,
                    end=pd.Timestamp.today(),
                    interval='1d'
                )

                # Get dividend data
                dividends = ticker.dividends

                # Update progress
                if progress_dialog:
                    progress_dialog.setValue(60)

                if not history.empty:
                    logger.info(f"Retrieved {len(history)} new data points")
                    
                    # Prepare bulk insert data
                    historical_prices = []
                    for index, row in history.iterrows():
                        # Check if there's a dividend on this date
                        dividend_amount = dividends[dividends.index == index].iloc[0] if not dividends.empty and index in dividends.index else 0.0
                        
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
                            dividend_amount
                        ))
                    
                    # Update progress
                    if progress_dialog:
                        progress_dialog.setValue(80)
                    
                    # Insert new historical data
                    self.db_manager.bulk_insert_historical_prices(historical_prices)
                    logger.info(f"Successfully stored historical data")
                    
                    # Complete progress
                    if progress_dialog:
                        progress_dialog.setValue(100)
                    
                    return True
                else:
                    logger.warning(f"No new historical data found")
                    if progress_dialog:
                        progress_dialog.close()
                    return False
            else:
                logger.info("Historical data is up to date")
                if progress_dialog:
                    progress_dialog.close()
                return True

        except Exception as e:
            logger.error(f"Failed to collect historical data: {str(e)}")
            if progress_dialog:
                progress_dialog.close()
            if parent_widget:
                QMessageBox.warning(
                    parent_widget,
                    "Data Collection Failed",
                    f"Failed to collect historical data for {yahoo_symbol}: {str(e)}"
                )
            return False

    def process_verification_results(self, verification_results, parent_widget=None):
        """
        Process verification results and collect historical data for verified stocks.
        
        Args:
            verification_results (dict): Results from verification dialog
            parent_widget: Widget to show messages on (optional)
            
        Returns:
            tuple: (success_count, total_count) of processed stocks
        """
        try:
            verified_stocks = []
            processed_count = 0
            
            # Create overall progress dialog
            progress = None
            if parent_widget:
                progress = QProgressDialog(
                    "Processing verified stocks...",
                    "Cancel",
                    0,
                    len(verification_results.get('verification_status', {})),
                    parent_widget
                )
                progress.setWindowModality(Qt.WindowModal)
                progress.show()
            
            # Get list of verified stocks
            for row in range(verification_results['table_row_count']):
                if progress and progress.wasCanceled():
                    break
                    
                status = verification_results['verification_status'].get(row)
                if status == "Verified":
                    instrument_code = verification_results['instrument_codes'][row]
                    yahoo_symbol = verification_results['yahoo_symbols'][row]
                    stock = self.db_manager.get_stock_by_instrument_code(instrument_code)
                    if stock:
                        verified_stocks.append((stock[0], yahoo_symbol))
                
                if progress:
                    progress.setValue(row + 1)

            # Process verified stocks
            for stock_id, yahoo_symbol in verified_stocks:
                if self.collect_historical_data(stock_id, yahoo_symbol, force_refresh=True, parent_widget=parent_widget):
                    processed_count += 1

            # Show completion message if parent widget provided
            if parent_widget and verified_stocks:
                QMessageBox.information(
                    parent_widget,
                    "Update Complete",
                    f"Historical data collected for {processed_count} out of {len(verified_stocks)} verified stocks."
                )

            return processed_count, len(verified_stocks)

        except Exception as e:
            logger.error(f"Error processing verification results: {str(e)}")
            if parent_widget:
                QMessageBox.warning(
                    parent_widget,
                    "Update Failed",
                    f"Failed to process verification results: {str(e)}"
                )
            return 0, 0