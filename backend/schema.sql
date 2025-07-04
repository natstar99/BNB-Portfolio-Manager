-- BNB Portfolio Manager Database Schema
-- Kimball Star Schema Implementation
-- Created: 2025-01-04

-- =============================================
-- STAGING TABLES
-- =============================================

-- Raw transaction staging table for imports
CREATE TABLE STG_RAW_TRANSACTIONS (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_batch_id VARCHAR(50) NOT NULL,
    portfolio_id INTEGER NOT NULL,
    raw_date TEXT NOT NULL,
    raw_instrument_code TEXT NOT NULL,
    raw_transaction_type TEXT NOT NULL,
    raw_quantity TEXT NOT NULL,
    raw_price TEXT NOT NULL,
    raw_currency TEXT,
    import_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    processed_flag BOOLEAN DEFAULT FALSE,
    validation_errors TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- =============================================
-- DIMENSION TABLES
-- =============================================

-- Stock dimension table
CREATE TABLE DIM_STOCK (
    stock_key INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_code VARCHAR(20) NOT NULL UNIQUE,
    yahoo_symbol VARCHAR(20) NOT NULL,
    name VARCHAR(255) NOT NULL,
    market_key INTEGER,
    sector VARCHAR(100),
    industry VARCHAR(100),
    exchange VARCHAR(50),
    currency VARCHAR(10) DEFAULT 'USD',
    country VARCHAR(50),
    market_cap DECIMAL(20, 2),
    verification_status VARCHAR(20) DEFAULT 'pending',
    current_price DECIMAL(10, 4) DEFAULT 0.0,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (market_key) REFERENCES DIM_YAHOO_MARKET_CODES(market_key)
);

-- Portfolio dimension table
CREATE TABLE DIM_PORTFOLIO (
    portfolio_key INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_name VARCHAR(255) NOT NULL,
    description TEXT,
    base_currency VARCHAR(10) DEFAULT 'USD',
    portfolio_type VARCHAR(50) DEFAULT 'INVESTMENT',
    created_by VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Transaction type dimension table
CREATE TABLE DIM_TRANSACTION_TYPE (
    transaction_type_key INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_type VARCHAR(20) NOT NULL UNIQUE,
    description VARCHAR(255),
    is_buy_type BOOLEAN DEFAULT FALSE,
    is_sell_type BOOLEAN DEFAULT FALSE,
    affects_quantity BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE
);

-- Date dimension table for analytics
CREATE TABLE DIM_DATE (
    date_key INTEGER PRIMARY KEY,
    date_value DATE NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    day_name VARCHAR(20) NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    is_weekend BOOLEAN DEFAULT FALSE,
    is_holiday BOOLEAN DEFAULT FALSE,
    fiscal_year INTEGER,
    fiscal_quarter INTEGER
);

-- Yahoo Finance market codes dimension table
CREATE TABLE DIM_YAHOO_MARKET_CODES (
    market_key INTEGER PRIMARY KEY AUTOINCREMENT,
    market_or_index TEXT NOT NULL UNIQUE,
    market_suffix TEXT
);

-- =============================================
-- FACT TABLES
-- =============================================

-- Main transaction fact table
CREATE TABLE FACT_TRANSACTIONS (
    transaction_key INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_key INTEGER NOT NULL,
    portfolio_key INTEGER NOT NULL,
    transaction_type_key INTEGER NOT NULL,
    date_key INTEGER NOT NULL,
    
    -- Transaction details
    transaction_date DATE NOT NULL,
    quantity DECIMAL(15, 6) NOT NULL,
    price DECIMAL(10, 4) NOT NULL,
    total_value DECIMAL(20, 2) NOT NULL,
    
    -- Currency information
    original_currency VARCHAR(10) DEFAULT 'USD',
    base_currency VARCHAR(10) DEFAULT 'USD',
    exchange_rate DECIMAL(10, 6) DEFAULT 1.0,
    
    -- Calculated fields
    total_value_base DECIMAL(20, 2) NOT NULL,
    
    -- Audit fields
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    FOREIGN KEY (stock_key) REFERENCES DIM_STOCK(stock_key),
    FOREIGN KEY (portfolio_key) REFERENCES DIM_PORTFOLIO(portfolio_key),
    FOREIGN KEY (transaction_type_key) REFERENCES DIM_TRANSACTION_TYPE(transaction_type_key),
    FOREIGN KEY (date_key) REFERENCES DIM_DATE(date_key)
);

-- =============================================
-- PORTFOLIO POSITIONS (SNAPSHOT TABLE)
-- =============================================

-- Current portfolio positions
CREATE TABLE PORTFOLIO_POSITIONS (
    position_key INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_key INTEGER NOT NULL,
    stock_key INTEGER NOT NULL,
    
    -- Position details
    current_quantity DECIMAL(15, 6) NOT NULL DEFAULT 0,
    average_cost DECIMAL(10, 4) NOT NULL DEFAULT 0,
    total_cost DECIMAL(20, 2) NOT NULL DEFAULT 0,
    current_price DECIMAL(10, 4) NOT NULL DEFAULT 0,
    current_value DECIMAL(20, 2) NOT NULL DEFAULT 0,
    
    -- P&L information
    unrealized_pl DECIMAL(20, 2) NOT NULL DEFAULT 0,
    unrealized_pl_percent DECIMAL(10, 4) NOT NULL DEFAULT 0,
    
    -- Audit fields
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    FOREIGN KEY (portfolio_key) REFERENCES DIM_PORTFOLIO(portfolio_key),
    FOREIGN KEY (stock_key) REFERENCES DIM_STOCK(stock_key),
    UNIQUE(portfolio_key, stock_key)
);

-- Portfolio-specific stock configuration
CREATE TABLE PORTFOLIO_STOCK_CONFIG (
    config_key INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_key INTEGER NOT NULL,
    stock_key INTEGER NOT NULL,
    drp_enabled BOOLEAN DEFAULT FALSE,  -- Dividend Reinvestment Plan
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_key) REFERENCES DIM_PORTFOLIO(portfolio_key),
    FOREIGN KEY (stock_key) REFERENCES DIM_STOCK(stock_key),
    UNIQUE(portfolio_key, stock_key)
);

-- =============================================
-- INDEXES FOR PERFORMANCE
-- =============================================

-- Staging table indexes
CREATE INDEX idx_stg_raw_batch ON STG_RAW_TRANSACTIONS(import_batch_id);
CREATE INDEX idx_stg_raw_processed ON STG_RAW_TRANSACTIONS(processed_flag);
CREATE INDEX idx_stg_raw_portfolio ON STG_RAW_TRANSACTIONS(portfolio_id);

-- Dimension table indexes
CREATE INDEX idx_dim_stock_instrument ON DIM_STOCK(instrument_code);
CREATE INDEX idx_dim_stock_yahoo ON DIM_STOCK(yahoo_symbol);
CREATE INDEX idx_dim_portfolio_name ON DIM_PORTFOLIO(portfolio_name);
CREATE INDEX idx_dim_transaction_type ON DIM_TRANSACTION_TYPE(transaction_type);
CREATE INDEX idx_dim_date_value ON DIM_DATE(date_value);

-- Fact table indexes
CREATE INDEX idx_fact_trans_stock ON FACT_TRANSACTIONS(stock_key);
CREATE INDEX idx_fact_trans_portfolio ON FACT_TRANSACTIONS(portfolio_key);
CREATE INDEX idx_fact_trans_date ON FACT_TRANSACTIONS(date_key);
CREATE INDEX idx_fact_trans_type ON FACT_TRANSACTIONS(transaction_type_key);
CREATE INDEX idx_fact_trans_date_value ON FACT_TRANSACTIONS(transaction_date);

-- Position table indexes
CREATE INDEX idx_positions_portfolio ON PORTFOLIO_POSITIONS(portfolio_key);
CREATE INDEX idx_positions_stock ON PORTFOLIO_POSITIONS(stock_key);

-- Market codes table indexes
CREATE INDEX idx_market_codes_suffix ON DIM_YAHOO_MARKET_CODES(market_suffix);

-- Portfolio stock config indexes
CREATE INDEX idx_portfolio_stock_config_portfolio ON PORTFOLIO_STOCK_CONFIG(portfolio_key);
CREATE INDEX idx_portfolio_stock_config_stock ON PORTFOLIO_STOCK_CONFIG(stock_key);

-- Stock table index for market_key
CREATE INDEX idx_dim_stock_market ON DIM_STOCK(market_key);

-- =============================================
-- INITIAL DATA SETUP
-- =============================================

-- Insert default transaction types
INSERT INTO DIM_TRANSACTION_TYPE (transaction_type, description, is_buy_type, is_sell_type, affects_quantity) VALUES
('BUY', 'Purchase of securities', TRUE, FALSE, TRUE),
('SELL', 'Sale of securities', FALSE, TRUE, TRUE),
('DIVIDEND', 'Dividend payment', FALSE, FALSE, FALSE),
('SPLIT', 'Stock split', FALSE, FALSE, TRUE),
('BONUS', 'Bonus shares', FALSE, FALSE, TRUE),
('RIGHTS', 'Rights issue', FALSE, FALSE, TRUE);

-- Yahoo market codes
INSERT OR IGNORE INTO DIM_YAHOO_MARKET_CODES (market_or_index, market_suffix) VALUES
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

-- No default portfolios - users must explicitly create them
-- This enforces portfolio-first navigation paradigm

-- =============================================
-- VIEWS FOR COMMON QUERIES
-- =============================================

-- Portfolio summary view
CREATE VIEW V_PORTFOLIO_SUMMARY AS
SELECT 
    p.portfolio_key,
    p.portfolio_name,
    COUNT(DISTINCT pos.stock_key) as total_stocks,
    SUM(pos.current_value) as total_value,
    SUM(pos.total_cost) as total_cost,
    SUM(pos.unrealized_pl) as total_unrealized_pl,
    CASE 
        WHEN SUM(pos.total_cost) > 0 THEN 
            (SUM(pos.unrealized_pl) / SUM(pos.total_cost)) * 100 
        ELSE 0 
    END as unrealized_pl_percent
FROM DIM_PORTFOLIO p
LEFT JOIN PORTFOLIO_POSITIONS pos ON p.portfolio_key = pos.portfolio_key
WHERE p.is_active = TRUE
GROUP BY p.portfolio_key, p.portfolio_name;

-- Stock performance view
CREATE VIEW V_STOCK_PERFORMANCE AS
SELECT 
    s.stock_key,
    s.instrument_code,
    s.name,
    s.current_price,
    COUNT(DISTINCT t.portfolio_key) as portfolios_count,
    SUM(CASE WHEN tt.is_buy_type THEN t.quantity ELSE 0 END) as total_bought,
    SUM(CASE WHEN tt.is_sell_type THEN t.quantity ELSE 0 END) as total_sold,
    SUM(CASE WHEN tt.is_buy_type THEN t.total_value_base ELSE 0 END) as total_invested,
    SUM(CASE WHEN tt.is_sell_type THEN t.total_value_base ELSE 0 END) as total_realized
FROM DIM_STOCK s
LEFT JOIN FACT_TRANSACTIONS t ON s.stock_key = t.stock_key
LEFT JOIN DIM_TRANSACTION_TYPE tt ON t.transaction_type_key = tt.transaction_type_key
WHERE s.is_active = TRUE
GROUP BY s.stock_key, s.instrument_code, s.name, s.current_price;

-- Recent transactions view
CREATE VIEW V_RECENT_TRANSACTIONS AS
SELECT 
    t.transaction_key,
    t.transaction_date,
    p.portfolio_name,
    s.instrument_code,
    s.name as stock_name,
    tt.transaction_type,
    t.quantity,
    t.price,
    t.total_value_base
FROM FACT_TRANSACTIONS t
JOIN DIM_STOCK s ON t.stock_key = s.stock_key
JOIN DIM_PORTFOLIO p ON t.portfolio_key = p.portfolio_key
JOIN DIM_TRANSACTION_TYPE tt ON t.transaction_type_key = tt.transaction_type_key
ORDER BY t.transaction_date DESC, t.created_at DESC
LIMIT 100;