-- File: database/final_metrics.sql

-- Query to calculate and update metrics including split-adjusted values, weighted averages, and returns analysis.
WITH RECURSIVE 
-- First CTE: Gather all relevant dates and base data for the analysis
dates_and_data AS (
    SELECT DISTINCT 
        COALESCE(hp.stock_id, t.stock_id) as stock_id,
        s.yahoo_symbol,
        COALESCE(hp.date, date(t.date)) as date,
        hp.close_price,
        hp.dividend,
        s.drp as drp_flag,
        COALESCE(ss.ratio, 1) as split_ratio,
        t.id as transaction_id,
        t.transaction_type,
        t.quantity,
        t.price,
        -- Calculate row numbers for both forward and reverse chronological order
        ROW_NUMBER() OVER (ORDER BY COALESCE(hp.date, date(t.date)) DESC) as reverse_row_num, -- Order by date DESC
        ROW_NUMBER() OVER (ORDER BY COALESCE(hp.date, date(t.date))) as row_num
    FROM (
        -- Get all unique dates from both historical prices and transactions
        SELECT DISTINCT date FROM historical_prices WHERE stock_id = :stock_id
        UNION
        SELECT DISTINCT date(date) FROM transactions WHERE stock_id = :stock_id
    ) dates
    LEFT JOIN historical_prices hp ON dates.date = hp.date AND hp.stock_id = :stock_id
    LEFT JOIN transactions t ON dates.date = date(t.date) AND t.stock_id = :stock_id
    LEFT JOIN stock_splits ss ON dates.date = ss.date AND ss.stock_id = :stock_id
    LEFT JOIN stocks s ON COALESCE(hp.stock_id, t.stock_id) = s.id
),

-- Second CTE: Calculate cumulative split ratios backwards in time
reverse_split_calc AS (
    -- Base case: Start with most recent date
    SELECT 
        stock_id,
        yahoo_symbol,
        date,
        close_price,
        dividend,
        drp_flag,
        split_ratio,
        COALESCE(split_ratio, 1) as cumulative_split_ratio,
        transaction_id,
        transaction_type,
        quantity,
        price,
        reverse_row_num,
        row_num
    FROM dates_and_data
    WHERE reverse_row_num = 1

    UNION ALL

    -- Recursive case: Work backwards through time
    SELECT 
        d.stock_id,
        d.yahoo_symbol,
        d.date,
        d.close_price,
        d.dividend,
        d.drp_flag,
        d.split_ratio,
        rc.cumulative_split_ratio * COALESCE(d.split_ratio, 1),
        d.transaction_id,
        d.transaction_type,
        d.quantity,
        d.price,
        d.reverse_row_num,
        d.row_num
    FROM dates_and_data d
    JOIN reverse_split_calc rc ON d.reverse_row_num = rc.reverse_row_num + 1
),

-- Third CTE: Calculate running totals forward with split-adjusted values
running_calculations AS (
    -- Base case: Initial values for earliest date
    SELECT 
        stock_id,
        yahoo_symbol,
        date,
        close_price,
        dividend,
        drp_flag,
        split_ratio,
        cumulative_split_ratio,
        transaction_type,
        -- Split-adjusted quantity and price
        CASE 
            WHEN quantity IS NOT NULL THEN quantity * cumulative_split_ratio 
            ELSE NULL 
        END AS adjusted_quantity,
        CASE 
            WHEN price IS NOT NULL THEN price / cumulative_split_ratio 
            ELSE NULL 
        END AS adjusted_price,
        row_num,
        -- Track net transactions
        CASE 
            WHEN transaction_type = 'BUY' THEN quantity * cumulative_split_ratio
            WHEN transaction_type = 'SELL' THEN -quantity * cumulative_split_ratio
            ELSE 0 
        END AS net_transaction_quantity,
        CASE 
            WHEN transaction_type = 'BUY' THEN 
                quantity * cumulative_split_ratio * (price / cumulative_split_ratio)
            ELSE 0 
        END AS total_investment_amount,
        -- Track total shares owned (includes DRP)
        CASE 
            WHEN transaction_type = 'BUY' THEN quantity * cumulative_split_ratio
            WHEN transaction_type = 'SELL' THEN -quantity * cumulative_split_ratio
            ELSE 0 
        END AS total_shares_owned,
        -- Initialise dividend tracking
        CAST(0 AS REAL) AS cash_dividend,
        CAST(0 AS REAL) AS cash_dividends_total,
        CAST(0 AS REAL) AS drp_share,
        CAST(0 AS REAL) AS drp_shares_total,
        -- Initialise realised P/L tracking
        CAST(0 AS REAL) AS realised_pl
    FROM reverse_split_calc
    WHERE row_num = 1
    
    UNION ALL
    
    -- Recursive case: Calculate running totals
    SELECT 
        d.stock_id,
        d.yahoo_symbol,
        d.date,
        d.close_price,
        d.dividend,
        d.drp_flag,
        d.split_ratio,
        d.cumulative_split_ratio,
        d.transaction_type,
        -- Split-adjusted quantity and price
        CASE 
            WHEN d.quantity IS NOT NULL THEN d.quantity * d.cumulative_split_ratio 
            ELSE NULL 
        END,
        CASE 
            WHEN d.price IS NOT NULL THEN d.price / d.cumulative_split_ratio 
            ELSE NULL 
        END,
        d.row_num,
        -- Update cumulative transaction total
        rc.net_transaction_quantity + 
        CASE 
            WHEN d.transaction_type = 'BUY' THEN d.quantity * d.cumulative_split_ratio
            WHEN d.transaction_type = 'SELL' THEN -d.quantity * d.cumulative_split_ratio
            ELSE 0 
        END,
        -- Update total_investment_amount (cumulative sum of BUY transactions)
        rc.total_investment_amount + 
        CASE 
            WHEN d.transaction_type = 'BUY' THEN 
                d.quantity * d.cumulative_split_ratio * (d.price / d.cumulative_split_ratio)
            ELSE 0 
        END,
        -- Update total shares (including DRP)
        rc.total_shares_owned + 
        CASE 
            WHEN d.transaction_type = 'BUY' THEN d.quantity * d.cumulative_split_ratio
            WHEN d.transaction_type = 'SELL' THEN -d.quantity * d.cumulative_split_ratio
            ELSE 
                CASE 
                    WHEN d.dividend > 0 AND d.drp_flag = 1 AND d.close_price > 0 THEN
                        CASE 
                            -- Handle whole vs fractional shares differently
                            WHEN rc.total_shares_owned = FLOOR(rc.total_shares_owned) THEN 
                                FLOOR((d.dividend * rc.total_shares_owned) / d.close_price + 
                                    (rc.drp_shares_total - FLOOR(rc.drp_shares_total)))
                            ELSE (d.dividend * rc.total_shares_owned) / d.close_price
                        END
                    ELSE 0
                END
        END,
        -- Update cash dividend calculations
        CASE 
            WHEN d.dividend > 0 AND d.drp_flag = 0 THEN 
                d.dividend * rc.total_shares_owned
            ELSE 0 
        END,
        rc.cash_dividends_total + 
        CASE 
            WHEN d.dividend > 0 AND d.drp_flag = 0 THEN 
                d.dividend * rc.total_shares_owned
            ELSE 0 
        END,
        -- Update DRP calculations
        CASE 
            WHEN d.dividend > 0 AND d.drp_flag = 1 AND d.close_price > 0 THEN 
                (d.dividend * rc.total_shares_owned) / d.close_price
            ELSE 0 
        END,
        rc.drp_shares_total + 
        CASE 
            WHEN d.dividend > 0 AND d.drp_flag = 1 AND d.close_price > 0 THEN 
                (d.dividend * rc.total_shares_owned) / d.close_price
            ELSE 0 
        END,
        -- Update realised P/L
		rc.realised_pl +
		CASE 
		    WHEN d.transaction_type = 'SELL' THEN
		        -- Get the method-specific realised P/L for this sell transaction
		        COALESCE(
		            (
		                SELECT SUM(rpl.realised_pl)
		                FROM realised_pl rpl
		                WHERE rpl.stock_id = d.stock_id
		                AND rpl.sell_id = d.transaction_id  -- Join on the transaction ID
		                AND rpl.method = :pl_method
		            ),
		            0
		        )
		    ELSE 0
		END +
		CASE 
		    WHEN d.dividend > 0 AND d.drp_flag = 0 THEN 
		        -- Add cash dividends to the realised P/L
		        d.dividend * rc.total_shares_owned
		    ELSE 0
		END
    FROM reverse_split_calc d
    JOIN running_calculations rc ON d.row_num = rc.row_num + 1
),

-- Fourth CTE: to calculate cost_basis from realised_pl table
realised_cost AS (
    SELECT
        stock_id,
        date(trade_date) as trade_date,
        SUM(purchase_price) as cost_basis_variation  -- This represents the total original purchase price of the shares sold on a particular 'SELL' date
    FROM realised_pl
    WHERE method = :pl_method
    GROUP BY stock_id, date(trade_date)
),

-- Fifth CTE: Build a base portfolio_metrics table to include the cost basis variation
base_portfolio_metrics AS (
    SELECT
        NULL as metric_index,
        rc.*,
        
        -- Calculate market value with validation for tiny values
        CASE 
            WHEN (rc.total_shares_owned * rc.close_price) < 0.00001 THEN 
                0
            ELSE 
                (rc.total_shares_owned * rc.close_price)
        END as market_value,
        
        -- Calculate cost_basis_variation, multiplying by -1 for SELL transactions
        -- We only consider it on SELL days to avoid double counting
        COALESCE(
            CASE 
                WHEN rc.transaction_type = 'SELL' THEN -1 * r.cost_basis_variation
                ELSE 0 
            END, 
            0
        ) as cost_basis_variation
        
    FROM running_calculations rc
    LEFT JOIN realised_cost r ON 
        rc.stock_id = r.stock_id 
        AND rc.date = r.trade_date
),

-- Sixth CTE: Calculate core portfolio metrics including cost basis and P/L calculations
portfolio_metrics AS (
    SELECT
        bpm.*,
        
        -- Calculate running sum of cost_basis_variation
        -- This tracks how the cost basis changes over time as shares are sold
        SUM(bpm.cost_basis_variation) OVER (
            PARTITION BY bpm.stock_id 
            ORDER BY bpm.date
        ) as cumulative_cost_basis_variation,
        
        -- Calculate unrealised P/L by comparing current market value against adjusted cost basis
        -- We add (not subtract) the cost_basis_variation because it's stored as a negative value
        (market_value) - 
        (bpm.total_investment_amount + 
         SUM(bpm.cost_basis_variation) OVER (
            PARTITION BY bpm.stock_id 
            ORDER BY bpm.date
         )
        ) as unrealised_pl,
        
        -- Calculate daily P/L by comparing consecutive market values and adjusting for transactions
        CASE
            -- Special handling for the first BUY transaction
            -- We compare the investment amount against the end-of-day market value
            WHEN bpm.transaction_type = 'BUY' AND 
                 NOT EXISTS (
                     SELECT 1 
                     FROM running_calculations rc2 
                     WHERE rc2.date < bpm.date AND rc2.total_shares_owned > 0
                 ) THEN
                ((bpm.adjusted_quantity * bpm.adjusted_price) - bpm.market_value) * -1
            
            -- For all other days, calculate the change in market value
            -- while adjusting for any transactions and dividends
            ELSE COALESCE(
                bpm.market_value - 
                LAG(bpm.market_value) OVER (ORDER BY bpm.date) -
                -- Remove the impact of today's transactions
                CASE 
                    WHEN bpm.transaction_type = 'BUY' THEN bpm.adjusted_quantity * bpm.adjusted_price
                    WHEN bpm.transaction_type = 'SELL' THEN -(bpm.adjusted_quantity * bpm.adjusted_price)
                    ELSE 0 
                END +
                -- Add any cash dividends received
                COALESCE(bpm.cash_dividend, 0),
                0
            )
        END as daily_pl
    FROM base_portfolio_metrics bpm
),

-- Seventh CTE: Additional metrics that depend on the core calculations above
extended_metrics AS (
    SELECT 
        pm.*,
        
        -- Calculate the current cost basis of the shares owned at each date 
       pm.total_investment_amount + pm.cumulative_cost_basis_variation
       as current_cost_basis,
       
		-- Calculate daily percentage return
		CASE
		    -- For the first transaction (no previous market value exists)
		    WHEN LAG(pm.market_value) OVER (ORDER BY pm.date) IS NULL THEN
		        (pm.daily_pl / (pm.adjusted_quantity * pm.adjusted_price)) * 100
		    -- For BUY transactions, calculate including the investment amount on that day
		    WHEN pm.transaction_type = 'BUY' THEN
		        (pm.daily_pl / (LAG(pm.market_value) OVER (ORDER BY pm.date) + (pm.adjusted_quantity * pm.adjusted_price))) * 100
		    -- For all other transactions
		    WHEN LAG(pm.market_value) OVER (ORDER BY pm.date) IS NOT NULL THEN
		        (pm.daily_pl / LAG(pm.market_value) OVER (ORDER BY pm.date)) * 100
		    ELSE
		        0
		END AS daily_pl_pct,
        
        -- Calculate total return (combining realized and unrealized gains/losses)
        pm.realised_pl + pm.unrealised_pl as total_return,
        
        -- Express total return as a percentage of total investment
        CASE
            WHEN pm.total_investment_amount > 0 THEN
                ((pm.realised_pl + pm.unrealised_pl) / pm.total_investment_amount) * 100
            ELSE NULL
        END as total_return_pct
    FROM portfolio_metrics pm
),


-- Final CTE: Calculate cumulative returns and order columns
final_metrics AS (
    SELECT
	    NULL as metric_index,           -- Start with system columns
	    em.stock_id,
	    em.yahoo_symbol,
	    em.date,                       -- Date information
	    em.close_price,                -- Price information
	    em.dividend,                   -- Dividend related columns
	    em.cash_dividend,
	    em.cash_dividends_total,
	    em.drp_flag,                   -- DRP related columns
	    em.drp_share,
	    em.drp_shares_total,
	    em.split_ratio,                -- Split related columns
	    em.cumulative_split_ratio,
	    em.transaction_type,           -- Transaction related columns
	    em.adjusted_quantity,
	    em.adjusted_price,
	    em.net_transaction_quantity,
	    em.total_investment_amount,
	    em.cost_basis_variation,       -- Cost basis related columns
	    em.cumulative_cost_basis_variation,
	    em.current_cost_basis,
	    em.total_shares_owned,         -- Position related columns
	    em.market_value,
	    em.realised_pl,                -- Profit/Loss related columns
	    em.unrealised_pl,
	    em.daily_pl,
	    em.daily_pl_pct,
	    em.total_return,
	    em.total_return_pct,
	    -- Calculate cumulative return using geometric mean of daily returns
	    -- This provides a more accurate measure of investment performance over time
	    EXP(SUM(LN(COALESCE(1 + (daily_pl_pct/100), 1))) OVER (
	        ORDER BY date
	    )) * 100 - 100 as cumulative_return_pct
FROM extended_metrics em           -- Using table alias for cleaner code
)
-- FINAL SELECT: Execute Main query for all metrics
SELECT * FROM final_metrics ORDER BY date;

-- Query to get metrics for date range
SELECT * FROM final_metrics 
WHERE stock_id = :stock_id 
{% if start_date %}
    AND date >= :start_date
{% endif %}
{% if end_date %}
    AND date <= :end_date
{% endif %}
ORDER BY date;

-- Query to get latest metrics
SELECT * FROM final_metrics 
WHERE stock_id = :stock_id 
ORDER BY date DESC 
LIMIT 1;