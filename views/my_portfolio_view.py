# File: views/my_portfolio_view.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QAbstractItemView)
from PySide6.QtCore import Qt, Signal

class MyPortfolioView(QWidget):
    refresh_data = Signal()
    view_history = Signal(str)
    manage_portfolio = Signal() 

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()

        # Portfolio name and value
        self.portfolio_name_label = QLabel("Portfolio Name")
        self.portfolio_value_label = QLabel("Total Value: $0.00")
        layout.addWidget(self.portfolio_name_label)
        layout.addWidget(self.portfolio_value_label)

        # Create Buttons
        button_layout = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh Data")
        self.manage_portfolio_button = QPushButton("Manage Portfolio")
        self.view_history_button = QPushButton("View History")
        self.view_history_button.setEnabled(False)

        # Add buttons to widget
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.manage_portfolio_button)
        button_layout.addWidget(self.view_history_button)
        layout.addLayout(button_layout)

        # Stocks table
        self.stocks_table = QTableWidget()
        self.stocks_table.setColumnCount(10)
        self.stocks_table.setHorizontalHeaderLabels([
            "Name",
            "Yahoo Symbol",
            "Shares",
            "Avg Price",
            "Current Price",
            "Cost Basis",
            "Current Value",
            "Realised P/L",
            "Total P/L",
            "% Change"
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
        total_value = portfolio.calculate_total_value()
        self.portfolio_value_label.setText(f"Total Value: ${total_value:,.2f}")

        self.stocks_table.setRowCount(len(portfolio.stocks))
        
        for row, (yahoo_symbol, stock) in enumerate(portfolio.stocks.items()):
            # Calculate all values
            shares = stock.calculate_total_shares()
            avg_cost = stock.calculate_average_cost()
            cost_basis = stock.calculate_cost_basis()
            current_value = stock.calculate_market_value()
            realised_pl = stock.calculate_realised_pl()
            total_pl = stock.calculate_total_pl()
            pct_change = stock.calculate_percentage_change()

            # Create table items
            self.stocks_table.setItem(row, 0, QTableWidgetItem(stock.name))
            self.stocks_table.setItem(row, 1, QTableWidgetItem(yahoo_symbol))
            self.stocks_table.setItem(row, 2, QTableWidgetItem(f"{shares:,.4f}"))
            self.stocks_table.setItem(row, 3, QTableWidgetItem(f"${avg_cost:,.2f}"))
            self.stocks_table.setItem(row, 4, QTableWidgetItem(f"${stock.current_price:,.2f}"))
            self.stocks_table.setItem(row, 5, QTableWidgetItem(f"${cost_basis:,.2f}"))
            self.stocks_table.setItem(row, 6, QTableWidgetItem(f"${current_value:,.2f}"))
            
            # Realised P/L with colour
            realised_pl_item = QTableWidgetItem(f"${realised_pl:,.2f}")
            realised_pl_item.setForeground(Qt.darkGreen if realised_pl >= 0 else Qt.red)
            self.stocks_table.setItem(row, 7, realised_pl_item)
            
            # Total P/L with colour
            total_pl_item = QTableWidgetItem(f"${total_pl:,.2f}")
            total_pl_item.setForeground(Qt.darkGreen if total_pl >= 0 else Qt.red)
            self.stocks_table.setItem(row, 8, total_pl_item)
            
            # Percentage change with colour
            pct_item = QTableWidgetItem(f"{pct_change:+.2f}%")
            pct_item.setForeground(Qt.darkGreen if pct_change >= 0 else Qt.red)
            self.stocks_table.setItem(row, 9, pct_item)

        # Auto-resize columns to content
        self.stocks_table.resizeColumnsToContents()