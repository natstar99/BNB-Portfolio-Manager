import numpy as np
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from PySide6.QtWidgets import QMessageBox, QTableWidgetItem
import logging

logger = logging.getLogger(__name__)

class PortfolioStudyController:
    """
    Enhanced controller for portfolio study functionality.
    Provides efficient data retrieval and visualisation using pre-calculated metrics.
    """
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.view = None
        self.current_portfolio = None
        self.data = None
    
    def set_view(self, view):
        """Set the view and connect signals."""
        self.view = view
        self.view.update_plot.connect(self.analyse_portfolio)
    
    def set_portfolio(self, portfolio):
        """Set the current portfolio."""
        self.current_portfolio = portfolio
        if self.view:
            self.view.update_portfolio_stocks(portfolio.stocks.values())

    def get_portfolio_data(self, params):
        """
        Get portfolio metrics data based on study parameters.
        
        Args:
            params: Dictionary containing analysis parameters
            
        Returns:
            pd.DataFrame: DataFrame containing requested metrics
        """
        try:
            # Build the columns list based on study type
            study_type = params['study_type']
            columns = ['date']  # Always include date
            
            if study_type == "Market Value":
                columns.extend(['market_value'])
            elif study_type == "Profitability":
                if params['display_type'] == "Percentage":
                    if params['time_period'] == "Daily Changes":
                        columns.extend(['daily_pl_pct'])
                    else:  # Cumulative
                        columns.extend(['total_return_pct'])
                else:  # Dollar Value
                    if params['time_period'] == "Daily Changes":
                        columns.extend(['daily_pl'])
                    else:  # Cumulative
                        columns.extend(['total_return'])
            elif study_type == "Dividend Performance":
                if params['view_type'] == "Cash Dividends":
                    columns.extend(['cash_dividend', 'cash_dividends_total'])
                else:  # DRP
                    columns.extend(['drp_share', 'drp_shares_total'])
            elif study_type == "Portfolio Distribution":
                columns.extend(['market_value'])  # Only need latest values
            
            # Get data for selected stocks
            data_frames = []
            for yahoo_symbol in params['selected_stocks']:
                stock = self.current_portfolio.get_stock(yahoo_symbol)
                if stock:
                    query = f"""
                        SELECT {', '.join(columns)}
                        FROM portfolio_metrics
                        WHERE stock_id = ? AND date BETWEEN ? AND ?
                        ORDER BY date
                    """
                    
                    results = self.db_manager.fetch_all(
                        query,
                        (stock.id, params['start_date'], params['end_date'])
                    )
                    
                    if results:
                        df = pd.DataFrame(results, columns=columns)
                        df['stock'] = yahoo_symbol
                        data_frames.append(df)
            
            if data_frames:
                return pd.concat(data_frames, ignore_index=True)
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting portfolio data: {str(e)}")
            raise

    def analyse_portfolio(self, params):
        """
        Analyse portfolio based on given parameters and update views.
        
        Args:
            params: Dictionary containing analysis parameters
        """
        try:
            # Get data based on study type
            self.data = self.get_portfolio_data(params)
            
            if self.data.empty:
                QMessageBox.warning(
                    self.view,
                    "No Data",
                    "No data available for the selected stocks and date range."
                )
                return
            
            # Update plot based on study type
            self.view.figure.clear()
            ax = self.view.figure.add_subplot(111)
            
            study_type = params['study_type']
            
            if study_type == "Market Value":
                self.plot_market_value(ax, params)
            elif study_type == "Profitability":
                self.plot_profitability(ax, params)
            elif study_type == "Dividend Performance":
                self.plot_dividends(ax, params)
            else:  # Portfolio Distribution
                self.plot_distribution(ax)
            
            # Update statistics
            self.update_statistics_table(params)
            
            # Refresh canvases
            self.view.figure.tight_layout()
            self.view.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error in portfolio analysis: {str(e)}")
            QMessageBox.warning(
                self.view,
                "Analysis Error",
                f"Failed to analyse portfolio: {str(e)}"
            )

    def setup_date_axis(self, ax):
        """
        Configure date axis formatting and ticks.
        
        Args:
            ax: The matplotlib axis to configure
        """
        from matplotlib.dates import AutoDateLocator
        import matplotlib.dates as mdates
        
        # Create locator and formatter for smart date tick handling
        locator = AutoDateLocator(minticks=3, maxticks=7)
        formatter = mdates.ConciseDateFormatter(locator)
        
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)
        
        # Rotate labels
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
        
        # Adjust the subplot parameters for the current figure
        plt.gcf().tight_layout()

    def plot_market_value(self, ax, params):
        """Plot market value analysis."""
        if params['view_type'] == "Individual Stocks":
            # Plot individual stock values
            for stock in params['selected_stocks']:
                stock_data = self.data[self.data['stock'] == stock]
                dates = pd.to_datetime(stock_data['date'])
                ax.plot(dates, stock_data['market_value'], 
                       label=stock, linewidth=1.5)
        else:  # Portfolio Total
            if params['chart_type'] == "Line Chart":
                # Sum market values by date
                portfolio_total = self.data.groupby('date')['market_value'].sum()
                dates = pd.to_datetime(portfolio_total.index)
                ax.plot(dates, portfolio_total.values,
                       label='Total Portfolio', linewidth=2)
            else:  # Stacked Area
                # Pivot data for stacked area plot
                plot_data = self.data.pivot(
                    index='date',
                    columns='stock',
                    values='market_value'
                ).fillna(0)  # Fill NaN with 0 for stacking
                
                dates = pd.to_datetime(plot_data.index)
                ax.stackplot(dates, plot_data.T, 
                           labels=plot_data.columns)
        
        ax.set_title("Portfolio Market Value Over Time")
        ax.set_xlabel("Date")
        ax.set_ylabel("Value ($)")
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3)
        
        # Set up date axis
        self.setup_date_axis(ax)
        
        # Format y-axis to use comma separator for thousands
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

    def plot_profitability(self, ax, params):
        """Plot profitability analysis."""
        # Determine which metric to plot
        if params['display_type'] == "Percentage":
            metric = 'daily_pl_pct' if params['time_period'] == "Daily Changes" else 'total_return_pct'
            ylabel = "Return (%)"
            value_format = lambda x, p: f'{x:.1f}%'
        else:  # Dollar Value
            metric = 'daily_pl' if params['time_period'] == "Daily Changes" else 'total_return'
            ylabel = "Profit/Loss ($)"
            value_format = lambda x, p: f'${x:,.0f}'
        
        if params['view_type'] == "Individual Stocks":
            for stock in params['selected_stocks']:
                stock_data = self.data[self.data['stock'] == stock]
                dates = pd.to_datetime(stock_data['date'])
                ax.plot(dates, stock_data[metric], label=stock)
        else:  # Portfolio Total
            portfolio_total = self.data.groupby('date')[metric].sum()
            dates = pd.to_datetime(portfolio_total.index)
            ax.plot(dates, portfolio_total.values,
                   label='Total Portfolio', linewidth=2)
        
        # Add zero line for reference
        ax.axhline(y=0, color='r', linestyle='--', alpha=0.3)
        
        ax.set_title(f"Portfolio {'Daily' if params['time_period'] == 'Daily Changes' else 'Cumulative'} Returns")
        ax.set_xlabel("Date")
        ax.set_ylabel(ylabel)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3)
        
        # Set up date axis
        self.setup_date_axis(ax)
        
        # Format y-axis
        ax.yaxis.set_major_formatter(plt.FuncFormatter(value_format))

    def plot_dividends(self, ax, params):
        """Plot dividend analysis."""
        if params['view_type'] == "Cash Dividends":
            metric = 'cash_dividends_total' if params['display'] == "Cumulative" else 'cash_dividend'
            ylabel = "Dividends ($)"
            value_format = lambda x, p: f'${x:,.2f}'
        else:  # DRP
            metric = 'drp_shares_total' if params['display'] == "Cumulative" else 'drp_share'
            ylabel = "DRP Shares"
            value_format = lambda x, p: f'{x:,.4f}'
        
        # Group by date and sum values
        dividend_data = self.data.groupby(['date', 'stock'])[metric].sum().unstack()
        
        # Filter out dates with no dividends
        dividend_data = dividend_data[dividend_data.sum(axis=1) > 0]
        
        if dividend_data.empty:
            ax.text(0.5, 0.5, 'No dividend data for selected period',
                   ha='center', va='center')
            return
        
        # Plot bars for each stock
        dividend_data.plot(kind='bar', ax=ax, width=0.8)
        
        ax.set_title(f"{'Cumulative ' if params['display'] == 'Cumulative' else ''}{'Cash Dividends' if params['view_type'] == 'Cash Dividends' else 'DRP Shares'}")
        ax.set_xlabel("Date")
        ax.set_ylabel(ylabel)
        ax.legend(title="Stocks", bbox_to_anchor=(1.05, 1), loc='upper left')
        
        # Format x-axis dates
        dates = pd.to_datetime(dividend_data.index)
        ax.set_xticklabels([d.strftime('%Y-%m-%d') for d in dates], rotation=45)
        
        # Format y-axis
        ax.yaxis.set_major_formatter(plt.FuncFormatter(value_format))

    def plot_distribution(self, ax):
        """Plot portfolio distribution pie chart."""
        # Get latest market values
        latest_date = self.data['date'].max()
        latest_values = self.data[self.data['date'] == latest_date]
        
        # Create pie chart
        sizes = latest_values.groupby('stock')['market_value'].sum()
        
        # Only plot if we have positive values
        if (sizes > 0).any():
            # Create labels with stock name and value
            labels = [f"{stock}\n(${value:,.0f})" for stock, value in sizes.items()]
            
            # Plot only positive values
            positive_sizes = sizes[sizes > 0]
            positive_labels = [labels[i] for i, size in enumerate(sizes) if size > 0]
            
            ax.pie(positive_sizes, labels=positive_labels, autopct='%1.1f%%')
            ax.set_title("Current Portfolio Distribution")
        else:
            ax.text(0.5, 0.5, 'No positive market values to display',
                   ha='center', va='center')

    def setup_date_axis(self, ax):
        """
        Configure date axis formatting and ticks.
        
        Args:
            ax: The matplotlib axis to configure
        """
        from matplotlib.dates import AutoDateLocator
        import matplotlib.dates as mdates
        
        # Create locator and formatter for smart date tick handling
        locator = AutoDateLocator(minticks=3, maxticks=7)
        formatter = mdates.ConciseDateFormatter(locator)
        
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)
        
        # Rotate labels for better readability
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
        
        # Get current figure
        fig = plt.gcf()
        
        # Use a tight layout to prevent label cutoff
        fig.tight_layout()

    def plot_profitability(self, ax, params):
        """Plot profitability analysis."""
        # Determine which metric to plot
        if params['display_type'] == "Percentage":
            metric = 'daily_pl_pct' if params['time_period'] == "Daily Changes" else 'total_return_pct'
            ylabel = "Return (%)"
        else:  # Dollar Value
            metric = 'daily_pl' if params['time_period'] == "Daily Changes" else 'total_return'
            ylabel = "Profit/Loss ($)"
        
        if params['view_type'] == "Individual Stocks":
            for stock in params['selected_stocks']:
                stock_data = self.data[self.data['stock'] == stock]
                ax.plot(stock_data['date'], stock_data[metric], label=stock)
        else:  # Portfolio Total
            portfolio_total = self.data.groupby('date')[metric].sum()
            ax.plot(
                portfolio_total.index,
                portfolio_total.values,
                label='Total Portfolio',
                linewidth=2
            )
        
        # Add zero line for reference
        ax.axhline(y=0, color='r', linestyle='--', alpha=0.3)
        
        ax.set_title(f"Portfolio {'Daily' if params['time_period'] == 'Daily Changes' else 'Cumulative'} Returns")
        ax.set_xlabel("Date")
        ax.set_ylabel(ylabel)
        ax.legend()
        ax.grid(True, alpha=0.3)

    def plot_dividends(self, ax, params):
        """Plot dividend analysis."""
        if params['view_type'] == "Cash Dividends":
            metric = 'cash_dividends_total' if params['display'] == "Cumulative" else 'cash_dividend'
            ylabel = "Dividends ($)"
        else:  # DRP
            metric = 'drp_shares_total' if params['display'] == "Cumulative" else 'drp_share'
            ylabel = "DRP Shares"
        
        # Group by date and sum values
        dividend_data = self.data.groupby(['date', 'stock'])[metric].sum().unstack()
        
        # Plot bars for each stock
        dividend_data.plot(kind='bar', ax=ax, width=0.8)
        
        ax.set_title(f"{'Cumulative ' if params['display'] == 'Cumulative' else ''}{'Cash Dividends' if params['view_type'] == 'Cash Dividends' else 'DRP Shares'}")
        ax.set_xlabel("Date")
        ax.set_ylabel(ylabel)
        ax.legend(title="Stocks")
        plt.setp(ax.get_xticklabels(), rotation=45)

    def plot_distribution(self, ax):
        """Plot portfolio distribution pie chart."""
        # Get latest market values
        latest_date = self.data['date'].max()
        latest_values = self.data[self.data['date'] == latest_date]
        
        # Create pie chart
        sizes = latest_values.groupby('stock')['market_value'].sum()
        ax.pie(
            sizes,
            labels=[f"{stock}\n(${value:,.0f})" for stock, value in sizes.items()],
            autopct='%1.1f%%'
        )
        ax.set_title("Current Portfolio Distribution")

    def update_statistics_table(self, params):
        """Update statistics table with current analysis."""
        study_type = params['study_type']
        
        # Clear existing stats
        self.view.stats_table.setRowCount(0)
        stats = {}
        
        if study_type == "Market Value":
            latest_values = self.data.groupby('stock')['market_value'].last()
            total_value = latest_values.sum()
            
            stats.update({
                'Total Portfolio Value': f"${total_value:,.2f}",
                'Number of Holdings': str(len(latest_values)),
                'Largest Holding': f"{latest_values.idxmax()} (${latest_values.max():,.2f})",
                'Smallest Holding': f"{latest_values.idxmin()} (${latest_values.min():,.2f})"
            })
            
        elif study_type == "Profitability":
            if params['display_type'] == "Percentage":
                metric = 'daily_pl_pct' if params['time_period'] == "Daily Changes" else 'total_return_pct'
                suffix = "%"
            else:
                metric = 'daily_pl' if params['time_period'] == "Daily Changes" else 'total_return'
                suffix = "$"
            
            data = self.data[metric]
            stats.update({
                'Average Return': f"{data.mean():.2f}{suffix}",
                'Best Return': f"{data.max():.2f}{suffix}",
                'Worst Return': f"{data.min():.2f}{suffix}",
                'Volatility': f"{data.std():.2f}{suffix}"
            })
            
        elif study_type == "Dividend Performance":
            if params['view_type'] == "Cash Dividends":
                total_col = 'cash_dividends_total'
                period_col = 'cash_dividend'
                prefix = "$"
            else:
                total_col = 'drp_shares_total'
                period_col = 'drp_share'
                prefix = ""
            
            stats.update({
                'Total Received': f"{prefix}{self.data[total_col].max():.2f}",
                'Average Per Period': f"{prefix}{self.data[period_col].mean():.2f}",
                'Largest Single Payment': f"{prefix}{self.data[period_col].max():.2f}",
                'Number of Payments': str(len(self.data[self.data[period_col] > 0]))
            })
            
        else:  # Portfolio Distribution
            latest_date = self.data['date'].max()
            latest_values = self.data[self.data['date'] == latest_date]
            holdings = latest_values.groupby('stock')['market_value'].sum()
            
            stats.update({
                'Number of Holdings': str(len(holdings)),
                'Total Portfolio Value': f"${holdings.sum():,.2f}",
                'Largest Allocation': f"{holdings.idxmax()} ({holdings.max()/holdings.sum()*100:.1f}%)",
                'Smallest Allocation': f"{holdings.idxmin()} ({holdings.min()/holdings.sum()*100:.1f}%)"
            })
        
        # Update table
        self.view.stats_table.setRowCount(len(stats))
        for i, (metric, value) in enumerate(stats.items()):
            self.view.stats_table.setItem(i, 0, QTableWidgetItem(metric))
            self.view.stats_table.setItem(i, 1, QTableWidgetItem(str(value)))
    
    def get_view(self):
        """Return the view instance."""
        return self.view