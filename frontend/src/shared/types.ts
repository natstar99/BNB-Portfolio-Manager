// Shared types between frontend and backend

/**
 * Portfolio Dashboard Summary
 * Represents aggregated portfolio metrics at a single point in time (latest data).
 * This is the total portfolio summary, NOT day-by-day historical data.
 * Source: V_PORTFOLIO_DASHBOARD_SUMMARY view
 */
export interface Portfolio {
  id: number;
  name: string;
  currency: string;
  description?: string;
  created_at: string;
  updated_at: string;
  // Optional financial metrics (may not be present initially)
  total_value?: number;
  total_cost?: number;
  unrealized_pl?: number;      // Unrealized profit/loss from open positions
  realized_pl?: number;        // Realized profit/loss from closed positions
  total_pl?: number;           // Total P/L (unrealized + realized)
  total_pl_percent?: number;   // Total P/L as percentage of cost basis
  day_change?: number;
  day_change_percent?: number;
  stock_count?: number;
}

export interface Stock {
  id: number;
  yahoo_symbol: string;
  instrument_code: string;
  name: string;
  current_price: number;
  last_updated: string;
  market_or_index: string;
  market_suffix: string;
  verification_status: 'pending' | 'verified' | 'failed';
  drp: boolean;
  trading_currency: string;
  current_currency: string;
}

export interface Transaction {
  id: number;
  stock_id: number;
  portfolio_id: number;
  portfolio_name?: string;
  symbol?: string;
  action?: 'buy' | 'sell';
  date: string;
  quantity: number;
  price: number;
  total_amount?: number;
  fees?: number;
  notes?: string;
  verified?: boolean;
  currency?: string;
  transaction_type: 'buy' | 'sell' | 'dividend' | 'split';
  currency_conversion_rate: number;
  original_price: number;
}

export interface StockHolding {
  stock: Stock;
  quantity: number;
  average_price: number;
  current_value: number;
  unrealised_pl: number;
  unrealised_pl_percentage: number;
  weight: number;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  page: number;
  limit: number;
  total: number;
  total_pages: number;
}

export interface Position {
  id: number;
  symbol: string;
  company_name?: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  market_value: number;
  gain_loss: number;
  gain_loss_percent: number;
  day_change: number;
  day_change_percent: number;
}

/**
 * Portfolio Performance Time-Series Data
 * Represents day-by-day historical portfolio metrics (NOT aggregated totals).
 * Each record is a snapshot of the portfolio on a specific date.
 * Source: V_PORTFOLIO_ANALYTICS_TIMESERIES view
 */
export interface PerformanceData {
  date: string;
  total_value: number;
  total_cost: number;
  unrealized_pl: number;       // Unrealized P/L on this date
  realized_pl: number;         // Cumulative realized P/L up to this date
  daily_pl: number;            // Day-over-day change in value
  total_return: number;        // Total return (unrealized + realized)
  return_pct: number;
  total_return_pct: number;
  active_positions: number;
  [key: string]: number | string;
}

export interface RecentTransaction {
  id: number;
  symbol: string;
  action: string;
  quantity: number;
  price: number;
  date: string;
}