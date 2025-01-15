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

        # Portfolio name and summary
        self.portfolio_name_label = QLabel("Portfolio Name")
        self.portfolio_value_label = QLabel("Portfolio Value: $0.00")
        self.portfolio_cost_basis_label = QLabel("Cost Basis: $0.00")
        self.portfolio_pl_dollar_label = QLabel("Total P/L: $0.00")
        self.portfolio_pl_percent_label = QLabel("Total Return: 0.00%")

        # Add all labels to layout
        layout.addWidget(self.portfolio_name_label)
        layout.addWidget(self.portfolio_value_label)
        layout.addWidget(self.portfolio_cost_basis_label)
        layout.addWidget(self.portfolio_pl_dollar_label)
        layout.addWidget(self.portfolio_pl_percent_label)

        # Create Buttons and Toggle
        button_layout = QHBoxLayout()

        # Add toggle for zero shares
        self.show_zero_shares = QCheckBox("Show Zero Share Positions")
        self.show_zero_shares.setChecked(True)  # Default to showing all
        self.show_zero_shares.stateChanged.connect(self.on_toggle_zero_shares)
        button_layout.addWidget(self.show_zero_shares)
        button_layout.addStretch()  # Add stretch to separate toggle from buttons

        self.refresh_button = QPushButton("Refresh Data")
        self.manage_portfolio_button = QPushButton("Manage Portfolio")
        self.view_history_button = QPushButton("View History")
        self.view_history_button.setEnabled(False)

        # Add buttons to widget
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.manage_portfolio_button)
        button_layout.addWidget(self.view_history_button)
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
        """Enable/disable the history button based on selection."""
        selected = bool(self.stocks_table.selectedItems())
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