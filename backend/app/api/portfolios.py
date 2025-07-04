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
    """Get a specific portfolio"""
    try:
        portfolio = Portfolio.get_by_id(portfolio_id)
        
        if not portfolio:
            return jsonify({
                'success': False,
                'error': 'Portfolio not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': portfolio.to_dict()
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
        
        # For now, return empty positions since we need transaction data to calculate positions
        # This endpoint would need to be implemented once transaction tracking is added
        return jsonify({
            'success': True,
            'data': {
                'positions': [],
                'message': 'Position calculation requires transaction data - feature coming soon'
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500