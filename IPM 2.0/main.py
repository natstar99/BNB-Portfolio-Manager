# File: main.py

import sys
from PySide6.QtWidgets import QApplication
from views.main_window import MainWindow
from database.database_manager import DatabaseManager
import config

def main():
    app = QApplication(sys.argv)

    # Initialise DatabaseManager
    db_manager = DatabaseManager(config.DB_FILE)
    db_manager.connect()
    db_manager.init_db()

    # Create main window
    window = MainWindow(db_manager)
    window.show()

    # Run the application
    exit_code = app.exec()

    # Clean up
    db_manager.disconnect()

    sys.exit(exit_code)

if __name__ == "__main__":
    main()