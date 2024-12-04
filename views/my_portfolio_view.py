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
        self.stocks_table.setColumnCount(8)
        self.stocks_table.setHorizontalHeaderLabels([
            "Yahoo Symbol", "Instrument Code", "Name", "Quantity", "Avg Cost", "Current Price", "Market Value", "Gain/Loss"
        ])
        self.stocks_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stocks_table.setEditTriggers(QAbstractItemView.NoEditTriggers) # Make the table read-only
        layout.addWidget(self.stocks_table)

        self.setLayout(layout)

        # Connect signals (buttons)
        self.refresh_button.clicked.connect(self.refresh_data)
        self.manage_portfolio_button.clicked.connect(self.manage_portfolio.emit)
        self.view_history_button.clicked.connect(self.on_view_history)

        # Connect selection change signal
        self.stocks_table.itemSelectionChanged.connect(self.on_selection_changed)

    def on_view_history(self):
        selected_items = self.stocks_table.selectedItems()
        if selected_items:
            yahoo_symbol = self.stocks_table.item(selected_items[0].row(), 0).text()
            self.view_history.emit(yahoo_symbol)

    # Modify the existing method to enable/disable history button
    def on_selection_changed(self):
        selected = bool(self.stocks_table.selectedItems())
        self.view_history_button.setEnabled(selected)

    def update_portfolio(self, portfolio):
        self.portfolio_name_label.setText(portfolio.name)
        self.portfolio_value_label.setText(f"Total Value: ${portfolio.calculate_total_value():.2f}")

        self.stocks_table.setRowCount(len(portfolio.stocks))
        for row, (yahoo_symbol, stock) in enumerate(portfolio.stocks.items()):
            self.stocks_table.setItem(row, 0, QTableWidgetItem(yahoo_symbol))
            self.stocks_table.setItem(row, 1, QTableWidgetItem(stock.instrument_code))
            self.stocks_table.setItem(row, 2, QTableWidgetItem(stock.name))
            self.stocks_table.setItem(row, 3, QTableWidgetItem(str(stock.calculate_total_shares())))
            self.stocks_table.setItem(row, 4, QTableWidgetItem(f"${stock.calculate_average_cost():.2f}"))
            self.stocks_table.setItem(row, 5, QTableWidgetItem(f"${stock.current_price:.2f}"))
            self.stocks_table.setItem(row, 6, QTableWidgetItem(f"${stock.calculate_market_value():.2f}"))
            gain_loss = stock.calculate_profit_loss()
            self.stocks_table.setItem(row, 7, QTableWidgetItem(f"${gain_loss:.2f}"))
            
            # Color code the gain/loss cell
            gain_loss_item = self.stocks_table.item(row, 7)
            gain_loss_item.setForeground(Qt.green if gain_loss >= 0 else Qt.red)