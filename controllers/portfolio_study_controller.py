# File: controllers/portfolio_study_controller.py

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from PySide6.QtWidgets import QMessageBox, QTableWidgetItem
import logging

logger = logging.getLogger(__name__)

class PortfolioStudyController:
    """
    Controller for portfolio study functionality.
    Provides portfolio analysis and visualisation.
    """
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.view = None
        self.current_portfolio = None
        self.data = None  # Store current analysis data
    
    def set_view(self, view):
        """Set the view and connect signals."""
        self.view = view
        self.view.update_plot.connect(self.analyse_portfolio)
    
    def set_portfolio(self, portfolio):
        """Set the current portfolio."""
        self.current_portfolio = portfolio
        if self.view:
            self.view.update_portfolio_stocks(portfolio.stocks.values())

    def analyse_portfolio(self, params):
        """
        analyse portfolio based on given parameters and update all views.
        
        Args:
            params: Dict containing analysis parameters
        """
        try:
            # Store current value type
            self.current_value_type = params['value_type']
            
            # Get data for analysis
            self.data = self.get_portfolio_data(
                params['selected_stocks'],
                params['start_date'],
                params['end_date']
            )
            
            if self.data.empty:
                QMessageBox.warning(self.view, "No Data", 
                    "No data available for the selected stocks and date range.")
                return
            
            # Update visualisations based on view mode
            self.view.figure.clear()
            ax = self.view.figure.add_subplot(111)
            
            if params['chart_type'] == "Line Chart":
                self.plot_line_chart(ax, params['view_mode'])
            elif params['chart_type'] == "Portfolio Distribution":
                self.plot_distribution(ax)
            elif params['chart_type'] == "Stacked Area":
                self.plot_stacked_area(ax)
            elif params['chart_type'] == "Performance Comparison":
                self.plot_performance_comparison(ax)
            
            # Update statistics
            self.update_statistics_table()
            
            # Refresh canvases
            self.view.figure.tight_layout()
            self.view.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error in portfolio analysis: {str(e)}")
            logger.exception("Detailed traceback:")
            QMessageBox.warning(self.view, "Analysis Error",
                              f"Failed to analyse portfolio: {str(e)}")

    def get_portfolio_data(self, selected_stocks, start_date, end_date):
        """
        Get historical portfolio data including market value and profit/loss.
        """
        try:
            data = {}
            
            for stock_text in selected_stocks:
                symbol = stock_text.split(" (")[0]
                stock = self.current_portfolio.get_stock(symbol)
                if stock:
                    values = self.db_manager.fetch_all("""
                        WITH RECURSIVE dates AS (
                            SELECT DISTINCT date 
                            FROM historical_prices 
                            WHERE stock_id = ? AND date BETWEEN ? AND ?
                            UNION
                            SELECT DISTINCT date(date) 
                            FROM transactions 
                            WHERE stock_id = ? AND date BETWEEN ? AND ?
                        ),
                        daily_changes AS (
                            SELECT 
                                d.date,
                                hp.close_price,
                                -- Track share changes
                                COALESCE(
                                    SUM(CASE 
                                        WHEN t.transaction_type = 'BUY' THEN t.quantity 
                                        WHEN t.transaction_type = 'SELL' THEN -t.quantity 
                                        ELSE 0 
                                    END)
                                , 0) as shares_change,
                                -- Track money invested/received
                                COALESCE(
                                    SUM(CASE 
                                        WHEN t.transaction_type = 'BUY' THEN -(t.quantity * t.price)  -- Money spent (negative)
                                        WHEN t.transaction_type = 'SELL' THEN (t.quantity * t.price)  -- Money received (positive)
                                        ELSE 0 
                                    END)
                                , 0) as money_flow,
                                ROW_NUMBER() OVER (ORDER BY d.date) as row_num
                            FROM dates d
                            LEFT JOIN historical_prices hp ON d.date = hp.date 
                                AND hp.stock_id = ?
                            LEFT JOIN transactions t ON d.date = date(t.date) 
                                AND t.stock_id = ?
                            GROUP BY d.date, hp.close_price
                        ),
                        running_totals AS (
                            -- Base case
                            SELECT
                                date,
                                close_price,
                                shares_change,
                                money_flow,
                                shares_change as total_shares,
                                money_flow as net_investment,
                                row_num
                            FROM daily_changes
                            WHERE row_num = 1
                            
                            UNION ALL
                            
                            -- Recursive case
                            SELECT
                                d.date,
                                d.close_price,
                                d.shares_change,
                                d.money_flow,
                                rt.total_shares + d.shares_change,
                                rt.net_investment + d.money_flow,
                                d.row_num
                            FROM daily_changes d
                            JOIN running_totals rt ON d.row_num = rt.row_num + 1
                        )
                        SELECT 
                            date,
                            ROUND(total_shares * close_price, 2) as market_value,
                            net_investment,
                            ROUND((total_shares * close_price) + net_investment, 2) as profit_loss
                        FROM running_totals
                        WHERE close_price IS NOT NULL
                        ORDER BY date
                    """, (stock.id, start_date, end_date, 
                          stock.id, start_date, end_date,
                          stock.id, stock.id))
                    
                    if values:
                        # Convert to DataFrame for better handling of duplicates
                        temp_df = pd.DataFrame(values, columns=['date', 'market_value', 'net_investment', 'profit_loss'])
                        temp_df['date'] = pd.to_datetime(temp_df['date'])
                        
                        # Handle duplicates by taking the last value for each date
                        temp_df = temp_df.sort_values('date').groupby('date').last()
                        
                        # Store based on the requested value type
                        if hasattr(self, 'current_value_type'):
                            if self.current_value_type == "Profit/Loss":
                                data[symbol] = temp_df['profit_loss']
                            else:
                                data[symbol] = temp_df['market_value']
                        else:
                            data[symbol] = temp_df['market_value']

            if data:
                # Create DataFrame with all unique dates
                all_dates = pd.DatetimeIndex(sorted(set(
                    date for series in data.values() for date in series.index
                )))
                
                # Create final DataFrame
                result = pd.DataFrame(index=all_dates)
                
                # Add each stock's data
                for symbol, series in data.items():
                    result[symbol] = series.reindex(all_dates)
                
                # Forward fill missing values
                result = result.fillna(method='ffill')
                
                return result
                
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error in get_portfolio_data: {str(e)}")
            logger.exception("Detailed traceback:")
            raise Exception(f"Failed to get portfolio data: {str(e)}")


    def plot_line_chart(self, ax, view_mode):
        """Plot line chart of portfolio values."""
        value_label = {
            "Market Value": "Value ($)",
            "Profit/Loss": "Profit/Loss ($)",
            "Percentage Return": "Return (%)"
        }.get(self.current_value_type, "Value ($)")

        if view_mode == "Individual Stocks":
            for column in self.data.columns:
                ax.plot(self.data.index, self.data[column], label=column)
        else:
            portfolio_total = self.data.sum(axis=1)
            ax.plot(self.data.index, portfolio_total, 
                   label='Total Portfolio', color='darkblue', linewidth=2)
        
        ax.set_title(f"Portfolio {self.current_value_type} Over Time")
        ax.set_xlabel("Date")
        ax.set_ylabel(value_label)
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.setp(ax.get_xticklabels(), rotation=45)

        # Add zero line for Profit/Loss view
        if self.current_value_type == "Profit/Loss":
            ax.axhline(y=0, color='r', linestyle='-', alpha=0.2)

    def plot_distribution(self, ax):
        """Plot current portfolio distribution."""
        latest_values = self.data.iloc[-1]
        sizes = latest_values[latest_values > 0]
        
        if not sizes.empty:
            labels = [f"{symbol}\n(${value:,.0f})" for symbol, value in sizes.items()]
            ax.pie(sizes, labels=labels, autopct='%1.1f%%')
            ax.set_title("Current Portfolio Distribution")
        else:
            ax.text(0.5, 0.5, "No holdings to display", ha='center', va='center')

    def plot_stacked_area(self, ax):
        """Plot stacked area chart showing portfolio composition over time."""
        self.data.plot(kind='area', stacked=True, ax=ax)
        ax.set_title("Portfolio Composition Over Time")
        ax.set_xlabel("Date")
        ax.set_ylabel("Value ($)")
        ax.legend(title="Stocks", bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.setp(ax.get_xticklabels(), rotation=45)

    def plot_performance_comparison(self, ax):
        """Plot performance comparison between stocks."""
        returns = ((self.data.iloc[-1] - self.data.iloc[0]) / self.data.iloc[0] * 100).sort_values()
        returns.plot(kind='barh', ax=ax)
        ax.set_title("Stock Performance Comparison")
        ax.set_xlabel("Total Return (%)")
        
        # Add value labels
        for i, v in enumerate(returns):
            ax.text(v + 1, i, f'{v:,.1f}%')

    def update_statistics_table(self):
        """Update statistics table with current analysis."""
        portfolio_total = self.data.sum(axis=1)
        returns = portfolio_total.pct_change()
        
        stats = {
            'Current Value': f"${portfolio_total.iloc[-1]:,.2f}",
            'Total Return': f"{((portfolio_total.iloc[-1] / portfolio_total.iloc[0]) - 1) * 100:.1f}%",
            'Average Monthly Return': f"{returns.resample('M').mean().mean() * 100:.1f}%",
            'Volatility (Annual)': f"{returns.std() * np.sqrt(252) * 100:.1f}%",
            'Maximum Drawdown': f"{((portfolio_total / portfolio_total.cummax()) - 1).min() * 100:.1f}%",
        }
        
        self.view.stats_table.setRowCount(len(stats))
        for i, (metric, value) in enumerate(stats.items()):
            self.view.stats_table.setItem(i, 0, QTableWidgetItem(metric))
            self.view.stats_table.setItem(i, 1, QTableWidgetItem(value))
    
    def get_view(self):
        """Return the view instance"""
        return self.view