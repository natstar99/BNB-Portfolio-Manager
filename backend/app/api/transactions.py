from flask import jsonify, request
from datetime import datetime
from app.api import bp
from app.models import Transaction, Stock
from app import db


@bp.route('/transactions', methods=['GET'])
def get_transactions():
    """Get all transactions"""
    try:
        # Parse query parameters
        stock_id = request.args.get('stock_id', type=int)
        transaction_type = request.args.get('type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = request.args.get('limit', type=int, default=100)
        offset = request.args.get('offset', type=int, default=0)
        
        query = Transaction.query
        
        # Apply filters
        if stock_id:
            query = query.filter_by(stock_id=stock_id)
        
        if transaction_type:
            query = query.filter_by(transaction_type=transaction_type)
        
        if start_date:
            start_date_obj = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(Transaction.date >= start_date_obj)
        
        if end_date:
            end_date_obj = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(Transaction.date <= end_date_obj)
        
        # Order by date descending and apply pagination
        transactions = query.order_by(Transaction.date.desc())\
                          .offset(offset)\
                          .limit(limit)\
                          .all()
        
        # Get total count for pagination
        total = query.count()
        
        return jsonify({
            'success': True,
            'data': [transaction.to_dict() for transaction in transactions],
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


@bp.route('/transactions/<int:transaction_id>', methods=['GET'])
def get_transaction(transaction_id):
    """Get a specific transaction"""
    try:
        transaction = Transaction.get_by_id(transaction_id)
        
        if not transaction:
            return jsonify({
                'success': False,
                'error': 'Transaction not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': transaction.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/transactions/<int:transaction_id>', methods=['PUT'])
def update_transaction(transaction_id):
    """Update a transaction"""
    try:
        transaction = Transaction.get_by_id(transaction_id)
        
        if not transaction:
            return jsonify({
                'success': False,
                'error': 'Transaction not found'
            }), 404
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate transaction type if provided
        if 'transaction_type' in data:
            valid_types = ['buy', 'sell', 'dividend', 'split']
            if data['transaction_type'] not in valid_types:
                return jsonify({
                    'success': False,
                    'error': f'Invalid transaction type. Must be one of: {", ".join(valid_types)}'
                }), 400
        
        # Parse date if provided
        if 'date' in data:
            try:
                data['date'] = datetime.fromisoformat(data['date'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'
                }), 400
        
        # Validate stock if provided
        if 'stock_id' in data:
            stock = Stock.get_by_id(data['stock_id'])
            if not stock:
                return jsonify({
                    'success': False,
                    'error': 'Stock not found'
                }), 404
        
        transaction.update(**data)
        
        return jsonify({
            'success': True,
            'data': transaction.to_dict(),
            'message': 'Transaction updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/transactions/<int:transaction_id>', methods=['DELETE'])
def delete_transaction(transaction_id):
    """Delete a transaction"""
    try:
        transaction = Transaction.get_by_id(transaction_id)
        
        if not transaction:
            return jsonify({
                'success': False,
                'error': 'Transaction not found'
            }), 404
        
        transaction.delete()
        
        return jsonify({
            'success': True,
            'message': 'Transaction deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/transactions/bulk', methods=['POST'])
def bulk_create_transactions():
    """Bulk create transactions"""
    try:
        data = request.get_json()
        
        if not data or 'transactions' not in data:
            return jsonify({
                'success': False,
                'error': 'Transactions data is required'
            }), 400
        
        transactions_data = data['transactions']
        if not isinstance(transactions_data, list):
            return jsonify({
                'success': False,
                'error': 'Transactions must be a list'
            }), 400
        
        created_transactions = []
        errors = []
        
        for i, transaction_data in enumerate(transactions_data):
            try:
                # Validate required fields
                required_fields = ['stock_id', 'date', 'quantity', 'price', 'transaction_type']
                missing_fields = [field for field in required_fields if field not in transaction_data]
                
                if missing_fields:
                    errors.append({
                        'index': i,
                        'error': f'Missing required fields: {", ".join(missing_fields)}'
                    })
                    continue
                
                # Validate stock exists
                stock = Stock.get_by_id(transaction_data['stock_id'])
                if not stock:
                    errors.append({
                        'index': i,
                        'error': 'Stock not found'
                    })
                    continue
                
                # Parse date
                try:
                    transaction_date = datetime.fromisoformat(transaction_data['date'].replace('Z', '+00:00'))
                except ValueError:
                    errors.append({
                        'index': i,
                        'error': 'Invalid date format'
                    })
                    continue
                
                transaction = Transaction.create(
                    stock_id=transaction_data['stock_id'],
                    date=transaction_date,
                    quantity=transaction_data['quantity'],
                    price=transaction_data['price'],
                    transaction_type=transaction_data['transaction_type'],
                    currency_conversion_rate=transaction_data.get('currency_conversion_rate', 1.0),
                    original_price=transaction_data.get('original_price')
                )
                
                created_transactions.append(transaction.to_dict())
                
            except Exception as e:
                errors.append({
                    'index': i,
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'data': {
                'created': created_transactions,
                'errors': errors
            },
            'message': f'Bulk operation completed. {len(created_transactions)} transactions created, {len(errors)} errors'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/transactions/summary', methods=['GET'])
def get_transactions_summary():
    """Get transaction summary statistics"""
    try:
        stock_id = request.args.get('stock_id', type=int)
        
        query = Transaction.query
        if stock_id:
            query = query.filter_by(stock_id=stock_id)
        
        transactions = query.all()
        
        summary = {
            'total_transactions': len(transactions),
            'by_type': {},
            'total_value': 0
        }
        
        for transaction in transactions:
            transaction_type = transaction.transaction_type
            if transaction_type not in summary['by_type']:
                summary['by_type'][transaction_type] = {
                    'count': 0,
                    'total_quantity': 0,
                    'total_value': 0
                }
            
            summary['by_type'][transaction_type]['count'] += 1
            summary['by_type'][transaction_type]['total_quantity'] += transaction.quantity
            summary['by_type'][transaction_type]['total_value'] += transaction.total_value
            summary['total_value'] += transaction.total_value
        
        return jsonify({
            'success': True,
            'data': summary
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500