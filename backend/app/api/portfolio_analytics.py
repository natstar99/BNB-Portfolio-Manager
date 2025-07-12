from flask import jsonify, request
from app.api import bp
from app.models import Portfolio
from app import db
from datetime import datetime

@bp.route('/analytics/portfolio/<int:portfolio_id>/timeseries', methods=['GET'])
def get_portfolio_timeseries(portfolio_id):
    """Get portfolio time-series data for analytics charts"""
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
        
        # Build the query using the new view
        query = """
            SELECT 
                date,
                total_value,
                total_cost,
                unrealized_pl,
                daily_pl,
                realized_pl,
                total_return,
                return_pct,
                total_return_pct,
                active_positions
            FROM V_PORTFOLIO_ANALYTICS_TIMESERIES 
            WHERE portfolio_key = ?
        """
        params = [portfolio_id]
        
        # Add date filters if provided
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
            
        query += " ORDER BY date"
        
        # Execute the query
        cursor = db.engine.raw_connection().cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        cursor.close()
        
        # Convert results to list of dictionaries
        performance_data = []
        columns = [
            'date', 'total_value', 'total_cost', 'unrealized_pl', 
            'daily_pl', 'realized_pl', 'total_return', 'return_pct', 
            'total_return_pct', 'active_positions'
        ]
        
        for row in results:
            row_dict = dict(zip(columns, row))
            # Convert date to ISO format string for frontend
            if row_dict['date']:
                row_dict['date'] = row_dict['date'].isoformat() if hasattr(row_dict['date'], 'isoformat') else str(row_dict['date'])
            performance_data.append(row_dict)
        
        # Calculate summary from latest data
        summary = {
            'total_return': 0.0,
            'total_return_pct': 0.0,
            'current_value': 0.0,
            'total_investment': 0.0,
            'data_points': len(performance_data)
        }
        
        if performance_data:
            latest = performance_data[-1]
            summary.update({
                'total_return': latest.get('total_return', 0.0),
                'total_return_pct': latest.get('total_return_pct', 0.0),
                'current_value': latest.get('total_value', 0.0),
                'total_investment': latest.get('total_cost', 0.0)
            })
        
        return jsonify({
            'success': True,
            'data': performance_data,
            'summary': summary
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch portfolio timeseries: {str(e)}'
        }), 500

@bp.route('/analytics/portfolio/<int:portfolio_id>/stocks', methods=['GET'])
def get_portfolio_stocks_timeseries(portfolio_id):
    """Get individual stock time-series data for portfolio analytics charts"""
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
        
        # Build the query using the new stock view
        query = """
            SELECT 
                symbol,
                company_name,
                date,
                market_value,
                total_cost_basis,
                unrealized_pl,
                daily_pl,
                cumulative_shares,
                close_price,
                average_cost_basis
            FROM V_STOCK_ANALYTICS_TIMESERIES 
            WHERE portfolio_key = ?
        """
        params = [portfolio_id]
        
        # Add date filters if provided
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
            
        query += " ORDER BY symbol, date"
        
        # Execute the query
        cursor = db.engine.raw_connection().cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        cursor.close()
        
        # Convert results to grouped data structure
        stocks_data = {}
        columns = [
            'symbol', 'company_name', 'date', 'market_value', 'total_cost_basis',
            'unrealized_pl', 'daily_pl', 'cumulative_shares', 'close_price', 'average_cost_basis'
        ]
        
        for row in results:
            row_dict = dict(zip(columns, row))
            symbol = row_dict['symbol']
            
            if symbol not in stocks_data:
                stocks_data[symbol] = {
                    'symbol': symbol,
                    'company_name': row_dict['company_name'],
                    'timeseries': []
                }
            
            # Convert date to ISO format string for frontend
            if row_dict['date']:
                row_dict['date'] = row_dict['date'].isoformat() if hasattr(row_dict['date'], 'isoformat') else str(row_dict['date'])
            
            stocks_data[symbol]['timeseries'].append({
                'date': row_dict['date'],
                'market_value': row_dict['market_value'],
                'total_cost_basis': row_dict['total_cost_basis'],
                'unrealized_pl': row_dict['unrealized_pl'],
                'daily_pl': row_dict['daily_pl'],
                'cumulative_shares': row_dict['cumulative_shares'],
                'close_price': row_dict['close_price'],
                'average_cost_basis': row_dict['average_cost_basis']
            })
        
        return jsonify({
            'success': True,
            'data': list(stocks_data.values())
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch stock timeseries: {str(e)}'
        }), 500

@bp.route('/analytics/portfolio/<int:portfolio_id>/performance', methods=['GET'])
def get_portfolio_performance(portfolio_id):
    """Legacy endpoint - redirects to timeseries for backward compatibility"""
    return get_portfolio_timeseries(portfolio_id)