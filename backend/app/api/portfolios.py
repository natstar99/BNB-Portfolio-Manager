from flask import jsonify, request
from app.api import bp
from app.models import Portfolio, Stock
from app import db


@bp.route('/portfolios', methods=['GET'])
def get_portfolios():
    """Get all portfolios"""
    try:
        portfolios = Portfolio.get_all()
        return jsonify({
            'success': True,
            'data': [portfolio.to_dict() for portfolio in portfolios]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/portfolios', methods=['POST'])
def create_portfolio():
    """Create a new portfolio"""
    try:
        data = request.get_json()
        
        if not data or 'name' not in data:
            return jsonify({
                'success': False,
                'error': 'Portfolio name is required'
            }), 400
        
        portfolio_name = data['name']
        base_currency = data.get('currency', 'USD')
        description = data.get('description')
        
        # Check if portfolio with this name already exists
        existing = Portfolio.query.filter_by(portfolio_name=portfolio_name, is_active=True).first()
        if existing:
            return jsonify({
                'success': False,
                'error': 'Portfolio with this name already exists'
            }), 400
        
        portfolio = Portfolio.create(
            portfolio_name=portfolio_name, 
            base_currency=base_currency,
            description=description
        )
        
        return jsonify({
            'success': True,
            'data': portfolio.to_dict(),
            'message': 'Portfolio created successfully'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/portfolios/<int:portfolio_id>', methods=['GET'])
def get_portfolio(portfolio_id):
    """Get a specific portfolio with metrics"""
    try:
        portfolio = Portfolio.get_by_id(portfolio_id)
        
        if not portfolio:
            return jsonify({
                'success': False,
                'error': 'Portfolio not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': portfolio.to_dict(include_metrics=True)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/portfolios/<int:portfolio_id>', methods=['PUT'])
def update_portfolio(portfolio_id):
    """Update a portfolio"""
    try:
        portfolio = Portfolio.get_by_id(portfolio_id)
        
        if not portfolio:
            return jsonify({
                'success': False,
                'error': 'Portfolio not found'
            }), 404
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Check if name already exists for another portfolio
        if 'name' in data:
            existing = Portfolio.query.filter(
                Portfolio.portfolio_name == data['name'],
                Portfolio.portfolio_key != portfolio_id,
                Portfolio.is_active == True
            ).first()
            if existing:
                return jsonify({
                    'success': False,
                    'error': 'Portfolio with this name already exists'
                }), 400
                
            # Update the field mapping
            data['portfolio_name'] = data.pop('name')
        
        if 'currency' in data:
            data['base_currency'] = data.pop('currency')
        
        portfolio.update(**data)
        
        return jsonify({
            'success': True,
            'data': portfolio.to_dict(),
            'message': 'Portfolio updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/portfolios/<int:portfolio_id>', methods=['DELETE'])
def delete_portfolio(portfolio_id):
    """Delete a portfolio"""
    try:
        portfolio = Portfolio.get_by_id(portfolio_id)
        
        if not portfolio:
            return jsonify({
                'success': False,
                'error': 'Portfolio not found'
            }), 404
        
        portfolio.delete()
        
        return jsonify({
            'success': True,
            'message': 'Portfolio deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/portfolios/<int:portfolio_id>/stocks', methods=['GET'])
def get_portfolio_stocks(portfolio_id):
    """Get all stocks in a portfolio"""
    try:
        portfolio = Portfolio.get_by_id(portfolio_id)
        
        if not portfolio:
            return jsonify({
                'success': False,
                'error': 'Portfolio not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': [stock.to_dict() for stock in portfolio.stocks]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/portfolios/<int:portfolio_id>/stocks', methods=['POST'])
def add_stock_to_portfolio(portfolio_id):
    """Add a stock to a portfolio"""
    try:
        portfolio = Portfolio.get_by_id(portfolio_id)
        
        if not portfolio:
            return jsonify({
                'success': False,
                'error': 'Portfolio not found'
            }), 404
        
        data = request.get_json()
        if not data or 'stock_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Stock ID is required'
            }), 400
        
        stock = Stock.get_by_id(data['stock_id'])
        if not stock:
            return jsonify({
                'success': False,
                'error': 'Stock not found'
            }), 404
        
        portfolio.add_stock(stock)
        
        return jsonify({
            'success': True,
            'message': 'Stock added to portfolio successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/portfolios/<int:portfolio_id>/stocks/<int:stock_id>', methods=['DELETE'])
def remove_stock_from_portfolio(portfolio_id, stock_id):
    """Remove a stock from a portfolio"""
    try:
        portfolio = Portfolio.get_by_id(portfolio_id)
        
        if not portfolio:
            return jsonify({
                'success': False,
                'error': 'Portfolio not found'
            }), 404
        
        stock = Stock.get_by_id(stock_id)
        if not stock:
            return jsonify({
                'success': False,
                'error': 'Stock not found'
            }), 404
        
        portfolio.remove_stock(stock)
        
        return jsonify({
            'success': True,
            'message': 'Stock removed from portfolio successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/portfolios/<int:portfolio_id>/stocks/for-verification', methods=['GET'])
def get_portfolio_stocks_for_verification(portfolio_id):
    """Get all portfolio stocks formatted for StockVerification component"""
    try:
        portfolio = Portfolio.get_by_id(portfolio_id)
        
        if not portfolio:
            return jsonify({
                'success': False,
                'error': 'Portfolio not found'
            }), 404
        
        # Get all stocks in the portfolio and return them as complete stock objects
        # The StockVerification component will use these to populate the verification table
        stock_objects = [stock.to_dict() for stock in portfolio.stocks]
        
        return jsonify({
            'success': True,
            'data': {
                'new_stock_symbols': stock_objects,  # Changed from strings to full objects
                'validation_results': {
                    'new_stock_symbols': stock_objects  # Changed from strings to full objects
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/portfolios/<int:portfolio_id>/positions', methods=['GET'])
def get_portfolio_positions(portfolio_id):
    """Get portfolio positions with calculated metrics"""
    try:
        portfolio = Portfolio.get_by_id(portfolio_id)
        
        if not portfolio:
            return jsonify({
                'success': False,
                'error': 'Portfolio not found'
            }), 404
        
        positions = portfolio.get_current_positions()
        
        return jsonify({
            'success': True,
            'data': {
                'positions': positions,
                'count': len(positions)
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/portfolios/<int:portfolio_id>/analytics', methods=['GET'])
def get_portfolio_analytics(portfolio_id):
    """Get comprehensive portfolio analytics and dashboard data"""
    try:
        portfolio = Portfolio.get_by_id(portfolio_id)
        
        if not portfolio:
            return jsonify({
                'success': False,
                'error': 'Portfolio not found'
            }), 404
        
        # Get dashboard metrics - this now always returns data (zero values if no metrics)
        dashboard_metrics = portfolio.get_dashboard_metrics()
        
        # Get current positions (returns empty list if no data)
        positions = portfolio.get_current_positions()
        
        # Get recent transactions (returns empty list if no data)
        recent_transactions = portfolio.get_recent_transactions(limit=5)
        
        return jsonify({
            'success': True,
            'data': {
                'portfolio': dashboard_metrics,
                'positions': positions,
                'recent_transactions': recent_transactions,
                'summary': {
                    'active_positions': len(positions),
                    'total_transactions': len(recent_transactions),
                    'has_data': dashboard_metrics['total_value'] > 0 or len(positions) > 0
                }
            }
        })
        
    except Exception as e:
        print(f"Error in get_portfolio_analytics: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500