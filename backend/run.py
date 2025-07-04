#!/usr/bin/env python3
"""
BNB Portfolio Manager Backend
Entry point for the Flask application
"""

from app import create_app, db
from app.models import Portfolio, Stock, Transaction

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'Portfolio': Portfolio,
        'Stock': Stock,
        'Transaction': Transaction
    }


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)