# File: models/stock.py

from datetime import datetime
from typing import List, Dict, Optional
from database.final_metrics_manager import PortfolioMetricsManager
from models.transaction import Transaction
from database.final_metrics_manager import METRICS_COLUMNS
from utils.yahoo_finance_service import YahooFinanceService
import logging

logger = logging.getLogger(__name__)

class Stock:
    """
    Represents a stock holding with real-time metrics tracking.
    Uses pre-calculated metrics for efficient access to position data.
    """
    def __init__(self, id: int, yahoo_symbol: str, instrument_code: str, 
                 name: str, current_price: float, last_updated: datetime, 
                 db_manager) -> None:
        self.id = id
        self.yahoo_symbol = yahoo_symbol
        self.instrument_code = instrument_code
        self.name = name
        self.current_price = current_price
        self.last_updated = last_updated
        self.db_manager = db_manager
        self.metrics_manager = PortfolioMetricsManager(db_manager)
        
        # Cache latest metrics
        self._latest_metrics = None
        
        # Load transactions immediately on initialisation
        self.transactions = self.get_transactions()

    def get_transactions(self):
        """
        Get all transactions for this stock.
        Returns a list of Transaction objects ordered by date.
        """
        try:
            # Get raw transaction data from database
            transactions_data = self.db_manager.get_transactions_for_stock(self.id)
            
            # Convert tuple data into Transaction objects
            transactions = []
            for trans_data in transactions_data:
                transaction = Transaction(
                    id=trans_data[0],
                    date=trans_data[1],
                    quantity=trans_data[2],
                    price=trans_data[3],
                    transaction_type=trans_data[4],
                    db_manager=self.db_manager
                )
                transactions.append(transaction)
                
            return transactions
        except Exception as e:
            logger.error(f"Error getting transactions for stock {self.yahoo_symbol}: {str(e)}")
            return []
    
    def refresh_metrics(self) -> None:
        """
        Update all metrics for this stock.
        Called after transactions, prices, or DRP settings change.
        """
        try:
            self.metrics_manager.update_metrics_for_stock(self.id)
            self._latest_metrics = None  # Reset cache
            logger.info(f"Refreshed metrics for {self.yahoo_symbol}")
        except Exception as e:
            logger.error(f"Failed to refresh metrics for {self.yahoo_symbol}: {str(e)}")
            raise

    def get_metrics_in_range(self, start_date: Optional[datetime] = None, 
                   end_date: Optional[datetime] = None) -> List[Dict]:
        """Get metrics for a date range for plotting/analysis."""
        return self.metrics_manager.get_metrics_in_range(self.id, start_date, end_date)

    def update_metrics(self):
        """Update metrics after any change."""
        metrics_manager = PortfolioMetricsManager(self.db_manager)
        metrics_manager.update_metrics_for_stock(self.id)

    @property
    def latest_metrics(self) -> Dict:
        """Get latest position metrics with caching."""
        if self._latest_metrics is None:
            metrics_tuple = self.metrics_manager.get_latest_metrics(self.id)
            if metrics_tuple:
                # Simply zip the column names with the values
                self._latest_metrics = dict(zip(METRICS_COLUMNS, metrics_tuple))
                logger.debug(f"Converted metrics dict for {self.yahoo_symbol}")
            else:
                self._latest_metrics = None
                logger.debug(f"No metrics found for {self.yahoo_symbol}")
                    
        return self._latest_metrics

    # Position information - all use cached metrics
    def calculate_total_shares(self) -> float:
        """Get current total shares held."""
        metrics = self.latest_metrics
        return metrics['total_shares_owned'] if metrics else 0.0

    def calculate_current_cost_basis(self) -> float:
        """Get the current cost basis of shares owned."""
        metrics = self.latest_metrics
        return metrics['current_cost_basis'] if metrics else 0.0

    def calculate_market_value(self) -> float:
        """Get current market value."""
        metrics = self.latest_metrics
        return metrics['market_value'] if metrics else 0.0

    def calculate_realised_pl(self) -> float:
        """Get realised profit/loss including dividends."""
        metrics = self.latest_metrics
        return metrics['realised_pl'] if metrics else 0.0

    def calculate_unrealised_pl(self) -> float:
        """Get unrealised profit/loss."""
        metrics = self.latest_metrics
        return metrics['unrealised_pl'] if metrics else 0.0

    def calculate_total_return(self) -> float:
        """Get total return including all components."""
        metrics = self.latest_metrics
        return metrics['total_return'] if metrics else 0.0

    def calculate_total_return_pct(self) -> float:
        """Get total return percentage."""
        metrics = self.latest_metrics
        return metrics['total_return_pct'] if metrics else 0.0
    
    def calculate_cumulative_return_pct(self) -> float:
        """Get the cumulative return percentage."""
        metrics = self.latest_metrics
        return metrics['cumulative_return_pct'] if metrics else 0.0

    def update_price(self, new_price: float) -> None:
        """Update current price and metrics."""
        self.current_price = new_price
        self.last_updated = datetime.now().replace(microsecond=0)
        self.db_manager.update_stock_price(self.yahoo_symbol, new_price)
        self.refresh_metrics()  # Recalculate metrics with new price

    @classmethod
    def create(cls, yahoo_symbol: str, instrument_code: str, name: str, 
              current_price: float, db_manager) -> 'Stock':
        """Create a new stock instance."""
        stock_id = db_manager.add_stock(
            yahoo_symbol=yahoo_symbol,
            instrument_code=instrument_code,
            name=name,
            current_price=current_price
        )
        return cls(
            id=stock_id,
            yahoo_symbol=yahoo_symbol,
            instrument_code=instrument_code,
            name=name,
            current_price=current_price,
            last_updated=datetime.now().replace(microsecond=0),
            db_manager=db_manager
        )

    def get_converted_price(self) -> float:
        """
        Get the current price converted to portfolio's default currency if needed.
        
        Returns:
            float: The current price in the portfolio's default currency
        """
        try:
            # Get currencies
            currencies = self.db_manager.get_stock_currency_info(self.id)
            if not currencies:
                return self.current_price
                
            stock_currency, portfolio_currency = currencies
            
            # Get conversion rate using Yahoo Finance Service
            conversion_rate = YahooFinanceService.get_current_conversion_rate(
                stock_currency, 
                portfolio_currency
            )
            
            return self.current_price * conversion_rate
            
        except Exception as e:
            logger.warning(f"Failed to convert price for {self.yahoo_symbol}: {e}")
            return self.current_price