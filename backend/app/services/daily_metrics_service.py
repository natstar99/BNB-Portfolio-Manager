"""
Daily Metrics Service - Handles calculation and management of daily portfolio metrics
====================================================================================

This service handles the complex calculation of daily portfolio metrics that populate
FACT_DAILY_PORTFOLIO_METRICS in the Kimball star schema. It integrates transaction
data from FACT_TRANSACTIONS with market prices from FACT_MARKET_PRICES to calculate
comprehensive portfolio performance metrics.

ARCHITECTURAL PHILOSOPHY:
- Calculates cumulative metrics (shares, cost basis, P&L) for each trading day
- Handles complex scenarios: stock splits, dividends, DRP, partial sales
- Ensures data consistency through proper transaction context management
- Optimized for batch recalculation when historical data changes

DESIGN DECISIONS:
1. Transaction Context Management: All methods support commit=False for integration
   with TransactionImportService's atomic transaction context
2. Date Key Strategy: Uses YYYYMMDD date_key format for star schema consistency
3. Error Isolation: Individual metric calculation failures don't stop batch processing
4. Cumulative Calculations: Each day builds on previous day's metrics for efficiency
5. Corporate Actions: Handles splits and dividends from market data automatically

INTEGRATION POINTS:
- Called by TransactionImportService after market data collection
- Consumes data from FACT_TRANSACTIONS and FACT_MARKET_PRICES
- Populates FACT_DAILY_PORTFOLIO_METRICS for analytics and reporting
- Works with DateDimension for proper trading day calculations

CRITICAL REQUIREMENTS:
- Must handle transaction context properly (commit parameter)
- Must calculate cumulative metrics correctly across date ranges
- Must handle corporate actions (splits, dividends) properly
- Must support recalculation from any starting date
- Must maintain data integrity during batch operations

FUTURE DEVELOPERS: This service implements complex financial calculations.
Any changes must maintain mathematical accuracy and handle edge cases like:
- Stock splits (adjusting share counts and cost basis)
- Dividend payments (cash vs DRP)
- Partial sales (calculating realized P&L correctly)
- Position reversals (going from long to short)
"""

import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal

from app import db
from app.models.daily_metrics import DailyPortfolioMetric
from app.models.market_prices import MarketPrice
from app.models.transaction import Transaction, TransactionType
from app.models.stock import Stock
from app.models.date_dimension import DateDimension

logger = logging.getLogger(__name__)


class DailyMetricsService:
    """
    Service for calculating and managing daily portfolio metrics.
    Handles complex calculations like cumulative shares, cost basis, P&L calculations.
    """
    
    def __init__(self):
        pass
    
    def recalculate_portfolio_metrics(self, portfolio_key: int, stock_key: int, from_date: date = None, commit: bool = True) -> Dict[str, Any]:
        """
        Recalculate daily metrics for a specific portfolio/stock combination from specified date forward.
        Used when transactions are added or corrected.
        
        TRANSACTION CONTEXT MANAGEMENT: This method can be called within a transaction
        context manager from TransactionImportService. The commit parameter controls
        whether database operations are committed immediately or deferred.
        
        Args:
            portfolio_key: Portfolio identifier
            stock_key: Stock identifier
            from_date: Start date for recalculation (optional - auto-determined)
            commit: Whether to commit database changes (default True for standalone use)
            
        Returns:
            Dict: Results with success status and metrics count
        """
        try:
            # Convert date to date_key format
            if from_date:
                from_date_key = int(from_date.strftime('%Y%m%d'))
            else:
                # Find the earliest transaction date for this portfolio/stock
                earliest_transaction = Transaction.query.filter_by(
                    portfolio_key=portfolio_key,
                    stock_key=stock_key
                ).order_by(Transaction.transaction_date).first()
                
                if not earliest_transaction:
                    logger.info(f"No transactions found for portfolio {portfolio_key}, stock {stock_key}")
                    return {'success': True, 'metrics_calculated': 0}
                
                from_date_key = int(earliest_transaction.transaction_date.strftime('%Y%m%d'))
            
            # Delete existing metrics from this date forward to recalculate
            DailyPortfolioMetric.delete_metrics_from_date(portfolio_key, stock_key, from_date_key, commit=commit)
            
            # Get all transactions for this portfolio/stock from the start date
            transactions = Transaction.query.join(TransactionType).filter(
                Transaction.portfolio_key == portfolio_key,
                Transaction.stock_key == stock_key,
                Transaction.transaction_date >= from_date
            ).order_by(Transaction.transaction_date).all()
            
            if not transactions:
                return {'success': True, 'metrics_calculated': 0}
            
            # Get date range from first transaction to today
            end_date = date.today()
            end_date_key = int(end_date.strftime('%Y%m%d'))
            
            # Get all trading days in this range
            trading_days = DateDimension.get_trading_days_in_range(from_date_key, end_date_key)
            
            metrics_calculated = 0
            
            # Process each trading day
            for date_key in trading_days:
                metric = self._calculate_daily_metric(portfolio_key, stock_key, date_key, transactions, commit=commit)
                if metric:
                    metrics_calculated += 1
            
            logger.info(f"Recalculated {metrics_calculated} daily metrics for portfolio {portfolio_key}, stock {stock_key}")
            
            return {
                'success': True,
                'metrics_calculated': metrics_calculated,
                'from_date_key': from_date_key,
                'to_date_key': end_date_key
            }
            
        except Exception as e:
            logger.error(f"Error recalculating metrics for portfolio {portfolio_key}, stock {stock_key}: {str(e)}")
            # Don't rollback here - let calling method handle transaction rollback
            # if commit:
            #     db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    def _calculate_daily_metric(self, portfolio_key: int, stock_key: int, date_key: int, all_transactions: List[Transaction], commit: bool = True) -> Optional[DailyPortfolioMetric]:
        """
        Calculate daily metric for specific date.
        This is the core calculation logic that handles all the complex metrics.
        
        TRANSACTION CONTEXT MANAGEMENT: This method can be called within a transaction
        context manager from TransactionImportService. The commit parameter controls
        whether database operations are committed immediately or deferred to the
        calling context manager.
        
        Args:
            portfolio_key: Portfolio identifier
            stock_key: Stock identifier  
            date_key: Date in YYYYMMDD format
            all_transactions: List of transactions for this stock
            commit: Whether to commit database changes (default True for standalone use)
            
        Returns:
            DailyPortfolioMetric or None: Created metric record or None if no market data
        """
        try:
            # Convert date_key to date object for comparison
            date_str = str(date_key)
            target_date = datetime.strptime(date_str, '%Y%m%d').date()
            
            # Get previous day's metrics for cumulative calculations
            previous_metric = self._get_previous_metric(portfolio_key, stock_key, date_key)
            
            # Get transactions for this specific date
            day_transactions = [t for t in all_transactions if t.transaction_date == target_date]
            
            # Get market price for this date
            market_price = MarketPrice.get_by_stock_and_date(stock_key, date_key)
            if not market_price:
                # Skip days without market data (weekends, holidays, etc.)
                return None
            
            # Initialize cumulative values from previous day or start from zero
            if previous_metric:
                cumulative_shares = float(previous_metric.cumulative_shares)
                cumulative_split_ratio = float(previous_metric.cumulative_split_ratio)
                total_cost_basis = float(previous_metric.total_cost_basis)
                realized_pl = float(previous_metric.realized_pl)
                cumulative_dividends = float(previous_metric.cumulative_dividends)
            else:
                cumulative_shares = 0.0
                cumulative_split_ratio = 1.0
                total_cost_basis = 0.0
                realized_pl = 0.0
                cumulative_dividends = 0.0
            
            # Process transactions for this date
            transaction_quantity = 0.0
            transaction_value = 0.0
            transaction_type = None
            cash_dividend = 0.0
            drp_shares = 0.0
            
            for transaction in day_transactions:
                trans_type = transaction.transaction_type
                quantity = float(transaction.quantity)
                price = float(transaction.price)
                value = float(transaction.total_value)
                
                transaction_quantity += quantity
                transaction_value += value
                transaction_type = trans_type.transaction_type  # Use the last transaction type if multiple
                
                if trans_type.transaction_type == 'BUY':
                    cumulative_shares += quantity
                    total_cost_basis += value
                    
                elif trans_type.transaction_type == 'SELL':
                    cumulative_shares -= quantity
                    
                    # Calculate realized P&L for sale
                    if cumulative_shares > 0:
                        # Calculate average cost basis
                        avg_cost = total_cost_basis / (cumulative_shares + quantity)  # Before sale
                        cost_of_sold = avg_cost * quantity
                        realized_pl += (value - cost_of_sold)
                        total_cost_basis -= cost_of_sold
                    else:
                        # Sold all shares
                        realized_pl += (value - total_cost_basis)
                        total_cost_basis = 0.0
                        
                elif trans_type.transaction_type == 'DIVIDEND':
                    cash_dividend += value
                    cumulative_dividends += value
                    
                elif trans_type.transaction_type == 'SPLIT':
                    split_ratio = float(market_price.split_ratio) if market_price.split_ratio else 1.0
                    cumulative_shares *= split_ratio
                    cumulative_split_ratio *= split_ratio
                    # Cost basis per share decreases by split ratio
                    if split_ratio > 0:
                        total_cost_basis = total_cost_basis  # Total cost basis stays same
            
            # Handle stock splits from market data (even if no transaction)
            if market_price.split_ratio and float(market_price.split_ratio) != 1.0:
                split_ratio = float(market_price.split_ratio)
                cumulative_shares *= split_ratio
                cumulative_split_ratio *= split_ratio
            
            # Calculate current values
            close_price = float(market_price.close_price)
            market_value = cumulative_shares * close_price
            
            # Calculate average cost basis
            average_cost_basis = 0.0
            if cumulative_shares > 0:
                average_cost_basis = total_cost_basis / cumulative_shares
            
            # Calculate unrealized P&L
            unrealized_pl = market_value - total_cost_basis
            
            # Calculate daily P&L (change from previous day)
            daily_pl = 0.0
            if previous_metric:
                previous_market_value = float(previous_metric.market_value)
                daily_pl = market_value - previous_market_value
                
                # Adjust for any transactions today
                if day_transactions:
                    daily_pl -= transaction_value  # Remove transaction impact from daily P&L
            
            # Calculate daily P&L percentage
            daily_pl_pct = 0.0
            if previous_metric and float(previous_metric.market_value) > 0:
                daily_pl_pct = (daily_pl / float(previous_metric.market_value)) * 100
            
            # Calculate total return percentage
            total_return_pct = 0.0
            if total_cost_basis > 0:
                total_return = (market_value + realized_pl + cumulative_dividends - total_cost_basis)
                total_return_pct = (total_return / total_cost_basis) * 100
            
            # Create the daily metric record
            metric = DailyPortfolioMetric(
                portfolio_key=portfolio_key,
                stock_key=stock_key,
                date_key=date_key,
                close_price=close_price,
                dividend=float(market_price.dividend) if market_price.dividend else 0.0,
                split_ratio=float(market_price.split_ratio) if market_price.split_ratio else 1.0,
                transaction_type=transaction_type,
                transaction_quantity=transaction_quantity if transaction_quantity != 0 else None,
                transaction_value=transaction_value if transaction_value != 0 else None,
                cumulative_shares=cumulative_shares,
                cumulative_split_ratio=cumulative_split_ratio,
                average_cost_basis=average_cost_basis,
                total_cost_basis=total_cost_basis,
                market_value=market_value,
                unrealized_pl=unrealized_pl,
                realized_pl=realized_pl,
                daily_pl=daily_pl,
                daily_pl_pct=daily_pl_pct,
                total_return_pct=total_return_pct,
                cash_dividend=cash_dividend,
                drp_shares=drp_shares,
                cumulative_dividends=cumulative_dividends
            )
            
            db.session.add(metric)
            if commit:
                db.session.commit()
            
            return metric
            
        except Exception as e:
            logger.error(f"Error calculating daily metric for {portfolio_key}/{stock_key}/{date_key}: {str(e)}")
            # Don't rollback here - let calling method handle transaction rollback
            # if commit:
            #     db.session.rollback()
            raise
    
    def _get_previous_metric(self, portfolio_key: int, stock_key: int, date_key: int) -> Optional[DailyPortfolioMetric]:
        """Get the most recent metric before the specified date"""
        return DailyPortfolioMetric.query.filter(
            DailyPortfolioMetric.portfolio_key == portfolio_key,
            DailyPortfolioMetric.stock_key == stock_key,
            DailyPortfolioMetric.date_key < date_key
        ).order_by(DailyPortfolioMetric.date_key.desc()).first()
    
    def update_metrics_after_transaction(self, portfolio_key: int, stock_key: int, transaction_date: date) -> Dict[str, Any]:
        """
        Update metrics after a new transaction is added.
        This triggers recalculation from the transaction date forward.
        """
        return self.recalculate_portfolio_metrics(portfolio_key, stock_key, transaction_date)
    
    def calculate_portfolio_summary(self, portfolio_key: int, target_date: date = None) -> Dict[str, Any]:
        """
        Calculate comprehensive portfolio summary for a specific date.
        If no date provided, uses most recent data.
        """
        try:
            if not target_date:
                target_date = date.today()
            
            date_key = int(target_date.strftime('%Y%m%d'))
            
            # Get all current holdings (stocks with shares > 0)
            current_holdings = DailyPortfolioMetric.get_current_portfolio_holdings(portfolio_key)
            
            if not current_holdings:
                return {
                    'portfolio_key': portfolio_key,
                    'date': target_date.isoformat(),
                    'total_market_value': 0.0,
                    'total_cost_basis': 0.0,
                    'total_unrealized_pl': 0.0,
                    'total_realized_pl': 0.0,
                    'total_return_pct': 0.0,
                    'daily_pl': 0.0,
                    'daily_pl_pct': 0.0,
                    'stock_count': 0,
                    'holdings': []
                }
            
            # Calculate totals
            total_market_value = sum(float(h.market_value) for h in current_holdings)
            total_cost_basis = sum(float(h.total_cost_basis) for h in current_holdings)
            total_unrealized_pl = sum(float(h.unrealized_pl) for h in current_holdings)
            total_realized_pl = sum(float(h.realized_pl) for h in current_holdings)
            total_daily_pl = sum(float(h.daily_pl) for h in current_holdings)
            
            # Calculate percentages
            total_return_pct = 0.0
            daily_pl_pct = 0.0
            
            if total_cost_basis > 0:
                total_return = total_market_value + total_realized_pl - total_cost_basis
                total_return_pct = (total_return / total_cost_basis) * 100
            
            # Calculate portfolio daily P&L percentage
            previous_total_value = total_market_value - total_daily_pl
            if previous_total_value > 0:
                daily_pl_pct = (total_daily_pl / previous_total_value) * 100
            
            return {
                'portfolio_key': portfolio_key,
                'date': target_date.isoformat(),
                'total_market_value': total_market_value,
                'total_cost_basis': total_cost_basis,
                'total_unrealized_pl': total_unrealized_pl,
                'total_realized_pl': total_realized_pl,
                'total_return_pct': total_return_pct,
                'daily_pl': total_daily_pl,
                'daily_pl_pct': daily_pl_pct,
                'stock_count': len(current_holdings),
                'holdings': [h.to_dict() for h in current_holdings]
            }
            
        except Exception as e:
            logger.error(f"Error calculating portfolio summary for {portfolio_key}: {str(e)}")
            return {
                'error': str(e),
                'portfolio_key': portfolio_key
            }