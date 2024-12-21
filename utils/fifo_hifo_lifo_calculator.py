# File: utils/fifo_hifo_lifo_calclator.py

import sqlite3
from datetime import datetime
from enum import Enum

class MatchingMethod(Enum):
    FIFO = 'fifo'
    LIFO = 'lifo'
    HIFO = 'hifo'

class RealisedPLCalculator:
    def __init__(self, id, stock_id, date, quantity, price, type):
        self.id = id
        self.stock_id = stock_id
        self.date = date
        self.quantity = quantity
        self.price = price
        self.type = type
        self.buy_remainder = 0
        self.sell_remainder = 0
        self.realised_pl = 0.0

def process_stock_matches(transactions, method: MatchingMethod):
    """
    Process stock matches based on the specified method while ensuring temporal consistency.
    Each sell can only be matched with buys that occurred before it.
    
    Args:
        transactions: List of RealisedPLCalculator objects representing trades
        method: MatchingMethod enum specifying the matching strategy (FIFO, LIFO, HIFO)
    
    Returns:
        List of dictionaries containing match details
    """
    # Group transactions by stock_id
    stock_groups = {}
    for t in transactions:
        if t.stock_id not in stock_groups:
            stock_groups[t.stock_id] = []
        stock_groups[t.stock_id].append(t)
    
    results = []
    
    for stock_id, stock_transactions in stock_groups.items():
        # Sort sells chronologically
        sell_orders = sorted(
            [t for t in stock_transactions if t.type == 'SELL'],
            key=lambda x: x.date
        )
        
        # Get all buys for this stock
        all_buys = [t for t in stock_transactions if t.type == 'BUY']
        
        # Process each sell order sequentially
        for sell_order in sell_orders:
            # Filter buys that occurred before this sell
            valid_buys = [b for b in all_buys if b.date < sell_order.date]
            
            # Skip if no valid buys available
            if not valid_buys:
                continue
                
            # Sort the valid buys based on method
            if method == MatchingMethod.FIFO:
                buy_orders = sorted(valid_buys, key=lambda x: x.date)
            elif method == MatchingMethod.LIFO:
                buy_orders = sorted(valid_buys, key=lambda x: x.date, reverse=True)
            else:  # HIFO
                buy_orders = sorted(valid_buys, key=lambda x: (x.price, x.date), reverse=True)
            
            units_to_sell = sell_order.quantity
            current_buy_idx = 0
            
            while units_to_sell > 0 and current_buy_idx < len(buy_orders):
                buy_order = buy_orders[current_buy_idx]
                
                # Check if this buy has remaining units
                available_units = buy_order.quantity - buy_order.buy_remainder
                
                if available_units <= 0:
                    current_buy_idx += 1
                    continue
                
                # Calculate matched units
                matched_units = min(units_to_sell, available_units)
                
                # Update remainders
                buy_order.buy_remainder += matched_units
                units_to_sell -= matched_units
                
                # Calculate profit/loss for this match
                pl_for_match = (
                    (matched_units * sell_order.price) - 
                    (matched_units * buy_order.price)
                )
                
                # Record the match
                results.append({
                    'sell_id': sell_order.id,
                    'buy_id': buy_order.id,
                    'stock_id': stock_id,
                    'matched_units': matched_units,
                    'buy_price': buy_order.price,
                    'sell_price': sell_order.price,
                    'realised_pl': pl_for_match,
                    'trade_date': sell_order.date,
                    'method': method.value
                })
                
                current_buy_idx += 1
    
    return results

def calculate_all_pl_methods(db_path):
    """
    Calculate realised profit/loss using all matching methods and store results in database.
    
    Args:
        db_path: Path to the SQLite database file
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Clear existing data in realised_pl table
    cursor.execute('DELETE FROM realised_pl')
    
    # Get transactions
    cursor.execute('''
    SELECT id, stock_id, date, quantity, price, transaction_type
    FROM transactions
    ORDER BY stock_id, date
    ''')
    
    transactions = []
    for row in cursor.fetchall():
        transactions.append(RealisedPLCalculator(
            id=row[0],
            stock_id=row[1],
            date=row[2],
            quantity=row[3],
            price=row[4],
            type=row[5]
        ))
    
    # Process each method
    for method in MatchingMethod:
        # Use fresh copy of transactions for each method
        method_transactions = [RealisedPLCalculator(
            t.id, t.stock_id, t.date, t.quantity, t.price, t.type
        ) for t in transactions]
        
        results = process_stock_matches(method_transactions, method)
        
        cursor.executemany('''
        INSERT INTO realised_pl (
            sell_id, buy_id, stock_id, matched_units,
            buy_price, sell_price, realised_pl, trade_date, method
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', [
            (r['sell_id'], r['buy_id'], r['stock_id'], r['matched_units'],
            r['buy_price'], r['sell_price'], r['realised_pl'], r['trade_date'],
            r['method'])
            for r in results
        ])
    
    conn.commit()
    conn.close()

# Usage
if __name__ == '__main__':
    calculate_all_pl_methods(r'C:\codingProjects\BNB-Portfolio-Manager\portfolio.db')