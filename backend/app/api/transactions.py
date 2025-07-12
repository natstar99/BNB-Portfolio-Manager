from flask import jsonify, request
from datetime import datetime
from sqlalchemy.orm import joinedload
from app.api import bp
from app.models import Transaction, Stock, Portfolio
from app.models.transaction import TransactionType
from app.utils.error_handler import handle_api_errors, success_response, error_response
from app import db


@bp.route('/transactions', methods=['GET'])
@handle_api_errors
def get_transactions():
    """Get all transactions"""
    try:
        # Parse query parameters
        portfolio_id = request.args.get('portfolio_id', type=int)
        stock_id = request.args.get('stock_id', type=int)
        transaction_type = request.args.get('type')
        symbol = request.args.get('symbol')
        action = request.args.get('action')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = request.args.get('limit', type=int, default=100)
        offset = request.args.get('offset', type=int, default=0)
        
        
        # Start with simple query and add joins only if needed
        query = Transaction.query
        
        # Add joins for related data (use left joins to avoid missing data)
        query = query.options(
            db.joinedload(Transaction.stock),
            db.joinedload(Transaction.portfolio), 
            db.joinedload(Transaction.transaction_type)
        )
        
        # Apply filters using correct field names
        if portfolio_id:
            query = query.filter(Transaction.portfolio_key == portfolio_id)
            
        if stock_id:
            query = query.filter(Transaction.stock_key == stock_id)
        
        # Handle symbol filtering by joining with Stock table when needed
        if symbol:
            query = query.join(Stock).filter(Stock.instrument_code.ilike(f'%{symbol}%'))
        
        # Handle action filtering by joining with TransactionType table when needed
        if action or transaction_type:
            query = query.join(TransactionType)
            if action:
                query = query.filter(TransactionType.transaction_type.ilike(f'%{action}%'))
            if transaction_type:
                query = query.filter(TransactionType.transaction_type.ilike(f'%{transaction_type}%'))
        
        if start_date:
            start_date_obj = datetime.fromisoformat(start_date.replace('Z', '+00:00')).date()
            query = query.filter(Transaction.transaction_date >= start_date_obj)
        
        if end_date:
            end_date_obj = datetime.fromisoformat(end_date.replace('Z', '+00:00')).date()
            query = query.filter(Transaction.transaction_date <= end_date_obj)
        
        # Order by date descending and apply pagination
        transactions = query.order_by(Transaction.transaction_date.desc())\
                          .offset(offset)\
                          .limit(limit)\
                          .all()
        
        # Get total count for pagination
        total = query.count()
        
        # Transform transactions to simple format
        transaction_data = []
        for transaction in transactions:
            try:
                trans_dict = {
                    'id': transaction.transaction_key,
                    'portfolio_id': transaction.portfolio_key,
                    'portfolio_name': transaction.portfolio.portfolio_name if transaction.portfolio else 'Unknown',
                    'symbol': transaction.stock.instrument_code if transaction.stock else 'Unknown',
                    'action': transaction.transaction_type.transaction_type.lower() if transaction.transaction_type else 'unknown',
                    'quantity': float(transaction.quantity) if transaction.quantity else 0.0,
                    'price': float(transaction.price) if transaction.price else 0.0,
                    'total_amount': float(transaction.total_value) if transaction.total_value else 0.0,
                    'fees': 0.0,  # Not tracked in current schema
                    'date': transaction.transaction_date.isoformat() if transaction.transaction_date else None,
                    'notes': '',  # Not tracked in current schema
                    'verified': True,  # Assume verified
                    # Raw data fields you requested
                    'transaction_date': transaction.transaction_date.isoformat() if transaction.transaction_date else None,
                    'base_currency': transaction.base_currency,
                    'exchange_rate': float(transaction.exchange_rate) if transaction.exchange_rate else 1.0,
                    'total_value_base': float(transaction.total_value_base) if transaction.total_value_base else 0.0,
                    'currency': transaction.original_currency
                }
                transaction_data.append(trans_dict)
            except Exception as trans_error:
                continue
        
        return jsonify({
            'success': True,
            'transactions': transaction_data,  # Frontend expects this key
            'data': transaction_data,          # Keep for API consistency
            'pagination': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/transactions', methods=['POST'])
def create_transaction():
    """Create a new transaction"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        required_fields = ['stock_id', 'date', 'quantity', 'price', 'transaction_type']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Validate stock exists
        stock = Stock.get_by_id(data['stock_id'])
        if not stock:
            return jsonify({
                'success': False,
                'error': 'Stock not found'
            }), 404
        
        # Validate transaction type
        valid_types = ['buy', 'sell', 'dividend', 'split']
        if data['transaction_type'] not in valid_types:
            return jsonify({
                'success': False,
                'error': f'Invalid transaction type. Must be one of: {", ".join(valid_types)}'
            }), 400
        
        # Parse date
        try:
            transaction_date = datetime.fromisoformat(data['date'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'
            }), 400
        
        transaction = Transaction.create(
            stock_id=data['stock_id'],
            date=transaction_date,
            quantity=data['quantity'],
            price=data['price'],
            transaction_type=data['transaction_type'],
            currency_conversion_rate=data.get('currency_conversion_rate', 1.0),
            original_price=data.get('original_price')
        )
        
        return jsonify({
            'success': True,
            'data': transaction.to_dict(),
            'message': 'Transaction created successfully'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500