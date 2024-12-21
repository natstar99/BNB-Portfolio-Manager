# File: database/database_manager.py

import sqlite3
from datetime import datetime
import os
import logging
import pandas as pd
import numpy as np
from database.portfolio_metrics_manager import METRICS_COLUMNS, PortfolioMetricsManager

logging.basicConfig(level=logging.DEBUG, filename='import_transactions.log', filemode='w',
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_file):
        self.db_file = db_file
        self.conn = None
        self.cursor = None

    def connect(self):
        self.conn = sqlite3.connect(self.db_file)
        self.cursor = self.conn.cursor()

    def disconnect(self):
        if self.conn:
            self.conn.close()

    def init_db(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        schema_file = os.path.join(current_dir, 'schema.sql')
        with open(schema_file, 'r') as f:
            schema = f.read()
        self.conn.executescript(schema)
        self.conn.commit()

    def execute(self, sql, params=None):
        if params is None:
            self.cursor.execute(sql)
        else:
            self.cursor.execute(sql, params)
        self.conn.commit()

    def fetch_one(self, sql, params=None):
        if params is None:
            self.cursor.execute(sql)
        else:
            self.cursor.execute(sql, params)
        return self.cursor.fetchone()

    def fetch_all(self, sql, params=None):
        if params is None:
            self.cursor.execute(sql)
        else:
            self.cursor.execute(sql, params)
        return self.cursor.fetchall()

    # Portfolio methods
    def create_portfolio(self, name):
        self.execute("INSERT INTO portfolios (name) VALUES (?)", (name,))
        return self.cursor.lastrowid

    def get_all_portfolios(self):
        return self.fetch_all("SELECT id, name FROM portfolios")

    def delete_portfolio(self, portfolio_id):
        self.execute("DELETE FROM portfolios WHERE id = ?", (portfolio_id,))

    # Stock methods
    def update_stock_market(self, instrument_code, market_or_index):
        """
        Update stock's market information.
        
        Args:
            instrument_code (str): The stock's instrument code
            market_or_index (str): The market/index identifier
        """
        # Get the market suffix from market_codes table
        result = self.fetch_one(
            "SELECT market_suffix FROM market_codes WHERE market_or_index = ?", 
            (market_or_index,)
        )
        
        if result:
            market_suffix = result[0]
            yahoo_symbol = f"{instrument_code}{market_suffix}"
            
            self.execute("""
                UPDATE stocks 
                SET market_or_index = ?,
                    market_suffix = ?,
                    yahoo_symbol = ?,
                    last_updated = ?
                WHERE instrument_code = ?
            """, (
                market_or_index,
                market_suffix,
                yahoo_symbol,
                datetime.now().replace(microsecond=0),
                instrument_code
            ))
            self.conn.commit()
            
            self.log_stock_entry(instrument_code)

    def add_stock(self, yahoo_symbol, instrument_code, name=None, current_price=None, market_or_index=None, verification_status=None):
        """Add or update a stock."""
        # Get market suffix if market_or_index is provided
        market_suffix = None
        if market_or_index:
            result = self.fetch_one(
                "SELECT market_suffix FROM market_codes WHERE market_or_index = ?",
                (market_or_index,)
            )
            market_suffix = result[0] if result else None

        self.execute("""
            INSERT OR REPLACE INTO stocks 
            (yahoo_symbol, instrument_code, name, current_price, last_updated, 
            market_or_index, market_suffix, verification_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (yahoo_symbol, instrument_code, name, current_price, 
            datetime.now().replace(microsecond=0), market_or_index, 
            market_suffix, verification_status))
        self.conn.commit()
        self.log_stock_entry(instrument_code)  # Log after insert
        return self.cursor.lastrowid
        
    def update_stock_price(self, yahoo_symbol, current_price):
        current_time = datetime.now().replace(microsecond=0)
        self.execute("""
            UPDATE stocks SET current_price = ?, last_updated = ? WHERE yahoo_symbol = ?
        """, (current_price, current_time, yahoo_symbol))

    def get_stock(self, yahoo_symbol):
        return self.fetch_one("SELECT * FROM stocks WHERE yahoo_symbol = ?", (yahoo_symbol,))

    def get_stock_by_instrument_code(self, instrument_code):
        """
        Get stock information by instrument code.
        
        Args:
            instrument_code (str): The stock's instrument code
                
        Returns:
            tuple: Stock information in order:
                - id (int)                    [0]
                - yahoo_symbol (str)          [1]
                - instrument_code (str)       [2]
                - name (str)                  [3]
                - current_price (float)       [4]
                - last_updated (datetime)     [5]
                - market_or_index (str)       [6]
                - market_suffix (str)         [7]
                - verification_status (str)   [8]
                - drp (int)                   [9]
        """
        return self.fetch_one("""
            SELECT 
                s.id,
                s.yahoo_symbol,
                s.instrument_code,
                s.name,
                s.current_price,
                s.last_updated,
                s.market_or_index,
                s.market_suffix,
                s.verification_status,
                s.drp
            FROM stocks s
            WHERE s.instrument_code = ?
        """, (instrument_code,))
        
    def log_stock_entry(self, instrument_code):
        """Simple method to log stock table entries."""
        result = self.fetch_one("""
            SELECT id, yahoo_symbol, instrument_code, name, current_price, 
                last_updated, market_or_index, market_suffix, verification_status
            FROM stocks 
            WHERE instrument_code = ?
        """, (instrument_code,))
        
        if result:
            logging.info(f"""
    Stock Entry for {instrument_code}:
    - ID: {result[0]}
    - Yahoo Symbol: {result[1]}
    - Instrument Code: {result[2]}
    - Name: {result[3]}
    - Current Price: {result[4]}
    - Last Updated: {result[5]}
    - Market/Index: {result[6]}
    - Market Suffix: {result[7]}
    - Verification Status: {result[8]}
            """)
        
    # Transaction methods
    def add_transaction(self, stock_id, date, quantity, price, transaction_type):
        self.execute("""
            INSERT INTO transactions (stock_id, date, quantity, price, transaction_type)
            VALUES (?, ?, ?, ?, ?)
        """, (stock_id, date, quantity, price, transaction_type))

    def get_transactions_for_stock(self, stock_id):
        return self.fetch_all("""
            SELECT id, date, quantity, price, transaction_type
            FROM transactions
            WHERE stock_id = ?
            ORDER BY date
        """, (stock_id,))
    
    def bulk_insert_transactions(self, transactions):
        """
        Bulk insert transactions.
        
        Args:
            transactions: list of tuples (stock_id, date, quantity, price, transaction_type)
        """
        try:
            self.cursor.executemany("""
                INSERT INTO transactions 
                (stock_id, date, quantity, price, transaction_type)
                VALUES (?, ?, ?, ?, ?)
            """, transactions)
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error in bulk_insert_transactions: {str(e)}")
            raise

    def bulk_insert_stock_splits(self, splits):
        """
        Bulk insert stock splits.
        splits: list of tuples (stock_id, date, ratio, verified_source, verification_date)
        """
        self.cursor.executemany("""
            INSERT INTO stock_splits 
            (stock_id, date, ratio, verified_source, verification_date)
            VALUES (?, ?, ?, ?, ?)
        """, splits)
        self.conn.commit()

    def bulk_insert_historical_prices(self, records):
        """Bulk insert historical prices with raw data only."""
        self.cursor.executemany("""
            INSERT OR REPLACE INTO historical_prices 
            (stock_id, date, open_price, high_price, low_price, 
            close_price, volume, dividend, split_ratio)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, records)
        self.conn.commit()

    def get_existing_yahoo_data(self, stock_id: int) -> pd.DataFrame:
        """
        Retrieve existing Yahoo Finance data from the historical_prices table.
        
        Args:
            stock_id (int): The database ID of the stock
            
        Returns:
            pd.DataFrame: DataFrame containing historical price data with columns:
                - Date
                - Open
                - High
                - Low
                - Close
                - Volume
                - Dividends
                - Stock Splits
        """
        try:
            # Fetch the historical data from the database
            results = self.fetch_all("""
                SELECT 
                    date AS Date,
                    open_price AS Open,
                    high_price AS High,
                    low_price AS Low,
                    close_price AS Close,
                    volume AS Volume,
                    dividend AS Dividends,
                    split_ratio AS 'Stock Splits'
                FROM historical_prices
                WHERE stock_id = ?
                ORDER BY date
            """, (stock_id,))
            
            if not results:
                logger.info(f"No existing Yahoo data found for stock_id {stock_id}")
                return pd.DataFrame()
                
            # Convert to DataFrame
            df = pd.DataFrame(results, columns=[
                'Date', 'Open', 'High', 'Low', 'Close', 
                'Volume', 'Dividends', 'Stock Splits'
            ])
            
            # Convert date strings to datetime objects
            df['Date'] = pd.to_datetime(df['Date'])
            
            # Ensure numeric columns have correct types
            numeric_columns = ['Open', 'High', 'Low', 'Close', 'Dividends', 'Stock Splits']
            df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric)
            
            # Ensure Volume is integer type
            df['Volume'] = df['Volume'].fillna(0).astype(np.int64)
            
            return df
            
        except Exception as e:
            logger.error(f"Error retrieving existing Yahoo data for stock_id {stock_id}: {str(e)}")
            logger.exception("Detailed traceback:")
            return pd.DataFrame()

    # Portfolio-Stock relationship methods
    def add_stock_to_portfolio(self, portfolio_id, stock_id):
        self.execute("""
            INSERT OR IGNORE INTO portfolio_stocks (portfolio_id, stock_id)
            VALUES (?, ?)
        """, (portfolio_id, stock_id))

    def remove_stock_from_portfolio(self, portfolio_id, stock_id):
        self.execute("""
            DELETE FROM portfolio_stocks
            WHERE portfolio_id = ? AND stock_id = ?
        """, (portfolio_id, stock_id))

    def get_stocks_for_portfolio(self, portfolio_id):
        """
        Get only verified stocks for a portfolio with detailed logging to debug issues.
        """
        # First, check all stocks in the portfolio
        all_stocks = self.fetch_all("""
            SELECT s.id, s.yahoo_symbol, s.instrument_code, s.name, s.current_price, s.last_updated,
                s.verification_status, ps.portfolio_id
            FROM stocks s
            JOIN portfolio_stocks ps ON s.id = ps.stock_id
            WHERE ps.portfolio_id = ?
        """, (portfolio_id,))
        logger.info(f"All stocks in portfolio: {all_stocks}")

        # Then check verified stocks (without current_price condition)
        verified_stocks = self.fetch_all("""
            SELECT s.id, s.yahoo_symbol, s.instrument_code, s.name, s.current_price, s.last_updated,
                s.verification_status
            FROM stocks s
            JOIN portfolio_stocks ps ON s.id = ps.stock_id
            WHERE ps.portfolio_id = ?
            AND s.verification_status = 'Verified'
        """, (portfolio_id,))
        logger.info(f"Verified stocks in portfolio: {verified_stocks}")

        # Finally, check verified stocks with current price
        final_result = self.fetch_all("""
            SELECT s.id, s.yahoo_symbol, s.instrument_code, s.name, s.current_price, s.last_updated
            FROM stocks s
            JOIN portfolio_stocks ps ON s.id = ps.stock_id
            WHERE ps.portfolio_id = ?
            AND s.verification_status = 'Verified'
            AND s.current_price IS NOT NULL
        """, (portfolio_id,))
        logger.info(f"Final result (verified stocks with price): {final_result}")

        return final_result

    # Stock split methods
    def add_stock_split(self, stock_id, date, ratio):
        self.execute("""
            INSERT INTO stock_splits (stock_id, date, ratio)
            VALUES (?, ?, ?)
        """, (stock_id, date, ratio))

    def get_stock_splits(self, stock_id):
        """
        Get all stock splits for a given stock.
        
        Args:
            stock_id: The database ID of the stock
            
        Returns:
            List of tuples (date, ratio, verified_source)
        """
        return self.fetch_all("""
            SELECT date, ratio, verified_source 
            FROM stock_splits
            WHERE stock_id = ?
            ORDER BY date
        """, (stock_id,))
    
    # Dividend Reinvestment Plan methods
    def get_stock_drp(self, stock_id):
        result = self.fetch_one("SELECT drp FROM stocks WHERE id = ?", (stock_id,))
        return bool(result[0]) if result and result[0] is not None else False

    def update_stock_drp(self, stock_id, drp_status):
        self.execute("""
            UPDATE stocks 
            SET drp = ?
            WHERE id = ?
        """, (1 if drp_status else 0, stock_id))
        self.conn.commit()
        print(f"Database updated: Stock ID {stock_id} DRP status set to {drp_status}") 

    # Market code methods
    def get_all_market_codes(self):
        """
        Returns all market codes with their suffixes.
        Returns tuples of (market_or_index, market_suffix)
        """
        return self.fetch_all("""
            SELECT market_or_index, market_suffix 
            FROM market_codes 
            ORDER BY market_or_index
        """)

    def get_market_code_suffix(self, market_or_index):
        result = self.fetch_one("SELECT market_suffix FROM market_codes WHERE market_or_index = ?", (market_or_index,))
        return result[0] if result else None

    def update_stock_yahoo_symbol(self, instrument_code, yahoo_symbol):
        self.execute("UPDATE stocks SET yahoo_symbol = ? WHERE instrument_code = ?", (yahoo_symbol, instrument_code))

    def get_all_stocks(self):
        return self.fetch_all("""
            SELECT id, yahoo_symbol, instrument_code, name, current_price, 
                last_updated, market_or_index, market_suffix, verification_status, drp
            FROM stocks
        """)
    
    def get_stock(self, instrument_code):
        return self.fetch_one("""
            SELECT id, yahoo_symbol, instrument_code, name, current_price, last_updated, market_suffix
            FROM stocks
            WHERE instrument_code = ?
        """, (instrument_code,))

    # For interacting with the portfolio_metrics table:

    def execute_with_params(self, sql, params=None):
        """Execute SQL with named parameters."""
        if params is None:
            self.cursor.execute(sql)
        else:
            self.cursor.execute(sql, params)
        self.conn.commit()

    def fetch_all_with_params(self, sql, params=None):
        """Fetch all results with named parameters."""
        if params is None:
            self.cursor.execute(sql)
        else:
            self.cursor.execute(sql, params)
        return self.cursor.fetchall()

    def fetch_one_with_params(self, sql, params=None):
        """Fetch one result with named parameters."""
        if params is None:
            self.cursor.execute(sql)
        else:
            self.cursor.execute(sql, params)
        return self.cursor.fetchone()

    def bulk_update_stock_metrics(self, metrics_list):
        """
        Bulk update or insert metrics for multiple records at once.
        
        Args:
            metrics_list: List of dictionaries containing metrics data
        """
        try:
            # Convert metrics to tuples in correct column order
            batch_data = [
                tuple(metrics.get(col) for col in METRICS_COLUMNS)
                for metrics in metrics_list
            ]

            self.cursor.executemany(PortfolioMetricsManager.get_insert_sql(), batch_data)
            self.conn.commit()
            logger.debug(f"Bulk updated {len(batch_data)} metrics records")
                
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error in bulk_update_stock_metrics: {str(e)}")
            raise

    def update_stock_metrics(self, stock_id: int, metrics_data: dict):
        """Update metrics for a single stock."""
        try:
            # Create tuple of values in correct column order
            values = tuple(metrics_data.get(col) for col in METRICS_COLUMNS)
            
            self.execute(PortfolioMetricsManager.get_insert_sql(), values)
            logger.debug(f"Successfully updated metrics for stock {stock_id}")
            
        except Exception as e:
            logger.error(f"Error updating metrics for stock {stock_id}: {str(e)}")
            raise