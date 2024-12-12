# File: views/portfolio_optimisation_view.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QLabel, QListWidget, QComboBox, QMessageBox,
                              QLineEdit, QFormLayout, QScrollArea, QGroupBox,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QAbstractItemView, QTabWidget, QSizePolicy)
from PySide6.QtCore import Signal, Qt
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
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        main_layout.setSpacing(0)  # Remove spacing between scroll area and window edges
        
        # Create container for title and description (outside scroll area)
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(10, 10, 10, 0)
        
        title = QLabel("Portfolio Optimisation")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title)
        
        description = QLabel(
            "Optimise your portfolio using different criteria. Select stocks from your "
            "portfolio or enter additional tickers to include in the optimisation."
        )
        description.setWordWrap(True)
        header_layout.addWidget(description)
        main_layout.addWidget(header)
        
        # Create scroll area for main content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Create main content widget
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(20)  # Spacing between sections
        
        # Stock selection section
        selection_layout = QHBoxLayout()
        
        # Portfolio stocks list
        portfolio_group = QGroupBox("Portfolio Stocks")
        portfolio_layout = QVBoxLayout()
        portfolio_layout.setContentsMargins(10, 10, 10, 10)
        self.portfolio_list = QListWidget()
        self.portfolio_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.portfolio_list.setFixedHeight(200)  # Fixed height for list
        portfolio_layout.addWidget(self.portfolio_list)
        portfolio_group.setLayout(portfolio_layout)
        selection_layout.addWidget(portfolio_group)
        
        # Configuration group
        config_group = QGroupBox("Optimisation Settings")
        config_layout = QFormLayout()
        config_layout.setContentsMargins(10, 10, 10, 10)
        
        # Custom tickers input
        self.custom_tickers = QLineEdit()
        self.custom_tickers.setPlaceholderText("Enter tickers separated by commas")
        config_layout.addRow("Additional Tickers:", self.custom_tickers)
        
        # Optimisation criteria
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
            "1 Year", "3 Years", "5 Years", "10 Years"
        ])
        config_layout.addRow("Analysis Period:", self.period_combo)
        
        config_group.setLayout(config_layout)
        selection_layout.addWidget(config_group)
        
        layout.addLayout(selection_layout)
        
        # Optimise button
        self.optimise_btn = QPushButton("Optimise Portfolio")
        self.optimise_btn.clicked.connect(self.on_optimise_clicked)
        self.optimise_btn.setFixedHeight(40)  # Make button more prominent
        layout.addWidget(self.optimise_btn)
        
        # Results section
        results_group = QGroupBox("Optimisation Results")
        results_layout = QVBoxLayout()
        results_layout.setContentsMargins(10, 10, 10, 10)
        
        # Tab widget for results
        self.results_tab_widget = QTabWidget()
        
        # Results table tab
        table_tab = QWidget()
        table_layout = QVBoxLayout(table_tab)
        table_layout.setContentsMargins(0, 10, 0, 0)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels([
            "Metric", "Sharpe", "CVaR", "Sortino", "Min Variance"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table_layout.addWidget(self.results_table)
        self.results_tab_widget.addTab(table_tab, "Optimisation Results")
        
        # Efficient frontier tab
        plot_tab = QWidget()
        plot_layout = QVBoxLayout(plot_tab)
        plot_layout.setContentsMargins(10, 10, 10, 10)
        self.figure = Figure(figsize=(10, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setFixedHeight(400)  # Fixed height for plot
        plot_layout.addWidget(self.canvas)
        self.results_tab_widget.addTab(plot_tab, "Efficient Frontier")
        
        results_layout.addWidget(self.results_tab_widget)
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        # Set the content widget in the scroll area
        scroll.setWidget(content_widget)
        
        # Add scroll area to main layout
        main_layout.addWidget(scroll)
        
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
            weights_data: Dictionary of optimal weights and analysis reports
            statistics_data: Dictionary of statistics for each method
            efficient_frontier_data: Tuple of (returns, volatilities, optimal_points)
        """
        # Update existing results table
        self.update_results_table(weights_data, statistics_data)
        
        # Update efficient frontier plot
        self.plot_efficient_frontier(efficient_frontier_data)
        
        # Add detailed analysis tabs
        self.update_analysis_tabs(weights_data)
        
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

    def update_analysis_tabs(self, weights_data):
        """
        Update the analysis tabs with detailed reports.
        
        Args:
            weights_data: Dictionary containing weights and analysis reports
        """
        # Clear existing analysis tabs
        while self.results_tab_widget.count() > 2:  # Keep main results and plot tabs
            self.results_tab_widget.removeTab(2)
        
        # Add tab for each optimisation method
        methods = ['Sharpe', 'CVaR', 'Sortino', 'Min Variance']
        for method in methods:
            if f"{method}_report" in weights_data:
                report = weights_data[f"{method}_report"]
                tab = self.create_analysis_tab(method, report)
                self.results_tab_widget.addTab(tab, f"{method} Analysis")

    def create_analysis_tab(self, method, report):
        """Create a tab displaying detailed analysis for an optimisation method."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(20)  # Add spacing between sections
        layout.setContentsMargins(10, 10, 10, 10)
        
        def setup_table(table):
            """Configure table to show all content without scrollbars."""
            # Calculate required height
            header_height = table.horizontalHeader().height()
            row_total_height = 0
            for i in range(table.rowCount()):
                row_total_height += 25  # Fixed row height
            
            # Set fixed height with some padding
            table.setFixedHeight(header_height + row_total_height + 5)
            
            # Disable scrollbars
            table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            
            # Make columns fit content
            header = table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.ResizeToContents)
            
            # Other settings
            table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            table.setAlternatingRowColors(True)
        
        def create_group(title, table):
            """Create a GroupBox containing a table with proper layout."""
            group = QGroupBox(title)
            group_layout = QVBoxLayout()
            group_layout.setContentsMargins(10, 10, 10, 10)
            group_layout.setSpacing(5)
            setup_table(table)
            group_layout.addWidget(table)
            group.setLayout(group_layout)
            return group
        
        # Portfolio Composition Section
        composition_table = QTableWidget()
        composition_table.setColumnCount(2)
        composition_table.setHorizontalHeaderLabels(["Symbol", "Weight"])
        composition_table.setRowCount(len(report['composition']))
        for i, (symbol, weight) in enumerate(report['composition'].items()):
            composition_table.setItem(i, 0, QTableWidgetItem(symbol))
            composition_table.setItem(i, 1, QTableWidgetItem(f"{weight*100:.2f}%"))
        layout.addWidget(create_group("Portfolio Composition", composition_table))
        
        # Statistics Section
        stats_table = QTableWidget()
        stats_table.setColumnCount(2)
        stats_table.setHorizontalHeaderLabels(["Metric", "Value"])
        stats_table.setRowCount(len(report['statistics']))
        for i, (metric, value) in enumerate(report['statistics'].items()):
            stats_table.setItem(i, 0, QTableWidgetItem(metric))
            stats_table.setItem(i, 1, QTableWidgetItem(f"{value:.4f}"))
        layout.addWidget(create_group("Portfolio Statistics", stats_table))
        
        # Risk Contributions Section
        risk_table = QTableWidget()
        risk_table.setColumnCount(4)
        risk_table.setHorizontalHeaderLabels([
            "Symbol", 
            "Marginal Contribution", 
            "Component Contribution",
            "Percentage Contribution"
        ])
        risk_data = report['risk_contributions']
        risk_table.setRowCount(len(risk_data['symbols']))
        for i, symbol in enumerate(risk_data['symbols']):
            risk_table.setItem(i, 0, QTableWidgetItem(symbol))
            risk_table.setItem(i, 1, QTableWidgetItem(f"{risk_data['marginal_contribution'][i]:.4f}"))
            risk_table.setItem(i, 2, QTableWidgetItem(f"{risk_data['component_contribution'][i]:.4f}"))
            risk_table.setItem(i, 3, QTableWidgetItem(f"{risk_data['percentage_contribution'][i]*100:.2f}%"))
        layout.addWidget(create_group("Risk Contributions", risk_table))
        
        # Monthly Analysis Section
        monthly_table = QTableWidget()
        monthly_table.setColumnCount(2)
        monthly_table.setHorizontalHeaderLabels(["Metric", "Value"])
        monthly_data = report['monthly_analysis']
        monthly_table.setRowCount(3)
        monthly_table.setItem(0, 0, QTableWidgetItem("Best Month"))
        monthly_table.setItem(0, 1, QTableWidgetItem(f"{monthly_data['best_month']*100:.2f}%"))
        monthly_table.setItem(1, 0, QTableWidgetItem("Worst Month"))
        monthly_table.setItem(1, 1, QTableWidgetItem(f"{monthly_data['worst_month']*100:.2f}%"))
        monthly_table.setItem(2, 0, QTableWidgetItem("Positive Months Ratio"))
        monthly_table.setItem(2, 1, QTableWidgetItem(f"{monthly_data['positive_months_ratio']*100:.2f}%"))
        layout.addWidget(create_group("Monthly Performance Analysis", monthly_table))
        
        # Add stretch at the end to prevent unnecessary expansion
        layout.addStretch()
        
        return tab