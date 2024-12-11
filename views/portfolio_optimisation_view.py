# File: views/portfolio_optimisation_view.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QLabel, QListWidget, QComboBox, QMessageBox,
                              QLineEdit, QFormLayout, QScrollArea, QGroupBox,
                              QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Signal
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class PortfoliooptimisationView(QWidget):
    """
    View for portfolio optimisation analysis.
    Allows users to optimise their portfolio using different criteria and visualise the results.
    """
    optimise_portfolio = Signal(list)  # Emits [selected_tickers, optimisation_criteria, period]
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """Initialise the user interface components."""
        layout = QVBoxLayout(self)
        
        # Title and description
        title = QLabel("Portfolio Optimisation")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        description = QLabel(
            "Optimise your portfolio using different criteria. Select stocks from your "
            "portfolio or enter additional tickers to include in the optimisation."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        
        # Stock selection section
        selection_layout = QHBoxLayout()
        
        # Portfolio stocks list
        portfolio_group = QGroupBox("Portfolio Stocks")
        portfolio_layout = QVBoxLayout()
        self.portfolio_list = QListWidget()
        self.portfolio_list.setSelectionMode(QListWidget.ExtendedSelection)
        portfolio_layout.addWidget(self.portfolio_list)
        portfolio_group.setLayout(portfolio_layout)
        selection_layout.addWidget(portfolio_group)
        
        # Configuration group
        config_group = QGroupBox("Optimisation Settings")
        config_layout = QFormLayout()
        
        # Custom tickers input
        self.custom_tickers = QLineEdit()
        self.custom_tickers.setPlaceholderText("Enter tickers separated by commas")
        config_layout.addRow("Additional Tickers:", self.custom_tickers)
        
        # optimisation criteria
        self.criteria_combo = QComboBox()
        self.criteria_combo.addItems([
            "All Criteria",
            "Sharpe Ratio",
            "Conditional Value at Risk (CVaR)",
            "Sortino Ratio",
            "Minimum Variance"
        ])
        config_layout.addRow("Optimisation Criteria:", self.criteria_combo)
        
        # Analysis period
        self.period_combo = QComboBox()
        self.period_combo.addItems([
            "1 Year",
            "3 Years",
            "5 Years",
            "10 Years"
        ])
        config_layout.addRow("Analysis Period:", self.period_combo)
        
        config_group.setLayout(config_layout)
        selection_layout.addWidget(config_group)
        
        layout.addLayout(selection_layout)
        
        # optimise button
        self.optimise_btn = QPushButton("Optimise Portfolio")
        self.optimise_btn.clicked.connect(self.on_optimise_clicked)
        layout.addWidget(self.optimise_btn)
        
        # Results section
        results_group = QGroupBox("Optimisation Results")
        results_layout = QVBoxLayout()
        
        # Table for weights and statistics
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels([
            "Metric", "Sharpe", "CVaR", "Sortino", "Min Variance"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        results_layout.addWidget(self.results_table)
        
        # Efficient frontier plot
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        results_layout.addWidget(self.canvas)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
    def update_portfolio_stocks(self, stocks):
        """Update the list of available portfolio stocks."""
        self.portfolio_list.clear()
        for stock in stocks:
            self.portfolio_list.addItem(f"{stock.yahoo_symbol} ({stock.name})")
    
    def on_optimise_clicked(self):
        """Handle the optimise button click."""
        selected_tickers = []
        
        # Get selected portfolio stocks
        for item in self.portfolio_list.selectedItems():
            symbol = item.text().split(" (")[0]
            selected_tickers.append(symbol)
        
        # Get custom tickers
        custom_text = self.custom_tickers.text().strip()
        if custom_text:
            custom_tickers = [t.strip().upper() for t in custom_text.split(",")]
            selected_tickers.extend(custom_tickers)
        
        if len(selected_tickers) < 2:
            QMessageBox.warning(
                self,
                "Insufficient Stocks",
                "Please select at least two stocks for portfolio optimisation."
            )
            return
        
        # Get optimisation criteria and period
        criteria = self.criteria_combo.currentText()
        period = self.period_combo.currentText()
        
        # Emit signal with parameters
        self.optimise_portfolio.emit([selected_tickers, criteria, period])
    
    def update_results(self, weights_data, statistics_data, efficient_frontier_data):
        """
        Update the results display with optimisation results.
        
        Args:
            weights_data: Dictionary of optimal weights for each method
            statistics_data: Dictionary of statistics for each method
            efficient_frontier_data: Tuple of (returns, volatilities, optimal_points)
        """
        # Update results table
        self.update_results_table(weights_data, statistics_data)
        
        # Update efficient frontier plot
        self.plot_efficient_frontier(efficient_frontier_data)
        
    def update_results_table(self, weights_data, statistics_data):
        """Update the results table with optimisation results."""
        # Clear existing table
        self.results_table.setRowCount(0)
        
        # Add weights section
        self.results_table.setRowCount(len(weights_data['symbols']) + len(statistics_data))
        
        # Add weights rows
        for i, symbol in enumerate(weights_data['symbols']):
            self.results_table.setItem(i, 0, QTableWidgetItem(symbol))
            for j, method in enumerate(['Sharpe', 'CVaR', 'Sortino', 'Min Variance']):
                weight = weights_data[method][i]
                self.results_table.setItem(i, j+1, 
                    QTableWidgetItem(f"{weight*100:.2f}%" if weight >= 0.0001 else "0%"))
        
        # Add statistics rows
        row = len(weights_data['symbols'])
        for stat_name, stat_values in statistics_data.items():
            self.results_table.setItem(row, 0, QTableWidgetItem(stat_name))
            for j, value in enumerate(stat_values):
                self.results_table.setItem(row, j+1, 
                    QTableWidgetItem(f"{value:.4f}"))
            row += 1
    
    def plot_efficient_frontier(self, data):
        """Plot the efficient frontier and optimal portfolios."""
        returns, volatilities, optimal_points = data
        
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # Plot efficient frontier
        scatter = ax.scatter(volatilities, returns, c='lightgray', alpha=0.5)
        
        # Plot optimal portfolios
        colors = {'Sharpe': 'red', 'CVaR': 'blue', 'Sortino': 'green', 'Min Variance': 'purple'}
        for method, point in optimal_points.items():
            ax.scatter(point[0], point[1], color=colors[method], s=100, label=method)
        
        ax.set_xlabel('Volatility (Risk)')
        ax.set_ylabel('Expected Return')
        ax.set_title('Efficient Frontier and Optimal Portfolios')
        ax.legend()
        
        self.canvas.draw()