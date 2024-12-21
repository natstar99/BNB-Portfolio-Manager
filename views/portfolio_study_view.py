from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QLabel, QListWidget, QTabWidget, QButtonGroup,
                              QFrame, QGridLayout, QGroupBox, QDateEdit,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QRadioButton)
from PySide6.QtCore import Signal, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PortfolioStudyView(QWidget):
    """
    Enhanced view for analyzing portfolio performance using historical data.
    Uses pre-calculated metrics from the portfolio_metrics table for efficient display.
    """
    update_plot = Signal(dict)  # Emits analysis parameters
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """Initialise the user interface with a cleaner, more intuitive layout."""
        layout = QVBoxLayout(self)
        
        # Create main horizontal layout
        main_layout = QHBoxLayout()
        
        # Left panel - Controls
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)
        
        # Right panel - Analysis display with tabs
        display_panel = self.create_display_panel()
        main_layout.addWidget(display_panel)
        
        # Set the main layout proportions
        main_layout.setStretch(0, 1)  # Control panel
        main_layout.setStretch(1, 3)  # Display panel
        
        layout.addLayout(main_layout)

    def create_control_panel(self):
        """Create the left control panel with study options and stock selection."""
        control_group = QGroupBox("Analysis Controls")
        control_layout = QVBoxLayout()
        
        # Date Range Selection
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
        
        # Study Type Selection
        study_group = QGroupBox("Study Type")
        study_layout = QVBoxLayout()
        
        self.study_type_buttons = QButtonGroup()
        study_types = [
            ("Market Value", "market_value"),
            ("Profitability", "profitability"),
            ("Dividend Performance", "dividends"),
            ("Portfolio Distribution", "distribution")
        ]
        
        for text, value in study_types:
            radio = QRadioButton(text)
            self.study_type_buttons.addButton(radio)
            study_layout.addWidget(radio)
        
        self.study_type_buttons.buttons()[0].setChecked(True)  # Default to Market Value
        study_group.setLayout(study_layout)
        control_layout.addWidget(study_group)
        
        # View Options (changes based on study type)
        self.view_options_group = QGroupBox("View Options")
        self.view_options_layout = QVBoxLayout()
        self.view_options_group.setLayout(self.view_options_layout)
        control_layout.addWidget(self.view_options_group)
        
        # Stock Selection
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
        
        # Update button
        update_btn = QPushButton("Update Analysis")
        update_btn.clicked.connect(self.update_analysis)
        control_layout.addWidget(update_btn)
        
        control_group.setLayout(control_layout)
        
        # Connect study type change signal
        self.study_type_buttons.buttonClicked.connect(self.update_view_options)
        
        return control_group

    def create_display_panel(self):
        """Create the right display panel with chart and statistics tabs."""
        display_panel = QTabWidget()
        
        # Charts tab
        charts_tab = QWidget()
        charts_layout = QVBoxLayout(charts_tab)
        
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        
        # Add matplotlib toolbar for interactivity
        from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
        self.toolbar = NavigationToolbar2QT(self.canvas, charts_tab)
        charts_layout.addWidget(self.toolbar)
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
        
        return display_panel

    def update_view_options(self, button):
        """Update the view options based on the selected study type."""
        # Clear existing options
        while self.view_options_layout.count():
            item = self.view_options_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        study_type = next(btn.text() for btn in self.study_type_buttons.buttons() if btn.isChecked())
        
        if study_type == "Market Value":
            # Add view type toggle
            self.add_radio_pair("View Type", "Individual Stocks", "Portfolio Total")
            
            # Add chart type toggle (only for Portfolio Total)
            self.add_radio_pair("Chart Type", "Line Chart", "Stacked Area")
            
        elif study_type == "Profitability":
            # Add view type toggle
            self.add_radio_pair("View Type", "Individual Stocks", "Portfolio Total")
            
            # Add metric type toggle
            self.add_radio_pair("Display Type", "Percentage", "Dollar Value")
            
            # Add time period toggle
            self.add_radio_pair("Time Period", "Daily Changes", "Cumulative")
            
        elif study_type == "Dividend Performance":
            # Add view type toggle
            self.add_radio_pair("View Type", "Cash Dividends", "DRP")
            
            # Add aggregation toggle
            self.add_radio_pair("Display", "Individual", "Cumulative")
            
        # Portfolio Distribution has no toggles as it's always a pie chart
        
        self.view_options_group.setVisible(study_type != "Portfolio Distribution")

    def add_radio_pair(self, label, option1, option2):
        """Helper method to add a pair of radio buttons with a label."""
        group = QGroupBox(label)
        layout = QHBoxLayout()
        
        radio1 = QRadioButton(option1)
        radio2 = QRadioButton(option2)
        radio1.setChecked(True)
        
        layout.addWidget(radio1)
        layout.addWidget(radio2)
        
        group.setLayout(layout)
        self.view_options_layout.addWidget(group)

    def update_portfolio_stocks(self, stocks):
        """Update the list of available portfolio stocks."""
        self.stock_list.clear()
        for stock in stocks:
            self.stock_list.addItem(f"{stock.yahoo_symbol} ({stock.name})")

    def update_analysis(self):
        """Collect current settings and emit signal to update analysis."""
        study_type = next(btn.text() for btn in self.study_type_buttons.buttons() if btn.isChecked())
        
        # Get selected stocks
        selected_stocks = [
            item.text().split(" (")[0] 
            for item in self.stock_list.selectedItems()
        ]
        
        # Base parameters
        params = {
            'start_date': self.start_date.date().toPython(),
            'end_date': self.end_date.date().toPython(),
            'selected_stocks': selected_stocks,
            'study_type': study_type
        }
        
        # Add view options based on study type
        if study_type != "Portfolio Distribution":
            for group in self.view_options_group.findChildren(QGroupBox):
                label = group.title()
                value = next(btn.text() for btn in group.findChildren(QRadioButton) if btn.isChecked())
                params[label.lower().replace(" ", "_")] = value
        
        self.update_plot.emit(params)