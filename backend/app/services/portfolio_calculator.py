"""
Portfolio Calculator Service - FIFO/LIFO/HIFO Calculations
Handles all portfolio profit/loss calculations and tax lot matching
"""

from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum
import logging
from app.models import Transaction, Stock
from app import db

logger = logging.getLogger(__name__)


class MatchingMethod(Enum):
    """Tax lot matching methods for realised profit/loss calculations"""
    FIFO = 'fifo'  # First In, First Out
    LIFO = 'lifo'  # Last In, First Out
    HIFO = 'hifo'  # Highest In, First Out


class TransactionMatch:
    """Represents a transaction with tracking for remaining quantities"""
    
    def __init__(self, transaction: Transaction):
        self.id = transaction.id
        self.stock_id = transaction.stock_id
        self.date = transaction.date
        self.quantity = transaction.quantity
        self.price = transaction.price
        self.transaction_type = transaction.transaction_type.upper()
        self.buy_remainder = 0.0  # Tracks how much of this buy has been matched
        self.sell_remainder = 0.0  # Tracks how much of this sell has been matched
        
    @property
    def available_quantity(self) -> float:
        """Get remaining unmatched quantity"""
        if self.transaction_type == 'BUY':
            return self.quantity - self.buy_remainder
        elif self.transaction_type == 'SELL':
            return self.quantity - self.sell_remainder
        return 0.0
    
    def consume_quantity(self, amount: float):
        """Mark quantity as consumed/matched"""
        if self.transaction_type == 'BUY':
            self.buy_remainder += amount
        elif self.transaction_type == 'SELL':
            self.sell_remainder += amount


class PortfolioCalculator:
    """
    Service for calculating portfolio metrics including:
    - Realised profit/loss using FIFO/LIFO/HIFO methods
    - Unrealised profit/loss
    - Cost basis calculations
    - Tax lot matching
    """
    
    def __init__(self):
        pass
    
    # ============= CORE CALCULATION METHODS =============
    
    def calculate_realised_pl_for_stock(self, stock_id: int, method: MatchingMethod) -> List[Dict]:
        """
        Calculate realised profit/loss for a specific stock using the specified matching method.
        
        Args:
            stock_id: Database ID of the stock
            method: Tax lot matching method (FIFO/LIFO/HIFO)
            
        Returns:
            List[Dict]: List of matched transactions with P&L calculations
        """
        try:
            # Get all buy and sell transactions for this stock
            transactions = Transaction.get_by_stock(stock_id)
            if not transactions:
                return []
            
            # Convert to TransactionMatch objects
            transaction_matches = [TransactionMatch(t) for t in transactions]
            
            # Separate buys and sells
            buys = [tm for tm in transaction_matches if tm.transaction_type == 'BUY']
            sells = [tm for tm in transaction_matches if tm.transaction_type == 'SELL']
            
            if not buys or not sells:
                return []
            
            # Sort sells chronologically (process sells in order they occurred)
            sells.sort(key=lambda x: x.date)
            
            results = []
            
            # Process each sell transaction
            for sell in sells:
                # Find valid buys (must occur before this sell)
                valid_buys = [b for b in buys if b.date < sell.date and b.available_quantity > 0]
                
                if not valid_buys:
                    continue
                
                # Sort buys according to matching method
                if method == MatchingMethod.FIFO:
                    # First In, First Out - oldest buys first
                    valid_buys.sort(key=lambda x: x.date)
                elif method == MatchingMethod.LIFO:
                    # Last In, First Out - newest buys first
                    valid_buys.sort(key=lambda x: x.date, reverse=True)
                elif method == MatchingMethod.HIFO:
                    # Highest In, First Out - highest price buys first, then by date
                    valid_buys.sort(key=lambda x: (x.price, x.date), reverse=True)
                
                # Match this sell against available buys
                remaining_sell_quantity = sell.quantity
                
                for buy in valid_buys:
                    if remaining_sell_quantity <= 0:
                        break
                    
                    available_buy_quantity = buy.available_quantity
                    if available_buy_quantity <= 0:
                        continue
                    
                    # Calculate matched units
                    matched_units = min(remaining_sell_quantity, available_buy_quantity)
                    
                    # Update remainders
                    buy.consume_quantity(matched_units)
                    remaining_sell_quantity -= matched_units
                    
                    # Calculate P&L for this match
                    purchase_cost = matched_units * buy.price
                    sale_proceeds = matched_units * sell.price
                    realised_pl = sale_proceeds - purchase_cost
                    
                    # Create match record
                    match_record = {
                        'sell_id': sell.id,
                        'buy_id': buy.id,
                        'stock_id': stock_id,
                        'matched_units': matched_units,
                        'buy_price': buy.price,
                        'sell_price': sell.price,
                        'purchase_price': purchase_cost,
                        'realised_pl': realised_pl,
                        'trade_date': sell.date,
                        'method': method.value
                    }
                    
                    results.append(match_record)
                    
                    logger.debug(f"Matched {matched_units} units: Buy {buy.id} @ {buy.price} -> Sell {sell.id} @ {sell.price}, P&L: {realised_pl}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error calculating realised P&L for stock {stock_id}: {str(e)}")
            return []
    
    def calculate_realised_pl_all_stocks(self, method: MatchingMethod) -> Dict[int, List[Dict]]:
        """
        Calculate realised P&L for all stocks using the specified method.
        
        Args:
            method: Tax lot matching method
            
        Returns:
            Dict[int, List[Dict]]: Dictionary mapping stock_id to list of matches
        """
        try:
            # Get all stocks that have transactions
            stocks_with_transactions = db.session.query(Stock.id).join(Transaction).distinct().all()
            stock_ids = [stock[0] for stock in stocks_with_transactions]
            
            results = {}
            for stock_id in stock_ids:
                results[stock_id] = self.calculate_realised_pl_for_stock(stock_id, method)
            
            return results
            
        except Exception as e:
            logger.error(f"Error calculating realised P&L for all stocks: {str(e)}")
            return {}
    
    def save_realised_pl_to_database(self, matches: List[Dict]) -> bool:
        """
        Save realised P&L matches to the database.
        
        Args:
            matches: List of match records to save
            
        Returns:
            bool: Success status
        """
        try:
            for match in matches:
                RealisedPL.create(
                    sell_id=match['sell_id'],
                    buy_id=match['buy_id'],
                    stock_id=match['stock_id'],
                    matched_units=match['matched_units'],
                    buy_price=match['buy_price'],
                    sell_price=match['sell_price'],
                    purchase_price=match['purchase_price'],
                    realised_pl=match['realised_pl'],
                    trade_date=match['trade_date'],
                    method=match['method']
                )
            
            logger.info(f"Saved {len(matches)} realised P&L records to database")
            return True
            
        except Exception as e:
            logger.error(f"Error saving realised P&L to database: {str(e)}")
            db.session.rollback()
            return False
    
    def clear_realised_pl_for_method(self, method: MatchingMethod) -> bool:
        """
        Clear existing realised P&L records for a specific method.
        
        Args:
            method: The matching method to clear
            
        Returns:
            bool: Success status
        """
        try:
            RealisedPL.query.filter_by(method=method.value).delete()
            db.session.commit()
            logger.info(f"Cleared existing realised P&L records for method: {method.value}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing realised P&L records: {str(e)}")
            db.session.rollback()
            return False
    
    # ============= HIGH-LEVEL CALCULATION METHODS =============
    
    def recalculate_realised_pl_for_stock(self, stock_id: int, method: MatchingMethod) -> bool:
        """
        Recalculate and update realised P&L for a specific stock.
        
        Args:
            stock_id: Database ID of the stock
            method: Tax lot matching method
            
        Returns:
            bool: Success status
        """
        try:
            # Clear existing records for this stock and method
            RealisedPL.query.filter_by(stock_id=stock_id, method=method.value).delete()
            
            # Calculate new matches
            matches = self.calculate_realised_pl_for_stock(stock_id, method)
            
            # Save to database
            if matches:
                success = self.save_realised_pl_to_database(matches)
                if success:
                    db.session.commit()
                    logger.info(f"Recalculated realised P&L for stock {stock_id} using {method.value}")
                    return True
            else:
                # No matches found, but clearing was successful
                db.session.commit()
                logger.info(f"No realised P&L matches found for stock {stock_id} using {method.value}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error recalculating realised P&L for stock {stock_id}: {str(e)}")
            db.session.rollback()
            return False
    
    def recalculate_all_realised_pl(self, method: MatchingMethod) -> bool:
        """
        Recalculate realised P&L for all stocks using the specified method.
        
        Args:
            method: Tax lot matching method
            
        Returns:
            bool: Success status
        """
        try:
            # Clear existing records for this method
            if not self.clear_realised_pl_for_method(method):
                return False
            
            # Calculate for all stocks
            all_matches = self.calculate_realised_pl_all_stocks(method)
            
            # Flatten results and save to database
            flat_matches = []
            for stock_id, matches in all_matches.items():
                flat_matches.extend(matches)
            
            if flat_matches:
                success = self.save_realised_pl_to_database(flat_matches)
                if success:
                    db.session.commit()
                    logger.info(f"Recalculated realised P&L for all stocks using {method.value}, {len(flat_matches)} matches")
                    return True
            else:
                # No matches found, but clearing was successful
                db.session.commit()
                logger.info(f"No realised P&L matches found for any stocks using {method.value}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error recalculating all realised P&L: {str(e)}")
            db.session.rollback()
            return False
    
    def calculate_all_methods(self) -> bool:
        """
        Calculate realised P&L using all three methods (FIFO, LIFO, HIFO).
        
        Returns:
            bool: Success status
        """
        try:
            success_count = 0
            
            for method in MatchingMethod:
                if self.recalculate_all_realised_pl(method):
                    success_count += 1
                    logger.info(f"Successfully calculated realised P&L using {method.value}")
                else:
                    logger.error(f"Failed to calculate realised P&L using {method.value}")
            
            success = success_count == len(MatchingMethod)
            
            if success:
                logger.info("Successfully calculated realised P&L using all methods")
            else:
                logger.warning(f"Only {success_count} out of {len(MatchingMethod)} methods completed successfully")
            
            return success
            
        except Exception as e:
            logger.error(f"Error calculating all P&L methods: {str(e)}")
            return False
    
    # ============= UNREALISED P&L CALCULATIONS =============
    
    def calculate_unrealised_pl_for_stock(self, stock_id: int) -> Dict:
        """
        Calculate unrealised profit/loss for a stock based on current holdings.
        
        Args:
            stock_id: Database ID of the stock
            
        Returns:
            Dict: Unrealised P&L information
        """
        try:
            stock = Stock.get_by_id(stock_id)
            if not stock or not stock.current_price:
                return {
                    'stock_id': stock_id,
                    'total_shares': 0.0,
                    'average_cost': 0.0,
                    'current_value': 0.0,
                    'unrealised_pl': 0.0,
                    'unrealised_pl_pct': 0.0
                }
            
            # Get all transactions for this stock
            transactions = Transaction.get_by_stock(stock_id)
            
            # Calculate current holdings
            total_shares = 0.0
            total_cost = 0.0
            
            for transaction in transactions:
                if transaction.transaction_type.lower() == 'buy':
                    total_shares += transaction.quantity
                    total_cost += transaction.quantity * transaction.price
                elif transaction.transaction_type.lower() == 'sell':
                    # For unrealised P&L, we need to adjust cost basis
                    if total_shares > 0:
                        avg_cost = total_cost / total_shares
                        sold_cost = transaction.quantity * avg_cost
                        total_shares -= transaction.quantity
                        total_cost -= sold_cost
            
            # Calculate unrealised P&L
            current_value = total_shares * stock.current_price
            average_cost = total_cost / total_shares if total_shares > 0 else 0.0
            unrealised_pl = current_value - total_cost
            unrealised_pl_pct = (unrealised_pl / total_cost * 100) if total_cost > 0 else 0.0
            
            return {
                'stock_id': stock_id,
                'total_shares': total_shares,
                'average_cost': average_cost,
                'total_cost': total_cost,
                'current_value': current_value,
                'unrealised_pl': unrealised_pl,
                'unrealised_pl_pct': unrealised_pl_pct
            }
            
        except Exception as e:
            logger.error(f"Error calculating unrealised P&L for stock {stock_id}: {str(e)}")
            return {
                'stock_id': stock_id,
                'error': str(e)
            }
    
    # ============= PORTFOLIO SUMMARY METHODS =============
    
    def get_portfolio_summary(self, portfolio_id: int, method: MatchingMethod = MatchingMethod.FIFO) -> Dict:
        """
        Get complete portfolio summary including realised and unrealised P&L.
        
        Args:
            portfolio_id: Database ID of the portfolio
            method: Tax lot matching method for realised P&L
            
        Returns:
            Dict: Complete portfolio summary
        """
        try:
            from app.models import Portfolio
            
            portfolio = Portfolio.get_by_id(portfolio_id)
            if not portfolio:
                return {'error': 'Portfolio not found'}
            
            # Get all stocks in this portfolio
            stock_ids = [stock.id for stock in portfolio.stocks]
            
            if not stock_ids:
                return {
                    'portfolio_id': portfolio_id,
                    'total_realised_pl': 0.0,
                    'total_unrealised_pl': 0.0,
                    'total_current_value': 0.0,
                    'total_cost_basis': 0.0,
                    'stocks': []
                }
            
            # Calculate realised P&L
            total_realised_pl = RealisedPL.get_total_realised_pl(method=method.value)
            
            # Calculate unrealised P&L for each stock
            stock_summaries = []
            total_unrealised_pl = 0.0
            total_current_value = 0.0
            total_cost_basis = 0.0
            
            for stock_id in stock_ids:
                unrealised_data = self.calculate_unrealised_pl_for_stock(stock_id)
                if 'error' not in unrealised_data:
                    stock_summaries.append(unrealised_data)
                    total_unrealised_pl += unrealised_data.get('unrealised_pl', 0.0)
                    total_current_value += unrealised_data.get('current_value', 0.0)
                    total_cost_basis += unrealised_data.get('total_cost', 0.0)
            
            return {
                'portfolio_id': portfolio_id,
                'total_realised_pl': total_realised_pl,
                'total_unrealised_pl': total_unrealised_pl,
                'total_current_value': total_current_value,
                'total_cost_basis': total_cost_basis,
                'total_return': total_realised_pl + total_unrealised_pl,
                'stocks': stock_summaries,
                'calculation_method': method.value
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio summary: {str(e)}")
            return {'error': str(e)}