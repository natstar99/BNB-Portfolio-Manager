# File: main.py

import sys
import os
import logging
from PySide6.QtWidgets import QApplication
from views.main_window import MainWindow
from database.database_manager import DatabaseManager
from views.welcome_dialog import WelcomeDialog
import config

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def main():
    app = QApplication(sys.argv)

    # Check if database exists before we do anything
    db_exists = os.path.exists(config.DB_FILE)
    logger.debug(f"Database exists: {db_exists}")
    logger.debug(f"Database path: {config.DB_FILE}")

    # Initialise DatabaseManager
    db_manager = DatabaseManager(config.DB_FILE)
    db_manager.connect()

    if not db_exists:
        logger.debug("Creating new database...")
        db_manager.init_db()

    # Create the main window (without showing it yet)
    window = MainWindow(db_manager)

    if not db_exists:
        logger.debug("Showing welcome wizard...")
        welcome = WelcomeDialog(
            window.portfolio_controller,
            window.settings_controller,
            window
        )

        # Connect the import signal to the portfolio controller's import method
        welcome.import_requested.connect(window.portfolio_controller.import_transactions)

        if welcome.exec():
            logger.debug("Welcome wizard completed successfully")
            import_controller = window.portfolio_controller.import_controller
            if import_controller:
                # Connect the import completed signal to show the main window
                import_controller.import_completed.connect(window.show)
            else:
                window.show()
        else:
            logger.debug("User cancelled welcome wizard")
            sys.exit()
    else:
        # Database exists, show the main window directly
        window.show()

    # Run the application
    exit_code = app.exec()

    # Clean up
    db_manager.disconnect()

    sys.exit(exit_code)

if __name__ == "__main__":
    main()