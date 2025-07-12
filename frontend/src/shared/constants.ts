// Shared constants between frontend and backend

export const TRANSACTION_TYPES = {
  BUY: 'buy',
  SELL: 'sell',
  DIVIDEND: 'dividend',
  SPLIT: 'split'
} as const;

export const VERIFICATION_STATUS = {
  PENDING: 'pending',
  VERIFIED: 'verified',
  FAILED: 'failed'
} as const;

export const CURRENCIES = {
  AUD: 'AUD',
  USD: 'USD',
  EUR: 'EUR',
  GBP: 'GBP',
  JPY: 'JPY',
  CAD: 'CAD',
  NZD: 'NZD',
  CHF: 'CHF'
} as const;

export const CALCULATION_METHODS = {
  FIFO: 'fifo',
  LIFO: 'lifo',
  HIFO: 'hifo'
} as const;

export const API_ENDPOINTS = {
  PORTFOLIOS: '/api/portfolios',
  STOCKS: '/api/stocks',
  TRANSACTIONS: '/api/transactions',
  METRICS: '/api/metrics',
  MARKET_DATA: '/api/market-data'
} as const;

export const DEFAULT_SETTINGS = {
  CURRENCY: 'AUD',
  CALCULATION_METHOD: 'fifo',
  CHART_TYPE: 'line',
  DATE_FORMAT: 'DD/MM/YYYY',
  DECIMAL_PLACES: 2
} as const;

export const CHART_TYPES = {
  LINE: 'line',
  AREA: 'area',
  BAR: 'bar',
  PIE: 'pie'
} as const;

export const TIME_PERIODS = {
  '1D': '1D',
  '1W': '1W',
  '1M': '1M',
  '3M': '3M',
  '6M': '6M',
  '1Y': '1Y',
  'ALL': 'ALL'
} as const;