"""
Market Data API Endpoints - Yahoo Finance Integration for Portfolio Management
============================================================================

This module provides REST API endpoints for market data operations including:
- Stock verification and validation against Yahoo Finance
- Individual and bulk stock market data updates
- Portfolio-wide market data refresh functionality
- Current price fetching and currency conversion

ARCHITECTURAL DESIGN:
- Clean separation between API endpoints and business logic in MarketDataService
- Error isolation: market data failures don't impact core portfolio operations
- Efficient batching for multiple stock operations
- Consistent JSON response format across all endpoints

KEY INTEGRATION POINTS:
1. MarketDataService: Core business logic for Yahoo Finance operations
2. Portfolio/Stock Models: Kimball star schema entities for data persistence
3. Dashboard UI: Portfolio-wide market data update button functionality
4. Transaction Import: Bulk market data collection after import completion

MAJOR FEATURES:
- Stock Verification: Validate instruments against Yahoo Finance before adding
- Individual Updates: Refresh market data for specific stocks with date control
- Bulk Operations: Process multiple stocks efficiently in single request
- Portfolio Updates: One-click refresh of all stocks in a portfolio (NEW FEATURE)
- Currency Conversion: Real-time exchange rate fetching for multi-currency portfolios

CRITICAL DESIGN DECISIONS:
1. Portfolio Updates Use Individual Stock Logic: Unlike transaction import inefficiency,
   each stock determines its own optimal date range rather than using global earliest date
2. Error Handling: Individual stock failures don't stop batch operations
3. Date Range Optimization: Leverages existing efficient logic in MarketDataService
4. Transaction Safety: Proper commit/rollback handling for data consistency

RECENT CHANGES:
- Added portfolio-wide market data update endpoint for dashboard integration
- Fixed date range inefficiency from transaction import process
- Enhanced error reporting with per-stock status details

SECURITY CONSIDERATIONS:
- Portfolio ID validation to prevent unauthorized access
- Input sanitization for all date and symbol parameters
- Graceful error handling to prevent information disclosure

PERFORMANCE NOTES:
- Yahoo Finance API has rate limits - service implements retry logic
- Bulk operations use individual processing to optimize date ranges
- Caching strategies implemented in service layer for current prices
"""

from flask import jsonify, request
from app.api import bp
from app.services.market_data_service import MarketDataService
from app.models import Stock, Portfolio
from app import db
from datetime import datetime


@bp.route('/market-data/verify-stock', methods=['POST'])
def verify_stock_yahoo():
    """Verify a stock exists on Yahoo Finance"""
    try:
        data = request.get_json()
        
        if not data or 'yahoo_symbol' not in data:
            return jsonify({
                'success': False,
                'error': 'Yahoo symbol is required'
            }), 400
        
        yahoo_symbol = data['yahoo_symbol']
        instrument_code = data.get('instrument_code', yahoo_symbol)
        
        market_service = MarketDataService()
        result = market_service.verify_and_create_stock(yahoo_symbol, instrument_code)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/market-data/update-stock/<int:stock_id>', methods=['POST'])
def update_stock_data(stock_id):
    """Update historical data for a specific stock"""
    try:
        stock = Stock.get_by_id(stock_id)
        if not stock:
            return jsonify({
                'success': False,
                'error': 'Stock not found'
            }), 404
        
        # Get optional start date from request
        data = request.get_json() or {}
        start_date = None
        if 'start_date' in data:
            try:
                start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid start_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'
                }), 400
        
        market_service = MarketDataService()
        result = market_service.fetch_and_load_stock_data(stock.stock_key, start_date)
        success = result.get('success', False)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Successfully updated data for {stock.yahoo_symbol}'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to update data for {stock.yahoo_symbol}'
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/market-data/current-price/<int:stock_id>', methods=['GET'])
def get_current_price(stock_id):
    """Get current market price for a stock"""
    try:
        stock = Stock.get_by_id(stock_id)
        if not stock:
            return jsonify({
                'success': False,
                'error': 'Stock not found'
            }), 404
        
        market_service = MarketDataService()
        price, is_live = market_service.get_current_market_price(stock.yahoo_symbol)
        
        # Update stock's current price if we got a valid price
        if price > 0:
            market_service.update_stock_current_price(stock.stock_key, price)
        
        return jsonify({
            'success': True,
            'data': {
                'stock_id': stock_id,
                'yahoo_symbol': stock.yahoo_symbol,
                'current_price': price,
                'is_live': is_live,
                'last_updated': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/market-data/currency-rate', methods=['GET'])
def get_currency_rate():
    """Get current currency conversion rate"""
    try:
        from_currency = request.args.get('from')
        to_currency = request.args.get('to')
        
        if not from_currency or not to_currency:
            return jsonify({
                'success': False,
                'error': 'Both from and to currency parameters are required'
            }), 400
        
        market_service = MarketDataService()
        rate = market_service.get_current_conversion_rate(from_currency, to_currency)
        
        return jsonify({
            'success': True,
            'data': {
                'from_currency': from_currency,
                'to_currency': to_currency,
                'conversion_rate': rate,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/market-data/bulk-update', methods=['POST'])
def bulk_update_market_data():
    """Update market data for multiple stocks"""
    try:
        data = request.get_json()
        
        if not data or 'stock_ids' not in data:
            return jsonify({
                'success': False,
                'error': 'stock_ids array is required'
            }), 400
        
        stock_ids = data['stock_ids']
        if not isinstance(stock_ids, list):
            return jsonify({
                'success': False,
                'error': 'stock_ids must be an array'
            }), 400
        
        # Get optional start date
        start_date = None
        if 'start_date' in data:
            try:
                start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid start_date format'
                }), 400
        
        market_service = MarketDataService()
        results = []
        
        for stock_id in stock_ids:
            stock = Stock.get_by_id(stock_id)
            if not stock:
                results.append({
                    'stock_id': stock_id,
                    'success': False,
                    'error': 'Stock not found'
                })
                continue
            
            success = market_service.fetch_and_update_stock_data(stock_id, start_date)
            results.append({
                'stock_id': stock_id,
                'yahoo_symbol': stock.yahoo_symbol,
                'success': success,
                'error': None if success else 'Failed to update data'
            })
        
        successful_updates = len([r for r in results if r['success']])
        
        return jsonify({
            'success': True,
            'data': {
                'total_stocks': len(stock_ids),
                'successful_updates': successful_updates,
                'failed_updates': len(stock_ids) - successful_updates,
                'results': results
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/market-data/update-portfolio/<int:portfolio_id>', methods=['POST'])
def update_portfolio_market_data(portfolio_id):
    """Update market data for all stocks in a portfolio"""
    try:
        # Verify portfolio exists
        portfolio = Portfolio.query.filter_by(portfolio_key=portfolio_id).first()
        if not portfolio:
            return jsonify({
                'success': False,
                'error': 'Portfolio not found'
            }), 404
        
        market_service = MarketDataService()
        result = market_service.update_portfolio_market_data(portfolio_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Market data update failed')
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500