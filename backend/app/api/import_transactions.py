from flask import jsonify, request, make_response
from app.api import bp
from app.services.transaction_import_service import TransactionImportService
from app.models import YahooMarketCode, Stock
from app.services.market_data_service import MarketDataService
from app import db
import io
import pandas as pd
import json


@bp.route('/import/template', methods=['GET'])
def get_import_template():
    """Download a CSV template for transaction imports"""
    try:
        import_service = TransactionImportService()
        template_df = import_service.get_import_template()
        
        # Convert to CSV
        output = io.StringIO()
        template_df.to_csv(output, index=False)
        csv_data = output.getvalue()
        
        # Create response
        response = make_response(csv_data)
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = 'attachment; filename=bnb_transactions_template.csv'
        
        return response
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/import/markets', methods=['GET'])
def get_available_markets():
    """Get list of available Yahoo Finance market codes for assignment"""
    try:
        markets = YahooMarketCode.get_all()
        market_list = [market.to_dict() for market in markets]
        
        return jsonify({
            'success': True,
            'data': market_list
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/import/assign-markets', methods=['POST'])
def assign_markets_to_stocks():
    """Assign markets to stocks and perform lightweight verification"""
    try:
        data = request.get_json()
        if not data or 'stock_assignments' not in data:
            return jsonify({
                'success': False,
                'error': 'stock_assignments data is required'
            }), 400
        
        stock_assignments = data['stock_assignments']
        market_data_service = MarketDataService()
        results = []
        
        for assignment in stock_assignments:
            instrument_code = assignment.get('instrument_code')
            market_key = assignment.get('market_key')
            
            if not instrument_code or not market_key:
                results.append({
                    'instrument_code': instrument_code,
                    'success': False,
                    'error': 'Missing instrument_code or market_key'
                })
                continue
            
            try:
                # Get market details
                market = YahooMarketCode.get_by_key(market_key)
                if not market:
                    results.append({
                        'instrument_code': instrument_code,
                        'success': False,
                        'error': f'Invalid market_key: {market_key}'
                    })
                    continue
                
                # Generate Yahoo symbol
                market_suffix = market.market_suffix or ''
                yahoo_symbol = f"{instrument_code}{market_suffix}"
                
                # Perform lightweight verification (just check if symbol exists and get name/currency)
                verification_result = market_data_service.verify_stock_lightweight(yahoo_symbol)
                
                if verification_result['success']:
                    # Create or update stock with market assignment
                    existing_stock = Stock.get_by_instrument_code(instrument_code)
                    
                    if existing_stock:
                        # Update existing stock
                        existing_stock.update(
                            market_key=market_key,
                            yahoo_symbol=yahoo_symbol,
                            name=verification_result.get('name', existing_stock.name),
                            currency=verification_result.get('currency', existing_stock.currency),
                            verification_status='verified'
                        )
                        stock_key = existing_stock.stock_key
                    else:
                        # Create new stock
                        new_stock = Stock.create(
                            instrument_code=instrument_code,
                            yahoo_symbol=yahoo_symbol,
                            name=verification_result.get('name', instrument_code),
                            market_key=market_key,
                            currency=verification_result.get('currency', 'USD'),
                            verification_status='verified'
                        )
                        stock_key = new_stock.stock_key
                    
                    results.append({
                        'instrument_code': instrument_code,
                        'success': True,
                        'stock_key': stock_key,
                        'yahoo_symbol': yahoo_symbol,
                        'name': verification_result.get('name'),
                        'currency': verification_result.get('currency'),
                        'market': market.market_or_index
                    })
                    
                else:
                    results.append({
                        'instrument_code': instrument_code,
                        'success': False,
                        'error': f'Verification failed: {verification_result.get("error", "Unknown error")}',
                        'yahoo_symbol': yahoo_symbol
                    })
            
            except Exception as e:
                results.append({
                    'instrument_code': instrument_code,
                    'success': False,
                    'error': str(e)
                })
        
        # Calculate summary
        successful_assignments = len([r for r in results if r['success']])
        failed_assignments = len([r for r in results if not r['success']])
        
        return jsonify({
            'success': True,
            'data': {
                'results': results,
                'summary': {
                    'total': len(results),
                    'successful': successful_assignments,
                    'failed': failed_assignments
                }
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/import/analyze', methods=['POST'])
def analyze_import_file():
    """Analyze uploaded file and detect column structure"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        import_service = TransactionImportService()
        
        # Read file to analyze structure
        df = import_service.read_file(file)
        if df is None:
            return jsonify({
                'success': False,
                'error': 'Could not read file'
            }), 400
        
        # Detect column mapping
        detected_mapping = import_service.detect_column_mapping(df)
        
        # Get file info (ensure raw data is preserved for preview)
        sample_df = df.head(5).copy()
        # Convert all columns to string to preserve original formatting
        for col in sample_df.columns:
            sample_df[col] = sample_df[col].astype(str)
        
        file_info = {
            'filename': file.filename,
            'total_rows': len(df),
            'columns': df.columns.tolist(),
            'detected_mapping': detected_mapping,
            'sample_data': sample_df.to_dict('records') if len(df) > 0 else []
        }
        
        return jsonify({
            'success': True,
            'data': file_info
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/import/validate', methods=['POST'])
def validate_import():
    """Validate imported transaction data and prepare for final import"""
    try:
        # Check if file is provided (FormData) or JSON data
        if 'file' in request.files:
            # Handle file upload with FormData
            file = request.files['file']
            if file.filename == '':
                return jsonify({
                    'success': False,
                    'error': 'No file selected'
                }), 400
            
            # Get column mapping and date format from form data
            column_mapping_str = request.form.get('column_mapping')
            date_format = request.form.get('date_format', 'YYYY-MM-DD')
            
            if not column_mapping_str:
                return jsonify({
                    'success': False,
                    'error': 'Column mapping is required'
                }), 400
            
            try:
                column_mapping = json.loads(column_mapping_str)
            except json.JSONDecodeError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid column mapping JSON'
                }), 400
            
            import_service = TransactionImportService()
            
            # Read and process the file
            df = import_service.read_file(file)
            if df is None:
                return jsonify({
                    'success': False,
                    'error': 'Could not read file'
                }), 400
            
            # Apply column mapping
            try:
                df_mapped = import_service.apply_column_mapping(df, column_mapping)
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Column mapping failed: {str(e)}'
                }), 400
            
            # Validate the data structure and content
            validation_errors = []
            validated_transactions = []
            
            for index, row in df_mapped.iterrows():
                try:
                    # Basic validation - check required fields
                    if pd.isna(row.get('date')) or pd.isna(row.get('instrument_code')) or pd.isna(row.get('quantity')):
                        validation_errors.append(f"Row {index + 1}: Missing required fields")
                        continue
                    
                    # Convert and validate data types
                    validated_row = {
                        'row_number': index + 1,
                        'date': str(row['date']),
                        'instrument_code': str(row['instrument_code']),
                        'quantity': float(row['quantity']) if pd.notna(row.get('quantity')) else 0,
                        'price': float(row['price']) if pd.notna(row.get('price')) else 0,
                        'transaction_type': str(row.get('transaction_type', 'buy')),
                        'total_value': float(row.get('total_value', 0)) if pd.notna(row.get('total_value')) else 0
                    }
                    
                    validated_transactions.append(validated_row)
                    
                except Exception as e:
                    validation_errors.append(f"Row {index + 1}: {str(e)}")
            
            # Calculate unique stocks and transaction breakdown
            unique_stocks = set()
            transaction_breakdown = {}
            
            for transaction in validated_transactions:
                instrument_code = transaction['instrument_code']
                transaction_type = transaction['transaction_type'].upper()
                
                unique_stocks.add(instrument_code)
                
                if instrument_code not in transaction_breakdown:
                    transaction_breakdown[instrument_code] = {'BUY': 0, 'SELL': 0, 'DIVIDEND': 0, 'SPLIT': 0, 'total': 0}
                
                if transaction_type in transaction_breakdown[instrument_code]:
                    transaction_breakdown[instrument_code][transaction_type] += 1
                transaction_breakdown[instrument_code]['total'] += 1
            
            # Determine which stocks are new vs existing in portfolio
            from app.models.stock import Stock
            new_stock_symbols = []
            existing_stock_symbols = []
            
            for instrument_code in unique_stocks:
                existing_stock = Stock.get_by_instrument_code(instrument_code)
                if existing_stock:
                    existing_stock_symbols.append(instrument_code)
                else:
                    new_stock_symbols.append(instrument_code)
            
            return jsonify({
                'success': True,
                'data': {
                    'filename': file.filename,
                    'total_rows': len(df_mapped),
                    'valid_rows': len(validated_transactions),
                    'unique_stocks': len(unique_stocks),
                    'new_stocks': len(new_stock_symbols),
                    'existing_stocks': len(existing_stock_symbols),
                    'new_stock_symbols': new_stock_symbols,
                    'existing_stock_symbols': existing_stock_symbols,
                    'validation_errors': validation_errors,
                    'validated_transactions': validated_transactions,
                    'transaction_breakdown': transaction_breakdown,
                    'column_mapping': column_mapping,
                    'date_format': date_format
                },
                'message': f'Processed {len(df_mapped)} rows: {len(validated_transactions)} valid, {len(validation_errors)} errors, {len(new_stock_symbols)} new stocks'
            })
            
        else:
            # Handle JSON data (batch_id approach)
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'No data provided'
                }), 400

            # Required parameters
            required_fields = ['batch_id', 'column_mapping', 'date_format']
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                return jsonify({
                    'success': False,
                    'error': f'Missing required fields: {", ".join(missing_fields)}'
                }), 400

            batch_id = data['batch_id']
            column_mapping = data['column_mapping']
            date_format = data.get('date_format', 'YYYY-MM-DD')

            import_service = TransactionImportService()
            
            # Validate the staged data
            validated_data, validation_errors = import_service.validate_staged_data(batch_id, date_format)
            
            if validation_errors:
                return jsonify({
                    'success': False,
                    'validation_errors': validation_errors,
                    'error': 'Validation failed'
                }), 400

            return jsonify({
                'success': True,
                'data': {
                    'validated_transactions': validated_data,
                    'total_transactions': len(validated_data),
                    'batch_id': batch_id
                },
                'message': f'Successfully validated {len(validated_data)} transactions'
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/import/transactions', methods=['POST'])
def import_transactions():
    """Import transactions to portfolio - final step"""
    try:
        # Check if file is provided
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Get required parameters
        portfolio_id = request.form.get('portfolio_id')
        column_mapping_str = request.form.get('column_mapping')
        date_format = request.form.get('date_format', 'YYYY-MM-DD')
        
        if not portfolio_id:
            return jsonify({
                'success': False,
                'error': 'Portfolio ID is required'
            }), 400
        
        if not column_mapping_str:
            return jsonify({
                'success': False,
                'error': 'Column mapping is required'
            }), 400
        
        try:
            column_mapping = json.loads(column_mapping_str)
            portfolio_id = int(portfolio_id)
        except (json.JSONDecodeError, ValueError) as e:
            return jsonify({
                'success': False,
                'error': f'Invalid data format: {str(e)}'
            }), 400
        
        import_service = TransactionImportService()
        
        # Process the complete import
        result = import_service.process_file_import(
            file=file,
            column_mapping=column_mapping,
            date_format=date_format,
            portfolio_id=portfolio_id
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'summary': {
                    'successful_imports': result.get('successful_imports', 0),
                    'stocks_created': result.get('stocks_created', 0),
                    'validation_errors': len(result.get('validation_errors', [])),
                    'import_errors': len(result.get('import_errors', []))
                },
                'details': {
                    'import_errors': result.get('import_errors', []),
                    'validation_errors': result.get('validation_errors', [])
                },
                'message': result.get('message', 'Import completed successfully')
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Import failed'),
                'details': result.get('details', {})
            }), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500