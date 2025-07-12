from functools import wraps
from flask import jsonify
import logging

logger = logging.getLogger(__name__)


def handle_api_errors(f):
    """
    Decorator to handle common API errors and provide consistent error responses.
    
    Returns:
        - 400 for ValueError (client errors)
        - 500 for all other exceptions (server errors)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            logger.warning(f"Client error in {f.__name__}: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
        except Exception as e:
            logger.error(f"Server error in {f.__name__}: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    return decorated_function


def success_response(data=None, message=None):
    """Helper function to create consistent success responses"""
    response = {'success': True}
    if data is not None:
        response['data'] = data
    if message is not None:
        response['message'] = message
    return jsonify(response)


def error_response(error_message, status_code=400):
    """Helper function to create consistent error responses"""
    return jsonify({
        'success': False,
        'error': error_message
    }), status_code