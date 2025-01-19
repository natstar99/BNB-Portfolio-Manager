# File: config.py

import os
import sys
import appdirs

# Determine if we're running as executable
is_executable = getattr(sys, 'frozen', False)

if is_executable:
    # When running as exe, use the user's app data directory
    app_name = "BNB Portfolio Manager"
    app_author = "Bear No Bears"
    BASE_DIR = appdirs.user_data_dir(app_name, app_author)
    
    # Create the directory if it doesn't exist
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)
else:
    # When running as Python script, use the original behavior
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Database path - this works the same in both cases
DB_FILE = os.path.join(BASE_DIR, 'portfolio.db')