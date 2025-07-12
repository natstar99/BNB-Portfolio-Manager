import { useState, useEffect, useCallback } from 'react';
import { Portfolio } from '../shared/types';
import { portfolioApi } from '../services/api';

export const usePortfolios = () => {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPortfolio, setSelectedPortfolio] = useState<Portfolio | null>(null);

  const fetchPortfolios = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await portfolioApi.getAll();
      if (response.success && response.data) {
        setPortfolios(response.data);
        // DO NOT auto-select portfolio - user must explicitly choose
      } else {
        setError(response.error || 'Failed to fetch portfolios');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  }, []);

  const createPortfolio = useCallback(async (name: string, currency: string = 'USD', description?: string) => {
    try {
      setError(null);
      const response = await portfolioApi.create({ name, currency, description });
      if (response.success && response.data) {
        setPortfolios(prev => [...prev, response.data!]);
        // DO NOT auto-select new portfolio - user must explicitly choose
        return response.data;
      } else {
        throw new Error(response.error || 'Failed to create portfolio');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An error occurred';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, [portfolios.length]);

  const updatePortfolio = useCallback(async (id: number, data: Partial<Portfolio>) => {
    try {
      setError(null);
      const response = await portfolioApi.update(id, data);
      if (response.success && response.data) {
        setPortfolios(prev => 
          prev.map(portfolio => 
            portfolio.id === id ? response.data! : portfolio
          )
        );
        // Update selected portfolio if it's the one being updated
        if (selectedPortfolio?.id === id) {
          setSelectedPortfolio(response.data);
        }
        return response.data;
      } else {
        throw new Error(response.error || 'Failed to update portfolio');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An error occurred';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, [selectedPortfolio]);

  const deletePortfolio = useCallback(async (id: number) => {
    try {
      setError(null);
      const response = await portfolioApi.delete(id);
      if (response.success) {
        setPortfolios(prev => prev.filter(portfolio => portfolio.id !== id));
        // Clear selected portfolio if it was deleted
        if (selectedPortfolio?.id === id) {
          setSelectedPortfolio(null);
        }
      } else {
        throw new Error(response.error || 'Failed to delete portfolio');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An error occurred';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, [selectedPortfolio]);

  const selectPortfolio = useCallback((portfolio: Portfolio | null) => {
    setSelectedPortfolio(portfolio);
  }, []);

  useEffect(() => {
    fetchPortfolios();
  }, [fetchPortfolios]);

  // Computed properties
  const hasPortfolios = portfolios.length > 0;
  const isNewUser = !loading && !hasPortfolios;

  return {
    portfolios,
    selectedPortfolio,
    loading,
    error,
    hasPortfolios,
    isNewUser,
    refetch: fetchPortfolios,
    createPortfolio,
    updatePortfolio,
    deletePortfolio,
    selectPortfolio,
  };
};