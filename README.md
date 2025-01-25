<p align="center">
  <img src="bnb_logo.png" alt="Bear No Bears Portfolio Logo" width="320"/>
</p>

# Bear No Bears - Portfolio Manager (BNB)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

## About
The Bear No Bears (BNB) Portfolio Manager is an advanced, open-source portfolio management application designed to help investors track, analyse, and optimise their stock market investments. Built with Python and modern data analysis tools, BNB provides sophisticated portfolio analytics while maintaining an intuitive user interface for both novice and experienced investors.

## Quick Start
1. Download the latest release from our Releases page
   - https://github.com/natstar99/BNB-Portfolio-Manager/releases
2. Extract the downloaded ZIP file to your preferred location
3. Run the BNB_Portfolio_Manager.exe file
4. Create a new portfolio, import your transactions, and start managing your portfolio

## Core Features

### Portfolio Management
- Multi-portfolio support for managing different investment strategies
- Bulk import transactions from CSV/Excel files, or add individually through the application
- Stock split handling with automatic detection and verification
- Dividend reinvestment (DRP) tracking and management
- Tax optimisation calculation support for realised profit/loss (FIFO/LIFO/HIFO)

### Portfolio Analysis
- Interactive portfolio performance visualisation
- Multiple chart types (line, area, pie charts)
- Profitability analysis (percentage and dollar values)
- Market value tracking
- Dividend performance analysis and reinvestment tracking
- Portfolio distribution insights with dynamic updates
- Custom date range analysis for targeted performance review

### Market Support
- International market support from 60+ global exchanges (Any stock available on Yahoo Finance)
- Intelligent market code handling
- Manual override options for data gaps
- Automatic currency conversion for international portfolios

### Current Status and Future Development
BNB Portfolio Manager is currently in active development. With further areas of development including:

- Improving the asset correlation matrices and risk analysis (Sharpe ratio, beta, etc.)
- Improving the portfolio optimisation features
- Custom benchmark comparisons

Machine learning/neural network integration:
 - Portfolio risk prediction
 - Market trend analysis
 - Anomaly detection
 - Price movement forecasting
 - Investment pattern recognition

Market intelligence features:
 - Automated news aggregation and sentiment analysis
 - Real-time market trend detection
 - Company financial health monitoring
 - Sector performance analysis
 - Social media sentiment tracking

Personal finance integratoin:
 - Budgeting and expense tracking
 - Net worth monitoring
 - Income and expense categorisation
 - Property portfolio tracking

## Contributing
BNB is an open-source project and welcomes contributions from the community. Whether you're fixing bugs, adding features, or improving documentation, your help is appreciated.

### How to Contribute
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Technical Details (For Developers)

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

├── .vscode/                        # VS Code configuration
│   ├── launch.json                 # Debug and launch configurations
│   ├── settings.json               # VS Code workspace settings
│   └── tasks.json                  # Task to delete (Nuke) existing .db file when running application
│
├── controllers/                              # Application logic controllers
│   ├── import_transactions_controller.py     # Handles importing of transaction data
│   ├── market_analysis_controller.py         # Controls market analysis features
│   ├── portfolio_controller.py               # Core portfolio operations controller
│   ├── portfolio_optimisation_controller.py  # Portfolio optimisation features
│   ├── portfolio_study_controller.py         # Controls portfolio analysis and visualisation
│   ├── portfolio_view_controller.py          # Manages portfolio view and interactions
│   ├── portfolio_visualisation_controller.py # Manages portfolio view and interactions
│   └── settings_controller.py                # Manages application settings
│
├── database/                        # Database related files
│   ├── database_manager.py          # Core database operations manager
│   ├── final_metrics.sql            # SQL for portfolio metrics calculations
│   ├── final_metrics_manager.py     # Manages portfolio metrics calculations
│   └── schema.sql                   # Main database schema
│
├── models/                          # Data models
│   ├── portfolio.py                 # Portfolio data model
│   ├── stock.py                     # Stock data model
│   └── transaction.py               # Transaction data model
│
├── utils/                           # Utility functions
│   ├── date_utils.py                # Date handling utilities
│   ├── fifo_hifo_lifo_calculator.py # Tax lot calculation utilities
│   ├── historical_data_collector.py # Historical data collection utilities
│   └── yahoo_finance_service.py     # Yahoo Finance API service wrapper
│
├── views/                             # User interface views
│   ├── historical_data_view.py         # Historical data display view
│   ├── import_transactions_view.py     # Transaction import interface
│   ├── main_window.py                  # Main application window
│   ├── manage_markets_dialog.py        # Market settings management dialog
│   ├── manage_portfolios_view.py       # Portfolio management interface
│   ├── market_analysis_view.py         # Market analysis interface
│   ├── my_portfolio_view.py            # Individual portfolio view
│   ├── portfolio_optimisation_view.py  # Portfolio optimisation interface
│   ├── portfolio_study_view.py         # Portfolio analysis interface
│   ├── portfolio_visualisation_view.py # Portfolio visualisation interface
│   ├── settings_view.py                # Application settings interface
│   └── verify_transactions_view.py     # Transaction verification interface
│
│
├── config.py                         # Core configuration settings
├── config.yaml                       # User configuration file
├── build_exe.py                      # Executable build script
└──  main.py                          # Application entry point   

```

## Licensing and Legal Information

### Software License
Bear No Bears Portfolio Manager (BNB) is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0). This means:
- You can use, modify, and distribute this software freely
- If you modify the software, you must release your modifications under the same license
- If you run a modified version of this software on a server and make it available to users over a network, you must make your modified source code available to those users

### Third-Party Components
This software includes several third-party components:
- PySide6 (Qt for Python): LGPL v3
- pandas: BSD 3-Clause License
- matplotlib: PSF License
- numpy: BSD License
- yfinance: Apache License 2.0

### Data Usage Notice
This software uses data from Yahoo Finance. Usage of this data is subject to Yahoo Finance's terms of service. Users are responsible for ensuring their usage complies with these terms.

### Warranty Disclaimer
This software is provided "as is", without warranty of any kind, express or implied. See the AGPL-3.0 license for details.

## 
© 2024 Bear No Bears. All Rights Reserved.