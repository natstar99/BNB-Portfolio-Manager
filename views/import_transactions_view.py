# File: views/import_transactions_view.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QTableWidget, QTableWidgetItem, QFileDialog, 
                               QComboBox, QLabel, QStackedWidget, QHeaderView)
from PySide6.QtCore import Signal
import pandas as pd

class ImportTransactionsView(QWidget):
    import_transactions = Signal(str, dict)  # Emit filename and column mapping
    get_template = Signal()  # Signal to request template download

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # File selection
        file_layout = QHBoxLayout()
        self.file_path_label = QLabel("No file selected")
        self.select_file_button = QPushButton("Select File")
        self.get_template_button = QPushButton("Get Template")
        file_layout.addWidget(self.file_path_label)
        file_layout.addWidget(self.select_file_button)
        file_layout.addWidget(self.get_template_button)
        layout.addLayout(file_layout)

        # Stacked widget for different import views
        self.stacked_widget = QStackedWidget()
        
        # Template import view
        template_view = QWidget()
        template_layout = QVBoxLayout(template_view)
        self.template_preview = QTableWidget()
        template_layout.addWidget(QLabel("Template detected. Preview:"))
        template_layout.addWidget(self.template_preview)
        
        # Custom import view
        custom_view = QWidget()
        custom_layout = QVBoxLayout(custom_view)
        self.custom_preview = QTableWidget()
        custom_layout.addWidget(QLabel("Custom file. Please map columns:"))
        custom_layout.addWidget(self.custom_preview)
        
        # Column mapping (only for custom view)
        mapping_layout = QHBoxLayout()
        self.date_combo = QComboBox()
        self.symbol_combo = QComboBox()
        self.quantity_combo = QComboBox()
        self.price_combo = QComboBox()
        self.type_combo = QComboBox()
        mapping_layout.addWidget(QLabel("Date:"))
        mapping_layout.addWidget(self.date_combo)
        mapping_layout.addWidget(QLabel("Symbol:"))
        mapping_layout.addWidget(self.symbol_combo)
        mapping_layout.addWidget(QLabel("Quantity:"))
        mapping_layout.addWidget(self.quantity_combo)
        mapping_layout.addWidget(QLabel("Price:"))
        mapping_layout.addWidget(self.price_combo)
        mapping_layout.addWidget(QLabel("Type:"))
        mapping_layout.addWidget(self.type_combo)
        custom_layout.addLayout(mapping_layout)

        self.stacked_widget.addWidget(template_view)
        self.stacked_widget.addWidget(custom_view)
        layout.addWidget(self.stacked_widget)

        # Import and Cancel buttons
        button_layout = QHBoxLayout()
        self.import_button = QPushButton("Import")
        self.cancel_button = QPushButton("Cancel")
        button_layout.addWidget(self.import_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Connect signals
        self.select_file_button.clicked.connect(self.select_file)
        self.get_template_button.clicked.connect(self.get_template.emit)
        self.import_button.clicked.connect(self.import_data)
        self.cancel_button.clicked.connect(self.close)

    def select_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select File", "", "Excel Files (*.xlsx);;CSV Files (*.csv)")
        if file_name:
            self.file_path_label.setText(file_name)
            self.load_preview(file_name)

    def load_preview(self, file_name):
        if file_name.endswith('.xlsx'):
            df = pd.read_excel(file_name, nrows=5)
        elif file_name.endswith('.csv'):
            df = pd.read_csv(file_name, nrows=5)
        else:
            return

        if self.is_template_file(df):
            self.load_template_preview(df)
        else:
            self.load_custom_preview(df)

    def is_template_file(self, df):
        expected_columns = ['Trade Date', 'Instrument Code', 'Quantity', 'Price', 'Transaction Type']
        return all(col in df.columns for col in expected_columns)

    def load_template_preview(self, df):
        self.stacked_widget.setCurrentIndex(0)
        self.populate_table(self.template_preview, df)

    def load_custom_preview(self, df):
        self.stacked_widget.setCurrentIndex(1)
        self.populate_table(self.custom_preview, df)
        self.update_column_mappings(df.columns)

    def populate_table(self, table_widget, df):
        table_widget.setRowCount(df.shape[0])
        table_widget.setColumnCount(df.shape[1])
        table_widget.setHorizontalHeaderLabels(df.columns)

        for row in range(df.shape[0]):
            for col in range(df.shape[1]):
                item = QTableWidgetItem(str(df.iloc[row, col]))
                table_widget.setItem(row, col, item)

        table_widget.resizeColumnsToContents()
        table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def update_column_mappings(self, columns):
        for combo in [self.date_combo, self.symbol_combo, self.quantity_combo, self.price_combo, self.type_combo]:
            combo.clear()
            combo.addItems(columns)

    def import_data(self):
        if self.stacked_widget.currentIndex() == 0:
            # Template import
            self.import_transactions.emit(self.file_path_label.text(), None)
        else:
            # Custom import
            column_mapping = {
                'date': self.date_combo.currentText(),
                'symbol': self.symbol_combo.currentText(),
                'quantity': self.quantity_combo.currentText(),
                'price': self.price_combo.currentText(),
                'type': self.type_combo.currentText()
            }
            self.import_transactions.emit(self.file_path_label.text(), column_mapping)
        self.close()