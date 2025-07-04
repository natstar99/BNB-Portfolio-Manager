#!/usr/bin/env python3
"""
BNB Portfolio Manager - Flask Application Entry Point
Simple entry point that creates and runs the Flask app
"""

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)