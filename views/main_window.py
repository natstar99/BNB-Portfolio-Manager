# File: views/main_window.py

import os
import logging
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QPushButton, 
                               QStackedWidget, QLabel, QHBoxLayout, QApplication,
                               QStyle, QFrame)
from PySide6.QtGui import QPalette, QBrush, QPixmap
from PySide6.QtCore import Qt, QSize
from PySide6.QtCore import QTimer, Qt, QPropertyAnimation, QPoint, Property
from PySide6.QtGui import QPainter, QColor, QFont
from controllers.portfolio_controller import PortfolioController
from controllers.portfolio_view_controller import PortfolioViewController
from controllers.market_analysis_controller import MarketAnalysisController
from controllers.portfolio_study_controller import PortfolioStudyController
from controllers.settings_controller import SettingsController
from views.portfolio_study_view import PortfolioStudyView
from views.market_analysis_view import MarketAnalysisView

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.portfolio_controller = PortfolioController(self.db_manager)
        self.settings_controller = SettingsController(self.db_manager)
        self.setWindowTitle("Bear No Bears - Portfolio Manager")
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(0, 0, screen.width(), screen.height()-0.07*screen.height())

        # Load portfolios and check if there's only one portfolio
        self.portfolio_controller.load_portfolios()
        portfolios = self.portfolio_controller.portfolios
        if len(portfolios) == 1:
            self.portfolio_controller.select_portfolio(portfolios[0].name)

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

        # Navigation button configurations with logical icons
        self.nav_configs = [
            ("Manage Portfolios", "SP_DialogOpenButton", True),  # Always visible
            ("My Portfolio", "SP_FileDialogDetailedView", False),  # Initially hidden
            ("Study Portfolio", "SP_FileDialogContentsView", False),  # Initially hidden
            ("Study Market (Beta)", "SP_ComputerIcon", False),  # Initially hidden
            ("Settings", "SP_DialogHelpButton", False)  # Initially hidden
        ]
        
        # Add navigation buttons
        self.nav_buttons = []
        for button_text, icon_name, initially_visible in self.nav_configs:
            button = QPushButton(button_text)
            button.setStyleSheet(button_style)
            
            # Add icon to button
            icon = self.style().standardIcon(getattr(QStyle, icon_name))
            button.setIcon(icon)
            button.setIconSize(QSize(20, 20))
            
            # Set property for styling selected state
            button.setProperty("selected", False)
            
            # Set initial visibility
            button.setVisible(initially_visible)
            
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

        # Setup and initialise the ticker
        self.setup_ticker()

        # Load initial data and update ticker
        self.portfolio_controller.load_portfolios()
        self.update_ticker_data()  # Initial ticker update

    def on_nav_button_clicked(self, button_text):
        """Handle navigation button clicks."""
        index = [
            "Manage Portfolios",
            "My Portfolio",
            "Study Portfolio",
            "Study Market (Beta)",
            "Settings"
        ].index(button_text)
        
        self.content_widget.setCurrentIndex(index)
        self._update_button_styles(index)

    def _update_button_styles(self, selected_index):
        """Update the styles of all buttons."""
        for i, button in enumerate(self.nav_buttons):
            if button.isVisible():  # Only update style if button is visible
                button.setProperty("selected", i == selected_index)
                button.style().unpolish(button)
                button.style().polish(button)

    def on_portfolio_selected(self, portfolio_name):
        """Handle portfolio selection and update button visibility."""
        portfolio = self.portfolio_controller.get_portfolio_by_name(portfolio_name)
        if portfolio:
            # Update controllers
            self.portfolio_view_controller.set_portfolio(portfolio)
            self.portfolio_study_controller.set_portfolio(portfolio)
            self.market_analysis_controller.set_portfolio(portfolio)
            self.settings_controller.set_portfolio(portfolio)
            
            # Show all navigation buttons
            for button, (button_text, _, _) in zip(self.nav_buttons, self.nav_configs):
                # Keep "Manage Portfolios" visible and show others
                if button_text != "Manage Portfolios":
                    button.setVisible(True)
            
            # Switch to My Portfolio view and update button styles
            self.content_widget.setCurrentIndex(1)  # Switch to My Portfolio view
            self._update_button_styles(1)  # Update styles with My Portfolio selected
            
            # Force ticker update with new portfolio
            self.update_ticker_data()

    def setup_ticker(self):
        # Create main container with vertical layout
        main_container = QWidget()
        main_container_layout = QVBoxLayout(main_container)
        main_container_layout.setContentsMargins(0, 0, 0, 0)
        main_container_layout.setSpacing(0)
        
        # Add ticker at the top
        self.ticker_container = TickerContainer()
        main_container_layout.addWidget(self.ticker_container)
        
        # Create container for sidebar and content
        horizontal_container = QWidget()
        horizontal_layout = QHBoxLayout(horizontal_container)
        horizontal_layout.setContentsMargins(0, 0, 0, 0)
        
        # Move existing widgets (sidebar and content) to horizontal container
        main_layout = self.centralWidget().layout()
        while main_layout.count():
            item = main_layout.takeAt(0)
            if item.widget():
                horizontal_layout.addWidget(item.widget())
        
        # Add horizontal container below ticker
        main_container_layout.addWidget(horizontal_container)
        
        # Set main container as central widget
        main_layout.addWidget(main_container)
        
        # Update ticker with initial data
        self.update_ticker_data()

    def update_ticker_data(self):
        if hasattr(self, 'ticker_container'):
            ticker = self.ticker_container.ticker
            
            try:
                # First check if we have a selected portfolio
                if not (hasattr(self, 'portfolio_view_controller') and 
                    self.portfolio_view_controller.current_portfolio):
                    ticker.update_stocks([])  # This will trigger welcome message
                    return
                    
                portfolio_id = self.portfolio_view_controller.current_portfolio.id
                
                metrics_data = self.db_manager.fetch_all("""
                    WITH LatestDates AS (
                        SELECT stock_id, MAX(date) as max_date
                        FROM final_metrics
                        GROUP BY stock_id
                    )
                    SELECT 
                        s.instrument_code,
                        COALESCE(fm.daily_pl, 0) as daily_pl,
                        COALESCE(fm.daily_pl_pct, 0) as daily_pl_pct
                    FROM stocks s
                    JOIN portfolio_stocks ps ON s.id = ps.stock_id
                    LEFT JOIN (
                        SELECT fm.* 
                        FROM final_metrics fm
                        JOIN LatestDates ld ON fm.stock_id = ld.stock_id 
                            AND fm.date = ld.max_date
                    ) fm ON s.id = fm.stock_id
                    WHERE ps.portfolio_id = ?
                    AND COALESCE(fm.market_value, 0) > 0.0001
                    ORDER BY s.instrument_code
                """, (portfolio_id,))
                
                portfolio_data = []
                for row in metrics_data:
                    portfolio_data.append({
                        'symbol': str(row[0]),
                        'daily_pl': float(row[1]) if row[1] is not None else 0.0,
                        'change': float(row[2]) if row[2] is not None else 0.0
                    })
                
                if portfolio_data:
                    ticker.update_stocks(portfolio_data)
                else:
                    ticker.update_stocks([])  # No stocks in portfolio, show welcome message
                    
            except Exception as e:
                logger.error(f"Error updating ticker data: {str(e)}")
                ticker.update_stocks([])  # Show welcome message on error

class StockTicker(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(30)
        
        # LED configuration
        self.led_size = 3       # Size of each LED dot
        self.led_spacing = 1     # Space between LEDs
        self.char_width = 6      # Number of LEDs per character width
        self.char_height = 8     # Number of LEDs per character height
        
        # Styling and colors
        self.led_off_color = QColor(40, 40, 40)
        self.led_text_color = QColor(255, 140, 0)
        self.led_up_color = QColor(0, 255, 0)
        self.led_down_color = QColor(255, 0, 0)
        self.led_glow = QColor(255, 140, 0, 100)
        
        # Initialise variables
        self.offset = 0
        self.show_welcome = True  # Flag to control welcome message
        self.stocks_text = ""
        self.scroll_speed = 1.5
        
        # Set initial welcome message
        self.welcome_message = "<text>WALL STREET ADVISES INVESTORS TO BEAR NO BEARS!</text>"
        self.stocks_text = self.welcome_message
        
        # Setup animation timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_position)
        self.timer.start(20)
        
        # Data check timer (checks for portfolio data when welcome message ends)
        self.check_data_timer = QTimer(self)
        self.check_data_timer.timeout.connect(self.check_for_portfolio_data)
        self.check_data_timer.start(1000)  # Check every second

    def update_stocks(self, stocks_data):
        """Update the ticker with new stock data"""
        if not stocks_data:
            self.stocks_text = self.welcome_message
            self.show_welcome = True
            return

        text_parts = []
        for stock in stocks_data:
            # Format numbers with appropriate commas and decimal places
            pl = stock['daily_pl']
            pl_str = f"${abs(pl):,.2f}"
            if pl < 0:
                pl_str = f"-{pl_str}"
                
            text_parts.append(
                f"<text>{stock['symbol']}</text> "
                f"<{'up' if stock['change'] >= 0 else 'down'}>{stock['change']:+.2f}%</{('up' if stock['change'] >= 0 else 'down')}> "
                f"<{'up' if stock['daily_pl'] >= 0 else 'down'}>{pl_str}</{('up' if stock['daily_pl'] >= 0 else 'down')}> <text>•</text> "
            )
        
        self.stocks_text = "".join(text_parts)
        self.show_welcome = False

    def update_position(self):
        """Update the scroll position and handle text cycling"""
        self.offset -= self.scroll_speed
        text_width = self.get_text_width()
        
        # If text is completely off screen
        if self.offset < -text_width:
            self.offset = self.width()  # Reset position
            
            # If showing portfolio data, emit signal to check for updates
            if not self.show_welcome:
                self.check_for_portfolio_data()
                
        self.update()

    def check_for_portfolio_data(self):
        """Signal to parent to check for portfolio data"""
        # Get the main window through the parent chain
        main_window = None
        current = self
        while current:
            if isinstance(current, MainWindow):
                main_window = current
                break
            current = current.parent()
        
        if main_window and hasattr(main_window, 'portfolio_view_controller'):
            # Check if we have an active portfolio
            if main_window.portfolio_view_controller.current_portfolio:
                main_window.update_ticker_data()
            else:
                # No portfolio selected, show welcome message
                self.stocks_text = self.welcome_message
                self.show_welcome = True

    def draw_led_char(self, painter, x, y, char, color_type='text'):
        """Draw a single character using LED dots"""
        # Choose color based on type
        if color_type == 'text':
            color = self.led_text_color
            glow = self.led_glow
        elif color_type == 'up':
            color = self.led_up_color
            glow = QColor(0, 255, 0, 100)
        elif color_type == 'down':
            color = self.led_down_color
            glow = QColor(255, 0, 0, 100)
        else:
            color = self.led_text_color
            glow = self.led_glow
            
        # Simple LED matrix patterns for characters
        patterns = {
            '0': [(1,0), (2,0), (3,0), (0,1), (4,1), (0,2), (4,2), (0,3), (4,3),
                 (0,4), (4,4), (0,5), (4,5), (1,6), (2,6), (3,6)],
            '1': [(2,0), (1,1), (2,1), (2,2), (2,3), (2,4), (2,5), (2,6)],
            '2': [(0,1), (1,0), (2,0), (3,0), (4,1), (4,2), (3,3), (2,4), (1,5), (0,6), (1,6), (2,6), (3,6), (4,6)],
            '3': [(0,1), (1,0), (2,0), (3,0), (4,1), (4,2), (3,3), (4,4), (4,5), (3,6), (2,6), (1,6), (0,5)],
            '4': [(0,0), (0,1), (0,2), (1,3), (2,3), (3,3), (4,3), (4,0), (4,1), (4,2), (4,3), (4,4), (4,5), (4,6)],
            '5': [(1,0), (2,0), (3,0), (4,0), (0,1), (0,2), (1,3), (2,3), (3,3), (4,3), (4,4), (4,5), (0,5), (1,6), (2,6), (3,6)],
            '6': [(2,0), (3,0), (4,1), (1,0), (0,1), (0,2), (0,3), (0,4), (0,5), (1,6), (2,6),
                 (3,6), (4,5), (4,4), (3,3), (2,3), (1,3)],
            '7': [(0,0), (1,0), (2,0), (3,0), (4,0), (4,1), (3,2), (2,3), (1,4),
                 (1,5), (1,6)],
            '8': [(1,0), (2,0), (3,0), (0,1), (4,1), (0,2), (4,2), (1,3), (2,3),
                 (3,3), (0,4), (4,4), (0,5), (4,5), (1,6), (2,6), (3,6)],
            '9': [(1,0), (2,0), (3,0), (0,1), (4,1), (0,2), (4,2), (1,3), (2,3), (3,3), (4,3), (4,4), (4,5), (1,6), (2,6), (3,6), (0,5)],
            '.': [(1,6)],
            '$': [(1,1), (2,1), (3,1), (4,1), (0,2), (1,3), (2,3), (3,3), (4,4), (0,5), (1,5), (2,5), (3,5), (2,0), (2,1), (2,2), (2,3), (2,4), (2,5), (2,6)],
            '%': [(0,0), (1,0), (4,1), (3,2), (2,3), (1,4), (0,5), (3,6), (4,6)],
            '+': [(2,2), (1,3), (2,3), (3,3), (0,4), (1,4), (2,4), (3,4), (4,4)], # This is shown as an up arrow "▲"
            '-': [(0,2), (1,2), (2,2), (3,2), (4,2), (1,3), (2,3), (3,3), (2,4)], # This is shown as a down arrow "▼"
            ' ': [],
            '•': [(1,3), (2,3)],
            '!': [(2,0), (2,1), (2,2), (2,3), (2,4), (2,6)],
            # Add alphabet patterns
            'A': [(1,0), (2,0), (3,0), (0,5), (4,5), (0,4), (4,4), (0,3), (1,3), (2,3), (3,3), (4,3), (0,2), (4,2), (0,1), (4,1), (0,6), (4,6)],
            'B': [(0,0), (1,0), (2,0), (3,0), (0,1), (4,1), (0,2), (4,2), (0,3), (1,3), (2,3), (3,3), (0,4), (4,4), (0,5), (4,5), (0,6), (1,6), (2,6), (3,6)],
            'C': [(1,0), (2,0), (3,0), (0,1), (0,2), (0,3), (0,4), (0,5), (1,6), (2,6), (3,6)],
            'D': [(0,0), (1,0), (2,0), (3,0), (0,1), (4,1), (0,2), (4,2), (0,3), (4,3),
                (0,4), (4,4), (0,5), (4,5), (0,6), (1,6), (2,6), (3,6)],
            'E': [(0,0), (1,0), (2,0), (3,0), (4,0), (0,1), (0,2), (0,3), (1,3), (2,3),
                (0,4), (0,5), (0,6), (1,6), (2,6), (3,6), (4,6)],
            'F': [(0,0), (1,0), (2,0), (3,0), (4,0), (0,1), (0,2), (0,3), (1,3), (2,3), (0,4), (0,5), (0,6)],
            'G': [(1,0), (2,0), (3,0), (0,1), (0,2), (0,3), (0,4), (0,5), (1,6), (2,6), (3,6), (4,6), (4,5), (4,4), (4,3), (3,3)],
            'H': [(0,0), (0,1), (0,2), (0,3), (0,4), (0,5), (0,6), (4,0), (4,1), (4,2), (4,3), (4,4), (4,5), (4,6), (1,3), (2,3), (3,3)],
            'I': [(0,0), (1,0), (2,0), (3,0), (4,0), (2,1), (2,2), (2,3), (2,4), (2,5), (0,6), (1,6), (2,6), (3,6), (4,6)],
            'J': [(3,0), (4,0), (4,1), (4,2), (4,3), (4,4), (0,5), (4,5), (1,6), (2,6), (3,6)],
            'K': [(0,0), (0,1), (0,2), (0,3), (0,4), (0,5), (0,6), (0,3), (1,3), (2,2), (3,1), (4,0), (2,4), (3,5), (4,6)],
            'L': [(0,0), (0,1), (0,2), (0,3), (0,4), (0,5), (0,6), (1,6), (2,6), (3,6), (4,6)],
            'M': [(0,6), (0,5), (0,4), (0,3), (0,2), (0,1), (0,0), (1,1), (2,2), (3,1), (4,0), (4,1), (4,2), (4,3), (4,4), (4,5), (4,6)],
            'N': [(0,6), (0,5), (0,4), (0,3), (0,2), (0,1), (0,0), (1,1), (2,2), (3,3), (4,4), (4,6), (4,5), (4,4), (4,3), (4,2), (4,1), (4,0)],
            'O': [(1,0), (2,0), (3,0), (0,1), (4,1), (0,2), (4,2), (0,3), (4,3), (0,4), (4,4), (0,5), (4,5), (1,6), (2,6), (3,6)],
            'P': [(0,0), (1,0), (2,0), (3,0), (0,1), (4,1), (0,2), (4,2), (0,3), (1,3), (2,3), (3,3), (0,4), (0,5), (0,6)],
            'Q': [(1,0), (2,0), (3,0), (0,1), (4,1), (0,2), (4,2), (0,3), (4,3), (0,4), (2,4), (4,4), (1,5), (3,5), (2,6), (4,6)],
            'R': [(0,0), (1,0), (2,0), (3,0), (0,1), (4,1), (0,2), (4,2), (0,3), (1,3), (2,3), (3,3), (0,4), (2,4), (0,5), (3,5), (0,6), (4,6)],
            'S': [(1,0), (2,0), (3,0), (4,0), (0,1), (0,2), (1,3), (2,3), (3,3), (4,4), (4,5), (0,6), (1,6), (2,6), (3,6)],
            'T': [(0,0), (1,0), (2,0), (3,0), (4,0), (2,1), (2,2), (2,3), (2,4), (2,5), (2,6)],
            'U': [(0,0), (0,1), (0,2), (0,3), (0,4), (0,5), (1,6), (2,6), (3,6), (4,0), (4,1), (4,2), (4,3), (4,4), (4,5)],
            'V': [(0,0), (0,1), (0,2), (0,3), (0,4), (1,5), (2,6), (3,5), (4,4), (4,3), (4,2), (4,1), (4,0)],
            'W': [(0,0), (0,1), (0,2), (0,3), (0,4), (0,5), (1,5), (1,6), (2,4), (3,5), (3,6), (4,5), (4,4), (4,3), (4,2), (4,1), (4,0)],
            'X': [(0,0), (0,1), (4,0), (4,1), (1,2), (3,2), (2,3), (1,4), (3,4), (0,5), (0,6), (4,5), (4,6)],
            'Y': [(0,0), (0,1), (1,2), (2,3), (3,2), (4,1), (4,0), (2,4), (2,5), (2,6)],
            'Z': [(0,0), (1,0), (2,0), (3,0), (4,0), (3,1), (2,2), (1,3), (0,4), (0,5), (0,6), (1,6), (2,6), (3,6), (4,6)]
        }
        
        if char in patterns:
            # Draw glow effect first
            glow_brush = QBrush(self.led_glow)
            painter.setBrush(glow_brush)
            for dx, dy in patterns[char]:
                painter.drawEllipse(
                    x + dx * (self.led_size + self.led_spacing) - 1,
                    y + dy * (self.led_size + self.led_spacing) - 1,
                    self.led_size + 2,
                    self.led_size + 2
                )
            
            # Draw LEDs
            painter.setBrush(QBrush(color))
            for dx, dy in patterns[char]:
                painter.drawRect(
                    x + dx * (self.led_size + self.led_spacing),
                    y + dy * (self.led_size + self.led_spacing),
                    self.led_size,
                    self.led_size
                )
        
        return (self.char_width + 1) * (self.led_size + self.led_spacing)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Fill background
        painter.fillRect(self.rect(), Qt.black)
        
        # Draw text with LED effect
        x = self.offset
        y = 2
        
        current_color_type = 'text'  # Default color type
        i = 0
        
        while i < len(self.stocks_text):
            char = self.stocks_text[i]
            if char == '<':
                # Start of tag
                tag_end = self.stocks_text.find('>', i)
                if tag_end != -1:
                    tag = self.stocks_text[i+1:tag_end]
                    if not tag.startswith('/'):  # Only change color on opening tags
                        current_color_type = tag
                    i = tag_end + 1
                    continue
            else:
                x += self.draw_led_char(painter, x, y, char, current_color_type)
                i += 1
        
    def get_text_width(self):
        """Calculate the total width of the ticker text"""
        width = 0
        i = 0
        while i < len(self.stocks_text):
            char = self.stocks_text[i]
            if char == '<':
                # Skip the entire tag
                tag_end = self.stocks_text.find('>', i)
                if tag_end != -1:
                    i = tag_end + 1
                    continue
            elif char == '/':
                i += 1
                continue
            else:
                width += (self.char_width + 1) * (self.led_size + self.led_spacing)
                i += 1
        return width

class TickerContainer(QWidget):
    """
    A container widget that holds the stock ticker and toggle button.
    Features:
    - Grey border around the ticker
    - Centred toggle button
    - Toggle button shows/hides the ticker with appropriate arrow indicators
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.news_board_height = 70
        self.setFixedHeight(self.news_board_height)  # Height of the news ticker
        
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 0, 20, 0)  # Add left and right padding
        main_layout.setSpacing(0)
        
        # Create frame for ticker (adds border)
        self.ticker_frame = QFrame()
        self.ticker_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.ticker_frame.setLineWidth(3)  # Increased line width
        self.ticker_frame.setStyleSheet("""
            QFrame {
                border: 4px solid #666666;
                background-color: black;
                border-radius: 8px;
                margin-top: 2px;
            }
        """)
        
        # Create layout for ticker frame
        frame_layout = QHBoxLayout(self.ticker_frame)
        frame_layout.setContentsMargins(10, 1, 10, 1)  # Internal padding inside the border
        frame_layout.setSpacing(0)
        
        # Create the ticker
        self.ticker = StockTicker()
        frame_layout.addWidget(self.ticker)
        
        # Add frame to main layout
        main_layout.addWidget(self.ticker_frame)
        
        # Create container for toggle button to enable centering
        toggle_container = QWidget()
        toggle_container.setFixedHeight(20)
        toggle_layout = QHBoxLayout(toggle_container)
        toggle_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add spacers for centering
        toggle_layout.addStretch()
        
        # Create the toggle button
        self.toggle_btn = QPushButton("▲")  # Up arrow initially as ticker is shown
        self.toggle_btn.setFixedSize(50, 20)  # Slightly wider button
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #666666;
                color: white;
                border: none;
                border-radius: 0 0 5px 5px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #888888;
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle_ticker)
        toggle_layout.addWidget(self.toggle_btn)
        
        # Add spacer for centering
        toggle_layout.addStretch()
        
        # Add toggle container to main layout
        main_layout.addWidget(toggle_container)
        
        self.is_visible = True
        
    def toggle_ticker(self):
        """Toggles the visibility of the ticker and updates the button appearance"""
        self.is_visible = not self.is_visible
        if self.is_visible:
            self.setFixedHeight(self.news_board_height)  # Full height when visible
            self.toggle_btn.setText("▲")
            self.ticker_frame.show()
        else:
            self.setFixedHeight(20)  # Only toggle button height when hidden
            self.toggle_btn.setText("▼")
            self.ticker_frame.hide()