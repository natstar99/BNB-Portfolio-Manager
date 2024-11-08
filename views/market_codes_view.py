# File: views/market_codes_view.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QTableWidget, QTableWidgetItem, QHeaderView,
                               QComboBox, QStyledItemDelegate, QCheckBox)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor
from .manage_stock_splits_dialog import ManageStockSplitsDialog

class ReadOnlyDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        return None

class MarketCodesView(QWidget):
    refresh_symbol = Signal(str)
    update_symbol = Signal(str, str)

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Instrument Code", "Market or Index", "Stock Name", "Yahoo Finance Symbol", "Stock Splits", "DRP"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSortingEnabled(True)  # Enable sorting
        layout.addWidget(self.table)

        # Set up delegates
        read_only_delegate = ReadOnlyDelegate(self.table)
        self.table.setItemDelegateForColumn(0, read_only_delegate)
        self.table.setItemDelegateForColumn(2, read_only_delegate)
        self.table.setItemDelegateForColumn(4, read_only_delegate)

        # Create buttons
        button_layout = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh Selected")
        self.refresh_button.clicked.connect(self.refresh_selected)
        button_layout.addWidget(self.refresh_button)

        self.refresh_all_button = QPushButton("Refresh All")
        self.refresh_all_button.clicked.connect(self.refresh_all)
        button_layout.addWidget(self.refresh_all_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        self.load_data()

    def load_data(self):
        symbols = self.db_manager.get_all_stocks()
        market_codes = self.db_manager.get_all_market_codes()
        
        self.table.setRowCount(len(symbols))
        for row, stock_data in enumerate(symbols):
            # Assuming the order: id, yahoo_symbol, instrument_code, name, current_price, last_updated, market_suffix, drp
            stock_id = stock_data[0]
            instrument_code = stock_data[2]
            name = stock_data[3]
            yahoo_symbol = stock_data[1]
            market_suffix = stock_data[6]
            drp_status = stock_data[7]

            self.table.setItem(row, 0, QTableWidgetItem(instrument_code))
            
            # Create market combo box with clearer data handling
            market_combo = QComboBox()
            market_combo.addItem("", "")  # Empty option
            
            for market_name, suffix in market_codes:
                # Display format: "Market Name (.XX)"
                display_text = f"{market_name} ({suffix})" if suffix else market_name
                market_combo.addItem(display_text, suffix)  # suffix as the data
            
            if market_suffix:
                index = market_combo.findData(market_suffix)
                if index >= 0:
                    market_combo.setCurrentIndex(index)
            
            market_combo.currentIndexChanged.connect(lambda index, r=row: self.on_market_changed(r, index))
            self.table.setCellWidget(row, 1, market_combo)
            
            self.table.setItem(row, 2, QTableWidgetItem(name))
            self.table.setItem(row, 3, QTableWidgetItem(yahoo_symbol))

            # Stock Splits
            splits = self.db_manager.get_stock_splits(stock_data[0])
            splits_text = ", ".join(f"{split[0]}: {split[1]}" for split in splits)
            splits_item = QTableWidgetItem(splits_text)
            splits_item.setForeground(QColor(0, 0, 255))  # Blue color to indicate it's clickable
            self.table.setItem(row, 4, splits_item)

            # DRP
            drp_checkbox = QCheckBox()
            drp_checkbox.setChecked(drp_status)
            drp_checkbox.stateChanged.connect(lambda state, r=row, s_id=stock_id: self.on_drp_changed(r, s_id, state))
            self.table.setCellWidget(row, 5, drp_checkbox)

        self.table.cellChanged.connect(self.on_cell_changed)
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)

    def on_market_changed(self, row, index):
        instrument_code = self.table.item(row, 0).text()
        market_combo = self.table.cellWidget(row, 1)
        market_suffix = market_combo.itemData(index)
        self.update_symbol.emit(instrument_code, market_suffix)
        self.db_manager.update_stock_market(instrument_code, market_suffix)
        self.update_symbol_data(instrument_code)

    def update_symbol_data(self, instrument_code):
        stock_data = self.db_manager.get_stock(instrument_code)
        if stock_data:
            for row in range(self.table.rowCount()):
                if self.table.item(row, 0).text() == instrument_code:
                    # Assuming the order: id, yahoo_symbol, instrument_code, name, current_price, last_updated, market_suffix
                    self.table.item(row, 2).setText(stock_data[3])  # name
                    self.table.item(row, 3).setText(stock_data[1])  # yahoo_symbol
                    
                    market_combo = self.table.cellWidget(row, 1)
                    index = market_combo.findData(stock_data[6])  # market_suffix
                    if index >= 0:
                        market_combo.setCurrentIndex(index)

                    # Update Stock Splits
                    splits = self.db_manager.get_stock_splits(stock_data[0])
                    splits_text = ", ".join(f"{split[0]}: {split[1]}" for split in splits)
                    self.table.item(row, 4).setText(splits_text)
                    
                    # Update DRP
                    drp_checkbox = self.table.cellWidget(row, 5)
                    drp_checkbox.setChecked(self.db_manager.get_stock_drp(stock_data[0]))
                    
                    break

    def on_cell_changed(self, row, column):
        if column == 3:  # Yahoo Finance Symbol column
            instrument_code = self.table.item(row, 0).text()
            yahoo_symbol = self.table.item(row, 3).text()
            self.db_manager.update_stock_yahoo_symbol(instrument_code, yahoo_symbol)
    
    def on_drp_changed(self, row, stock_id, state):
        checkbox = self.table.cellWidget(row, 5)
        is_checked = checkbox.isChecked()
        instrument_code = self.table.item(row, 0).text()
        self.db_manager.update_stock_drp(stock_id, is_checked)
        print(f"DRP status changed for stock ID {stock_id} (Instrument Code: {instrument_code}) to {is_checked}")

    def on_cell_double_clicked(self, row, column):
        if column == 4:  # Stock Splits column
            instrument_code = self.table.item(row, 0).text()
            dialog = ManageStockSplitsDialog(self.db_manager, instrument_code, self)
            if dialog.exec_():
                self.update_symbol_data(instrument_code)

    def refresh_selected(self):
        selected_rows = set(index.row() for index in self.table.selectedIndexes())
        for row in selected_rows:
            instrument_code = self.table.item(row, 0).text()
            self.refresh_symbol.emit(instrument_code)
            self.update_symbol_data(instrument_code)

    def refresh_all(self):
        for row in range(self.table.rowCount()):
            instrument_code = self.table.item(row, 0).text()
            self.refresh_symbol.emit(instrument_code)
            self.update_symbol_data(instrument_code)