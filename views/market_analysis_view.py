# File: views/market_analysis_view.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QLabel, QListWidget, QComboBox, QMessageBox,
                              QLineEdit, QTabWidget)
from PySide6.QtCore import Signal
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class MarketAnalysisView(QWidget):
    """
    View for analysing market correlations and other metrics.
    Allows users to select stocks from their portfolio or enter custom tickers.
    """
    analyse_correlation = Signal(list)  # Emits list of selected tickers
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """Initialise the user interface components."""
        layout = QVBoxLayout(self)
        
        # Add tab widget for different analysis tools
        self.tab_widget = QTabWidget()
        
        # Create correlation analysis tab
        correlation_tab = QWidget()
        correlation_layout = QVBoxLayout(correlation_tab)
        
        # Title and description for correlation tab
        title = QLabel("Market Correlation Analysis")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        correlation_layout.addWidget(title)
        
        description = QLabel(
            "Analyse market correlations between stocks. Select stocks from your "
            "portfolio or enter additional tickers to compare."
        )
        description.setWordWrap(True)
        correlation_layout.addWidget(description)
        
        # Create main horizontal layout for left/right split
        main_horizontal_layout = QHBoxLayout()
        
        # Left side - Controls (15%)
        left_controls_layout = QVBoxLayout()
        
        # Portfolio stocks list
        left_controls_layout.addWidget(QLabel("Portfolio Stocks:"))
        self.portfolio_list = QListWidget()
        self.portfolio_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.portfolio_list.setMinimumHeight(200)  # Reduced height for compact layout
        left_controls_layout.addWidget(self.portfolio_list)
        
        # Custom tickers input
        left_controls_layout.addWidget(QLabel("Additional Tickers:"))
        self.custom_tickers = QLineEdit()
        self.custom_tickers.setPlaceholderText("Enter tickers separated by commas")
        left_controls_layout.addWidget(self.custom_tickers)
        
        # Analysis period
        left_controls_layout.addWidget(QLabel("Analysis Period:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems(["1 Month", "3 Months", "6 Months", "1 Year", "3 Years", "5 Years"])
        self.period_combo.setCurrentText("1 Year")
        left_controls_layout.addWidget(self.period_combo)
        
        # Analysis button
        self.analyse_btn = QPushButton("Generate Correlation Matrix")
        self.analyse_btn.clicked.connect(self.on_analyse_clicked)
        left_controls_layout.addWidget(self.analyse_btn)
        
        # Add stretch to push controls to top
        left_controls_layout.addStretch()
        
        # Right side - Correlation matrix (85%)
        right_plot_layout = QVBoxLayout()
        
        # Matplotlib figure for displaying the correlation matrix
        self.figure = Figure(figsize=(10, 8))
        self.canvas = FigureCanvas(self.figure)
        right_plot_layout.addWidget(self.canvas)
        
        # Add left and right layouts to main horizontal layout
        main_horizontal_layout.addLayout(left_controls_layout)
        main_horizontal_layout.addLayout(right_plot_layout)
        
        # Set proportions: 15% for controls, 85% for plot
        main_horizontal_layout.setStretch(0, 15)
        main_horizontal_layout.setStretch(1, 85)
        
        correlation_layout.addLayout(main_horizontal_layout)
        
        # Set the layout for the correlation tab
        correlation_tab.setLayout(correlation_layout)
        
        # Add the correlation tab to the tab widget
        self.tab_widget.addTab(correlation_tab, "Correlation Analysis")
        
        
        # Portfolio vs Indices tab
        from views.portfolio_visualisation_view import PortfolioVisualisationView
        self.visualisation_view = PortfolioVisualisationView()
        self.tab_widget.addTab(self.visualisation_view, "Portfolio vs Indices")
        
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)
        
    def update_portfolio_stocks(self, stocks):
        """Update the list of available portfolio stocks."""
        self.portfolio_list.clear()
        for stock in stocks:
            self.portfolio_list.addItem(f"{stock.yahoo_symbol} ({stock.name})")
    
    def on_analyse_clicked(self):
        """Handle the analyse button click."""
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
                "Please select at least two stocks for correlation analysis."
            )
            return
        
        # Get analysis period
        period = self.period_combo.currentText()
        
        # Emit signal with selected tickers and period
        self.analyse_correlation.emit([selected_tickers, period])
    
    def plot_correlation_matrix(self, correlation_matrix):
        """
        Plot the correlation matrix using seaborn heatmap.
        
        Args:
            correlation_matrix: Pandas DataFrame containing the correlation matrix
        """
        try:
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            
            # Create heatmap
            im = ax.imshow(correlation_matrix.values, aspect='auto', cmap='coolwarm')
            
            # Add colorbar
            self.figure.colorbar(im)
            
            # Add labels
            ax.set_xticks(range(len(correlation_matrix.columns)))
            ax.set_yticks(range(len(correlation_matrix.index)))
            ax.set_xticklabels(correlation_matrix.columns, rotation=45, ha='right')
            ax.set_yticklabels(correlation_matrix.index)
            
            # Add correlation values in cells
            for i in range(len(correlation_matrix.index)):
                for j in range(len(correlation_matrix.columns)):
                    text = ax.text(j, i, f'{correlation_matrix.iloc[i, j]:.2f}',
                                 ha='center', va='center')
            
            ax.set_title("Stock Returns Correlation Matrix")
            self.figure.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Plot Error",
                f"Failed to plot correlation matrix: {str(e)}"
            )