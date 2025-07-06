from flask import jsonify, request
from app.api import bp
from app.models import Stock
from app import db


@bp.route('/stocks', methods=['GET'])
def get_stocks():
    """Get all stocks"""
    try:
        stocks = Stock.get_all()
        return jsonify({
            'success': True,
            'data': [stock.to_dict() for stock in stocks]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/stocks', methods=['POST'])
def create_stock():
    """Create a new stock"""
    try:
        data = request.get_json()
        
        if not data or 'yahoo_symbol' not in data or 'instrument_code' not in data or 'portfolio_key' not in data:
            return jsonify({
                'success': False,
                'error': 'Yahoo symbol, instrument code, and portfolio_key are required'
            }), 400
        
        yahoo_symbol = data['yahoo_symbol']
        instrument_code = data['instrument_code']
        portfolio_key = data['portfolio_key']
        
        # Check if stock already exists for this portfolio
        existing = Stock.query.filter_by(
            portfolio_key=portfolio_key,
            instrument_code=instrument_code
        ).first()
        
        if existing:
            return jsonify({
                'success': False,
                'error': 'Stock with this instrument code already exists in this portfolio'
            }), 400
        
        stock = Stock.create(
            portfolio_key=portfolio_key,
            yahoo_symbol=yahoo_symbol,
            instrument_code=instrument_code,
            name=data.get('name', instrument_code),
            sector=data.get('sector'),
            industry=data.get('industry'),
            exchange=data.get('exchange'),
            country=data.get('country'),
            market_cap=data.get('market_cap'),
            currency=data.get('currency'),
            drp_enabled=data.get('drp_enabled', False)
        )
        
        return jsonify({
            'success': True,
            'data': stock.to_dict(),
            'message': 'Stock created successfully'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/stocks/<int:stock_id>', methods=['GET'])
def get_stock(stock_id):
    """Get a specific stock"""
    try:
        stock = Stock.get_by_id(stock_id)
        
        if not stock:
            return jsonify({
                'success': False,
                'error': 'Stock not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': stock.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/stocks/<int:stock_id>', methods=['PUT'])
def update_stock(stock_id):
    """Update a stock"""
    try:
        stock = Stock.get_by_id(stock_id)
        
        if not stock:
            return jsonify({
                'success': False,
                'error': 'Stock not found'
            }), 404
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        stock.update(**data)
        
        return jsonify({
            'success': True,
            'data': stock.to_dict(),
            'message': 'Stock updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/stocks/<int:stock_id>', methods=['DELETE'])
def delete_stock(stock_id):
    """Delete a stock"""
    try:
        stock = Stock.get_by_id(stock_id)
        
        if not stock:
            return jsonify({
                'success': False,
                'error': 'Stock not found'
            }), 404
        
        stock.delete()
        
        return jsonify({
            'success': True,
            'message': 'Stock deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/stocks/search', methods=['GET'])
def search_stocks():
    """Search stocks by symbol or name"""
    try:
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Search query is required'
            }), 400
        
        stocks = Stock.query.filter(
            db.or_(
                Stock.yahoo_symbol.ilike(f'%{query}%'),
                Stock.instrument_code.ilike(f'%{query}%'),
                Stock.name.ilike(f'%{query}%')
            )
        ).limit(20).all()
        
        return jsonify({
            'success': True,
            'data': [stock.to_dict() for stock in stocks]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/stocks/<int:stock_id>/price', methods=['PUT'])
def update_stock_price(stock_id):
    """Update stock price"""
    try:
        stock = Stock.get_by_id(stock_id)
        
        if not stock:
            return jsonify({
                'success': False,
                'error': 'Stock not found'
            }), 404
        
        data = request.get_json()
        if not data or 'price' not in data:
            return jsonify({
                'success': False,
                'error': 'Price is required'
            }), 400
        
        stock.update_price(data['price'])
        
        return jsonify({
            'success': True,
            'data': stock.to_dict(),
            'message': 'Stock price updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/stocks/<int:stock_id>/verify', methods=['POST'])
def verify_stock(stock_id):
    """Verify a stock"""
    try:
        stock = Stock.get_by_id(stock_id)
        
        if not stock:
            return jsonify({
                'success': False,
                'error': 'Stock not found'
            }), 404
        
        stock.verify()
        
        return jsonify({
            'success': True,
            'data': stock.to_dict(),
            'message': 'Stock verified successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/stocks/<int:stock_id>/market-prices', methods=['GET'])
def get_stock_market_prices(stock_id):
    """
    Get market prices for a stock from FACT_MARKET_PRICES.
    
    This endpoint replaces the deprecated historical-prices endpoint and uses
    the proper Kimball star schema with stock_key and date_key relationships.
    
    DESIGN DECISION: Uses MarketPrice model instead of deprecated HistoricalPrice
    to ensure consistency with the star schema and daily metrics calculations.
    """
    try:
        from app.models.market_prices import MarketPrice
        from app.models.date_dimension import DateDimension
        
        stock = Stock.get_by_id(stock_id)
        
        if not stock:
            return jsonify({
                'success': False,
                'error': 'Stock not found'
            }), 404
        
        # Convert stock.id to stock_key for star schema compatibility
        stock_key = stock.stock_key
        
        # Parse date parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        start_date_key = None
        end_date_key = None
        
        if start_date:
            start_date_key = DateDimension.get_date_key(start_date)
        if end_date:
            end_date_key = DateDimension.get_date_key(end_date)
        
        # Get market prices using star schema
        if start_date_key and end_date_key:
            market_prices = MarketPrice.get_price_range(stock_key, start_date_key, end_date_key)
        else:
            # Get recent prices if no date range specified
            market_prices = MarketPrice.query.filter_by(stock_key=stock_key).order_by(MarketPrice.date_key.desc()).limit(100).all()
        
        return jsonify({
            'success': True,
            'data': [price.to_dict() for price in market_prices]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500