from flask import jsonify, request
from app.api import bp
from app.models import Portfolio
from app import db
from datetime import datetime

@bp.route('/analytics/portfolio/<int:portfolio_id>/performance', methods=['GET'])
def get_portfolio_performance(portfolio_id):
    """Get portfolio performance metrics over time"""
    try:
        portfolio = Portfolio.get_by_id(portfolio_id)
        if not portfolio:
            return jsonify({
                'success': False,
                'error': 'Portfolio not found'
            }), 404
        
        # Get date range from query params
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        start_date_obj = None
        end_date_obj = None
        
        if start_date:
            try:
                start_date_obj = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid start_date format'
                }), 400
        
        if end_date:
            try:
                end_date_obj = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid end_date format'
                }), 400
        
        # Get stock IDs in portfolio
        stock_ids = [stock.id for stock in portfolio.stocks]
        
        if not stock_ids:
            return jsonify({
                'success': True,
                'data': {
                    'portfolio_id': portfolio_id,
                    'performance_data': [],
                    'summary': {
                        'total_return': 0.0,
                        'total_return_pct': 0.0,
                        'current_value': 0.0,
                        'total_investment': 0.0
                    }
                }
            })
        
        # Get performance data from final_metrics
        metrics = FinalMetric.get_portfolio_summary(stock_ids)
        
        performance_data = []
        total_current_value = 0.0
        total_cost_basis = 0.0
        
        for metric in metrics:
            metric_dict = metric.to_dict()
            performance_data.append(metric_dict)
            total_current_value += metric_dict.get('market_value', 0.0)
            # Use current_cost_basis or total_investment_amount
            total_cost_basis += metric_dict.get('total_investment_amount', 0.0)
        
        total_return = total_current_value - total_cost_basis
        total_return_pct = (total_return / total_cost_basis * 100) if total_cost_basis > 0 else 0.0
        
        return jsonify({
            'success': True,
            'data': {
                'portfolio_id': portfolio_id,
                'performance_data': performance_data,
                'summary': {
                    'total_return': total_return,
                    'total_return_pct': total_return_pct,
                    'current_value': total_current_value,
                    'total_investment': total_cost_basis,
                    'number_of_stocks': len(performance_data)
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500