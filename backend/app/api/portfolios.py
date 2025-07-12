from flask import request
from app.api import bp
from app.models import Portfolio, Stock
from app import db
from app.utils.error_handler import handle_api_errors, success_response, error_response


@bp.route('/portfolios', methods=['GET'])
@handle_api_errors
def get_portfolios():
    """Get all portfolios"""
    portfolios = Portfolio.get_all()
    return success_response([portfolio.to_dict() for portfolio in portfolios])


@bp.route('/portfolios', methods=['POST'])
@handle_api_errors
def create_portfolio():
    """Create a new portfolio"""
    data = request.get_json()
    
    if not data or 'name' not in data:
        raise ValueError('Portfolio name is required')
    
    portfolio_name = data['name']
    base_currency = data.get('currency', 'USD')
    description = data.get('description')
    
    # Check if portfolio with this name already exists
    existing = Portfolio.query.filter_by(portfolio_name=portfolio_name, is_active=True).first()
    if existing:
        raise ValueError('Portfolio with this name already exists')
    
    try:
        portfolio = Portfolio.create(
            portfolio_name=portfolio_name, 
            base_currency=base_currency,
            description=description
        )
        response = success_response(portfolio.to_dict(), 'Portfolio created successfully')
        response.status_code = 201
        return response
    except Exception as e:
        db.session.rollback()
        raise


@bp.route('/portfolios/<int:portfolio_id>', methods=['GET'])
@handle_api_errors
def get_portfolio(portfolio_id):
    """Get a specific portfolio with metrics"""
    portfolio = Portfolio.get_by_id(portfolio_id)
    
    if not portfolio:
        return error_response('Portfolio not found', 404)
    
    return success_response(portfolio.to_dict(include_metrics=True))


@bp.route('/portfolios/<int:portfolio_id>', methods=['PUT'])
@handle_api_errors
def update_portfolio(portfolio_id):
    """Update a portfolio"""
    portfolio = Portfolio.get_by_id(portfolio_id)
    
    if not portfolio:
        return error_response('Portfolio not found', 404)
    
    data = request.get_json()
    if not data:
        raise ValueError('No data provided')
    
    # Check if name already exists for another portfolio
    if 'name' in data:
        existing = Portfolio.query.filter(
            Portfolio.portfolio_name == data['name'],
            Portfolio.portfolio_key != portfolio_id,
            Portfolio.is_active == True
        ).first()
        if existing:
            raise ValueError('Portfolio with this name already exists')
            
        # Update the field mapping
        data['portfolio_name'] = data.pop('name')
    
    if 'currency' in data:
        data['base_currency'] = data.pop('currency')
    
    try:
        portfolio.update(**data)
        return success_response(portfolio.to_dict(), 'Portfolio updated successfully')
    except Exception as e:
        db.session.rollback()
        raise


@bp.route('/portfolios/<int:portfolio_id>', methods=['DELETE'])
@handle_api_errors
def delete_portfolio(portfolio_id):
    """Delete a portfolio"""
    portfolio = Portfolio.get_by_id(portfolio_id)
    
    if not portfolio:
        return error_response('Portfolio not found', 404)
    
    try:
        portfolio.delete()
        return success_response(message='Portfolio deleted successfully')
    except Exception as e:
        db.session.rollback()
        raise

@bp.route('/portfolios/<int:portfolio_id>/stocks/for-verification', methods=['GET'])
@handle_api_errors
def get_portfolio_stocks_for_verification(portfolio_id):
    """Get all portfolio stocks formatted for StockVerification component"""
    portfolio = Portfolio.get_by_id(portfolio_id)
    
    if not portfolio:
        return error_response('Portfolio not found', 404)
    
    # Get all stocks in the portfolio and return them as complete stock objects
    # The StockVerification component will use these to populate the verification table
    stock_objects = [stock.to_dict() for stock in portfolio.stocks]
    
    return success_response({
        'new_stock_symbols': stock_objects,  # Changed from strings to full objects
        'validation_results': {
            'new_stock_symbols': stock_objects  # Changed from strings to full objects
        }
    })

@bp.route('/portfolios/<int:portfolio_id>/analytics', methods=['GET'])
@handle_api_errors
def get_portfolio_analytics(portfolio_id):
    """Get comprehensive portfolio analytics and dashboard data"""
    portfolio = Portfolio.get_by_id(portfolio_id)
    
    if not portfolio:
        return error_response('Portfolio not found', 404)
    
    # Get dashboard metrics - this now always returns data (zero values if no metrics)
    dashboard_metrics = portfolio.get_dashboard_metrics()
    
    # Get current positions (returns empty list if no data)
    positions = portfolio.get_current_positions()
    
    # Get recent transactions (returns empty list if no data)
    recent_transactions = portfolio.get_recent_transactions(limit=5)
    
    return success_response({
        'portfolio': dashboard_metrics,
        'positions': positions,
        'recent_transactions': recent_transactions,
        'summary': {
            'active_positions': len(positions),
            'total_transactions': len(recent_transactions),
            'has_data': dashboard_metrics['total_value'] > 0 or len(positions) > 0
        }
    })


@bp.route('/portfolios/<int:portfolio_id>/staged-transactions', methods=['GET'])
@handle_api_errors
def get_portfolio_staged_transactions(portfolio_id):
    """Get unprocessed transactions from STG_RAW_TRANSACTIONS for a portfolio"""
    from app.models.transaction import RawTransaction
    
    portfolio = Portfolio.get_by_id(portfolio_id)
    
    if not portfolio:
        return error_response('Portfolio not found', 404)
    
    # Get unprocessed transactions for this portfolio
    staged_transactions = RawTransaction.query.filter_by(
        portfolio_id=portfolio_id,
        processed_flag=False
    ).order_by(RawTransaction.raw_import_timestamp.desc()).all()
    
    return success_response({
        'transactions': [transaction.to_dict() for transaction in staged_transactions],
        'count': len(staged_transactions)
    })