# File: views/portfolio_visualisation_view.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QLabel, QComboBox, QCheckBox, QGroupBox,
                              QFormLayout)
from PySide6.QtCore import Signal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

class PortfolioVisualisationView(QWidget):
    """
    View for comparing portfolio profitability against major market indices.
    Focuses on portfolio performance comparison rather than individual stock analysis.
    """
    plot_portfolio_vs_indices = Signal(dict)  # Emits plot parameters
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """Initialise the user interface components."""
        layout = QVBoxLayout(self)
        
        # Title and description
        title = QLabel("Portfolio vs Market Indices")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        description = QLabel(
            "Compare your portfolio's profitability against major market indices "
            "to understand relative performance and market correlation."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        
        # Create main horizontal layout for left/right split
        main_horizontal_layout = QHBoxLayout()
        
        # Left side - Settings and controls
        left_layout = QVBoxLayout()
        
        # Settings panel
        settings_group = QGroupBox("Analysis Settings")
        settings_layout = QFormLayout()
        
        # Analysis period
        self.period_combo = QComboBox()
        self.period_combo.addItems([
            "1 Month", "3 Months", "6 Months", "1 Year", 
            "2 Years", "3 Years", "5 Years", "All Time"
        ])
        self.period_combo.setCurrentText("1 Year")
        settings_layout.addRow("Time Period:", self.period_combo)
        
        # Profitability metric
        self.metric_combo = QComboBox()
        self.metric_combo.addItems([
            "Total Return (%)",
            "Daily P&L (%)",
            "Cumulative Return (%)"
        ])
        self.metric_combo.setCurrentText("Total Return (%)")
        settings_layout.addRow("Metric:", self.metric_combo)
        
        # Display options
        self.normalize_checkbox = QCheckBox("Start from zero (relative performance)")
        self.normalize_checkbox.setChecked(True)
        settings_layout.addRow("", self.normalize_checkbox)
        
        settings_group.setLayout(settings_layout)
        left_layout.addWidget(settings_group)
        
        # Market indices selection
        indices_group = QGroupBox("Market Indices to Compare")
        indices_layout = QVBoxLayout()
        
        # Create checkboxes for major indices
        self.index_checkboxes = {}
        indices_data = [
            ("^GSPC", "S&P 500 (US)"),
            ("^IXIC", "NASDAQ Composite (US)"),
            ("^DJI", "Dow Jones Industrial (US)"),
            ("^RUT", "Russell 2000 (US Small Cap)"),
            ("MSCI", "MSCI World Index"),
            ("^FTSE", "FTSE 100 (UK)"),
            ("^GDAXI", "DAX (Germany)"),
            ("^N225", "Nikkei 225 (Japan)"),
            ("000001.SS", "Shanghai Composite (China)"),
            ("^HSI", "Hang Seng (Hong Kong)"),
            ("^NSEI", "NIFTY 50 (India)"),
            ("^AXJO", "ASX 200 (Australia)")
        ]
        
        # Create checkboxes in a grid-like layout
        checkbox_layout = QVBoxLayout()
        for symbol, name in indices_data:
            checkbox = QCheckBox(f"{name} ({symbol})")
            # Default to showing major US indices
            if symbol in ["^GSPC", "^IXIC", "^DJI"]:
                checkbox.setChecked(True)
            self.index_checkboxes[symbol] = checkbox
            checkbox_layout.addWidget(checkbox)
        
        indices_layout.addLayout(checkbox_layout)
        indices_group.setLayout(indices_layout)
        left_layout.addWidget(indices_group)
        
        # Update button
        self.update_btn = QPushButton("Compare Portfolio Performance")
        self.update_btn.clicked.connect(self.update_plot)
        left_layout.addWidget(self.update_btn)
        
        # Add stretch to push controls to top
        left_layout.addStretch()
        
        # Right side - Plot
        right_layout = QVBoxLayout()
        
        # Matplotlib figure
        self.figure = Figure(figsize=(12, 8))
        self.canvas = FigureCanvas(self.figure)
        right_layout.addWidget(self.canvas)
        
        # Add left and right to main horizontal layout
        main_horizontal_layout.addLayout(left_layout)
        main_horizontal_layout.addLayout(right_layout)
        
        # Set proportions: 15% for controls, 85% for plot
        main_horizontal_layout.setStretch(0, 15)
        main_horizontal_layout.setStretch(1, 85)
        
        # Add main horizontal layout to main layout
        layout.addLayout(main_horizontal_layout)
        
    def update_plot(self):
        """Collect current settings and emit signal to update plot."""
        # Get selected indices
        selected_indices = []
        for symbol, checkbox in self.index_checkboxes.items():
            if checkbox.isChecked():
                selected_indices.append(symbol)
        
        # Build plot parameters
        plot_params = {
            'period': self.period_combo.currentText(),
            'metric': self.metric_combo.currentText(),
            'normalize': self.normalize_checkbox.isChecked(),
            'indices': selected_indices
        }
        
        self.plot_portfolio_vs_indices.emit(plot_params)
    
    def plot_results(self, portfolio_data, indices_data, params):
        """
        Plot portfolio performance against selected indices.
        
        Args:
            portfolio_data: DataFrame with portfolio performance data
            indices_data: Dict of DataFrames with index performance data
            params: Plot parameters dictionary
        """
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # Plot portfolio data
        if not portfolio_data.empty:
            ax.plot(portfolio_data.index, portfolio_data.values, 
                   linewidth=3, label='Your Portfolio', color='black')
        else:
            print("Warning: Portfolio data is empty - no portfolio line will be plotted")
        
        # Plot index data
        colors = ['#A23B72', '#F18F01', '#C73E1D', '#86A873', '#7209B7', 
                 '#F72585', '#4361EE', '#F77F00', '#FCBF49', '#90E0EF',
                 '#06FFA5', '#FFBE0B']
        
        for i, (symbol, data) in enumerate(indices_data.items()):
            if not data.empty:
                color = colors[i % len(colors)]
                # Get the display name for the index
                display_name = symbol
                for checkbox_symbol, checkbox in self.index_checkboxes.items():
                    if checkbox_symbol == symbol:
                        display_name = checkbox.text().split(' (')[0]
                        break
                
                ax.plot(data.index, data.values, 
                       linewidth=2, label=display_name, color=color, alpha=0.8)
        
        # Formatting
        ax.set_xlabel('Date')
        
        # All metrics are now percentages
        ax.set_ylabel('Return (%)')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1f}%'))
        
        ax.set_title(f'Portfolio vs Market Indices - {params["metric"]}')
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3)
        
        # Improve date formatting
        if len(portfolio_data) > 0:
            self.figure.autofmt_xdate()
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def update_portfolio_stocks(self, stocks):
        """Update when portfolio changes - no action needed for this view."""
        pass