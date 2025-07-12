-- BNB Portfolio Manager Database Views
-- Views for Portfolio Dashboard Data
-- Created: 2025-01-06

-- =============================================
-- PORTFOLIO DASHBOARD VIEWS
-- =============================================

-- Portfolio-level dashboard summary using FACT_DAILY_PORTFOLIO_METRICS
-- This provides aggregated portfolio metrics for the main dashboard
CREATE VIEW V_PORTFOLIO_DASHBOARD_SUMMARY AS
WITH latest_metrics AS (
    -- Get the most recent date for each portfolio
    SELECT 
        portfolio_key,
        MAX(date_key) as latest_date_key
    FROM FACT_DAILY_PORTFOLIO_METRICS
    GROUP BY portfolio_key
),
portfolio_aggregates AS (
    -- Aggregate metrics for each portfolio using latest daily data
    SELECT 
        dm.portfolio_key,
        COUNT(DISTINCT CASE WHEN dm.cumulative_shares > 0.000001 THEN dm.stock_key END) as active_positions,
        SUM(dm.market_value) as total_value,
        SUM(dm.total_cost_basis) as total_cost,
        SUM(dm.unrealized_pl) as unrealized_pl,
        SUM(dm.daily_pl) as day_change,
        SUM(dm.realized_pl) as realized_pl,
        -- Calculate percentage changes
        CASE 
            WHEN SUM(CASE WHEN dm.cumulative_shares > 0.000001 THEN dm.total_cost_basis ELSE 0 END) > 0 THEN
                (SUM(CASE WHEN dm.cumulative_shares > 0.000001 THEN dm.unrealized_pl ELSE 0 END) / 
                 SUM(CASE WHEN dm.cumulative_shares > 0.000001 THEN dm.total_cost_basis ELSE 0 END)) * 100
            ELSE 0
        END as unrealized_pl_percent,
        CASE 
            WHEN (SUM(CASE WHEN dm.cumulative_shares > 0.000001 THEN dm.market_value ELSE 0 END) - 
                  SUM(CASE WHEN dm.cumulative_shares > 0.000001 THEN dm.daily_pl ELSE 0 END)) > 0 THEN
                (SUM(CASE WHEN dm.cumulative_shares > 0.000001 THEN dm.daily_pl ELSE 0 END) / 
                 (SUM(CASE WHEN dm.cumulative_shares > 0.000001 THEN dm.market_value ELSE 0 END) - 
                  SUM(CASE WHEN dm.cumulative_shares > 0.000001 THEN dm.daily_pl ELSE 0 END))) * 100
            ELSE 0
        END as day_change_percent
    FROM FACT_DAILY_PORTFOLIO_METRICS dm
    INNER JOIN latest_metrics lm ON dm.portfolio_key = lm.portfolio_key 
                                 AND dm.date_key = lm.latest_date_key
    GROUP BY dm.portfolio_key
)
SELECT 
    p.portfolio_key,
    p.portfolio_name,
    p.base_currency,
    p.created_at,
    COALESCE(pa.active_positions, 0) as stock_count,
    COALESCE(pa.total_value, 0.0) as total_value,
    COALESCE(pa.total_cost, 0.0) as total_cost,
    COALESCE(pa.unrealized_pl, 0.0) as gain_loss,
    COALESCE(pa.unrealized_pl_percent, 0.0) as gain_loss_percent,
    COALESCE(pa.day_change, 0.0) as day_change,
    COALESCE(pa.day_change_percent, 0.0) as day_change_percent,
    COALESCE(pa.realized_pl, 0.0) as realized_pl
FROM DIM_PORTFOLIO p
LEFT JOIN portfolio_aggregates pa ON p.portfolio_key = pa.portfolio_key
WHERE p.is_active = TRUE;

-- =============================================
-- CURRENT POSITIONS VIEW
-- =============================================

-- Current stock positions for a portfolio using latest daily metrics
-- This provides individual stock position data for the positions table
CREATE VIEW V_CURRENT_POSITIONS AS
WITH latest_metrics AS (
    -- Get the most recent date for each portfolio/stock combination
    SELECT 
        portfolio_key,
        stock_key,
        MAX(date_key) as latest_date_key
    FROM FACT_DAILY_PORTFOLIO_METRICS
    GROUP BY portfolio_key, stock_key
)
SELECT 
    dm.portfolio_key,
    dm.stock_key,
    s.instrument_code as symbol,
    s.name as company_name,
    dm.cumulative_shares as quantity,
    dm.average_cost_basis as avg_cost,
    dm.close_price as current_price,
    dm.market_value,
    dm.total_cost_basis as total_cost,
    dm.unrealized_pl as gain_loss,
    dm.total_return_pct as gain_loss_percent,
    dm.daily_pl as day_change,
    dm.daily_pl_pct as day_change_percent,
    -- Additional useful fields
    dm.cumulative_dividends,
    dm.cash_dividend,
    s.currency,
    s.exchange,
    s.sector,
    s.industry,
    dd.date_value as last_updated_date
FROM FACT_DAILY_PORTFOLIO_METRICS dm
INNER JOIN latest_metrics lm ON dm.portfolio_key = lm.portfolio_key 
                             AND dm.stock_key = lm.stock_key
                             AND dm.date_key = lm.latest_date_key
INNER JOIN DIM_STOCK s ON dm.stock_key = s.stock_key
LEFT JOIN DIM_DATE dd ON dm.date_key = dd.date_key
WHERE dm.cumulative_shares > 0.000001  -- Only active positions
ORDER BY dm.market_value DESC;

-- =============================================
-- RECENT TRANSACTIONS VIEW
-- =============================================

-- Recent transactions across all portfolios
-- This provides transaction history for the recent transactions widget
CREATE VIEW V_RECENT_TRANSACTIONS AS
SELECT 
    t.transaction_key as id,
    t.portfolio_key,
    p.portfolio_name,
    t.stock_key,
    s.instrument_code as symbol,
    s.name as company_name,
    tt.transaction_type as action,
    t.quantity,
    t.price,
    t.total_value,
    t.transaction_date as date,
    t.original_currency,
    t.base_currency,
    t.exchange_rate,
    t.created_at,
    -- Additional calculated fields
    (t.quantity * t.price) as gross_value,
    dd.date_value as formatted_date,
    dd.day_name,
    dd.month_name
FROM FACT_TRANSACTIONS t
INNER JOIN DIM_PORTFOLIO p ON t.portfolio_key = p.portfolio_key
INNER JOIN DIM_STOCK s ON t.stock_key = s.stock_key
INNER JOIN DIM_TRANSACTION_TYPE tt ON t.transaction_type_key = tt.transaction_type_key
LEFT JOIN DIM_DATE dd ON t.date_key = dd.date_key
WHERE p.is_active = TRUE
ORDER BY t.transaction_date DESC, t.created_at DESC;

-- =============================================
-- PORTFOLIO PERFORMANCE HISTORY VIEW
-- =============================================

-- Historical portfolio performance for charts and analytics
-- This provides time-series data for performance visualization
CREATE VIEW V_PORTFOLIO_PERFORMANCE_HISTORY AS
WITH daily_portfolio_totals AS (
    SELECT 
        dm.portfolio_key,
        dm.date_key,
        dd.date_value,
        SUM(CASE WHEN dm.cumulative_shares > 0.000001 THEN dm.market_value ELSE 0 END) as total_value,
        SUM(CASE WHEN dm.cumulative_shares > 0.000001 THEN dm.total_cost_basis ELSE 0 END) as total_cost,
        SUM(CASE WHEN dm.cumulative_shares > 0.000001 THEN dm.unrealized_pl ELSE 0 END) as unrealized_pl,
        SUM(CASE WHEN dm.cumulative_shares > 0.000001 THEN dm.daily_pl ELSE 0 END) as daily_pl,
        SUM(CASE WHEN dm.cumulative_shares > 0.000001 THEN dm.realized_pl ELSE 0 END) as realized_pl,
        COUNT(CASE WHEN dm.cumulative_shares > 0.000001 THEN 1 END) as active_positions
    FROM FACT_DAILY_PORTFOLIO_METRICS dm
    INNER JOIN DIM_DATE dd ON dm.date_key = dd.date_key
    GROUP BY dm.portfolio_key, dm.date_key, dd.date_value
)
SELECT 
    p.portfolio_key,
    p.portfolio_name,
    p.base_currency,
    dpt.date_key,
    dpt.date_value,
    dpt.total_value,
    dpt.total_cost,
    dpt.unrealized_pl,
    dpt.daily_pl,
    dpt.realized_pl,
    dpt.active_positions,
    -- Calculate percentage returns
    CASE 
        WHEN dpt.total_cost > 0 THEN (dpt.unrealized_pl / dpt.total_cost) * 100
        ELSE 0
    END as unrealized_pl_percent,
    -- Calculate cumulative return from start
    CASE 
        WHEN dpt.total_cost > 0 THEN ((dpt.total_value - dpt.total_cost) / dpt.total_cost) * 100
        ELSE 0
    END as cumulative_return_percent
FROM DIM_PORTFOLIO p
INNER JOIN daily_portfolio_totals dpt ON p.portfolio_key = dpt.portfolio_key
WHERE p.is_active = TRUE
ORDER BY p.portfolio_key, dpt.date_value DESC;

-- =============================================
-- INDEXES FOR VIEW PERFORMANCE
-- =============================================

-- Additional indexes to optimize view performance
-- These complement the existing indexes in schema.sql

-- Optimize portfolio dashboard summary queries
CREATE INDEX IF NOT EXISTS idx_daily_metrics_portfolio_date_active 
ON FACT_DAILY_PORTFOLIO_METRICS(portfolio_key, date_key) 
WHERE cumulative_shares > 0.000001;

-- Optimize recent transactions queries
CREATE INDEX IF NOT EXISTS idx_transactions_date_portfolio 
ON FACT_TRANSACTIONS(transaction_date DESC, portfolio_key);

-- Optimize position queries
CREATE INDEX IF NOT EXISTS idx_daily_metrics_active_positions 
ON FACT_DAILY_PORTFOLIO_METRICS(portfolio_key, stock_key, date_key) 
WHERE cumulative_shares > 0.000001;