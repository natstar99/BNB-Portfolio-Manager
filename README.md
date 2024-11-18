<p align="center">
  <img src="bnb_logo.png" alt="Bear No Bears Portfolio Logo" width="320"/>
</p>

# Bear No Bears - Portfolio Manager (BNB)

## Version 2.X Development Branch
This branch (v2.X) is a major architectural overhaul focusing on:
- SQLite database integration for reliable data storage
- Model-View-Controller (MVC) pattern for better code organisation
- Better support for international markets
- Improved transaction management
- Automated data verification
- More user control over database settings

## Core Features

### Portfolio Management
- Create and manage multiple investment portfolios
- Import transactions from CSV/Excel files
- Track stocks across 60+ global exchanges (Pretty much any stock that is available on yahoo finance)
- Automatic stock verification against Yahoo Finance
- Real-time price updates
- Historical price data tracking

### Transaction Handling
- Secure local SQLite database
- Support for buy/sell transactions
- Dividend tracking
- Automated dividend reinvestment plan (DRP) calculations
- Stock split management and verification
- Historical transaction analysis

### Market Support
- Built-in support for major international exchanges
- Automatic market code handling
- Manual override options for special cases (To handle situations where yahoo finance is missing data)
- Yahoo Finance integration for real-time data

## Technical Details

### Requirements
- Python 3.8 or higher
- PySide6 (Qt for Python)
- pandas
- yfinance

### Installation
```bash
# Clone the repository
git clone https://github.com/natstar99/BNB-Portfolio-Manager.git
cd BNB-Portfolio-Manager

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

### Project Structure
```
BNB/
├── config.py                # Application configuration
├── main.py                  # Entry point
├── controllers/             # Application logic
│   ├── import_transactions_controller.py
│   ├── portfolio_controller.py
│   └── portfolio_view_controller.py
├── models/                  # Data models
│   ├── portfolio.py
│   ├── stock.py
│   └── transaction.py
├── views/                   # User interface
│   ├── import_transactions_view.py
│   ├── manage_portfolios_view.py
│   └── my_portfolio_view.py
├── database/               # Database management
│   ├── database_manager.py
│   └── schema.sql
└── utils/                  # Utility functions
    └── stock_symbol_manager.py
```

## Current Status

### Working Features
- Portfolio creation and management
- Transaction import and verification
- International market support
- Stock split handling
- Dividend reinvestment tracking
- Historical data storage
- Basic portfolio analysis
- Yahoo Finance integration

### Under Development
V2.X is still under development and not ready for release.
- V2.X is primarily focused on portfolio set up, database management and validation, along with error handling. 
V3.X will include many of the graphs, settings,
V4.X will include deeper stock market analysis such as machine learning/neural network integration, portfolio health checks and asset correlation matrices.

### Known Limitations
- Manual price refresh required
- Limited charting capabilities
- Basic reporting only
- Some market data may be delayed

## Contributing
BNB is an open-source project and welcomes contributions from the community. Whether you're fixing bugs, adding features, or improving documentation, your help is appreciated.

### How to Contribute
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Licence
[Pending - To be determined]

## Acknowledgements
- Yahoo Finance for market data
- Qt/PySide6 for the user interface framework
- Community contributors and testers

---
*Note: This is a development branch. Features and functionality may change.*