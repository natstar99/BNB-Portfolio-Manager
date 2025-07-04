# BNB Portfolio Manager - Architecture Documentation

## Overview

The BNB Portfolio Manager has been restructured using modern web application architecture with clear separation of concerns:

- **Backend**: Flask REST API with SQLAlchemy ORM
- **Frontend**: React with TypeScript
- **Shared**: Common types and constants

## Architecture Principles

### MVC Implementation
- **Models**: SQLAlchemy models in `backend/app/models/`
- **Views**: React components in `frontend/src/`
- **Controllers**: Flask controllers in `backend/app/controllers/`

### Service Layer
- **External APIs**: Yahoo Finance integration
- **Business Logic**: Portfolio calculations and metrics
- **Data Processing**: ETL operations within service classes

## Development Workflow

### Backend Development
```bash
cd backend
pip install -r requirements.txt
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
python run.py
```

### Frontend Development
```bash
cd frontend
npm install
npm start
```

## API Design

RESTful API endpoints:
- `GET /api/portfolios` - List portfolios
- `POST /api/portfolios` - Create portfolio
- `GET /api/portfolios/:id` - Get portfolio details
- `PUT /api/portfolios/:id` - Update portfolio
- `DELETE /api/portfolios/:id` - Delete portfolio

Similar patterns for stocks, transactions, and metrics.

## Data Flow

1. **Frontend** makes API requests to backend
2. **Controllers** handle requests and coordinate business logic
3. **Services** handle external data sources and complex operations
4. **Models** manage database operations
5. **Response** sent back through the API

## Key Improvements

1. **Separation of Concerns**: Clear boundaries between layers
2. **Type Safety**: TypeScript throughout frontend
3. **API First**: Backend designed as API service
4. **Modern UI**: React with hooks and modern patterns
5. **Testability**: Each layer can be tested independently