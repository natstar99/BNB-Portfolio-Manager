# BNB Portfolio Manager - Modernised Architecture

## Overview

This is the modernised version of the BNB Portfolio Manager, restructured with proper separation of concerns and modern web development practices.

## Architecture

### Technology Stack
- **Backend**: Flask REST API with SQLAlchemy ORM
- **Frontend**: React with TypeScript
- **Database**: SQLite (development) / PostgreSQL (production ready)
- **Shared**: Common TypeScript types and constants

### Project Structure
```
├── backend/                    # Flask REST API
│   ├── app/
│   │   ├── api/               # REST endpoints
│   │   ├── controllers/       # Business logic (to be added)
│   │   ├── models/           # SQLAlchemy database models
│   │   ├── services/         # External integrations (to be added)
│   │   └── utils/            # Shared utilities (to be added)
│   ├── migrations/           # Database migrations
│   ├── config.py             # Configuration settings
│   ├── run.py                # Application entry point
│   └── requirements.txt      # Python dependencies
├── frontend/                  # React TypeScript app
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── pages/           # Page-level components
│   │   ├── hooks/           # Custom React hooks
│   │   ├── services/        # API client code
│   │   └── utils/           # Frontend utilities
│   └── package.json         # Node.js dependencies
├── shared/                   # Shared types/constants
│   ├── types.ts             # TypeScript type definitions
│   └── constants.ts         # Shared constants
└── docs/                     # Documentation
```

## Development Setup

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm or yarn

### Backend Setup

1. **Navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database**
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

6. **Run the development server**
   ```bash
   python run.py
   ```

   Backend will be available at: `http://localhost:5000`

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Set up environment variables**
   ```bash
   # Create .env file if needed
   echo "REACT_APP_API_URL=http://localhost:5000/api" > .env
   ```

4. **Run the development server**
   ```bash
   npm start
   ```

   Frontend will be available at: `http://localhost:3000`

## API Documentation

### Authentication
Currently, no authentication is implemented. This will be added in future iterations.

### Endpoints

#### Portfolios
- `GET /api/portfolios` - List all portfolios
- `POST /api/portfolios` - Create new portfolio
- `GET /api/portfolios/{id}` - Get portfolio details
- `PUT /api/portfolios/{id}` - Update portfolio
- `DELETE /api/portfolios/{id}` - Delete portfolio
- `GET /api/portfolios/{id}/stocks` - Get portfolio stocks
- `POST /api/portfolios/{id}/stocks` - Add stock to portfolio
- `DELETE /api/portfolios/{id}/stocks/{stock_id}` - Remove stock from portfolio

#### Stocks
- `GET /api/stocks` - List all stocks
- `POST /api/stocks` - Create new stock
- `GET /api/stocks/{id}` - Get stock details
- `PUT /api/stocks/{id}` - Update stock
- `DELETE /api/stocks/{id}` - Delete stock
- `GET /api/stocks/search?q={query}` - Search stocks
- `PUT /api/stocks/{id}/price` - Update stock price
- `POST /api/stocks/{id}/verify` - Verify stock
- `GET /api/stocks/{id}/historical-prices` - Get historical prices

#### Transactions
- `GET /api/transactions` - List transactions (with filters)
- `POST /api/transactions` - Create new transaction
- `GET /api/transactions/{id}` - Get transaction details
- `PUT /api/transactions/{id}` - Update transaction
- `DELETE /api/transactions/{id}` - Delete transaction
- `POST /api/transactions/bulk` - Bulk create transactions
- `GET /api/transactions/summary` - Get transaction summary

## Database Schema

The application uses SQLAlchemy ORM with the following main models:

- **Portfolio**: Portfolio management
- **Stock**: Stock information and market data
- **Transaction**: Buy/sell/dividend/split transactions
- **HistoricalPrice**: Historical price data
- **FinalMetric**: Calculated portfolio metrics
- **RealisedPL**: Realised profit/loss calculations
- **StockSplit**: Stock split information
- **SupportedCurrency**: Currency definitions
- **MarketCode**: Market and exchange codes

## Key Improvements

### 1. Separation of Concerns
- **Clear MVC pattern**: Models (SQLAlchemy), Views (React), Controllers (Flask)
- **Service layer**: For external integrations and complex business logic
- **API-first design**: Backend serves data, frontend consumes

### 2. Type Safety
- **TypeScript throughout**: Shared types between frontend and backend
- **Runtime validation**: API request/response validation
- **Type-safe API client**: Strongly typed API calls

### 3. Modern Development Practices
- **RESTful API design**: Standard HTTP methods and status codes
- **Error handling**: Consistent error responses and frontend error states
- **Pagination**: Built-in pagination for large datasets
- **Search functionality**: Full-text search across entities

### 4. Scalability
- **Modular architecture**: Easy to add new features and data sources
- **Database migrations**: Version-controlled schema changes
- **Environment configuration**: Easy deployment across environments

## Migration from Legacy Code

### Phase 1: ✅ Foundation
- [x] New directory structure
- [x] Flask backend with SQLAlchemy models
- [x] React frontend with TypeScript
- [x] Basic API endpoints
- [x] Shared type definitions

### Phase 2: Data Migration (Next Steps)
- [ ] Migrate existing business logic
- [ ] Yahoo Finance service integration
- [ ] Portfolio calculation engine
- [ ] Data import/export functionality

### Phase 3: Advanced Features (Future)
- [ ] Real-time data updates
- [ ] Advanced analytics and charts
- [ ] User authentication and authorization
- [ ] Background job processing
- [ ] API rate limiting and caching

## Development Guidelines

### Code Style
- **Backend**: Follow PEP 8 for Python code
- **Frontend**: Use ESLint and Prettier for TypeScript/React
- **Database**: Use descriptive table and column names
- **API**: Follow RESTful conventions

### Testing
- **Backend**: pytest for unit and integration tests
- **Frontend**: Jest and React Testing Library
- **API**: Automated API testing with pytest

### Documentation
- **API**: OpenAPI/Swagger documentation (to be added)
- **Code**: Inline comments for complex business logic
- **Architecture**: Keep this README updated

## Contributing

1. Create a feature branch from `main`
2. Make your changes following the coding guidelines
3. Add tests for new functionality
4. Update documentation as needed
5. Create a pull request for review

## License

This project maintains the same license as the original BNB Portfolio Manager (AGPL-3.0).

## Support

For questions or issues with the new architecture, please refer to the original repository's issue tracker or documentation.