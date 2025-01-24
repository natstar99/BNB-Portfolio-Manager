# File: views/portfolio_study_view.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QLabel, QListWidget, QTabWidget, QButtonGroup,
                              QFrame, QGridLayout, QGroupBox, QDateEdit,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QRadioButton, QMessageBox)
from PySide6.QtCore import Signal, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
from matplotlib.figure import Figure
from datetime import datetime
import logging
import yaml

logger = logging.getLogger(__name__)

class StudyViewConfig:
    """
    Manages the hierarchical configuration for the portfolio study view.
    Centralizes all option management and dependencies.
    """
    def __init__(self, config_data):
        """
        Initialise with configuration loaded from yaml.
        
        Args:
            config_data (dict): The loaded yaml configuration for portfolio_study_view
        """
        self.config = config_data
        self.current_selections = {
            'study_type': None,
            'view_type': None,
            'display_type': None,
            'time_period': None,
            'dividend_type': None
        }
        
    def get_available_options(self, level):
        """
        Get available options for a given level based on current selections.
        
        Args:
            level (str): The hierarchy level to get options for
            
        Returns:
            list: List of (key, display_name) tuples for available options
        """
        if level == 'study_type':
            return [(key, data['name']) for key, data in self.config['hierarchy'].items()]
            
        study_type = self.current_selections['study_type']
        if not study_type or study_type not in self.config['hierarchy']:
            return []
            
        current_level = self.config['hierarchy'][study_type]
        
        if level == 'view_type':
            if 'view_types' in current_level:
                return [(key, data['name']) for key, data in current_level['view_types'].items()]
            return []
            
        view_type = self.current_selections['view_type']
        if not view_type or 'view_types' not in current_level or view_type not in current_level['view_types']:
            return []
            
        current_level = current_level['view_types'][view_type]
        
        if level == 'chart_type' and 'chart_types' in current_level:
            return [(key, data['name']) for key, data in current_level['chart_types'].items()]
        
        chart_type = self.current_selections['chart_type']
        
        # Add this section for time_period options
        if level == 'time_period' and chart_type:
            if ('chart_types' in current_level and 
                chart_type in current_level['chart_types'] and
                'time_periods' in current_level['chart_types'][chart_type]):
                
                time_periods = current_level['chart_types'][chart_type]['time_periods']
                return [(key, name) for key, name in time_periods.items()]
        
        return []
    
    def set_selection(self, level, value):
        """
        Set selection for a level and clear dependent selections.
        
        Args:
            level (str): The hierarchy level being set
            value (str): The selected value
        """
        # Define level dependencies
        level_order = ['study_type', 'view_type', 'display_type', 'dividend_type', 'time_period']
        
        # Clear all dependent selections
        if level in level_order:
            idx = level_order.index(level)
            for dependent_level in level_order[idx+1:]:
                self.current_selections[dependent_level] = None
        
        self.current_selections[level] = value

    def get_selection(self, level):
        """
        Get current selection for a level.
        
        Args:
            level (str): The hierarchy level
            
        Returns:
            str: Currently selected value or None
        """
        return self.current_selections[level]


class StudyOptionGroup(QGroupBox):
    """
    A group box containing radio buttons for a specific level of options.
    Manages its own state and notifies parent of changes.
    """
    selection_changed = Signal(str, str)  # (level, selected_value)
    
    def __init__(self, level, title, parent=None):
        """
        Initialise option group.
        
        Args:
            level (str): The hierarchy level this group represents
            title (str): Display title for the group box
            parent (QWidget): Parent widget
        """
        super().__init__(title, parent)
        self.level = level
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.button_group = QButtonGroup(self)
        self.button_group.buttonClicked.connect(self.on_selection_changed)
        self.buttons = {}
    
    def update_options(self, options):
        """
        Update available options in the group.
        
        Args:
            options (list): List of (value, display_name) tuples
        """
        # Clear existing buttons
        for button in self.buttons.values():
            self.layout.removeWidget(button)
            self.button_group.removeButton(button)
            button.deleteLater()
        self.buttons.clear()
        
        # Add new buttons
        for value, display_name in options:
            button = QRadioButton(display_name)
            button.value = value  # Store value for reference
            self.buttons[value] = button
            self.layout.addWidget(button)
            self.button_group.addButton(button)
            
        self.setVisible(bool(options))
    
    def set_selection(self, value):
        """
        Set the currently selected option.
        
        Args:
            value (str): Value to select
        """
        if value in self.buttons:
            self.buttons[value].setChecked(True)
        else:
            # Clear selection if value not available
            self.button_group.setExclusive(False)
            for button in self.buttons.values():
                button.setChecked(False)
            self.button_group.setExclusive(True)
    
    def on_selection_changed(self, button):
        """Handle radio button selection change."""
        self.selection_changed.emit(self.level, button.value)


class PortfolioStudyView(QWidget):
    """
    Enhanced view for analyzing portfolio performance using historical data.
    Uses pre-calculated metrics from the final_metrics table for efficient display.
    """
    update_plot = Signal(dict)  # Emits analysis parameters
    
    def __init__(self):
        super().__init__()
        self.manual_update = False
        self.init_ui()
    
    def init_ui(self):
        """Initialise the user interface with a cleaner, more intuitive layout."""
        layout = QVBoxLayout(self)
        
        # Create main horizontal layout for control panel and display
        main_layout = QHBoxLayout()
        
        # Left panel - Controls
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)
        
        # Right panel - Analysis display with tabs
        display_panel = self.create_display_panel()
        main_layout.addWidget(display_panel)
        
        # Set the main layout proportions (1:3 ratio)
        main_layout.setStretch(0, 1)  # Control panel
        main_layout.setStretch(1, 3)  # Display panel
        
        layout.addLayout(main_layout)

    def create_control_panel(self):
        """Create the left control panel with study options and stock selection."""
        control_group = QGroupBox("Analysis Controls")
        control_layout = QVBoxLayout()
        
        # Load configuration
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
            study_config = config.get('portfolio_study_view', {})
        
        # Initialise configuration manager
        self.study_config = StudyViewConfig(study_config)
        
        # Create option groups
        self.option_groups = {
            'study_type': StudyOptionGroup('study_type', "Study Type"),
            'view_type': StudyOptionGroup('view_type', "View Type"),
            'chart_type': StudyOptionGroup('chart_type', "Chart Type"),
            'time_period': StudyOptionGroup('time_period', "Time Period"),
            'dividend_type': StudyOptionGroup('dividend_type', "Dividend Type")
        }
        
        # Connect signals and add option groups
        for group in self.option_groups.values():
            group.selection_changed.connect(self.on_option_selected)
            control_layout.addWidget(group)
            
            # After adding time_period group, add our zero start toggle
            if group.level == 'time_period':
                # Create a container for the zero start toggle without a title
                zero_container = QFrame()
                zero_layout = QVBoxLayout()
                zero_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins for better spacing
                
                # Create and configure the toggle button
                self.zero_start_button = QPushButton("Zero at Start Date")
                self.zero_start_button.setCheckable(True)
                self.zero_start_button.setChecked(False)
                self.zero_start_button.clicked.connect(self.on_zero_start_toggled)
                self.zero_start_button.setVisible(False)
                
                # Add button to container with some padding
                zero_layout.addSpacing(5)  # Add a small space above
                zero_layout.addWidget(self.zero_start_button)
                zero_layout.addSpacing(5)  # Add a small space below
                
                zero_container.setLayout(zero_layout)
                control_layout.addWidget(zero_container)
            
        # Initialise study type options
        study_options = self.study_config.get_available_options('study_type')
        self.option_groups['study_type'].update_options(study_options)
        
        # Date Range Selection
        date_group = QGroupBox("Date Range")
        date_layout = QGridLayout()
        
        date_layout.addWidget(QLabel("From:"), 0, 0)
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.dateChanged.connect(self.on_date_range_changed) # Connection to date_range triggered update
        date_layout.addWidget(self.start_date, 0, 1)
        
        date_layout.addWidget(QLabel("To:"), 1, 0)
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(datetime.now())
        self.end_date.dateChanged.connect(self.on_date_range_changed) # Connection to date_range triggered update
        date_layout.addWidget(self.end_date, 1, 1)
        
        date_group.setLayout(date_layout)
        control_layout.addWidget(date_group)
        
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
        return control_group

    def create_display_panel(self):
        """Create the right display panel with chart and statistics tabs."""
        display_panel = QTabWidget()
        
        # Charts tab
        charts_tab = QWidget()
        charts_layout = QVBoxLayout(charts_tab)
        
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        
        # Add matplotlib toolbar
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

    def on_option_selected(self, level, value):
        """
        Handle option selection at any level.
        
        Args:
            level (str): The hierarchy level that changed
            value (str): The newly selected value
        """
        # Store the new selection
        self.study_config.set_selection(level, value)
        
        # Get current study type
        study_type = self.study_config.get_selection('study_type')

        # Create filter for dividends (to avoid plotting dividends that don't pay dividends)
        if study_type == 'dividend_performance' and level == 'chart_type':
            # Get current date range
            start_date = self.start_date.date().toPython()
            end_date = self.end_date.date().toPython()
            
            # Update stock list considering dividend type
            if hasattr(self, 'controller'):
                active_stocks = self.controller.get_active_stocks_for_date_range(
                    start_date, 
                    end_date,
                    dividend_type=value  # Pass the selected chart type
                )
                self.update_portfolio_stocks(active_stocks)

        if not study_type:
            return
            
        # Get the configuration for current study type
        study_config = self.study_config.config['hierarchy'].get(study_type, {})
        
        # If study type changed, reset everything
        if level == 'study_type':

            # Clear all other selections
            self.study_config.current_selections = {
                'study_type': value,  # Keep new study type
                'view_type': None,
                'chart_type': None,
                'time_period': None,
                'dividend_type': None
            }
            # Reset UI groups
            for group_level, group in self.option_groups.items():
                if group_level != 'study_type':
                    group.update_options([])
                    group.set_selection(None)
            
            # Update view type options
            if 'view_types' in study_config:
                view_type_options = [
                    (key, data['name']) 
                    for key, data in study_config['view_types'].items()
                ]
                self.option_groups['view_type'].update_options(view_type_options)
            
            # Clear displays
            self.clear_plot()
            self.clear_statistics()
            
        elif level == 'view_type':
            # Clear dependent selections
            self.study_config.current_selections.update({
                'chart_type': None,
                'time_period': None
            })
            
            # Update chart type options based on view type
            view_config = study_config['view_types'].get(value, {})
            if 'chart_types' in view_config:
                chart_type_options = [
                    (key, data['name'])
                    for key, data in view_config['chart_types'].items()
                ]
                self.option_groups['chart_type'].update_options(chart_type_options)
                
            # Clear time period options until chart type is selected
            self.option_groups['time_period'].update_options([])
            
        elif level == 'chart_type':
            # Clear dependent selection
            self.study_config.current_selections['time_period'] = None
            
            # Get current view type
            view_type = self.study_config.get_selection('view_type')
            if view_type:
                # Update time period options based on chart type
                view_config = study_config['view_types'].get(view_type, {})
                chart_config = view_config.get('chart_types', {}).get(value, {})
                
                if 'time_periods' in chart_config:
                    time_period_options = [
                        (key, name) 
                        for key, name in chart_config['time_periods'].items()
                    ]
                    self.option_groups['time_period'].update_options(time_period_options)
        
        # Show/hide zero start button based on time period
        if level == 'time_period':
            # Show the button only if we're in cumulative mode
            self.zero_start_button.setVisible(value == 'cumulative')
            # Reset button state when changing modes
            self.zero_start_button.setChecked(False)

        # Update analysis if we have all required selections
        self.update_analysis_if_ready()

    def on_zero_start_toggled(self):
        """Handle toggling of the Zero at Start Date button."""
        logger.debug(f"Zero at start date toggled: {self.zero_start_button.isChecked()}")
        self.update_analysis_if_ready()

    def update_analysis_if_ready(self):
        """
        Check if we have all required selections and update analysis if we do.
        Validates selections and emits update signal with parameters.
        """
        study_type = self.study_config.get_selection('study_type')
        if not study_type:
            return
                
        # Validate stock selection
        selected_stocks = [
            item.text().split(" (")[0] 
            for item in self.stock_list.selectedItems()
        ]
        
        # Show warning only on manual update
        if not selected_stocks:
            if self.manual_update:
                QMessageBox.warning(
                    self,
                    "Selection Required",
                    "Please select at least one stock to analyze."
                )
            return
                
        # Build basic parameters
        params = {
            'start_date': self.start_date.date().toPython(),
            'end_date': self.end_date.date().toPython(),
            'selected_stocks': selected_stocks,
            'study_type': study_type
        }
        
        # Get all current selections
        view_type = self.study_config.get_selection('view_type')
        chart_type = self.study_config.get_selection('chart_type')
        time_period = self.study_config.get_selection('time_period')
        
        # Check required selections based on study type
        missing = []
        if study_type == 'market_value':
            if not view_type:
                missing.append('view_type')
            if view_type == 'portfolio_total' and not chart_type:
                missing.append('chart_type')
        elif study_type == 'profitability':
            if not view_type:
                missing.append('view_type')
            if not chart_type:
                missing.append('chart_type')
            if not time_period:
                missing.append('time_period')
        elif study_type == 'dividend_performance':
            if not view_type:
                missing.append('view_type')
            if not chart_type:
                missing.append('dividend_type')
            if not time_period:
                missing.append('time_period')
                
        # Show warning if missing required selections (only on manual update)
        if missing and self.manual_update:
            QMessageBox.warning(
                self,
                "Selection Required",
                f"Please select options for: {', '.join(missing).replace('_', ' ').title()}"
            )
            return
        elif missing:
            return

        # Add valid selections to parameters
        params.update({
            'view_type': view_type,
            'chart_type': chart_type,
            'time_period': time_period
        })
        
        # Add study-specific parameters
        if study_type == 'profitability':
            if view_type == 'individual_stocks':
                if chart_type == 'dollar_value':
                    # Use daily_pl for daily changes, total_return for cumulative
                    params['metric'] = 'daily_pl' if time_period == 'daily' else 'total_return'
                elif chart_type == 'percentage':
                    # Use daily_pl_pct for daily changes, total_return_pct for cumulative
                    params['metric'] = 'daily_pl_pct' if time_period == 'daily' else 'total_return_pct'
                elif chart_type == 'aggregated_percentage':
                    # Use cumulative_return_pct for both, will calculate delta in controller if needed
                    params['metric'] = 'cumulative_return_pct'
            else:  # portfolio_total
                if chart_type == 'dollar_value':
                    # For portfolio total, we'll sum these values
                    params['metric'] = 'daily_pl' if time_period == 'daily' else 'total_return'
                elif chart_type == 'percentage':
                    # Need both metrics to calculate percentage
                    params['metrics'] = ['total_return', 'market_value']

            params['calculation_type'] = time_period  # 'daily' or 'cumulative'
                
        elif study_type == 'dividend_performance':
            if chart_type == 'cash':
                params['metric'] = 'cash_dividends_total' if time_period == 'cumulative' else 'cash_dividend'
            elif chart_type == 'drp':
                params['metric'] = 'drp_shares_total' if time_period == 'cumulative' else 'drp_share'
            elif chart_type == 'combined':
                params['metric'] = ['cash_dividends_total', 'drp_shares_total'] if time_period == 'cumulative' else ['cash_dividend', 'drp_share']

        # Add zero_at_start parameter to the analysis parameters
        params.update({
            'zero_at_start': self.zero_start_button.isChecked() if hasattr(self, 'zero_start_button') else False
        })

        # Emit update signal with validated parameters
        self.update_plot.emit(params)

    def update_portfolio_stocks(self, stocks):
        """
        Update the list of available portfolio stocks in the selection list.
        
        Args:
            stocks: List of Stock objects to display
        """
        # Store scroll position
        scroll_pos = self.stock_list.verticalScrollBar().value()
        
        # Clear and update list
        self.stock_list.clear()
        for stock in stocks:
            self.stock_list.addItem(f"{stock.yahoo_symbol} ({stock.name})")
            
        # Restore scroll position
        self.stock_list.verticalScrollBar().setValue(scroll_pos)

    def update_analysis(self):
        """
        Manual update triggered by update button.
        Validates date range before proceeding.
        """
        # Validate date range
        start = self.start_date.date()
        end = self.end_date.date()
        
        if start > end:
            QMessageBox.warning(
                self,
                "Invalid Date Range",
                "Start date cannot be after end date."
            )
            return
            
        if end > datetime.now().date():
            QMessageBox.warning(
                self,
                "Invalid Date Range",
                "End date cannot be in the future."
            )
            return
        
        self.manual_update = True  # Set flag before update
        try:
            self.update_analysis_if_ready()
        finally:
            self.manual_update = False  # Clear flag after update

    def on_date_range_changed(self):
        """Handle changes to the date range selection."""
        try:
            start = self.start_date.date().toPython()
            end = self.end_date.date().toPython()
            
            # Only update if we have valid dates
            if start <= end:
                # Get currently selected stocks before updating
                selected_stocks = [
                    item.text().split(" (")[0] 
                    for item in self.stock_list.selectedItems()
                ]
                
                # Update stock list
                if hasattr(self, 'controller'):
                    active_stocks = self.controller.get_active_stocks_for_date_range(start, end)
                    self.update_portfolio_stocks(active_stocks)
                    
                    # Restore previous selections if stocks still exist
                    for i in range(self.stock_list.count()):
                        item = self.stock_list.item(i)
                        stock_symbol = item.text().split(" (")[0]
                        if stock_symbol in selected_stocks:
                            item.setSelected(True)
                            
        except Exception as e:
            logger.error(f"Error updating stock list on date change: {str(e)}")
        
    def clear_plot(self):
        """Clear the current plot."""
        self.figure.clear()
        self.canvas.draw()
        
    def clear_statistics(self):
        """Clear the statistics table."""
        self.stats_table.setRowCount(0)
        
    def reset_selections(self):
        """Reset all option selections and clear displays."""
        # Reset all options
        for group in self.option_groups.values():
            group.set_selection(None)
            
        # Reset study config
        for level in self.study_config.current_selections:
            self.study_config.current_selections[level] = None
            
        # Clear displays
        self.clear_plot()
        self.clear_statistics()

    def set_controller(self, controller):
        """
        Set the controller for this view.
        
        Args:
            controller: PortfolioStudyController instance to handle business logic
        """
        self.controller = controller