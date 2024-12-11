# File: views/portfolio_visualisation_view.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QLabel, QListWidget, QComboBox, QMessageBox,
                              QLineEdit, QSpinBox, QDoubleSpinBox, QGridLayout,
                              QScrollArea, QFrame)
from PySide6.QtCore import Signal, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class PortfolioVisualisationView(QWidget):
    """
    View for visualising stock prices and portfolio performance.
    Allows users to select stocks and their weights to see combined performance.
    """
    plot_portfolio = Signal(dict)  # Emits dict of {symbol: weight}
    
    def __init__(self):
        super().__init__()
        self.stock_weights = {}  # Store stock weights
        self.init_ui()
        
    def init_ui(self):
        """Initialise the user interface components."""
        layout = QVBoxLayout(self)
        
        # Title and description
        title = QLabel("Portfolio Performance Visualisation")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        description = QLabel(
            "Compare individual stock performances and see the combined portfolio "
            "performance based on your chosen weights."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        
        # Create horizontal layout for list and settings
        content_layout = QHBoxLayout()
        
        # Left side - Stock selection and weights
        left_layout = QVBoxLayout()
        
        # Portfolio stocks list with weights
        left_layout.addWidget(QLabel("Select Stocks and Set Weights:"))
        
        # Scrollable area for stock weights
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        self.weights_layout = QGridLayout(scroll_content)
        self.weights_layout.setColumnStretch(1, 1)  # Make weight column stretch
        
        # Headers
        self.weights_layout.addWidget(QLabel("Stock"), 0, 0)
        self.weights_layout.addWidget(QLabel("Weight (%)"), 0, 1)
        
        scroll.setWidget(scroll_content)
        left_layout.addWidget(scroll)
        
        # Additional stocks input
        left_layout.addWidget(QLabel("Additional Tickers:"))
        self.custom_tickers = QLineEdit()
        self.custom_tickers.setPlaceholderText("Enter tickers separated by commas")
        left_layout.addWidget(self.custom_tickers)
        
        # Add stock button
        self.add_stock_btn = QPushButton("Add Stocks")
        self.add_stock_btn.clicked.connect(self.add_custom_stocks)
        left_layout.addWidget(self.add_stock_btn)
        
        # Analysis period
        left_layout.addWidget(QLabel("Analysis Period:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems([
            "1 Month", "3 Months", "6 Months", "1 Year", 
            "3 Years", "5 Years", "10 Years"
        ])
        self.period_combo.setCurrentText("1 Year")
        left_layout.addWidget(self.period_combo)
        
        # Base amount input
        left_layout.addWidget(QLabel("Initial Investment ($):"))
        self.base_amount = QSpinBox()
        self.base_amount.setRange(1000, 1000000)
        self.base_amount.setSingleStep(1000)
        self.base_amount.setValue(10000)
        left_layout.addWidget(self.base_amount)
        
        content_layout.addLayout(left_layout)
        
        # Right side - Plot
        right_layout = QVBoxLayout()
        
        # Plot options
        plot_options = QHBoxLayout()
        
        self.normalise_cb = QComboBox()
        self.normalise_cb.addItems([
            "Absolute Prices",
            "normalise to 100",
            "Percent Change"
        ])
        plot_options.addWidget(QLabel("Display:"))
        plot_options.addWidget(self.normalise_cb)
        
        self.show_individual_cb = QComboBox()
        self.show_individual_cb.addItems([
            "Show All",
            "Portfolio Only",
            "Individual Only"
        ])
        plot_options.addWidget(QLabel("Show:"))
        plot_options.addWidget(self.show_individual_cb)
        
        right_layout.addLayout(plot_options)
        
        # Matplotlib figure
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        right_layout.addWidget(self.canvas)
        
        content_layout.addLayout(right_layout)
        
        # Set the content layout proportions
        content_layout.setStretch(0, 1)  # Left side
        content_layout.setStretch(1, 2)  # Right side (plot)
        
        layout.addLayout(content_layout)
        
        # Update button
        self.update_btn = QPushButton("Update Plot")
        self.update_btn.clicked.connect(self.update_plot)
        layout.addWidget(self.update_btn)
        
    def add_custom_stocks(self):
        """Add custom stocks to the weights grid."""
        custom_text = self.custom_tickers.text().strip()
        if custom_text:
            tickers = [t.strip().upper() for t in custom_text.split(",")]
            for ticker in tickers:
                self.add_stock_to_grid(ticker)
            self.custom_tickers.clear()
    
    def add_stock_to_grid(self, stock_symbol, initial_weight=0.0):
        """Add a stock to the weights grid."""
        # Check if stock already exists
        for row in range(1, self.weights_layout.rowCount()):
            item = self.weights_layout.itemAtPosition(row, 0)
            if item and item.widget().text() == stock_symbol:
                return
        
        # Add new row
        row = self.weights_layout.rowCount()
        
        # Stock symbol
        self.weights_layout.addWidget(QLabel(stock_symbol), row, 0)
        
        # Weight input
        weight_spin = QDoubleSpinBox()
        weight_spin.setRange(0, 100)
        weight_spin.setValue(initial_weight)
        weight_spin.setSingleStep(5)
        weight_spin.setDecimals(1)
        weight_spin.setSuffix("%")
        weight_spin.valueChanged.connect(self.check_total_weight)
        self.weights_layout.addWidget(weight_spin, row, 1)
        
        # Delete button
        delete_btn = QPushButton("×")
        delete_btn.setMaximumWidth(30)
        delete_btn.clicked.connect(lambda: self.remove_stock(row))
        self.weights_layout.addWidget(delete_btn, row, 2)
        
        self.check_total_weight()
    
    def remove_stock(self, row):
        """Remove a stock from the weights grid."""
        # Remove widgets from the grid
        for col in range(3):
            item = self.weights_layout.itemAtPosition(row, col)
            if item:
                widget = item.widget()
                self.weights_layout.removeWidget(widget)
                widget.deleteLater()
        
        self.check_total_weight()
    
    def check_total_weight(self):
        """Check if weights sum to 100% and update button state."""
        total_weight = 0
        for row in range(1, self.weights_layout.rowCount()):
            item = self.weights_layout.itemAtPosition(row, 1)
            if item:
                weight_spin = item.widget()
                total_weight += weight_spin.value()
        
        # Enable update button only if weights sum to 100%
        self.update_btn.setEnabled(abs(total_weight - 100.0) < 0.1)
        
        # Update button text to show current total
        self.update_btn.setText(f"Update Plot (Total: {total_weight:.1f}%)")
    
    def update_plot(self):
        """Collect current settings and emit signal to update plot."""
        weights = {}
        for row in range(1, self.weights_layout.rowCount()):
            symbol_item = self.weights_layout.itemAtPosition(row, 0)
            weight_item = self.weights_layout.itemAtPosition(row, 1)
            
            if symbol_item and weight_item:
                symbol = symbol_item.widget().text()
                weight = weight_item.widget().value() / 100.0  # Convert to decimal
                weights[symbol] = weight
        
        plot_params = {
            'weights': weights,
            'period': self.period_combo.currentText(),
            'base_amount': self.base_amount.value(),
            'normalise': self.normalise_cb.currentText(),
            'show_mode': self.show_individual_cb.currentText()
        }
        
        self.plot_portfolio.emit(plot_params)
    
    def update_portfolio_stocks(self, stocks):
        """Update the list of available portfolio stocks."""
        # Clear existing stocks
        while self.weights_layout.rowCount() > 1:  # Keep header row
            self.remove_stock(1)
        
        # Add portfolio stocks
        for stock in stocks:
            self.add_stock_to_grid(stock.yahoo_symbol)