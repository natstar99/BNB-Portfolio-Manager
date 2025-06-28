# File: views/manage_portfolios_view.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
                               QPushButton, QLabel, QLineEdit, QMessageBox,
                               QDialog, QDialogButtonBox, QFormLayout)
from PySide6.QtCore import Signal, Qt

class CreatePortfolioDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Portfolio")
        self.layout = QFormLayout(self)
        
        # Style the dialog
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border-radius: 8px;
            }
            QLineEdit {
                padding: 8px;
                border: 2px solid #ddd;
                border-radius: 4px;
                background-color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #4DAF47;
            }
            QPushButton {
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton[text="OK"] {
                background-color: #4DAF47;
                color: white;
                border: none;
            }
            QPushButton[text="OK"]:hover {
                background-color: #45a33e;
            }
            QPushButton[text="Cancel"] {
                background-color: #f0f0f0;
                border: 2px solid #ddd;
            }
            QPushButton[text="Cancel"]:hover {
                background-color: #e5e5e5;
            }
        """)

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
        # Add style to the view
        self.setStyleSheet("""
            ManagePortfoliosView {
                background-color: transparent;
            }
            
            QWidget {
                background-color: white;
            }
            QLabel {
                color: #2c3e50;
                font-size: 16px;
                font-weight: bold;
                padding: 10px 0;
            }
            QListWidget {
                background-color: white;
                border: 2px solid #ddd;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                selection-background-color: #4DAF47;
                selection-color: white;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background-color: #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: #4DAF47;
                color: white;
            }
            QPushButton {
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                margin: 5px;
            }
            QPushButton#createButton {
                background-color: #4DAF47;
                color: white;
                border: none;
            }
            QPushButton#createButton:hover {
                background-color: #45a33e;
            }
            QPushButton#viewButton {
                background-color: #3498db;
                color: white;
                border: none;
            }
            QPushButton#viewButton:hover {
                background-color: #2980b9;
            }
            QPushButton#importButton {
                background-color: #f39c12;
                color: white;
                border: none;
            }
            QPushButton#importButton:hover {
                background-color: #d68910;
            }
            QPushButton#deleteButton {
                background-color: #e74c3c;
                color: white;
                border: none;
            }
            QPushButton#deleteButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
            
            /* List Widget Styling - Fix background issues */
            QListWidget {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 5px;
            }
            
            QListWidget::item {
                padding: 8px;
                background-color: white;
                border-bottom: 1px solid #eee;
            }
            
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: black;
            }
            
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Portfolio list
        self.portfolio_list = QListWidget()
        list_label = QLabel("Your Portfolios:")
        list_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(list_label)
        layout.addWidget(self.portfolio_list)

        # Buttons
        button_layout = QHBoxLayout()
        self.create_button = QPushButton("Create New Portfolio")
        self.delete_button = QPushButton("Delete Portfolio")
        self.view_button = QPushButton("View Portfolio")
        self.import_button = QPushButton("Import Transactions")

        # Set object names for specific styling
        self.create_button.setObjectName("createButton")
        self.delete_button.setObjectName("deleteButton")
        self.view_button.setObjectName("viewButton")
        self.import_button.setObjectName("importButton")

        # Add buttons to layout
        button_layout.addWidget(self.create_button)
        button_layout.addWidget(self.view_button)
        button_layout.addWidget(self.import_button)
        button_layout.addWidget(self.delete_button)

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