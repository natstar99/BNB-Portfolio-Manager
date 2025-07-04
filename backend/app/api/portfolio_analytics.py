from flask import jsonify, request
from app.api import bp
from app.services.portfolio_calculator import PortfolioCalculator, MatchingMethod
from app.models import Portfolio
from app import db
from datetime import datetime


@bp.route('/analytics/portfolio/<int:portfolio_id>/summary', methods=['GET'])
def get_portfolio_summary(portfolio_id):
    """Get complete portfolio summary with P&L calculations"""
    try:
        # Get calculation method from query params
        method_param = request.args.get('method', 'fifo').upper()
        try:
            method = MatchingMethod[method_param]
        except KeyError:
            return jsonify({
                'success': False,
                'error': f'Invalid calculation method. Must be one of: {[m.value for m in MatchingMethod]}'
            }), 400
        
        calculator = PortfolioCalculator()
        summary = calculator.get_portfolio_summary(portfolio_id, method)
        
        if 'error' in summary:
            return jsonify({
                'success': False,
                'error': summary['error']
            }), 404 if summary['error'] == 'Portfolio not found' else 500
        
        return jsonify({
            'success': True,
            'data': summary
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/analytics/stock/<int:stock_id>/unrealised-pl', methods=['GET'])
def get_stock_unrealised_pl(stock_id):
    """Get unrealised profit/loss for a specific stock"""
    try:
        calculator = PortfolioCalculator()
        unrealised_pl = calculator.calculate_unrealised_pl_for_stock(stock_id)
        
        if 'error' in unrealised_pl:
            return jsonify({
                'success': False,
                'error': unrealised_pl['error']
            }), 500
        
        return jsonify({
            'success': True,
            'data': unrealised_pl
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/analytics/stock/<int:stock_id>/realised-pl', methods=['GET'])
def get_stock_realised_pl(stock_id):
    """Get realised profit/loss for a specific stock"""
    try:
        # Get calculation method from query params
        method_param = request.args.get('method', 'fifo').upper()
        try:
            method = MatchingMethod[method_param]
        except KeyError:
            return jsonify({
                'success': False,
                'error': f'Invalid calculation method. Must be one of: {[m.value for m in MatchingMethod]}'
            }), 400
        
        calculator = PortfolioCalculator()
        realised_pl = calculator.calculate_realised_pl_for_stock(stock_id, method)
        
        # Calculate totals
        total_realised_pl = sum(match['realised_pl'] for match in realised_pl)
        total_matches = len(realised_pl)
        
        return jsonify({
            'success': True,
            'data': {
                'stock_id': stock_id,
                'method': method.value,
                'total_realised_pl': total_realised_pl,
                'total_matches': total_matches,
                'matches': realised_pl
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/analytics/recalculate', methods=['POST'])
def recalculate_portfolio_metrics():
    """Recalculate portfolio metrics using specified method"""
    try:
        data = request.get_json()
        
        # Get calculation method
        method_param = data.get('method', 'fifo').upper() if data else 'FIFO'
        try:
            method = MatchingMethod[method_param]
        except KeyError:
            return jsonify({
                'success': False,
                'error': f'Invalid calculation method. Must be one of: {[m.value for m in MatchingMethod]}'
            }), 400
        
        # Get optional stock ID for single stock recalculation
        stock_id = data.get('stock_id') if data else None
        
        calculator = PortfolioCalculator()
        
        if stock_id:
            # Recalculate for single stock
            success = calculator.recalculate_realised_pl_for_stock(stock_id, method)
            if success:
                return jsonify({
                    'success': True,
                    'message': f'Successfully recalculated realised P&L for stock {stock_id} using {method.value}'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'Failed to recalculate realised P&L for stock {stock_id}'
                }), 500
        else:
            # Recalculate for all stocks
            success = calculator.recalculate_all_realised_pl(method)
            if success:
                return jsonify({
                    'success': True,
                    'message': f'Successfully recalculated realised P&L for all stocks using {method.value}'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'Failed to recalculate realised P&L using {method.value}'
                }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/analytics/recalculate-all-methods', methods=['POST'])
def recalculate_all_methods():
    """Recalculate portfolio metrics using all methods (FIFO, LIFO, HIFO)"""
    try:
        calculator = PortfolioCalculator()
        success = calculator.calculate_all_methods()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Successfully recalculated realised P&L using all methods (FIFO, LIFO, HIFO)'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to recalculate realised P&L for some methods'
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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


@bp.route('/analytics/methods', methods=['GET'])
def get_calculation_methods():
    """Get available P&L calculation methods"""
    return jsonify({
        'success': True,
        'data': {
            'methods': [method.value for method in MatchingMethod],
            'descriptions': {
                'fifo': 'First In, First Out - Sells oldest purchases first',
                'lifo': 'Last In, First Out - Sells newest purchases first', 
                'hifo': 'Highest In, First Out - Sells highest cost purchases first'
            }
        }
    })