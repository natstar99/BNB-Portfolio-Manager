# File: utils/historical_data_collector.py


from utils.yahoo_finance_service import YahooFinanceService
from utils.date_utils import DateUtils
import logging

logger = logging.getLogger(__name__)

class HistoricalDataCollector:
    """Collects and stores historical price data."""

    @staticmethod
    def process_and_store_historical_data(db_manager, stock_id: int, yahoo_symbol: str) -> bool:
        """
        Fetch and store historical data, then update metrics.
        
        Args:
            db_manager: Database manager instance
            stock_id (int): The database ID of the stock
            yahoo_symbol (str): Yahoo Finance symbol for the stock
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get currencies
            stock_currency, portfolio_currency = db_manager.get_stock_currency_info(stock_id)

            # Get earliest transaction date
            transactions = db_manager.get_transactions_for_stock(stock_id)
            if not transactions:
                logger.info(f"No transactions found for stock {yahoo_symbol} (ID: {stock_id})")
                return False

            start_date = DateUtils.parse_date(min(t[1] for t in transactions))
            logger.info(f"Fetching historical data for {yahoo_symbol} from {start_date}")
            
            # Fetch and store data using YahooFinanceService
            data = YahooFinanceService.fetch_stock_data(
                db_manager=db_manager,
                stock_id=stock_id,
                yahoo_symbol=yahoo_symbol,
                start_date=start_date,
                stock_currency=stock_currency,
                portfolio_currency=portfolio_currency
            )
            
            if data is None:
                logger.warning(f"No historical data retrieved for {yahoo_symbol}")
                return False

            logger.info(f"Successfully processed historical data for {yahoo_symbol}")
            return True
                
        except Exception as e:
            logger.error(f"Error processing historical data for {yahoo_symbol}: {str(e)}")
            logger.exception("Detailed traceback:")
            return False

    def process_verification_results(self, verification_results, parent_widget=None):
        """Process verification results for verified stocks."""
        try:
            verified_stocks = []
            for row in range(verification_results['table_row_count']):
                if verification_results['verification_status'].get(row) == "Verified":
                    instrument_code = verification_results['instrument_codes'][row]
                    yahoo_symbol = verification_results['yahoo_symbols'][row]
                    stock = self.db_manager.get_stock_by_instrument_code(instrument_code)
                    if stock:
                        verified_stocks.append((stock[0], yahoo_symbol))
            
            # Process verified stocks
            for stock_id, yahoo_symbol in verified_stocks:
                self.process_and_store_historical_data(
                    self.db_manager, 
                    stock_id,
                    yahoo_symbol
                )
            
            return len(verified_stocks), len(verified_stocks)
            
        except Exception as e:
            logger.error(f"Error processing verification results: {str(e)}")
            return 0, 0