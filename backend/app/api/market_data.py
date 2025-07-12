from flask import jsonify, request
from app.api import bp
from app.services.market_data_service import MarketDataService
from app.models import Stock, Portfolio
from app import db
from datetime import datetime


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