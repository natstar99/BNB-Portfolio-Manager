# File: views/portfolio_study_view.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QLabel, QListWidget, QComboBox, QMessageBox,
                              QTabWidget, QRadioButton, QButtonGroup, QScrollArea,
                              QFrame, QGridLayout, QGroupBox, QDateEdit, QSpinBox,
                              QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Signal, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from datetime import datetime, timedelta

class PortfolioStudyView(QWidget):
    """
    View for analysing portfolio performance using historical data.
    Provides various visualisations and statistics for portfolio analysis.
    """
    update_plot = Signal(dict)  # Emits analysis parameters
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """Initialise the user interface components."""
        layout = QVBoxLayout(self)
        
        # Create main horizontal layout
        main_layout = QHBoxLayout()
        
        # Left panel - Controls
        control_panel = QScrollArea()
        control_panel.setWidgetResizable(True)
        control_panel.setMaximumWidth(300)
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        
        # Date range selection
        date_group = QGroupBox("Date Range")
        date_layout = QGridLayout()
        
        date_layout.addWidget(QLabel("From:"), 0, 0)
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        date_layout.addWidget(self.start_date, 0, 1)
        
        date_layout.addWidget(QLabel("To:"), 1, 0)
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(datetime.now())
        date_layout.addWidget(self.end_date, 1, 1)
        
        date_group.setLayout(date_layout)
        control_layout.addWidget(date_group)
        
        # Stock selection
        stocks_group = QGroupBox("Select Stocks")
        stocks_layout = QVBoxLayout()
        self.stock_list = QListWidget()
        self.stock_list.setSelectionMode(QListWidget.ExtendedSelection)
        stocks_layout.addWidget(self.stock_list)
        
        # Quick selection buttons
        button_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(lambda: self.stock_list.selectAll())
        button_layout.addWidget(select_all_btn)
        
        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.clicked.connect(lambda: self.stock_list.clearSelection())
        button_layout.addWidget(clear_all_btn)
        
        stocks_layout.addLayout(button_layout)
        stocks_group.setLayout(stocks_layout)
        control_layout.addWidget(stocks_group)
        
        # Analysis options
        analysis_group = QGroupBox("Analysis Options")
        analysis_layout = QVBoxLayout()
        
        self.view_mode = QComboBox()
        self.view_mode.addItems([
            "Portfolio Value",
            "Individual Stocks",
            "Combined View"
        ])
        analysis_layout.addWidget(QLabel("View Mode:"))
        analysis_layout.addWidget(self.view_mode)
        
        self.chart_type = QComboBox()
        self.chart_type.addItems([
            "Line Chart",
            "Stacked Area",
            "Portfolio Distribution",
            "Performance Comparison"
        ])
        analysis_layout.addWidget(QLabel("Chart Type:"))
        analysis_layout.addWidget(self.chart_type)
        
        self.value_type = QComboBox()
        self.value_type.addItems([
            "Market Value",
            "Profit/Loss",
            "Percentage Return",
            "Total Return (incl. Dividends)"
        ])
        analysis_layout.addWidget(QLabel("Value Type:"))
        analysis_layout.addWidget(self.value_type)
        
        analysis_group.setLayout(analysis_layout)
        control_layout.addWidget(analysis_group)
        
        # Metrics to show
        metrics_group = QGroupBox("Show Metrics")
        metrics_layout = QVBoxLayout()
        
        self.show_dividends = QRadioButton("Include Dividends")
        self.show_dividends.setChecked(True)
        metrics_layout.addWidget(self.show_dividends)
        
        self.show_drp = QRadioButton("Show DRP Impact")
        metrics_layout.addWidget(self.show_drp)
        
        self.show_benchmark = QRadioButton("Compare to Benchmark")
        metrics_layout.addWidget(self.show_benchmark)
        
        metrics_group.setLayout(metrics_layout)
        control_layout.addWidget(metrics_group)
        
        # Update button
        update_btn = QPushButton("Update Analysis")
        update_btn.clicked.connect(self.update_analysis)
        control_layout.addWidget(update_btn)
        
        control_panel.setWidget(control_widget)
        main_layout.addWidget(control_panel)
        
        # Right panel - Analysis display
        display_panel = QTabWidget()
        
        # Charts tab
        charts_tab = QWidget()
        charts_layout = QVBoxLayout(charts_tab)
        
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        charts_layout.addWidget(self.canvas)
        
        display_panel.addTab(charts_tab, "Charts")
        
        # Statistics tab
        stats_tab = QWidget()
        stats_layout = QVBoxLayout(stats_tab)
        
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        stats_layout.addWidget(self.stats_table)
        
        display_panel.addTab(stats_tab, "Statistics")
        
        # Portfolio Composition tab
        composition_tab = QWidget()
        composition_layout = QVBoxLayout(composition_tab)
        
        self.composition_figure = Figure(figsize=(10, 6))
        self.composition_canvas = FigureCanvas(self.composition_figure)
        composition_layout.addWidget(self.composition_canvas)
        
        display_panel.addTab(composition_tab, "Portfolio Composition")
        
        main_layout.addWidget(display_panel)
        
        # Set the main layout
        layout.addLayout(main_layout)
    
    def update_analysis(self):
        """Collect current settings and emit signal to update analysis."""
        params = {
            'start_date': self.start_date.date().toPython(),
            'end_date': self.end_date.date().toPython(),
            'selected_stocks': [item.text() for item in self.stock_list.selectedItems()],
            'view_mode': self.view_mode.currentText(),
            'chart_type': self.chart_type.currentText(),
            'value_type': self.value_type.currentText(),
            'show_dividends': self.show_dividends.isChecked(),
            'show_drp': self.show_drp.isChecked(),
            'show_benchmark': self.show_benchmark.isChecked()
        }
        
        self.update_plot.emit(params)
    
    def update_portfolio_stocks(self, stocks):
        """Update the list of available portfolio stocks."""
        self.stock_list.clear()
        for stock in stocks:
            self.stock_list.addItem(f"{stock.yahoo_symbol} ({stock.name})")
            
        # Set earliest date based on portfolio data
        earliest_date = min(stock.transactions[0].date for stock in stocks if stock.transactions)
        self.start_date.setDate(earliest_date)