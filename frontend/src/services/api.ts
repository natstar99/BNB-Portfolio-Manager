import axios from 'axios';
import { Portfolio, Stock, Transaction, ApiResponse } from '../types/shared';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

// Portfolio API
export const portfolioApi = {
  getAll: (): Promise<ApiResponse<Portfolio[]>> =>
    api.get('/portfolios').then(res => res.data),
  
  getById: (id: number): Promise<ApiResponse<Portfolio>> =>
    api.get(`/portfolios/${id}`).then(res => res.data),
  
  create: (data: { name: string; currency?: string; description?: string }): Promise<ApiResponse<Portfolio>> =>
    api.post('/portfolios', data).then(res => res.data),
  
  update: (id: number, data: Partial<Portfolio>): Promise<ApiResponse<Portfolio>> =>
    api.put(`/portfolios/${id}`, data).then(res => res.data),
  
  delete: (id: number): Promise<ApiResponse<void>> =>
    api.delete(`/portfolios/${id}`).then(res => res.data),
  
  getStocks: (id: number): Promise<ApiResponse<Stock[]>> =>
    api.get(`/portfolios/${id}/stocks`).then(res => res.data),
  
  addStock: (portfolioId: number, stockId: number): Promise<ApiResponse<void>> =>
    api.post(`/portfolios/${portfolioId}/stocks`, { stock_id: stockId }).then(res => res.data),
  
  removeStock: (portfolioId: number, stockId: number): Promise<ApiResponse<void>> =>
    api.delete(`/portfolios/${portfolioId}/stocks/${stockId}`).then(res => res.data),
};

// Stock API
export const stockApi = {
  getAll: (): Promise<ApiResponse<Stock[]>> =>
    api.get('/stocks').then(res => res.data),
  
  getById: (id: number): Promise<ApiResponse<Stock>> =>
    api.get(`/stocks/${id}`).then(res => res.data),
  
  create: (data: Partial<Stock>): Promise<ApiResponse<Stock>> =>
    api.post('/stocks', data).then(res => res.data),
  
  update: (id: number, data: Partial<Stock>): Promise<ApiResponse<Stock>> =>
    api.put(`/stocks/${id}`, data).then(res => res.data),
  
  delete: (id: number): Promise<ApiResponse<void>> =>
    api.delete(`/stocks/${id}`).then(res => res.data),
  
  search: (query: string): Promise<ApiResponse<Stock[]>> =>
    api.get(`/stocks/search?q=${encodeURIComponent(query)}`).then(res => res.data),
  
  updatePrice: (id: number, price: number): Promise<ApiResponse<Stock>> =>
    api.put(`/stocks/${id}/price`, { price }).then(res => res.data),
  
  verify: (id: number): Promise<ApiResponse<Stock>> =>
    api.post(`/stocks/${id}/verify`).then(res => res.data),
  
  getHistoricalPrices: (id: number, startDate?: string, endDate?: string): Promise<ApiResponse<any[]>> =>
    api.get(`/stocks/${id}/historical-prices`, {
      params: { start_date: startDate, end_date: endDate }
    }).then(res => res.data),
};

// Transaction API
export const transactionApi = {
  getAll: (params?: {
    stock_id?: number;
    type?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
    offset?: number;
  }): Promise<ApiResponse<Transaction[]> & { pagination: any }> =>
    api.get('/transactions', { params }).then(res => res.data),
  
  getById: (id: number): Promise<ApiResponse<Transaction>> =>
    api.get(`/transactions/${id}`).then(res => res.data),
  
  create: (data: Partial<Transaction>): Promise<ApiResponse<Transaction>> =>
    api.post('/transactions', data).then(res => res.data),
  
  update: (id: number, data: Partial<Transaction>): Promise<ApiResponse<Transaction>> =>
    api.put(`/transactions/${id}`, data).then(res => res.data),
  
  delete: (id: number): Promise<ApiResponse<void>> =>
    api.delete(`/transactions/${id}`).then(res => res.data),
  
  bulkCreate: (transactions: Partial<Transaction>[]): Promise<ApiResponse<any>> =>
    api.post('/transactions/bulk', { transactions }).then(res => res.data),
  
  getSummary: (stockId?: number): Promise<ApiResponse<any>> =>
    api.get('/transactions/summary', { params: { stock_id: stockId } }).then(res => res.data),
};

export default api;