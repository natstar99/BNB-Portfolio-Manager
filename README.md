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


# Bear No License (BNL) v1.0

## In Normal Words

The logo belongs to me and you can not steal it because I really like it. The code I don't like as much, so you can take it - just give thanks. I would prefer if you did not make money off it (unless its like voluntary donations or something), because it's meant to be a free app for all the people to use. But if you have made a significant development, and wish to take the code off on your own path and under your own name and license, I don't want to restrict that either - so in that case, just let me know first, and then it'll be sweet.

## In Lawyer Words

Copyright (c) 2024 Bear No Bears

### Definitions

- "Software" refers to the Bear No Bears Portfolio Manager application code and associated documentation
- "Logo" refers to the Bear No Bears logo, the name "Bear No Bears", and all associated branding materials
- "Original Author" refers to the creator of Bear No Bears
- "Derivative Work" refers to any modified version of the Software
- "Significant Development" refers to substantial modifications or enhancements that materially change the Software's functionality or purpose

### Logo Rights

The Logo (including the name "Bear No Bears") is protected by copyright and trademark law. Use of the Logo is permitted only for the purpose of attribution and acknowledging the Original Author ("giving thanks"). Any other use including, but not limited to, commercial use, modification, merging, publishing, distribution, sublicensing, and/or selling copies of the Logo, or using the name "Bear No Bears" as part of another project's branding, requires explicit written permission from the Original Author.

### Software License Terms

Permission is hereby granted, free of charge, to any person obtaining a copy of the Software, to deal in the Software with the following restrictions:

1. **Attribution Requirements**
   - All copies or substantial portions of the Software must include appropriate attribution ("giving thanks") to the Original Author

2. **Commercial Use**
   - Non-commercial use is freely permitted
   - Voluntary donations for non-commercial use are permitted without notification
   - Commercial use or monetisation of the Software or Derivative Works requires prior written notification to the Original Author
   - The Original Author reserves the right to review and approve commercial applications

3. **Warranty and Liability**
   - The Software is provided "AS IS", without warranty of any kind, express or implied
   - In no event shall the Original Author be liable for any claim, damages or other liability arising from the use of the Software

4. **Notification Requirements**
   - Written notifications required under this license shall be sent to the Original Author via the project's official communication channels
   - Notifications must include detailed information about:
     - Intended commercial use or monetisation plans
     - Description of Significant Development for relicensing purposes
     - Proposed new license for Derivative Works

### Additional Terms

1. This license applies only to the Software and not to the Logo or other trademarked materials
2. The Original Author reserves the right to modify this license for future versions of the Software
3. Failure to comply with the terms of this license automatically terminates your rights under this license

---

END OF TERMS AND CONDITIONS


## Acknowledgements
- Yahoo Finance for market data
- Qt/PySide6 for the user interface framework
- Community contributors and testers

---