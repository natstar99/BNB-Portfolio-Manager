# File: database/final_metrics_manager.py

import os
from datetime import datetime
import logging
import yaml
import sys
logger = logging.getLogger(__name__)

# Definition of the columns in the final_metrics table
# This is referenced throughout the code as a single source of truth
METRICS_COLUMNS = [
    'metric_index',
    'stock_id',
    'yahoo_symbol',
    'date',
    'close_price',
    'dividend',
    'cash_dividend',
    'cash_dividends_total',
    'drp_flag',
    'drp_share',
    'drp_shares_total',
    'split_ratio',
    'cumulative_split_ratio',
    'transaction_type',
    'adjusted_quantity',
    'adjusted_price',
    'net_transaction_quantity',
    'total_investment_amount',
    'cost_basis_variation',
    'cumulative_cost_basis_variation',
    'current_cost_basis',
    'total_shares_owned',
    'market_value',
    'realised_pl',
    'unrealised_pl',
    'daily_pl',
    'daily_pl_pct',
    'total_return',
    'total_return_pct',
    'cumulative_return_pct'
]


class PortfolioMetricsManager:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.queries = self.load_queries()

    def get_queries_path(self):
        """
        Get the correct path to final_metrics.sql whether running as script or executable.
        
        Returns:
            str: The full path to final_metrics.sql file
        
        This method handles path resolution differently based on whether the application
        is running as a script or as a compiled executable, ensuring the SQL file can
        be found in either case.
        """
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            base_path = sys._MEIPASS
            return os.path.join(base_path, 'database', 'final_metrics.sql')
        else:
            # Running as script
            current_dir = os.path.dirname(os.path.abspath(__file__))
            return os.path.join(current_dir, "final_metrics.sql")
    
    def load_queries(self):
        """
        Load SQL queries from file.
        
        Returns:
            dict: Dictionary containing all loaded SQL queries
            
        Raises:
            Exception: If queries cannot be loaded
        """
        queries_path = self.get_queries_path()
        
        try:
            logger.debug(f"Attempting to load queries from: {queries_path}")
            
            with open(queries_path, 'r') as f:
                queries = {}
                current_query = []
                current_name = None
                
                for line in f:
                    if line.startswith('-- Query to'):
                        if current_name and current_query:
                            logger.debug(f"Storing query: {current_name}")
                            queries[current_name] = ''.join(current_query)
                        # Extract just the first few words for the key
                        full_name = line[11:].strip()
                        current_name = ' '.join(full_name.split()[:4])  # Take first 4 words
                        logger.debug(f"Found new query: {current_name}")
                        current_query = []
                    else:
                        current_query.append(line)
                        
                if current_name and current_query:
                    logger.debug(f"Storing final query: {current_name}")
                    queries[current_name] = ''.join(current_query)
                
                logger.debug(f"Loaded queries: {list(queries.keys())}")
                return queries
                    
        except Exception as e:
            logger.error(f"Error loading queries: {str(e)}")
            logger.exception("Detailed traceback:")
            raise Exception(f"Failed to load metrics queries: {str(e)}")

    def update_metrics_for_stock(self, stock_id: int):
        """
        Update all metrics for a given stock
        
        Args:
            stock_id: The database ID of the stock
        """
        try:
            # Load config to get P/L method
            with open('config.yaml', 'r') as f:
                config = yaml.safe_load(f)
                pl_method = config.get('profit_loss_calculations', {}).get('default_method', 'fifo')

            # Get metrics data from SQL query with pl_method parameter
            metrics_data = self.db_manager.fetch_all_with_params(
                self.queries['calculate and update metrics'],
                {
                    'stock_id': stock_id,
                    'pl_method': pl_method
                }
            )
            
            if not metrics_data:
                logger.info(f"No metrics data for stock_id {stock_id}")
                return

            # Convert SQL results to list of dictionaries
            batch_metrics = []
            for row in metrics_data:
                # Create dict by zipping columns with values
                metrics_dict = dict(zip(METRICS_COLUMNS, row))
                batch_metrics.append(metrics_dict)

            # Bulk update the metrics
            self.db_manager.bulk_update_stock_metrics(batch_metrics)
            
            logger.info(f"Completed metrics update for stock_id {stock_id} "
                    f"({len(metrics_data)} records)")
            
        except Exception as e:
            logger.error(f"Error updating metrics for stock {stock_id}: {str(e)}")
            raise

    def get_metrics_in_range(self, stock_id: int, start_date=None, end_date=None):
        """
        Get metrics for a stock within a date range.
        
        Args:
            stock_id: The database ID of the stock
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            
        Returns:
            List of dictionaries containing metrics data
        """
        try:
            # Get raw metrics data
            raw_metrics = self.db_manager.fetch_all_with_params(
                self.queries['get metrics for date range'],
                {
                    'stock_id': stock_id,
                    'start_date': start_date,
                    'end_date': end_date
                }
            )
            
            # Convert to list of dictionaries using METRICS_COLUMNS
            metrics = [dict(zip(METRICS_COLUMNS, row)) for row in raw_metrics]
            return metrics
                
        except Exception as e:
            logger.error(f"Error getting metrics for stock {stock_id}: {str(e)}")
            raise

    def get_latest_metrics(self, stock_id: int):
        """
        Get the most recent metrics for a stock.
        
        Args:
            stock_id: The database ID of the stock
            
        Returns:
            Tuple containing latest metrics values in column order
        """
        try:
            raw_metrics = self.db_manager.fetch_one_with_params(
                self.queries['get latest metrics'],
                {'stock_id': stock_id}
            )
            
            return raw_metrics
            
        except Exception as e:
            logger.error(f"Error getting latest metrics for stock {stock_id}: {str(e)}")
            raise

    def get_insert_sql():
        """Returns SQL insert statement with explicit column names."""
        # Get all columns except metric_index (first column)
        columns = METRICS_COLUMNS
        cols = ','.join(columns)
        placeholders = ','.join(['?' for _ in columns])
        
        sql = f"""
            INSERT OR REPLACE INTO final_metrics 
            ({cols}) 
            VALUES ({placeholders})
        """
        return sql.strip()