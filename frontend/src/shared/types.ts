// Shared types between frontend and backend

export interface Portfolio {
  id: number;
  name: string;
  currency: string;
  created_at: string;
  updated_at: string;
  // Optional financial metrics (may not be present initially)
  total_value?: number;
  total_cost?: number;
  gain_loss?: number;
  gain_loss_percent?: number;
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

export interface PortfolioMetrics {
  total_value: number;
  total_investment: number;
  unrealised_pl: number;
  realised_pl: number;
  total_return: number;
  total_return_percentage: number;
  daily_pl: number;
  daily_pl_percentage: number;
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

export interface PerformanceData {
  date: string;
  total_value: number;
  total_cost: number;
  unrealized_pl: number;
  realized_pl: number;
  total_pl: number;
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