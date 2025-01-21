# File: views/main_window.py

import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QPushButton, 
                               QStackedWidget, QLabel, QHBoxLayout, QApplication,
                               QStyle)
from PySide6.QtGui import QPalette, QBrush, QPixmap
from PySide6.QtCore import Qt, QSize

from controllers.portfolio_controller import PortfolioController
from controllers.portfolio_view_controller import PortfolioViewController
from controllers.market_analysis_controller import MarketAnalysisController
from controllers.portfolio_study_controller import PortfolioStudyController
from controllers.settings_controller import SettingsController
from views.portfolio_study_view import PortfolioStudyView
from views.market_analysis_view import MarketAnalysisView

class MainWindow(QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.setWindowTitle("Bear No Bears - Portfolio Manager")
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(0, 0, screen.width(), screen.height()-0.07*screen.height())

        # Set up the background
        current_dir = os.path.dirname(os.path.abspath(__file__))
        background_path = os.path.join(current_dir, "..", "wallpaper.png")
        
        # Create and set the palette for the background
        palette = self.palette()
        background_pixmap = QPixmap(background_path)
        scaled_pixmap = background_pixmap.scaled(
            self.size(), 
            Qt.KeepAspectRatioByExpanding, 
            Qt.SmoothTransformation
        )
        palette.setBrush(QPalette.Window, QBrush(scaled_pixmap))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        self.db_manager = db_manager

        # Create main widget and layout
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Create and set up sidebar with styling
        sidebar = QWidget()
        sidebar.setMaximumWidth(220)
        sidebar.setMinimumWidth(220)
        sidebar_layout = QVBoxLayout()
        sidebar.setLayout(sidebar_layout)
        
        # Set up sidebar with no margins to maximize space
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(10)  # Adjust spacing between elements

        # Add logo with maximized size
        logo_label = QLabel()
        logo_path = os.path.join(current_dir, "..", "bnb_logo.png")
        logo_pixmap = QPixmap(logo_path)

        # Scale to sidebar width while maintaining aspect ratio
        scaled_width = 220  # Match sidebar width
        aspect_ratio = logo_pixmap.height() / logo_pixmap.width()
        scaled_height = int(scaled_width * aspect_ratio)

        logo_label.setPixmap(logo_pixmap.scaled(
            scaled_width, 
            scaled_height,
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        ))
        logo_label.setAlignment(Qt.AlignCenter)

        sidebar_layout.addWidget(logo_label)

        # Add some space after the logo
        sidebar_layout.addSpacing(10)

        # Style for navigation buttons
        button_style = """
            QPushButton {
                text-align: left;
                padding: 12px 15px;
                border: none;
                border-radius: 8px;
                background-color: rgba(255, 255, 255, 0.9);
                color: #2c3e50;
                font-size: 14px;
                font-weight: bold;
                margin: 3px 10px;
            }
            QPushButton:hover {
                background-color: rgba(77, 175, 71, 0.9);
                color: white;
            }
            QPushButton:pressed {
                background-color: rgba(77, 175, 71, 0.9);
            }
            QPushButton[selected=true] {
                background-color: rgba(77, 175, 71, 0.9);
                color: white;
            }
        """

        # Navigation button configurations with more logical icons
        nav_configs = [
            ("Manage Portfolios", "SP_DialogOpenButton"),
            ("My Portfolio", "SP_FileDialogDetailedView"),
            ("Study Portfolio", "SP_FileDialogContentsView"),
            ("Study Market (Beta)", "SP_ComputerIcon"),
            ("Settings", "SP_DialogHelpButton")
        ]
        
        # Add navigation buttons
        self.nav_buttons = []
        for button_text, icon_name in nav_configs:
            button = QPushButton(button_text)
            button.setStyleSheet(button_style)
            
            # Add icon to button
            icon = self.style().standardIcon(getattr(QStyle, icon_name))
            button.setIcon(icon)
            button.setIconSize(QSize(20, 20))
            
            # Set property for styling selected state
            button.setProperty("selected", False)
            
            button.clicked.connect(lambda checked, text=button_text: self.on_nav_button_clicked(text))
            sidebar_layout.addWidget(button)
            self.nav_buttons.append(button)

        sidebar_layout.addStretch()

        # Create stacked widget for main content
        self.content_widget = QStackedWidget()

        # Create controllers and views
        self.portfolio_controller = PortfolioController(self.db_manager)
        self.portfolio_view_controller = PortfolioViewController(self.db_manager)
        self.portfolio_study_controller = PortfolioStudyController(self.db_manager)
        self.market_analysis_controller = MarketAnalysisController(self.db_manager)
        self.settings_controller = SettingsController(self.db_manager)

        # Set up views
        self.portfolio_study_view = PortfolioStudyView()
        self.portfolio_study_controller.set_view(self.portfolio_study_view)

        self.market_analysis_view = MarketAnalysisView()
        self.market_analysis_controller.set_view(self.market_analysis_view)

        # Connect signals
        self.portfolio_controller.view.select_portfolio.connect(self.on_portfolio_selected)

        # Add pages to stacked widget
        self.content_widget.addWidget(self.portfolio_controller.get_view())
        self.content_widget.addWidget(self.portfolio_view_controller.get_view())
        self.content_widget.addWidget(self.portfolio_study_controller.get_view())
        self.content_widget.addWidget(self.market_analysis_controller.get_view())
        self.content_widget.addWidget(self.settings_controller.get_view())

        # Add sidebar and content to main layout
        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.content_widget)

        # Load initial data
        self.portfolio_controller.load_portfolios()

    def on_nav_button_clicked(self, button_text):
        index = [
            "Manage Portfolios",
            "My Portfolio",
            "Study Portfolio",
            "Study Market (Beta)",
            "Settings"
        ].index(button_text)
        
        self.content_widget.setCurrentIndex(index)
        
        # Update button styles
        for i, button in enumerate(self.nav_buttons):
            button.setProperty("selected", i == index)
            button.style().unpolish(button)  # Force style refresh
            button.style().polish(button)

    def on_portfolio_selected(self, portfolio_name):
        portfolio = self.portfolio_controller.get_portfolio_by_name(portfolio_name)
        if portfolio:
            self.portfolio_view_controller.set_portfolio(portfolio)
            self.portfolio_study_controller.set_portfolio(portfolio)
            self.market_analysis_controller.set_portfolio(portfolio)
            self.settings_controller.set_portfolio(portfolio)
            self.content_widget.setCurrentIndex(1)  # Switch to My Portfolio view
            
            # Update button styles - use the same mechanism as on_nav_button_clicked
            for i, button in enumerate(self.nav_buttons):
                button.setProperty("selected", i == 1)  # 1 is the index for "My Portfolio"
                button.style().unpolish(button)
                button.style().polish(button)