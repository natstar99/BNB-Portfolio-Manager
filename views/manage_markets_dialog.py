# File: views/manage_markets_dialog.py

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QMessageBox, QLabel, QLineEdit, QDialogButtonBox)
from PySide6.QtCore import Qt
import logging

logger = logging.getLogger(__name__)

class ManageMarketsDialog(QDialog):
    """
    Dialog for managing market codes in the database.
    Allows users to view, add, edit, and delete market codes.
    """
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.init_ui()
        self.load_market_codes()
        
    def init_ui(self):
        """Initialize the user interface components."""
        self.setWindowTitle("Manage Market Codes")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel(
            "Manage available market codes for stock verification.\n"
            "• Market/Index: The name of the market or index\n"
            "• Market Suffix: The Yahoo Finance suffix for this market"
        )
        layout.addWidget(instructions)
        
        # Add new market section
        add_layout = QHBoxLayout()
        
        self.market_name_input = QLineEdit()
        self.market_name_input.setPlaceholderText("Market/Index Name")
        add_layout.addWidget(self.market_name_input)
        
        self.suffix_input = QLineEdit()
        self.suffix_input.setPlaceholderText("Market Suffix (e.g., .AX)")
        self.suffix_input.setMaximumWidth(150)
        add_layout.addWidget(self.suffix_input)
        
        add_button = QPushButton("Add Market")
        add_button.clicked.connect(self.add_market)
        add_layout.addWidget(add_button)
        
        layout.addLayout(add_layout)
        
        # Market codes table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([
            "Market/Index",
            "Market Suffix",
            "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        layout.addWidget(self.table)
        
        # Dialog buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Close)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def load_market_codes(self):
        """Load all market codes from the database into the table."""
        try:
            market_codes = self.db_manager.get_all_market_codes()
            self.table.setRowCount(len(market_codes))
            
            for row, (market, suffix) in enumerate(market_codes):
                # Market/Index name
                self.table.setItem(row, 0, QTableWidgetItem(market))
                
                # Market suffix
                self.table.setItem(row, 1, QTableWidgetItem(suffix))
                
                # Delete button
                delete_button = QPushButton("Delete")
                delete_button.clicked.connect(lambda checked, r=row: self.delete_market(r))
                self.table.setCellWidget(row, 2, delete_button)
                
        except Exception as e:
            logger.error(f"Error loading market codes: {str(e)}")
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to load market codes: {str(e)}"
            )

    def add_market(self):
        """Add a new market code to the database."""
        market_name = self.market_name_input.text().strip()
        suffix = self.suffix_input.text().strip()
        
        if not market_name or not suffix:
            QMessageBox.warning(
                self,
                "Invalid Input",
                "Please enter both a market name and suffix."
            )
            return
            
        try:
            # Attempt to add the new market code
            self.db_manager.execute("""
                INSERT INTO market_codes (market_or_index, market_suffix)
                VALUES (?, ?)
            """, (market_name, suffix))
            
            self.db_manager.conn.commit()
            
            # Clear inputs
            self.market_name_input.clear()
            self.suffix_input.clear()
            
            # Reload the table
            self.load_market_codes()
            
        except Exception as e:
            logger.error(f"Error adding market code: {str(e)}")
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to add market code: {str(e)}"
            )

    def delete_market(self, row):
        """
        Delete a market code after confirming it's not in use.
        
        Args:
            row: The row index in the table of the market to delete
        """
        market_name = self.table.item(row, 0).text()
        
        try:
            # Check if the market is in use
            result = self.db_manager.fetch_one("""
                SELECT COUNT(*) FROM stocks
                WHERE market_or_index = ?
            """, (market_name,))
            
            if result and result[0] > 0:
                QMessageBox.warning(
                    self,
                    "Cannot Delete",
                    f"This market code is currently in use by {result[0]} stocks "
                    "and cannot be deleted."
                )
                return
                
            # Confirm deletion
            confirm = QMessageBox.question(
                self,
                "Confirm Deletion",
                f"Are you sure you want to delete the market code for {market_name}?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if confirm == QMessageBox.Yes:
                self.db_manager.execute("""
                    DELETE FROM market_codes
                    WHERE market_or_index = ?
                """, (market_name,))
                
                self.db_manager.conn.commit()
                self.load_market_codes()
                
        except Exception as e:
            logger.error(f"Error deleting market code: {str(e)}")
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to delete market code: {str(e)}"
            )