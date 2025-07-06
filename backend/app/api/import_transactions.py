from flask import jsonify, request, make_response
from app.api import bp
from app.services.transaction_import_service import TransactionImportService
from app.models import YahooMarketCode, Stock
from app.services.market_data_service import MarketDataService
from app.utils.transaction_validator import TransactionValidator
from app.utils.date_parser import DateParser
from app import db
import io
import pandas as pd
import json
import uuid
from datetime import datetime


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
                
                # Perform verification to get comprehensive stock data
                verification_result = market_data_service.verify_stock(yahoo_symbol)
                
                if verification_result['success']:
                    # Note: We don't save to DIM_STOCK yet in verification step
                    # This is just returning the verification data for the frontend
                    # The actual saving happens in the final save step
                    
                    results.append({
                        'instrument_code': instrument_code,
                        'success': True,
                        'yahoo_symbol': yahoo_symbol,
                        'name': verification_result.get('name'),
                        'currency': verification_result.get('currency'),
                        'current_price': verification_result.get('current_price', 0.0),
                        'market_cap_formatted': verification_result.get('market_cap_formatted'),
                        'sector': verification_result.get('sector'),
                        'industry': verification_result.get('industry'),
                        'exchange': verification_result.get('exchange'),
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


@bp.route('/import/confirm-transactions', methods=['POST'])
def confirm_transactions():
    """
    Step 3a: Confirm transaction data - validation only, no database changes.
    
    This endpoint validates transaction data and provides confirmation details to the user
    without saving anything to the database. User can review the results before proceeding
    to staging.
    
    DESIGN DECISION: Separated from staging to give user explicit control over the process.
    """
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

        # Get required parameters
        column_mapping_str = request.form.get('column_mapping')
        date_format = request.form.get('date_format', 'YYYY-MM-DD')
        portfolio_id_str = request.form.get('portfolio_id')

        if not column_mapping_str:
            return jsonify({
                'success': False,
                'error': 'Column mapping is required'
            }), 400

        if not portfolio_id_str:
            return jsonify({
                'success': False,
                'error': 'Portfolio ID is required'
            }), 400

        try:
            column_mapping = json.loads(column_mapping_str)
            portfolio_id = int(portfolio_id_str)
        except (json.JSONDecodeError, ValueError) as e:
            return jsonify({
                'success': False,
                'error': f'Invalid parameters: {str(e)}'
            }), 400

        # Process file using service
        import_service = TransactionImportService()
        
        # Read and apply column mapping
        df = import_service.read_file(file)
        if df is None:
            return jsonify({
                'success': False,
                'error': 'Could not read file'
            }), 400

        try:
            df_mapped = import_service.apply_column_mapping(df, column_mapping)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Column mapping failed: {str(e)}'
            }), 400

        # Validate using shared utility
        validation_results = TransactionValidator.validate_complete_dataset(
            df_mapped, portfolio_id, date_format
        )

        # Prepare response data
        response_data = {
            'filename': file.filename,
            'total_rows': validation_results['total_rows'],
            'valid_rows': validation_results['valid_rows'],
            'validation_errors': validation_results['validation_errors'],
            'new_transactions': validation_results['new_transactions'],
            'duplicate_transactions': validation_results['duplicate_transactions'],
            'column_mapping': column_mapping,
            'date_format': date_format,
            'confirmed': False  # Not yet confirmed - user must proceed to staging
        }

        # Add instrument analysis
        if validation_results['instrument_analysis']:
            analysis = validation_results['instrument_analysis']
            response_data.update({
                'unique_stocks': analysis['unique_stock_count'],
                'new_stocks': analysis['new_stock_count'],
                'existing_stocks': analysis['existing_stock_count'],
                'new_stock_symbols': analysis['new_stocks'],
                'existing_stock_symbols': analysis['existing_stocks'],
                'transaction_breakdown': analysis['transaction_breakdown']
            })

        return jsonify({
            'success': True,
            'data': response_data,
            'message': f'Validation complete: {validation_results["valid_rows"]} valid transactions, '
                      f'{validation_results["new_transactions"]} new, {validation_results["duplicate_transactions"]} duplicates'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/import/stage-transactions', methods=['POST'])
def stage_transactions():
    """
    Step 3b: Stage confirmed transactions to STG_RAW_TRANSACTIONS.
    
    This endpoint takes validated transaction data and saves it to the staging table.
    Should only be called after user has confirmed the transaction data.
    
    DESIGN DECISION: Separated staging from validation to give user explicit control.
    """
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

        # Get required parameters
        column_mapping_str = request.form.get('column_mapping')
        date_format = request.form.get('date_format', 'YYYY-MM-DD')
        portfolio_id_str = request.form.get('portfolio_id')

        if not all([column_mapping_str, portfolio_id_str]):
            return jsonify({
                'success': False,
                'error': 'Missing required parameters'
            }), 400

        try:
            column_mapping = json.loads(column_mapping_str)
            portfolio_id = int(portfolio_id_str)
        except (json.JSONDecodeError, ValueError) as e:
            return jsonify({
                'success': False,
                'error': f'Invalid parameters: {str(e)}'
            }), 400

        # Process file using service
        import_service = TransactionImportService()
        
        # Read and apply column mapping
        df = import_service.read_file(file)
        if df is None:
            return jsonify({
                'success': False,
                'error': 'Could not read file'
            }), 400

        try:
            df_mapped = import_service.apply_column_mapping(df, column_mapping)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Column mapping failed: {str(e)}'
            }), 400

        # Validate and get new transactions
        validation_results = TransactionValidator.validate_complete_dataset(
            df_mapped, portfolio_id, date_format
        )

        if validation_results['validation_errors']:
            return jsonify({
                'success': False,
                'error': 'Data validation failed',
                'validation_errors': validation_results['validation_errors']
            }), 400

        # Get new transactions for staging
        valid_transactions = validation_results['valid_transactions']
        new_transactions, duplicate_count = TransactionValidator.check_for_duplicates(
            valid_transactions, portfolio_id
        )

        # Stage new transactions to STG_RAW_TRANSACTIONS
        saved_transactions = 0
        batch_id = None

        if new_transactions:
            from app.models.transaction import RawTransaction
            
            batch_id = str(uuid.uuid4())
            
            try:
                raw_transactions = RawTransaction.create_batch(batch_id, portfolio_id, new_transactions)
                saved_transactions = len(raw_transactions)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                return jsonify({
                    'success': False,
                    'error': f'Failed to stage transactions: {str(e)}'
                }), 500

        # Prepare response
        response_data = {
            'filename': file.filename,
            'total_rows': validation_results['total_rows'],
            'valid_rows': validation_results['valid_rows'],
            'new_transactions': len(new_transactions),
            'duplicate_transactions': duplicate_count,
            'saved_transactions': saved_transactions,
            'batch_id': batch_id,
            'confirmed': True,  # Mark as confirmed since we've staged the data
            'column_mapping': column_mapping,
            'date_format': date_format
        }

        # Add instrument analysis
        if validation_results['instrument_analysis']:
            analysis = validation_results['instrument_analysis']
            response_data.update({
                'unique_stocks': analysis['unique_stock_count'],
                'new_stocks': analysis['new_stock_count'],
                'existing_stocks': analysis['existing_stock_count'],
                'new_stock_symbols': analysis['new_stocks'],
                'existing_stock_symbols': analysis['existing_stocks'],
                'transaction_breakdown': analysis['transaction_breakdown']
            })

        return jsonify({
            'success': True,
            'data': response_data,
            'message': f'Staged {saved_transactions} new transactions successfully. {duplicate_count} duplicates skipped.'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500




@bp.route('/import/transactions', methods=['POST'])
def import_transactions():
    """Process staged transactions to portfolio - final step (Step 5)"""
    try:
        # Get portfolio ID from JSON request (no file upload needed)
        data = request.get_json()
        if not data or 'portfolio_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Portfolio ID is required'
            }), 400
        
        try:
            portfolio_id = int(data['portfolio_id'])
        except (ValueError, TypeError) as e:
            return jsonify({
                'success': False,
                'error': f'Invalid portfolio ID: {str(e)}'
            }), 400
        
        import_service = TransactionImportService()
        
        # Process staged transactions (no file processing needed)
        result = import_service.process_staged_transactions(portfolio_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'summary': {
                    'successful_imports': result.get('successful_imports', 0),
                    'stocks_created': result.get('stocks_created', 0),
                    'processed_transactions': result.get('processed_transactions', 0),
                    'import_errors': len(result.get('import_errors', []))
                },
                'details': {
                    'import_errors': result.get('import_errors', []),
                    'earliest_date': result.get('earliest_date')
                },
                'message': result.get('message', 'Import completed successfully')
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Import failed'),
                'details': {
                    'import_errors': result.get('import_errors', [])
                }
            }), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/import/save-verification', methods=['POST'])
def save_verification_results():
    """Save verification results and import verified stocks"""
    try:
        data = request.get_json()
        
        if not data or 'portfolioId' not in data or 'stockAssignments' not in data:
            return jsonify({
                'success': False,
                'error': 'Portfolio ID and stock assignments are required'
            }), 400
        
        portfolio_id = data['portfolioId']
        stock_assignments = data['stockAssignments']
        
        verified_stocks = []
        unverified_stocks = []
        errors = []
        
        from app.models.stock import Stock
        
        for stock_assignment in stock_assignments:
            try:
                instrument_code = stock_assignment['instrument_code']
                verification_status = stock_assignment['verification_status']
                
                # Check if stock already exists for this portfolio
                existing_stock = Stock.get_by_portfolio_and_instrument(portfolio_id, instrument_code)
                
                # Save ALL stocks to DIM_STOCK regardless of verification status
                stock_data = {
                    'market_key': stock_assignment.get('market_key'),
                    'yahoo_symbol': stock_assignment.get('yahoo_symbol', instrument_code),
                    'name': stock_assignment.get('name', instrument_code),
                    'verification_status': verification_status,  # Use actual status from assignment
                    'drp_enabled': stock_assignment.get('drp_enabled', False),
                    'currency': stock_assignment.get('currency'),
                    'current_price': stock_assignment.get('current_price', 0.0),
                    'sector': stock_assignment.get('sector'),
                    'industry': stock_assignment.get('industry'),
                    'exchange': stock_assignment.get('exchange'),
                    'country': stock_assignment.get('country'),
                    'market_cap': stock_assignment.get('market_cap')
                }
                
                if existing_stock:
                    # Update existing stock
                    existing_stock.update(**stock_data)
                    stock_key = existing_stock.stock_key
                else:
                    # Create new stock
                    new_stock = Stock.create(
                        portfolio_key=portfolio_id,
                        instrument_code=instrument_code,
                        **stock_data
                    )
                    stock_key = new_stock.stock_key
                
                # Categorize stocks based on verification status
                if verification_status == 'verified':
                    verified_stocks.append({
                        'instrument_code': instrument_code,
                        'stock_key': stock_key
                    })
                else:
                    unverified_stocks.append({
                        'instrument_code': instrument_code,
                        'verification_status': verification_status,
                        'stock_key': stock_key
                    })
                        
            except Exception as e:
                errors.append({
                    'instrument_code': stock_assignment.get('instrument_code', 'unknown'),
                    'error': str(e)
                })
        
        # TODO: For verified stocks, initiate historical data collection
        # TODO: Import transactions for verified stocks to FACT_TRANSACTIONS
        # TODO: Handle unverified stocks in staging area
        
        return jsonify({
            'success': True,
            'data': {
                'verified_stocks': verified_stocks,
                'unverified_stocks': unverified_stocks,
                'errors': errors
            },
            'summary': {
                'verified_count': len(verified_stocks),
                'unverified_count': len(unverified_stocks),
                'error_count': len(errors)
            },
            'message': f'Saved {len(verified_stocks)} verified stocks. {len(unverified_stocks)} stocks remain unverified.'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500