# File: views/my_portfolio_view.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QAbstractItemView, QCheckBox)
from PySide6.QtCore import Qt, Signal
import math
import logging

logger = logging.getLogger(__name__)

class MyPortfolioView(QWidget):
    refresh_data = Signal()
    view_history = Signal(str)
    manage_portfolio = Signal() 

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """Initialise the user interface."""
        layout = QVBoxLayout()
        layout.setSpacing(1)
        
        self.setStyleSheet("""
            MyPortfolioView {
                background-color: transparent;
            }
            
            /* Metrics Container Styling */
            QWidget#metricsContainer {
                background-color: transparent;
                padding: 0px;
                margin: 0px;
            }
            
            /* Individual Metric Box Styling - Button-like */
            QWidget#metricBox {
                background-color: rgba(255, 255, 255, 0.9);
                border: 2px solid rgba(77, 175, 71, 0.3);
                border-radius: 8px;
                padding: 12px 15px;
                margin: 3px 5px;
            }
            
            /* Portfolio Metrics Styling */
            QLabel#portfolioName {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                padding: 5px 0;
                background-color: transparent;
            }
            
            QLabel#metricValue {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
                padding: 4px 8px;
                background-color: transparent;
                margin: 2px 0;
            }
            
            /* Button Styling */
            QPushButton {
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                margin: 5px;
            }
            
            QPushButton#refreshButton {
                background-color: #3498db;
                color: white;
                border: none;
            }
            QPushButton#refreshButton:hover {
                background-color: #2980b9;
            }
            
            QPushButton#manageButton {
                background-color: #f39c12;
                color: white;
                border: none;
            }
            QPushButton#manageButton:hover {
                background-color: #d68910;
            }
            
            QPushButton#historyButton {
                background-color: #4DAF47;
                color: white;
                border: none;
            }
            QPushButton#historyButton:hover {
                background-color: #45a33e;
            }
            
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
            
            /* Checkbox Styling */
            QCheckBox {
                font-size: 14px;
                color: #2c3e50;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #bdc3c7;
                background-color: white;
                border-radius: 4px;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #4DAF47;
                background-color: #4DAF47;
                border-radius: 4px;
            }
            
            /* Table Styling - Only for My Portfolio View */
            MyPortfolioView QTableWidget {
                background-color: rgba(255, 255, 255, 0.9);
                border: 2px solid rgba(77, 175, 71, 0.3);
                border-radius: 8px;
                gridline-color: rgba(77, 175, 71, 0.2);
                selection-background-color: rgba(77, 175, 71, 0.3);
            }
            
            MyPortfolioView QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid rgba(77, 175, 71, 0.1);
                background-color: transparent;
            }
            
            MyPortfolioView QTableWidget::item:selected {
                background-color: rgba(77, 175, 71, 0.3);
                color: #2c3e50;
            }
            
            MyPortfolioView QHeaderView::section {
                background-color: rgba(77, 175, 71, 0.8);
                color: white;
                padding: 10px;
                border: none;
                font-weight: bold;
                font-size: 13px;
            }
            
            MyPortfolioView QHeaderView::section:hover {
                background-color: rgba(77, 175, 71, 0.9);
            }
        """)

        # Create metrics container
        metrics_container = QWidget()
        metrics_container.setObjectName("metricsContainer")
        metrics_layout = QHBoxLayout(metrics_container)
        metrics_layout.setSpacing(15)

        # Portfolio name label (keeping reference for updates but not displaying)
        self.portfolio_name_label = QLabel("Portfolio Name")
        self.portfolio_name_label.setObjectName("portfolioName")
        
        # Create individual metric boxes
        metric_box_1 = QWidget()
        metric_box_1.setObjectName("metricBox")
        metric_layout_1 = QVBoxLayout(metric_box_1)
        metric_layout_1.setContentsMargins(5, 5, 5, 5)
        metric_layout_1.setSpacing(2)
        
        self.portfolio_value_label = QLabel("Portfolio Value: $0.00")
        self.portfolio_value_label.setObjectName("metricValue")
        self.portfolio_value_label.setAlignment(Qt.AlignCenter)
        metric_layout_1.addWidget(self.portfolio_value_label)
        
        metric_box_2 = QWidget()
        metric_box_2.setObjectName("metricBox")
        metric_layout_2 = QVBoxLayout(metric_box_2)
        metric_layout_2.setContentsMargins(5, 5, 5, 5)
        metric_layout_2.setSpacing(2)
        
        self.portfolio_cost_basis_label = QLabel("Cost Basis: $0.00")
        self.portfolio_cost_basis_label.setObjectName("metricValue")
        self.portfolio_cost_basis_label.setAlignment(Qt.AlignCenter)
        metric_layout_2.addWidget(self.portfolio_cost_basis_label)
        
        metric_box_3 = QWidget()
        metric_box_3.setObjectName("metricBox")
        metric_layout_3 = QVBoxLayout(metric_box_3)
        metric_layout_3.setContentsMargins(5, 5, 5, 5)
        metric_layout_3.setSpacing(2)
        
        self.portfolio_pl_dollar_label = QLabel("Total P/L: $0.00")
        self.portfolio_pl_dollar_label.setObjectName("metricValue")
        self.portfolio_pl_dollar_label.setAlignment(Qt.AlignCenter)
        metric_layout_3.addWidget(self.portfolio_pl_dollar_label)
        
        metric_box_4 = QWidget()
        metric_box_4.setObjectName("metricBox")
        metric_layout_4 = QVBoxLayout(metric_box_4)
        metric_layout_4.setContentsMargins(5, 5, 5, 5)
        metric_layout_4.setSpacing(2)
        
        self.portfolio_pl_percent_label = QLabel("Total Return: 0.00%")
        self.portfolio_pl_percent_label.setObjectName("metricValue")
        self.portfolio_pl_percent_label.setAlignment(Qt.AlignCenter)
        metric_layout_4.addWidget(self.portfolio_pl_percent_label)

        # Add metrics to horizontal layout
        metrics_layout.addWidget(metric_box_1)
        metrics_layout.addWidget(metric_box_2)
        metrics_layout.addWidget(metric_box_3)
        metrics_layout.addWidget(metric_box_4)
        
        layout.addWidget(metrics_container)

        # Create Buttons and Toggle
        button_layout = QHBoxLayout()

        self.show_zero_shares = QCheckBox("Show Zero Share Positions")
        self.show_zero_shares.setChecked(True)
        self.show_zero_shares.stateChanged.connect(self.on_toggle_zero_shares)
        button_layout.addWidget(self.show_zero_shares)
        button_layout.addStretch()

        # Create buttons with object names for styling
        self.view_history_button = QPushButton("View History")
        self.view_history_button.setObjectName("historyButton")
        self.view_history_button.setVisible(False)  # Start hidden (this is shown once a stock is selected)

        self.refresh_button = QPushButton("Refresh Data")
        self.refresh_button.setObjectName("refreshButton")
        
        self.manage_portfolio_button = QPushButton("Manage Portfolio")
        self.manage_portfolio_button.setObjectName("manageButton")
        
        # Add buttons to layout
        button_layout.addWidget(self.view_history_button)
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.manage_portfolio_button)

        layout.addLayout(button_layout)

        # Stocks Table
        self.stocks_table = QTableWidget(self)
        self.stocks_table.setColumnCount(13)
        self.stocks_table.setHorizontalHeaderLabels([
            "Name",
            "Yahoo Symbol",
            "Shares",
            "Current Price",
            "Cost Basis",
            "Current Value",
            "Realised P/L",
            "Cash Dividends",
            "DRP Shares",
            "DRP Value",
            "Total Return $",
            "Total Return %",
            "Aggregate %"
        ])
        
        # Set column resize modes
        header = self.stocks_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Name
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Symbol
        for i in range(2, 10):
            header.setSectionResizeMode(i, QHeaderView.Interactive)
        
        self.stocks_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.stocks_table)
        
        # Add bottom spacing
        layout.addSpacing(20)
        layout.setContentsMargins(10, 10, 10, 20)

        self.setLayout(layout)

        # Connect signals
        self.refresh_button.clicked.connect(self.refresh_data)
        self.manage_portfolio_button.clicked.connect(self.manage_portfolio.emit)
        self.view_history_button.clicked.connect(self.on_view_history)
        self.stocks_table.itemSelectionChanged.connect(self.on_selection_changed)

    def on_view_history(self):
        """Handle the view history button click."""
        selected_items = self.stocks_table.selectedItems()
        if selected_items:
            yahoo_symbol = self.stocks_table.item(selected_items[0].row(), 1).text()
            self.view_history.emit(yahoo_symbol)

    def on_selection_changed(self):
        """Show/hide and enable/disable the history button based on selection."""
        selected = bool(self.stocks_table.selectedItems())
        self.view_history_button.setVisible(selected)  # Show/hide based on selection
        self.view_history_button.setEnabled(selected)

    def update_portfolio(self, portfolio):
        """Update the portfolio display with current data."""
        self.portfolio_name_label.setText(portfolio.name)
        
        # Update table
        self.stocks_table.setRowCount(len(portfolio.stocks))
        
        total_value = 0.0
        total_cost_basis = 0.0
        total_return = 0.0
        
        for row, (yahoo_symbol, stock) in enumerate(portfolio.stocks.items()):
            metrics = stock.latest_metrics
            if not metrics:
                # Basic info
                self.stocks_table.setItem(row, 0, QTableWidgetItem(stock.name))
                self.stocks_table.setItem(row, 1, QTableWidgetItem(yahoo_symbol))
                    
            try:
                # Basic info
                self.stocks_table.setItem(row, 0, QTableWidgetItem(stock.name))
                self.stocks_table.setItem(row, 1, QTableWidgetItem(yahoo_symbol))
                
                # Position data - map to correct metrics fields
                # Shares (total shares owned)
                self.stocks_table.setItem(row, 2, QTableWidgetItem(
                    f"{metrics.get('total_shares_owned', 0):,.4f}"))
                # After populating the row, check if it should be hidden
                shares = metrics.get('total_shares_owned', 0)
                self.stocks_table.setRowHidden(
                    row, 
                    not self.show_zero_shares.isChecked() and shares == 0
                )
                
                # Current Price
                self.stocks_table.setItem(row, 3, QTableWidgetItem(
                    f"${stock.get_converted_price():,.2f}"))
                
                # Cost Basis
                self.stocks_table.setItem(row, 4, QTableWidgetItem(
                    f"${metrics.get('current_cost_basis', 0):,.2f}"))
                
                # Current Value (market value)
                self.stocks_table.setItem(row, 5, QTableWidgetItem(
                    f"${metrics.get('market_value', 0):,.2f}"))
                
                # Realised P/L
                realised_pl = metrics.get('realised_pl', 0)
                if realised_pl != 0:
                    realised_pl_item = QTableWidgetItem(f"${realised_pl:,.2f}")
                    realised_pl_item.setForeground(Qt.darkGreen if realised_pl >= 0 else Qt.red)
                    self.stocks_table.setItem(row, 6, realised_pl_item)
                
                # Cash Dividends
                cash_dividends = metrics.get('cash_dividends_total', 0)
                if cash_dividends > 0:
                    dividends_item = QTableWidgetItem(f"${cash_dividends:,.2f}")
                    dividends_item.setForeground(Qt.darkGreen)
                    self.stocks_table.setItem(row, 7, dividends_item)
                
                # DRP Shares
                drp_shares = metrics.get('drp_shares_total', 0)
                if drp_shares > 0:
                    drp_shares_item = QTableWidgetItem(f"{drp_shares:,.4f}")
                    drp_value_item = QTableWidgetItem(
                        f"${drp_shares * stock.current_price:,.2f}")
                    drp_shares_item.setForeground(Qt.blue)
                    drp_value_item.setForeground(Qt.blue)
                    self.stocks_table.setItem(row, 8, drp_shares_item)
                    self.stocks_table.setItem(row, 9, drp_value_item)
                
                # Total Return
                stock_total_return = metrics.get('total_return', 0)
                if abs(stock_total_return) > 0.001:
                    total_return_item = QTableWidgetItem(f"${stock_total_return:,.2f}")
                    total_return_item.setForeground(Qt.darkGreen if stock_total_return >= 0 else Qt.red)
                    self.stocks_table.setItem(row, 10, total_return_item)
                
                # Total Return %
                total_return_pct = metrics.get('total_return_pct', 0)
                return_pct_item = QTableWidgetItem(f"{total_return_pct:+.2f}%")
                return_pct_item.setForeground(Qt.darkGreen if total_return_pct >= 0 else Qt.red)
                self.stocks_table.setItem(row, 11, return_pct_item)

                # Aggregate Return %
                cumulative_return = metrics.get('cumulative_return_pct', 0)
                cumulative_return_item = QTableWidgetItem(f"{cumulative_return:+.2f}%")
                cumulative_return_item.setForeground(
                    Qt.darkGreen if cumulative_return >= 0 else Qt.red
                )
                self.stocks_table.setItem(row, 12, cumulative_return_item)
                
                # Update running totals
                total_value += metrics.get('market_value', 0)
                total_cost_basis += metrics.get('current_cost_basis', 0)
                total_return += metrics.get('total_return', 0)
                
                
            except Exception as e:
                logger.error(f"Error processing row {row} for {yahoo_symbol}: {str(e)}")
                continue
        
        # Update summary labels
        self.portfolio_value_label.setText(f"Portfolio Value: ${total_value:,.2f}")
        self.portfolio_cost_basis_label.setText(f"Cost Basis: ${total_cost_basis:,.2f}")
        self.portfolio_pl_dollar_label.setText(f"Portfolio P/L: ${total_return:,.2f}")
        if total_cost_basis > 0.0001:
            total_return_pct = (total_return / total_cost_basis) * 100
            self.portfolio_pl_percent_label.setText(f"Total Return: {total_return_pct:,.2f}%")

    def on_toggle_zero_shares(self, state):
        """Handle toggling of zero share positions visibility."""
        for row in range(self.stocks_table.rowCount()):
            shares_item = self.stocks_table.item(row, 2)  # Column index for shares
            if shares_item:
                try:
                    shares = float(shares_item.text().replace(',', ''))
                    # Show/hide row based on toggle state and shares value
                    self.stocks_table.setRowHidden(row, not state and shares == 0)
                except (ValueError, AttributeError):
                    continue