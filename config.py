# File: config.py

import os

# Get the directory of the current script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Database
DB_FILE = os.path.join(BASE_DIR, 'portfolio.db')