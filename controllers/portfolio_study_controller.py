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
        """
        Set the view and connect signals.
        
        Args:
            view: PortfolioStudyView instance to be controlled
        """
        self.view = view
        self.view.set_controller(self)
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
            # Get unique fields for the query
            fields = ['date']  # Always include date

            # Map study types to database columns
            study_type_mapping = {
                'market_value': 'market_value',
                'profitability': ['total_return', 'market_value', 'daily_pl', 'daily_pl_pct', 'total_return_pct', 'cumulative_return_pct'],
                'dividend_performance': ['cash_dividend', 'cash_dividends_total', 'drp_share', 'drp_shares_total']
            }
            
            # Add required fields based on study type
            if params['study_type'] in study_type_mapping:
                study_fields = study_type_mapping[params['study_type']]
                if isinstance(study_fields, list):
                    fields.extend(study_fields)
                else:
                    fields.append(study_fields)
                    
            # Add any specific metric if provided
            if 'metric' in params:
                if isinstance(params['metric'], list):
                    fields.extend(params['metric'])
                else:
                    fields.append(params['metric'])
                    
            if 'metrics' in params:
                fields.extend(params['metrics'])

            # Remove any duplicates while preserving order
            fields = list(dict.fromkeys(fields))
            
            # Build query using the ordered fields
            query = f"""
                    SELECT {', '.join(fields)}
                    FROM final_metrics
                    WHERE stock_id = :stock_id 
                    AND date BETWEEN :start_date AND :end_date
                    ORDER BY date
                """
            logger.debug(f"Generated SQL query: {query}")
            
            # Get data for selected stocks
            data_frames = []
            for yahoo_symbol in params['selected_stocks']:
                stock = self.current_portfolio.get_stock(yahoo_symbol)
                if stock:
                    query_params = {
                        'stock_id': stock.id,
                        'start_date': params['start_date'],
                        'end_date': params['end_date']
                    }
                    
                    logger.debug(f"Executing query for stock {yahoo_symbol} with params: {query_params}")
                    results = self.db_manager.fetch_all_with_params(query, query_params)
                    
                    if results:
                        df = pd.DataFrame(results, columns=fields)
                        df['stock'] = yahoo_symbol
                        data_frames.append(df)
            
            if data_frames:
                return pd.concat(data_frames, ignore_index=True)
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting portfolio data: {str(e)}")
            logger.error(f"Parameters received: {params}")
            raise

    def calculate_portfolio_total_metrics(self, data, params):
        """Calculate portfolio-wide metrics."""
        if params['chart_type'] == 'dollar_value':
            # Simple sum for dollar values
            return data.groupby('date')['total_return'].sum().reset_index()
        else:  # percentage
            # Calculate weighted return
            grouped = data.groupby('date').agg({
                'total_return': 'sum',
                'market_value': 'sum'
            }).reset_index()
            grouped['value'] = grouped['total_return'] / grouped['market_value'] * 100
            return grouped

    def calculate_deltas(self, data, params):
        """Calculate day-over-day changes."""
        if params['view_type'] == 'individual_stocks':
            # Calculate deltas for each stock
            for stock in data['stock'].unique():
                mask = data['stock'] == stock
                base_col = params['metric'].replace('_delta', '')
                data.loc[mask, 'value'] = data.loc[mask, base_col].diff()
        else:
            # Calculate deltas for portfolio total
            data['value'] = data['value'].diff()
        
        return data

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
            
            if study_type == "market_value":
                self.plot_market_value(ax, params)
            elif study_type == "profitability":
                self.plot_profitability(ax, params)
            elif study_type == "dividend_performance":
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
        """
        Plot market value analysis with proper handling of weekend/holiday data.
        Uses forward fill to maintain last known values for non-trading days.
        
        Args:
            ax: Matplotlib axis object for plotting
            params: Dictionary containing plot parameters including view_type and chart_type
        """
        # Add debug logging
        logger.debug(f"Market Value plot parameters: {params}")
        
        # Create a copy of the data to avoid modifying the original
        plot_data = self.data.copy()
        
        # Convert date column to datetime if not already
        plot_data['date'] = pd.to_datetime(plot_data['date'])
        
        # Set multi-index using both date and stock
        plot_data.set_index(['date', 'stock'], inplace=True)
        
        # Unstack to get stock as columns, then resample to daily frequency and forward fill
        plot_data = plot_data['market_value'].unstack()
        plot_data = plot_data.asfreq('D').ffill()
        
        # Check view type using the correct mapped value
        if params['view_type'] == "individual_stocks":  # This should match the value in config.yaml
            # Plot individual stock values
            for stock in params['selected_stocks']:
                if stock in plot_data.columns:
                    ax.plot(plot_data.index, plot_data[stock], 
                        label=stock, linewidth=1.5)
                    
        else:  # Portfolio Total
            # Check chart type using the correct mapped value
            if params['chart_type'] == "line_chart":  # This should match the value in config.yaml
                # Sum market values by date using the forward-filled values
                portfolio_total = plot_data.sum(axis=1)
                ax.plot(plot_data.index, portfolio_total.values,
                    label='Total Portfolio', linewidth=2)
            elif params['chart_type'] == "stacked_area":  # This should match the value in config.yaml
                # Fill any remaining NaN values with 0 for stacking
                plot_data = plot_data.fillna(0)
                
                # Ensure all stocks are properly aligned
                sorted_columns = sorted(plot_data.columns)
                plot_data = plot_data[sorted_columns]
                
                # Create the stacked area plot
                ax.stackplot(plot_data.index, 
                            [plot_data[col] for col in plot_data.columns],
                            labels=plot_data.columns,
                            alpha=0.8)
            
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
        """
        Plot profitability analysis with proper date axis formatting.
        """
        try:
            view_type = params['view_type']
            time_period = params['calculation_type']  # 'daily' or 'cumulative'
            chart_type = params['chart_type']
            
            # Convert dates to datetime if they aren't already
            self.data['date'] = pd.to_datetime(self.data['date'])
            
            # Determine which metric to use
            if chart_type == 'dollar_value':
                metric = 'daily_pl' if time_period == 'daily' else 'total_return'
                ylabel = "Return ($)"
                value_format = lambda x, p: f'${x:,.0f}'
            elif chart_type == 'percentage':
                metric = 'daily_pl_pct' if time_period == 'daily' else 'total_return_pct'
                ylabel = "Return (%)"
                value_format = lambda x, p: f'{x:.1f}%'
            else:  # aggregated_percentage
                metric = 'cumulative_return_pct'
                ylabel = "Return (%)"
                value_format = lambda x, p: f'{x:.1f}%'
            
            if view_type == 'individual_stocks':
                for stock in params['selected_stocks']:
                    stock_data = self.data[self.data['stock'] == stock].copy()
                    ax.plot(stock_data['date'], stock_data[metric], label=stock)
            else:  # portfolio_total
                if chart_type == 'percentage':
                    # Calculate portfolio percentage return
                    grouped = self.data.groupby('date').agg({
                        'total_return': 'sum',
                        'market_value': 'sum'
                    })
                    y_values = grouped['total_return'] / grouped['market_value'] * 100
                else:
                    grouped = self.data.groupby('date')[metric].sum()
                    y_values = grouped
                    
                ax.plot(grouped.index, y_values.values, label='Portfolio Total', linewidth=2)
            
            # Add zero line for reference
            ax.axhline(y=0, color='r', linestyle='--', alpha=0.3)
            
            # Set axis limits based on actual data range
            min_date = self.data['date'].min()
            max_date = self.data['date'].max()
            ax.set_xlim(min_date, max_date)
            
            period_type = 'Daily' if time_period == 'daily' else 'Cumulative'
            ax.set_title(f"Portfolio {period_type} Returns")
            ax.set_xlabel("Date")
            ax.set_ylabel(ylabel)
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            ax.grid(True, alpha=0.3)
            
            # Format axes
            self.setup_date_axis(ax)
            ax.yaxis.set_major_formatter(plt.FuncFormatter(value_format))
            
        except Exception as e:
            logger.error(f"Error plotting profitability: {str(e)}")
            logger.exception("Detailed traceback:")
            raise

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

    def get_active_stocks_for_date_range(self, start_date, end_date):
        """
        Get stocks that have at least one non-zero market value within the date range.
        Uses the portfolio_stocks linking table to find stocks associated with the current portfolio.
        
        Args:
            start_date (datetime): Start date for filtering
            end_date (datetime): End date for filtering
                
        Returns:
            list: List of stock objects that have market activity in the date range
        """
        try:
            logger.debug(f"Fetching active stocks between {start_date} and {end_date}")
            logger.debug(f"Current portfolio ID: {self.current_portfolio.id}")
            
            # Modified query to use portfolio_stocks linking table
            query = """
                WITH stock_activity AS (
                    SELECT 
                        s.id,
                        s.yahoo_symbol,
                        s.name,
                        COUNT(*) as total_days,
                        SUM(CASE WHEN fm.market_value > 0 THEN 1 ELSE 0 END) as active_days,
                        MAX(fm.market_value) as max_value
                    FROM stocks s
                    JOIN portfolio_stocks ps ON s.id = ps.stock_id
                    JOIN final_metrics fm ON s.id = fm.stock_id
                    WHERE fm.date BETWEEN :start_date AND :end_date
                    AND ps.portfolio_id = :portfolio_id
                    GROUP BY s.id, s.yahoo_symbol, s.name
                )
                SELECT 
                    id,
                    yahoo_symbol,
                    name,
                    total_days,
                    active_days,
                    max_value
                FROM stock_activity
                WHERE active_days > 0
                ORDER BY yahoo_symbol;
            """
            
            params = {
                'start_date': start_date,
                'end_date': end_date,
                'portfolio_id': self.current_portfolio.id
            }
            
            logger.debug(f"Executing query with params: {params}")
            results = self.db_manager.fetch_all_with_params(query, params)
            logger.debug(f"Query returned {len(results)} results")
            
            # Log detailed information about each stock found
            # Note: results are tuples with indices:
            # 0: id, 1: yahoo_symbol, 2: name, 3: total_days, 4: active_days, 5: max_value
            for row in results:
                logger.debug(f"Stock {row[1]}: "  # row[1] is yahoo_symbol
                            f"Total days: {row[3]}, "  # row[3] is total_days
                            f"Active days: {row[4]}, "  # row[4] is active_days
                            f"Max value: {row[5]}")    # row[5] is max_value
            
            # Convert results to stock objects
            active_stocks = []
            for row in results:
                stock = self.current_portfolio.get_stock(row[1])  # row[1] is yahoo_symbol
                if stock:
                    active_stocks.append(stock)
                    logger.debug(f"Added stock {stock.yahoo_symbol} to active stocks list")
                else:
                    logger.warning(f"Stock {row[1]} found in database but not in portfolio")
            
            logger.debug(f"Returning {len(active_stocks)} active stocks")
            return active_stocks
                
        except Exception as e:
            logger.error(f"Error getting active stocks: {str(e)}")
            logger.exception("Detailed traceback:")
            return []
    
    def get_view(self):
        """Return the view instance."""
        return self.view