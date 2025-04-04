# File: controllers/portfolio_optimisation_controller.py

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from scipy.optimize import minimize
from scipy.stats import norm, skew, kurtosis
from scipy.stats.mstats import gmean
from PySide6.QtWidgets import QMessageBox
import logging

logger = logging.getLogger(__name__)

class PortfolioOptimisationController:
    """
    Controller for portfolio optimisation functionality.
    Handles data retrieval, optimisation calculations, and results processing.
    """
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.view = None
        self.current_portfolio = None
    
    def set_view(self, view):
        """Set the view and connect signals."""
        self.view = view
        self.view.optimise_portfolio.connect(self.optimise_portfolio)
    
    def set_portfolio(self, portfolio):
        """Set the current portfolio and update the view."""
        self.current_portfolio = portfolio
        if self.view:
            self.view.update_portfolio_stocks(portfolio.stocks.values())
    
    def get_view(self):
        """Return the view instance."""
        return self.view
    
    def optimise_portfolio(self, params):
        """
        Perform portfolio optimisation based on selected criteria.
        
        Args:
            params: List containing [selected_tickers, optimisation_criteria, period]
        """
        try:
            tickers, criteria, period = params
            
            # Convert period to datetime
            years = int(period.split()[0])
            start_date = datetime.now() - timedelta(days=years*365)
            
            # Download data
            data = yf.download(tickers, start=start_date, end=datetime.now())['Close']
            returns = data.pct_change().dropna()
            
            # Initialise optimisation parameters
            num_assets = len(tickers)
            init_guess = np.array(num_assets * [1. / num_assets])
            bounds = tuple((0, 1) for _ in range(num_assets))
            constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
            
            # Perform optimisations
            weights_data = {'symbols': tickers}
            statistics_data = {}
            optimal_points = {}
            
            # Get optimal portfolios for each criterion
            methods = ['Sharpe', 'CVaR', 'Sortino', 'Min Variance']
            for method in methods:
                weights = self.optimise_for_criterion(
                    method, returns, init_guess, bounds, constraints)
                weights_data[method] = weights
                
                # Generate detailed analysis report for each optimisation method
                analysis_report = self.generate_analysis_report(weights, returns, tickers)
                
                # Add report statistics to statistics_data
                for stat_name, value in analysis_report['statistics'].items():
                    if stat_name not in statistics_data:
                        statistics_data[stat_name] = []
                    statistics_data[stat_name].append(value)
                
                # Store optimal point for plotting
                vol = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
                ret = np.dot(weights, returns.mean()) * 252
                optimal_points[method] = (vol, ret)
                
                # Store the full analysis report
                weights_data[f"{method}_report"] = analysis_report
            
            # Generate efficient frontier data
            ef_returns, ef_volatilities = self.generate_efficient_frontier(returns)
            
            # Update view with results including the analysis reports
            self.view.update_results(
                weights_data,
                statistics_data,
                (ef_returns, ef_volatilities, optimal_points)
            )
            
        except Exception as e:
            logger.error(f"Error in portfolio optimisation: {str(e)}")
            QMessageBox.warning(
                self.view,
                "Optimisation Error",
                f"Failed to optimise portfolio: {str(e)}"
            )
    
    def optimise_for_criterion(self, method, returns, init_guess, bounds, constraints):
        """optimise portfolio based on specified criterion."""
        if method == 'Sharpe':
            objective = lambda w: -self.calculate_sharpe_ratio(w, returns)
        elif method == 'CVaR':
            objective = lambda w: -self.calculate_cvar(w, returns)
        elif method == 'Sortino':
            objective = lambda w: -self.calculate_sortino_ratio(w, returns)
        else:  # Min Variance
            objective = lambda w: self.calculate_variance(w, returns)
        
        result = minimize(objective, init_guess, method='SLSQP',
                        bounds=bounds, constraints=constraints)
        return result.x
    
    def calculate_portfolio_statistics(self, weights, returns):
        """Calculate comprehensive portfolio statistics."""
        portfolio_returns = returns.dot(weights)
        
        # Basic statistics
        mean_return = portfolio_returns.mean() * 252
        std_dev = portfolio_returns.std() * np.sqrt(252)
        sharpe = self.calculate_sharpe_ratio(weights, returns)
        sortino = self.calculate_sortino_ratio(weights, returns)
        cvar = self.calculate_cvar(weights, returns)
        
        return {
            'Expected Return': mean_return,
            'Volatility': std_dev,
            'Sharpe Ratio': sharpe,
            'Sortino Ratio': sortino,
            'CVaR': cvar,
            'Max Drawdown': self.calculate_max_drawdown(portfolio_returns)
        }
    
    def calculate_sharpe_ratio(self, weights, returns):
        """Calculate the Sharpe ratio with configurable risk-free rate."""
        risk_free_rate = 0.02
        portfolio_return = np.dot(weights, returns.mean()) * 252
        portfolio_std = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
        return (portfolio_return - risk_free_rate) / portfolio_std if portfolio_std > 0 else 0
    
    def calculate_cvar(self, weights, returns):
        """Calculate the Conditional Value at Risk."""
        portfolio_returns = returns.dot(weights)
        confidence_level = 0.05
        var = np.percentile(portfolio_returns, confidence_level * 100)
        cvar = portfolio_returns[portfolio_returns <= var].mean()
        return -cvar  # Negative because we want to maximise
    
    def calculate_sortino_ratio(self, weights, returns):
            """Calculate the Sortino ratio."""
            portfolio_returns = returns.dot(weights)
            downside_returns = portfolio_returns[portfolio_returns < 0]
            downside_std = downside_returns.std() * np.sqrt(252)
            expected_return = portfolio_returns.mean() * 252
            return expected_return / downside_std if downside_std > 0 else 0

    def calculate_variance(self, weights, returns):
        """
        Calculate the portfolio variance.
        
        Args:
            weights: Array of portfolio weights
            returns: DataFrame of historical returns
            
        Returns:
            float: Annualised portfolio variance
        """
        return np.dot(weights.T, np.dot(returns.cov() * 252, weights))

    def calculate_max_drawdown(self, returns):
        """
        Calculate the maximum drawdown of a portfolio.
        
        Args:
            returns: Series of portfolio returns
            
        Returns:
            float: Maximum drawdown as a percentage
        """
        cumulative_returns = (1 + returns).cumprod()
        rolling_max = cumulative_returns.expanding(min_periods=1).max()
        drawdowns = (cumulative_returns - rolling_max) / rolling_max
        return drawdowns.min()

    def generate_efficient_frontier(self, returns, num_portfolios=5000):
        """
        Generate the efficient frontier through Monte Carlo simulation.
        
        Args:
            returns: DataFrame of historical returns
            num_portfolios: Number of random portfolios to generate
            
        Returns:
            tuple: Arrays of returns and volatilities for plotting
        """
        num_assets = len(returns.columns)
        port_returns = []
        port_volatilities = []

        for _ in range(num_portfolios):
            # Generate random weights
            weights = np.random.random(num_assets)
            weights = weights / np.sum(weights)
            
            # Calculate portfolio return and volatility
            portfolio_return = np.dot(weights, returns.mean()) * 252
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
            
            port_returns.append(portfolio_return)
            port_volatilities.append(portfolio_vol)

        return np.array(port_returns), np.array(port_volatilities)

    def calculate_detailed_stats(self, weights, returns):
        """
        Calculate detailed portfolio statistics including higher moments.
        
        Args:
            weights: Array of portfolio weights
            returns: DataFrame of historical returns
            
        Returns:
            dict: Dictionary of portfolio statistics
        """
        portfolio_returns = returns.dot(weights)
        
        # Basic statistics
        mean_return = portfolio_returns.mean() * 252
        std_dev = portfolio_returns.std() * np.sqrt(252)
        
        # Higher moments
        skewness = skew(portfolio_returns)
        kurt = kurtosis(portfolio_returns)
        
        # Risk metrics
        max_dd = self.calculate_max_drawdown(portfolio_returns)
        var_95 = np.percentile(portfolio_returns, 5)
        cvar_95 = portfolio_returns[portfolio_returns <= var_95].mean()
        
        # Risk-adjusted returns
        sharpe = self.calculate_sharpe_ratio(weights, returns)
        sortino = self.calculate_sortino_ratio(weights, returns)
        
        # Information ratio (assuming equal-weight benchmark)
        benchmark_weights = np.ones(len(weights)) / len(weights)
        benchmark_returns = returns.dot(benchmark_weights)
        excess_returns = portfolio_returns - benchmark_returns
        information_ratio = excess_returns.mean() / excess_returns.std()
        
        # Treynor ratio (using market beta)
        market_returns = returns.mean(axis=1)  # Equally-weighted market proxy
        beta = np.cov(portfolio_returns, market_returns)[0,1] / np.var(market_returns)
        treynor_ratio = mean_return / beta if beta != 0 else 0

        return {
            'Expected Annual Return': mean_return,
            'Annual Volatility': std_dev,
            'Sharpe Ratio': sharpe,
            'Sortino Ratio': sortino,
            'Information Ratio': information_ratio,
            'Treynor Ratio': treynor_ratio,
            'Skewness': skewness,
            'Kurtosis': kurt,
            'Maximum Drawdown': max_dd,
            'Value at Risk (95%)': var_95,
            'Conditional VaR (95%)': cvar_95,
            'Beta': beta
        }

    def analyse_risk_contributions(self, weights, returns):
        """
        Analyse the risk contribution of each asset to the portfolio.
        
        Args:
            weights: Array of portfolio weights
            returns: DataFrame of historical returns
            
        Returns:
            dict: Dictionary containing risk contribution metrics
        """
        cov_matrix = returns.cov() * 252
        port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        
        # Marginal risk contribution
        mrc = np.dot(cov_matrix, weights) / port_vol
        
        # Component risk contribution
        crc = np.multiply(weights, mrc)
        
        # Percentage risk contribution
        prc = crc / port_vol
        
        return {
            'symbols': returns.columns.tolist(),
            'marginal_contribution': mrc,
            'component_contribution': crc,
            'percentage_contribution': prc
        }

    def generate_analysis_report(self, weights, returns, symbols):
        """
        Generate a comprehensive analysis report for the optimised portfolio.
        
        Args:
            weights: Array of optimal portfolio weights
            returns: DataFrame of historical returns
            symbols: List of stock symbols
            
        Returns:
            dict: Dictionary containing all analysis results
        """
        stats = self.calculate_detailed_stats(weights, returns)
        risk_contributions = self.analyse_risk_contributions(weights, returns)
        
        # Portfolio composition
        composition = {symbol: weight for symbol, weight in zip(symbols, weights)}
        
        # Monthly returns analysis
        monthly_returns = returns.dot(weights).resample('M').apply(
            lambda x: (1 + x).prod() - 1
        )
        
        best_month = monthly_returns.max()
        worst_month = monthly_returns.min()
        positive_months = (monthly_returns > 0).sum() / len(monthly_returns)
        
        return {
            'composition': composition,
            'statistics': stats,
            'risk_contributions': risk_contributions,
            'monthly_analysis': {
                'best_month': best_month,
                'worst_month': worst_month,
                'positive_months_ratio': positive_months
            }
        }