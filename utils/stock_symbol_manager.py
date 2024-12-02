# File: utils/stock_symbol_manager.py

import json
import os
import yfinance as yf

class StockSymbolManager:
    def __init__(self, config_file='stock_symbols.json'):
        self.config_file = config_file
        self.symbols = self.load_symbols()

    def load_symbols(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                symbols = json.load(f)
                # Ensure 'stock_splits' exists for all symbols
                for symbol_data in symbols.values():
                    if 'stock_splits' not in symbol_data:
                        symbol_data['stock_splits'] = {}
                return symbols
        return {}

    def save_symbols(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.symbols, f, indent=2)

    def add_symbol(self, instrument_code, market_or_index=None):
        if instrument_code not in self.symbols:
            self.symbols[instrument_code] = {
                'market_or_index': market_or_index,
                'stock_name': None,
                'yahoo_symbol': self.construct_yahoo_symbol(instrument_code, market_or_index),
                'stock_splits': {},
                'drp': False
            }
            self.save_symbols()

    def update_symbol(self, instrument_code, market_or_index):
        if instrument_code in self.symbols:
            self.symbols[instrument_code]['market_or_index'] = market_or_index
            self.symbols[instrument_code]['yahoo_symbol'] = self.construct_yahoo_symbol(instrument_code, market_or_index)
            self.refresh_stock_info(instrument_code)
            self.save_symbols()

    def construct_yahoo_symbol(self, instrument_code, market_or_index):
        """
        Construct the Yahoo Finance symbol for a stock.
        
        Args:
            instrument_code (str): The stock's instrument code
            market_or_index (str): The market/index identifier
            
        Returns:
            str: The constructed Yahoo Finance symbol
        """
        if not market_or_index:
            return instrument_code
            
        # Get market suffix from database
        market_suffix = self.db_manager.get_market_code_suffix(market_or_index)
        return f"{instrument_code}{market_suffix}" if market_suffix else instrument_code

    def refresh_stock_info(self, instrument_code):
        if instrument_code in self.symbols:
            yahoo_symbol = self.symbols[instrument_code]['yahoo_symbol']
            try:
                ticker = yf.Ticker(yahoo_symbol)
                info = ticker.info
                self.symbols[instrument_code]['stock_name'] = info.get('longName', 'N/A')
                
                # Fetch and update stock splits
                splits = ticker.splits
                for date, ratio in splits.items():
                    date_str = date.strftime('%Y-%m-%d')
                    self.symbols[instrument_code]['stock_splits'][date_str] = ratio
                
                self.save_symbols()
                return True
            except Exception as e:
                print(f"Error refreshing stock info for {yahoo_symbol}: {str(e)}")
                return False
        return False

    def get_yahoo_symbol(self, instrument_code):
        return self.symbols.get(instrument_code, {}).get('yahoo_symbol', instrument_code)

    def get_all_symbols(self):
        return self.symbols

    def get_market_codes(self):
        return self.market_codes

    def set_drp(self, instrument_code, drp_status):
        if instrument_code in self.symbols:
            self.symbols[instrument_code]['drp'] = bool(drp_status)
            self.save_symbols()

    def add_stock_split(self, instrument_code, date, ratio):
        if instrument_code in self.symbols:
            if 'stock_splits' not in self.symbols[instrument_code]:
                self.symbols[instrument_code]['stock_splits'] = {}
            self.symbols[instrument_code]['stock_splits'][date] = ratio
            self.save_symbols()

    def remove_stock_split(self, instrument_code, date):
        if instrument_code in self.symbols and 'stock_splits' in self.symbols[instrument_code]:
            if date in self.symbols[instrument_code]['stock_splits']:
                del self.symbols[instrument_code]['stock_splits'][date]
                self.save_symbols()