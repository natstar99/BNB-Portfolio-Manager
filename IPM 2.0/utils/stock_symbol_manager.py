import json
import os
import yfinance as yf

class StockSymbolManager:
    def __init__(self, config_file='stock_symbols.json'):
        self.config_file = config_file
        self.symbols = self.load_symbols()
        self.market_codes = {
            'Argentina - Buenos Aires Stock Exchange (BYMA)': '.BA',
            'Australia - Australian Stock Exchange': '.AX',
            'Austria - Vienna Stock Exchange': '.VI',
            'Belgium - Euronext Brussels': '.BR',
            'Brazil - Sao Paolo Stock Exchange (BOVESPA)': '.SA',
            'Canada - Canadian Securities Exchange Toronto Stock Exchange': '.CN',
            'Canada - NEO Exchange': '.NE',
            'Canada - Toronto Stock Exchange': '.TO',
            'Canada - TSX Venture Exchange (TSXV)': '.V',
            'Chile - Santiago Stock Exchange': '.SN',
            'China - Shanghai Stock Exchange': '.SS',
            'China - Shenzhen Stock Exchange': '.SZ',
            'Czech Republic - Prague Stock Exchange Index': '.PR',
            'Denmark - Nasdaq OMX Copenhagen': '.CO',
            'Egypt - Egyptian Exchange Index (EGID)': '.CA',
            'Estonia - Nasdaq OMX Tallinn': '.TL',
            'Finland - Nasdaq OMX Helsinki': '.HE',
            'France - Euronext': '.NX',
            'France - Euronext Paris': '.PA',
            'Germany - Berlin Stock Exchange': '.BE',
            'Germany - Bremen Stock Exchange': '.BM',
            'Germany - Dusseldorf Stock Exchange': '.DU',
            'Germany - Frankfurt Stock Exchange': '.F',
            'Germany - Hamburg Stock Exchange': '.HM',
            'Germany - Hanover Stock Exchange': '.HA',
            'Germany - Munich Stock Exchange': '.MU',
            'Germany - Stuttgart Stock Exchange': '.SG',
            'Germany - Deutsche Boerse XETRA': '.DE',
            'Global - Currency Rates': '',
            'Greece - Athens Stock Exchange (ATHEX)': '.AT',
            'Hong Kong - Hong Kong Stock Exchange (HKEX)': '.HK',
            'Hungary - Budapest Stock Exchange': '.BD',
            'Iceland - Nasdaq OMX Iceland': '.IC',
            'India - Bombay Stock Exchange': '.BO',
            'India - National Stock Exchange of India': '.NS',
            'Indonesia - Indonesia Stock Exchange (IDX)': '.JK',
            'Ireland - Euronext Dublin': '.IR',
            'Israel - Tel Aviv Stock Exchange': '.TA',
            'Italy - EuroTLX': '.TI',
            'Italy - Italian Stock Exchange, former Milano': '.MI',
            'Japan - Nikkei Indices': '',
            'Japan - Tokyo Stock Exchange': '.T',
            'Latvia - Nasdaq OMX Riga': '.RG',
            'Lithuania - Nasdaq OMX Vilnius': '.VS',
            'Malaysia - Malaysian Stock Exchange': '.KL',
            'Mexico - Mexico Stock Exchange (BMV)': '.MX',
            'Netherlands - Euronext Amsterdam': '.AS',
            'New Zealand - New Zealand Stock Exchange (NZX)': '.NZ',
            'Norway - Oslo Stock Exchange': '.OL',
            'Portugal - Euronext Lisbon': '.LS',
            'Qatar - Qatar Stock Exchange': '.QA',
            'Russia - Moscow Exchange (MOEX)': '.ME',
            'Singapore - Singapore Stock Exchange': '.SI',
            'South Africa - Johannesburg Stock Exchange': '.Jo',
            'South Korea - Korea Stock Exchange': '.KS',
            'South Korea - KOSDAQ': '.KQ',
            'Spain - Madrid SE C.A.T.S.': '.MC',
            'Saudi Arabia - Saudi Stock Exchange (Tadawul)': '.SAU',
            'Sweden - Nasdaq OMX Stockholm': '.ST',
            'Switzerland - Swiss Exchange (SIX)': '.SW',
            'Taiwan - Taiwan OTC Exchange': '.TWO',
            'Taiwan - Taiwan Stock Exchange (TWSE)': '.TW',
            'Thailand - Stock Exchange of Thailand (SET)': '.BK',
            'Turkey - Borsa İstanbul': '.IS',
            'United Kingdom - FTSE Indices': '',
            'United Kingdom - London Stock Exchange': '.L',
            'United Kingdom - London Stock Exchange': '.IL',
            'United States of America - Chicago Board of Trade (CBOT)': '.CBT',
            'United States of America - Chicago Mercantile Exchange (CME)': '.CME',
            'United States of America - Dow Jones Indexes': '',
            'United States of America - NASDAQ Stock Exchange': '',
            'United States of America - ICE Futures US, former New York Board of Trade': '.NYB',
            'United States of America - New York Commodities Exchange (COMEX)': '.CMX',
            'United States of America - New York Mercantile Exchange (NYMEX)': '.NYM',
            'United States of America - Options Price Reporting Authority (OPRA)': '',
            'United States of America - OTC Bulletin Board Market': '',
            'United States of America - OTC Markets Group': '',
            'United States of America - S & P Indices': '',
            'Venezuela - Caracas Stock Exchange': '.CR',
        }

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
        if not market_or_index:
            return instrument_code
        suffix = self.market_codes.get(market_or_index, "")
        return f"{instrument_code}{suffix}" if suffix else instrument_code

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

    def set_yahoo_symbol(self, instrument_code, yahoo_symbol):
        if instrument_code in self.symbols:
            self.symbols[instrument_code]['yahoo_symbol'] = yahoo_symbol
            self.symbols[instrument_code]['market_or_index'] = ''  # Clear market when manually set
            self.save_symbols()

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