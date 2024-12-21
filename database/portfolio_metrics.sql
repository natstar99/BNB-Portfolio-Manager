-- File: database/portfolio_metrics.sql

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
        -- Calculate transaction impact
        CASE 
            WHEN transaction_type = 'BUY' THEN quantity * cumulative_split_ratio
            WHEN transaction_type = 'SELL' THEN -quantity * cumulative_split_ratio
            ELSE 0 
        END AS transaction_quantity_delta,
        -- Track net transactions
        CASE 
            WHEN transaction_type = 'BUY' THEN quantity * cumulative_split_ratio
            WHEN transaction_type = 'SELL' THEN -quantity * cumulative_split_ratio
            ELSE 0 
        END AS net_transaction_quantity,
        -- Track total bought and sold quantities
        CASE 
            WHEN transaction_type = 'BUY' THEN quantity * cumulative_split_ratio
            ELSE 0 
        END AS total_bought_quantity,

        CASE 
            WHEN transaction_type = 'SELL' THEN quantity * cumulative_split_ratio
            ELSE 0 
        END AS total_sold_quantity,
        -- Track cumulative values for weighted averages
        CASE 
            WHEN transaction_type = 'BUY' THEN 
                quantity * cumulative_split_ratio * (price / cumulative_split_ratio)
            ELSE 0 
        END AS cumulative_buy_value,
        CASE 
            WHEN transaction_type = 'SELL' THEN 
                quantity * cumulative_split_ratio * (price / cumulative_split_ratio)
            ELSE 0 
        END AS cumulative_sell_value,
        CASE 
            WHEN transaction_type = 'BUY' THEN 
                quantity * cumulative_split_ratio * (price / cumulative_split_ratio)
            WHEN transaction_type = 'SELL' THEN 
                -(quantity * cumulative_split_ratio * (price / cumulative_split_ratio))
            ELSE 0 
        END AS running_cost_basis,
        -- Track total shares including DRP
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
        -- Transaction impact
        CASE 
            WHEN d.transaction_type = 'BUY' THEN d.quantity * d.cumulative_split_ratio
            WHEN d.transaction_type = 'SELL' THEN -d.quantity * d.cumulative_split_ratio
            ELSE 0 
        END,
        -- Update cumulative transaction total
        rc.net_transaction_quantity + 
        CASE 
            WHEN d.transaction_type = 'BUY' THEN d.quantity * d.cumulative_split_ratio
            WHEN d.transaction_type = 'SELL' THEN -d.quantity * d.cumulative_split_ratio
            ELSE 0 
        END,
        -- Update total bought quantity
        rc.total_bought_quantity + 
        CASE 
            WHEN d.transaction_type = 'BUY' THEN d.quantity * d.cumulative_split_ratio
            ELSE 0 
        END,

        -- Update total sold quantity
        rc.total_sold_quantity + 
        CASE 
            WHEN d.transaction_type = 'SELL' THEN d.quantity * d.cumulative_split_ratio
            ELSE 0 
        END,
        -- Update buy value total
        rc.cumulative_buy_value + 
        CASE 
            WHEN d.transaction_type = 'BUY' THEN 
                d.quantity * d.cumulative_split_ratio * (d.price / d.cumulative_split_ratio)
            ELSE 0 
        END,
        -- Update sell value total
        rc.cumulative_sell_value + 
        CASE 
            WHEN d.transaction_type = 'SELL' THEN 
                d.quantity * d.cumulative_split_ratio * (d.price / d.cumulative_split_ratio)
            ELSE 0 
        END,
        rc.running_cost_basis + 
        CASE 
            WHEN d.transaction_type = 'BUY' THEN 
                d.quantity * d.cumulative_split_ratio * (d.price / d.cumulative_split_ratio)
            WHEN d.transaction_type = 'SELL' THEN 
                -(d.quantity * d.cumulative_split_ratio * (d.price / d.cumulative_split_ratio))
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

-- Final CTE: Calculate almost all portfolio metrics
portfolio_metrics AS (
	SELECT
	    NULL as metric_index,
	    rc.stock_id,
	    rc.yahoo_symbol,
	    rc.date,
	    rc.close_price,
	    rc.dividend,
	    rc.drp_flag,
	    rc.split_ratio,
	    rc.cumulative_split_ratio,
	    rc.transaction_type,
	    rc.adjusted_quantity as quantity,
	    rc.adjusted_price as price,
	    rc.transaction_quantity_delta,
	    rc.total_bought_quantity,
	    rc.total_sold_quantity,
	    rc.net_transaction_quantity,
	    rc.total_shares_owned,
	
	    -- Calculate weighted average prices
	    CASE 
	        WHEN rc.cumulative_buy_value > 0 AND rc.total_bought_quantity > 0 THEN 
	            rc.cumulative_buy_value / rc.total_bought_quantity
	        ELSE NULL 
	    END as weighted_avg_purchase_price,
	
	    CASE 
	        WHEN rc.cumulative_sell_value > 0 AND rc.total_sold_quantity > 0 THEN 
	            rc.cumulative_sell_value / rc.total_sold_quantity
	        ELSE NULL 
	    END as weighted_avg_sale_price,
	
	    rc.cumulative_buy_value,
	    rc.cumulative_sell_value,
	
	    -- Track cost basis
	    rc.running_cost_basis as cost_basis,
	
	    -- Track dividends
	    rc.cash_dividend,
	    rc.cash_dividends_total,
	    rc.drp_share,
	    rc.drp_shares_total,
	
	    -- Calculate market value
	    rc.total_shares_owned * rc.close_price as market_value,
	
	    
	    -- ***CALCULATE PROFITABILITY METRICS***
	  
	     -- Calculate daily P/L
	    -- This compares current market value with previous day's market value, adjusting for transactions
	    CASE
	        -- For the first transaction (when it's a BUY)
	        WHEN rc.transaction_type = 'BUY' AND 
	             NOT EXISTS (
	                 SELECT 1 
	                 FROM running_calculations rc2 
	                 WHERE rc2.date < rc.date AND rc2.total_shares_owned > 0
	             ) THEN
	            ((rc.adjusted_quantity * rc.adjusted_price) -
	            (rc.total_shares_owned * rc.close_price))*-1
	            
	        -- For all other days
	        ELSE COALESCE(
	            (rc.total_shares_owned * rc.close_price) - 
	            LAG(rc.total_shares_owned * rc.close_price) OVER (ORDER BY rc.date) -
	            -- Subtract impact of buys/sells
	            CASE 
	                WHEN rc.transaction_type = 'BUY' THEN rc.adjusted_quantity * rc.adjusted_price
	                WHEN rc.transaction_type = 'SELL' THEN -(rc.adjusted_quantity * rc.adjusted_price)
	                ELSE 0 
	            END +
	            -- Add impact of cash dividends
	            COALESCE(rc.cash_dividend, 0),
	            0
	        )
	    END as daily_pl,
	
	    -- Calculate daily P/L percentage
	    CASE
	        -- For the first transaction (when it's a BUY)
	        WHEN rc.transaction_type = 'BUY' AND 
	             NOT EXISTS (
	                 SELECT 1 
	                 FROM running_calculations rc2 
	                 WHERE rc2.date < rc.date AND rc2.total_shares_owned > 0
	             ) THEN
	            CASE 
	                WHEN (rc.adjusted_quantity * rc.adjusted_price) > 0 THEN
	                    ((rc.total_shares_owned * rc.close_price) - 
	                     (rc.adjusted_quantity * rc.adjusted_price)) / 
	                    (rc.adjusted_quantity * rc.adjusted_price) * 100
	                ELSE NULL
	            END
	        -- For all other days
	        WHEN LAG(rc.total_shares_owned * rc.close_price) OVER (ORDER BY rc.date) > 0 THEN
	            (COALESCE(
	                (rc.total_shares_owned * rc.close_price) - 
	                LAG(rc.total_shares_owned * rc.close_price) OVER (ORDER BY rc.date) -
	                -- Subtract impact of buys/sells
	                CASE 
	                    WHEN rc.transaction_type = 'BUY' THEN rc.adjusted_quantity * rc.adjusted_price
	                    WHEN rc.transaction_type = 'SELL' THEN -(rc.adjusted_quantity * rc.adjusted_price)
	                    ELSE 0 
	                END +
	                -- Add impact of cash dividends
	                COALESCE(rc.cash_dividend, 0),
	                0
	            ) / LAG(rc.total_shares_owned * rc.close_price) OVER (ORDER BY rc.date)) * 100
	        ELSE NULL
	    END as daily_pl_pct,
	    
	    
	    -- Calculate realised P/L (includes both sell profits and cash dividends)
	    rc.realised_pl,
	    
	    CASE 
	        WHEN rc.total_shares_owned > 0 THEN 
	            (rc.total_shares_owned * rc.close_price) - rc.running_cost_basis
	        ELSE 0
	    END as unrealised_pl,
	
	    -- Calculate total return
	    rc.realised_pl + 
	    CASE 
	        WHEN rc.total_shares_owned > 0 THEN 
	            (rc.total_shares_owned * rc.close_price) - rc.running_cost_basis
	        ELSE 0
	    END as total_return,
	
		-- Calculate return percentage
		CASE 
		    WHEN rc.running_cost_basis > 0 THEN 
		        (
		            rc.realised_pl +  -- Already includes cash dividends
		            CASE 
		                WHEN rc.total_shares_owned > 0 THEN 
		                    (rc.total_shares_owned * rc.close_price) - rc.running_cost_basis
		                ELSE 0
		            END
		        ) / rc.running_cost_basis * 100
		    ELSE NULL
		END as total_return_pct
	FROM running_calculations rc
	)

SELECT 
    *,
    EXP(SUM(LN(COALESCE(1 + (daily_pl_pct/100), 1))) OVER (
        ORDER BY date
    )) * 100 - 100 as cumulative_return_pct
FROM portfolio_metrics
ORDER BY date;

-- Query to get metrics for date range
SELECT * FROM portfolio_metrics 
WHERE stock_id = :stock_id 
{% if start_date %}
    AND date >= :start_date
{% endif %}
{% if end_date %}
    AND date <= :end_date
{% endif %}
ORDER BY date;

-- Query to get latest metrics
SELECT * FROM portfolio_metrics 
WHERE stock_id = :stock_id 
ORDER BY date DESC 
LIMIT 1;