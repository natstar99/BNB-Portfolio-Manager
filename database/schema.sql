-- File: database/schema.sql

-- Portfolios table
CREATE TABLE IF NOT EXISTS portfolios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Stocks table
CREATE TABLE IF NOT EXISTS stocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    yahoo_symbol TEXT NOT NULL,
    instrument_code TEXT NOT NULL,
    name TEXT,
    current_price REAL,
    last_updated DATETIME,
    market_or_index TEXT,
    market_suffix TEXT,
    verification_status TEXT DEFAULT 'pending', -- tracks verification status (pending, verified, failed)
    drp INTEGER DEFAULT 0,
    UNIQUE(yahoo_symbol, instrument_code),
    FOREIGN KEY (market_or_index) REFERENCES market_codes(market_or_index)
);

-- Portfolio_Stocks table (for many-to-many relationship)
CREATE TABLE IF NOT EXISTS portfolio_stocks (
    portfolio_id INTEGER,
    stock_id INTEGER,
    PRIMARY KEY (portfolio_id, stock_id),
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE,
    FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE
);

-- Transactions table
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER,
    date DATETIME NOT NULL,
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    transaction_type TEXT NOT NULL,
    FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE
);

-- Realised Profit/Loss table
CREATE TABLE IF NOT EXISTS realised_pl (
    sell_id INTEGER,
    buy_id INTEGER,
    stock_id INTEGER,
    matched_units REAL,
    buy_price REAL,
    sell_price REAL,
    realised_pl REAL,
    trade_date DATETIME,
    method TEXT CHECK(method IN ('fifo', 'lifo', 'hifo')),
    FOREIGN KEY (sell_id) REFERENCES transactions(id),
    FOREIGN KEY (buy_id) REFERENCES transactions(id),
    FOREIGN KEY (stock_id) REFERENCES stocks(id)
);

-- Stock_Splits table
CREATE TABLE IF NOT EXISTS stock_splits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER,
    date DATE NOT NULL,
    ratio REAL NOT NULL,
    verified_source TEXT,      -- New: indicates if split came from Yahoo or manual entry
    verification_date DATETIME, -- New: when the split was verified
    FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE
);

-- Historical_Prices table
CREATE TABLE IF NOT EXISTS historical_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER NOT NULL,
    date DATE NOT NULL,
    open_price REAL,
    high_price REAL,
    low_price REAL,
    close_price REAL,
    volume INTEGER,
    dividend REAL,
    split_ratio REAL,
    FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE,
    UNIQUE(stock_id, date)
);

-- Portfolio Metrics table for real-time position tracking
CREATE TABLE IF NOT EXISTS portfolio_metrics (
    metric_index INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER NOT NULL,
    yahoo_symbol TEXT,
    date DATE,
    close_price REAL,
    dividend REAL DEFAULT 0.0,
    drp_flag INTEGER DEFAULT 0,
    split_ratio REAL DEFAULT 1.0,
    cumulative_split_ratio REAL DEFAULT 1.0,
    transaction_type TEXT,
    quantity REAL,
    price REAL,
    transaction_quantity_delta REAL,
    total_bought_quantity REAL DEFAULT 0.0,
    total_sold_quantity REAL DEFAULT 0.0,
    net_transaction_quantity REAL,
    total_shares_owned REAL,
    weighted_avg_purchase_price REAL,
    weighted_avg_sale_price REAL,
    cumulative_buy_value REAL DEFAULT 0.0,
    cumulative_sell_value REAL DEFAULT 0.0,
    cost_basis REAL DEFAULT 0.0,
    cash_dividend REAL DEFAULT 0.0,
    cash_dividends_total REAL DEFAULT 0.0,
    drp_share REAL DEFAULT 0.0,
    drp_shares_total REAL DEFAULT 0.0,
    market_value REAL DEFAULT 0.0,
    daily_pl REAL DEFAULT 0.0,
    daily_pl_pct REAL DEFAULT 0.0,
    realised_pl REAL DEFAULT 0.0,
    unrealised_pl REAL DEFAULT 0.0,
    total_return REAL DEFAULT 0.0,
    total_return_pct REAL DEFAULT 0.0,
    cumulative_return_pct REAL DEFAULT 0.0,
    last_updated DATETIME,
    FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE,
    UNIQUE(stock_id, date)
);

-- Create indices for common queries
CREATE INDEX IF NOT EXISTS idx_portfolio_metrics_stock_date 
    ON portfolio_metrics(stock_id, date);
CREATE INDEX IF NOT EXISTS idx_portfolio_metrics_date 
    ON portfolio_metrics(date);

-- Market_Codes table
CREATE TABLE IF NOT EXISTS market_codes (
    market_or_index TEXT NOT NULL PRIMARY KEY,
    market_suffix TEXT NOT NULL UNIQUE
);

-- Yahoo market codes
INSERT OR IGNORE INTO market_codes (market_or_index, market_suffix) VALUES
('Argentina - Buenos Aires Stock Exchange (BYMA)', '.BA'),
('Australia - Australian Stock Exchange', '.AX'),
('Austria - Vienna Stock Exchange', '.VI'),
('Belgium - Euronext Brussels', '.BR'),
('Brazil - Sao Paolo Stock Exchange (BOVESPA)', '.SA'),
('Canada - Canadian Securities Exchange Toronto Stock Exchange', '.CN'),
('Canada - NEO Exchange', '.NE'),
('Canada - Toronto Stock Exchange', '.TO'),
('Canada - TSX Venture Exchange (TSXV)', '.V'),
('Chile - Santiago Stock Exchange', '.SN'),
('China - Shanghai Stock Exchange', '.SS'),
('China - Shenzhen Stock Exchange', '.SZ'),
('Czech Republic - Prague Stock Exchange Index', '.PR'),
('Denmark - Nasdaq OMX Copenhagen', '.CO'),
('Egypt - Egyptian Exchange Index (EGID)', '.CA'),
('Estonia - Nasdaq OMX Tallinn', '.TL'),
('Finland - Nasdaq OMX Helsinki', '.HE'),
('France - Euronext', '.NX'),
('France - Euronext Paris', '.PA'),
('Germany - Berlin Stock Exchange', '.BE'),
('Germany - Bremen Stock Exchange', '.BM'),
('Germany - Dusseldorf Stock Exchange', '.DU'),
('Germany - Frankfurt Stock Exchange', '.F'),
('Germany - Hamburg Stock Exchange', '.HM'),
('Germany - Hanover Stock Exchange', '.HA'),
('Germany - Munich Stock Exchange', '.MU'),
('Germany - Stuttgart Stock Exchange', '.SG'),
('Germany - Deutsche Boerse XETRA', '.DE'),
('Global - Currency Rates', ''),
('Greece - Athens Stock Exchange (ATHEX)', '.AT'),
('Hong Kong - Hong Kong Stock Exchange (HKEX)', '.HK'),
('Hungary - Budapest Stock Exchange', '.BD'),
('Iceland - Nasdaq OMX Iceland', '.IC'),
('India - Bombay Stock Exchange', '.BO'),
('India - National Stock Exchange of India', '.NS'),
('Indonesia - Indonesia Stock Exchange (IDX)', '.JK'),
('Ireland - Euronext Dublin', '.IR'),
('Israel - Tel Aviv Stock Exchange', '.TA'),
('Italy - EuroTLX', '.TI'),
('Italy - Italian Stock Exchange, former Milano', '.MI'),
('Japan - Nikkei Indices', ''),
('Japan - Tokyo Stock Exchange', '.T'),
('Latvia - Nasdaq OMX Riga', '.RG'),
('Lithuania - Nasdaq OMX Vilnius', '.VS'),
('Malaysia - Malaysian Stock Exchange', '.KL'),
('Mexico - Mexico Stock Exchange (BMV)', '.MX'),
('Netherlands - Euronext Amsterdam', '.AS'),
('New Zealand - New Zealand Stock Exchange (NZX)', '.NZ'),
('Norway - Oslo Stock Exchange', '.OL'),
('Portugal - Euronext Lisbon', '.LS'),
('Qatar - Qatar Stock Exchange', '.QA'),
('Russia - Moscow Exchange (MOEX)', '.ME'),
('Singapore - Singapore Stock Exchange', '.SI'),
('South Africa - Johannesburg Stock Exchange', '.Jo'),
('South Korea - Korea Stock Exchange', '.KS'),
('South Korea - KOSDAQ', '.KQ'),
('Spain - Madrid SE C.A.T.S.', '.MC'),
('Saudi Arabia - Saudi Stock Exchange (Tadawul)', '.SAU'),
('Sweden - Nasdaq OMX Stockholm', '.ST'),
('Switzerland - Swiss Exchange (SIX)', '.SW'),
('Taiwan - Taiwan OTC Exchange', '.TWO'),
('Taiwan - Taiwan Stock Exchange (TWSE)', '.TW'),
('Thailand - Stock Exchange of Thailand (SET)', '.BK'),
('Turkey - Borsa İstanbul', '.IS'),
('United Kingdom - FTSE Indices', ''),
('United Kingdom - London Stock Exchange', '.L'),
('United Kingdom - London Stock Exchange', '.IL'),
('United States of America - Chicago Board of Trade (CBOT)', '.CBT'),
('United States of America - Chicago Mercantile Exchange (CME)', '.CME'),
('United States of America - Dow Jones Indexes', ''),
('United States of America - NASDAQ Stock Exchange', ''),
('United States of America - ICE Futures US, former New York Board of Trade', '.NYB'),
('United States of America - New York Commodities Exchange (COMEX)', '.CMX'),
('United States of America - New York Mercantile Exchange (NYMEX)', '.NYM'),
('United States of America - Options Price Reporting Authority (OPRA)', ''),
('United States of America - OTC Bulletin Board Market', ''),
('United States of America - OTC Markets Group', ''),
('United States of America - S & P Indices', ''),
('Venezuela - Caracas Stock Exchange', '.CR');