# File: views/manage_portfolios_view.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
                               QPushButton, QLabel, QLineEdit, QMessageBox,
                               QDialog, QDialogButtonBox, QFormLayout)
from PySide6.QtCore import Signal

class CreatePortfolioDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Portfolio")
        self.layout = QFormLayout(self)

        self.name_input = QLineEdit(self)
        self.layout.addRow("Portfolio Name:", self.name_input)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addRow(self.buttons)

class ManagePortfoliosView(QWidget):
    create_portfolio = Signal(str)
    select_portfolio = Signal(str)
    delete_portfolio = Signal(str)
    import_transactions = Signal(str)

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Portfolio list
        self.portfolio_list = QListWidget()
        layout.addWidget(QLabel("Your Portfolios:"))
        layout.addWidget(self.portfolio_list)

        # Buttons
        button_layout = QHBoxLayout()
        self.create_button = QPushButton("Create New Portfolio")
        self.delete_button = QPushButton("Delete Portfolio")
        self.view_button = QPushButton("View Portfolio")
        self.import_button = QPushButton("Import Transactions")
        self.delete_button.setEnabled(False)
        self.view_button.setEnabled(False)
        self.import_button.setEnabled(False)
        button_layout.addWidget(self.create_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.view_button)
        button_layout.addWidget(self.import_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Connect signals
        self.create_button.clicked.connect(self.show_create_dialog)
        self.delete_button.clicked.connect(self.delete_selected_portfolio)
        self.view_button.clicked.connect(self.view_selected_portfolio)
        self.import_button.clicked.connect(self.import_transactions_clicked)
        self.portfolio_list.itemSelectionChanged.connect(self.update_button_states)
        self.portfolio_list.itemDoubleClicked.connect(self.on_portfolio_double_clicked)

    def show_create_dialog(self):
        dialog = CreatePortfolioDialog(self)
        if dialog.exec_():
            portfolio_name = dialog.name_input.text().strip()
            if portfolio_name:
                self.create_portfolio.emit(portfolio_name)
            else:
                QMessageBox.warning(self, "Invalid Input", "Portfolio name cannot be empty.")

    def update_portfolios(self, portfolios):
        self.portfolio_list.clear()
        for portfolio in portfolios:
            self.portfolio_list.addItem(portfolio.name)

    def update_button_states(self):
        selected = bool(self.portfolio_list.selectedItems())
        self.delete_button.setEnabled(selected)
        self.view_button.setEnabled(selected)
        self.import_button.setEnabled(selected)

    def delete_selected_portfolio(self):
        selected_item = self.portfolio_list.currentItem()
        if selected_item:
            confirm = QMessageBox.question(self, "Confirm Deletion",
                                           f"Are you sure you want to delete the portfolio '{selected_item.text()}'?",
                                           QMessageBox.Yes | QMessageBox.No)
            if confirm == QMessageBox.Yes:
                self.delete_portfolio.emit(selected_item.text())

    def view_selected_portfolio(self):
        selected_item = self.portfolio_list.currentItem()
        if selected_item:
            self.select_portfolio.emit(selected_item.text())

    def on_portfolio_double_clicked(self, item):
        self.select_portfolio.emit(item.text())

    def import_transactions_clicked(self):
        selected_item = self.portfolio_list.currentItem()
        if selected_item:
            self.import_transactions.emit(selected_item.text())
        else:
            QMessageBox.warning(self, "No Portfolio Selected", "Please select a portfolio to import transactions into.")