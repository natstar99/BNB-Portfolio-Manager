# File: views/main_window.py

import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QPushButton, 
                               QStackedWidget, QLabel, QHBoxLayout, QApplication)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

from controllers.portfolio_controller import PortfolioController
from controllers.portfolio_view_controller import PortfolioViewController
from controllers.market_analysis_controller import MarketAnalysisController
from controllers.portfolio_study_controller import PortfolioStudyController
from views.portfolio_study_view import PortfolioStudyView
from views.market_analysis_view import MarketAnalysisView

class MainWindow(QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.setWindowTitle("Bear No Bears - Portfolio Manager")
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(0, 0, screen.width(), screen.height()-0.07*screen.height())

        self.db_manager = db_manager

        # Create main widget and layout
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Create and set up sidebar
        sidebar = QWidget()
        sidebar.setMaximumWidth(210)
        sidebar.setMinimumWidth(210)
        sidebar_layout = QVBoxLayout()
        sidebar.setLayout(sidebar_layout)

        # Add logo
        logo_label = QLabel()
        current_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(current_dir, "..", "bnb_logo.png")
        logo_pixmap = QPixmap(logo_path)
        logo_label.setPixmap(logo_pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(logo_label)

        # Add navigation buttons
        self.nav_buttons = []
        for button_text in [
            "Manage Portfolios", 
            "My Portfolio",
            "Study Portfolio",
            "Study Market",
            "Settings"
        ]:
            button = QPushButton(button_text)
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
        self.content_widget.addWidget(QLabel("Settings Page"))

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
            "Study Market",
            "Settings"
        ].index(button_text)
        self.content_widget.setCurrentIndex(index)
        for button in self.nav_buttons:
            button.setStyleSheet("")
        self.nav_buttons[index].setStyleSheet("background-color: #ddd;")

    def on_portfolio_selected(self, portfolio_name):
        portfolio = self.portfolio_controller.get_portfolio_by_name(portfolio_name)
        if portfolio:
            self.portfolio_view_controller.set_portfolio(portfolio)
            self.portfolio_study_controller.set_portfolio(portfolio)
            self.market_analysis_controller.set_portfolio(portfolio)
            self.content_widget.setCurrentIndex(1)
            self.nav_buttons[1].setStyleSheet("background-color: #ddd;")