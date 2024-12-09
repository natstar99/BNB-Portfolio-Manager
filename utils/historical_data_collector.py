# File: utils/historical_data_collector.py

import logging
import pandas as pd
import yfinance as yf
from PySide6.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)

class HistoricalDataCollector:
    """
    Utility class for collecting and managing historical price data.
    Provides consistent historical data collection across different parts of the application.
    """
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def collect_historical_data(self, stock_id, yahoo_symbol, force_refresh=False):
        """
        Collect historical data for a stock.
        
        Args:
            stock_id (int): The database ID of the stock
            yahoo_symbol (str): The Yahoo Finance symbol for the stock
            force_refresh (bool): If True, re-fetch all data. If False, only fetch new data.
            
        Returns:
            bool: True if collection was successful, False otherwise
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
                    return True
                else:
                    logger.warning(f"No new historical data found")
                    return False
            else:
                logger.info("Historical data is up to date")
                return True

        except Exception as e:
            logger.error(f"Failed to collect historical data: {str(e)}")
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
            
            # Get list of verified stocks
            for row in range(verification_results['table_row_count']):
                status = verification_results['verification_status'].get(row)
                if status == "Verified":
                    instrument_code = verification_results['instrument_codes'][row]
                    yahoo_symbol = verification_results['yahoo_symbols'][row]
                    stock = self.db_manager.get_stock_by_instrument_code(instrument_code)
                    if stock:
                        verified_stocks.append((stock[0], yahoo_symbol))

            # Process verified stocks
            for stock_id, yahoo_symbol in verified_stocks:
                if self.collect_historical_data(stock_id, yahoo_symbol, force_refresh=True):
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