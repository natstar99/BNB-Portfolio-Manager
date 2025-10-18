from flask import request
from app.api import bp
from app.services.currency_service import CurrencyService
from app.utils.error_handler import handle_api_errors, success_response, error_response


@bp.route('/currencies', methods=['GET'])
@handle_api_errors
def get_supported_currencies():
    """Get list of supported currency codes"""
    currency_service = CurrencyService()
    currencies = currency_service.get_supported_currencies()

    return success_response({
        'currencies': currencies,
        'count': len(currencies)
    })


@bp.route('/currencies/exchange-rate', methods=['GET'])
@handle_api_errors
def get_exchange_rate():
    """
    Get exchange rate for a specific currency pair and date.

    Query Parameters:
        from_currency: Source currency code (required)
        to_currency: Target currency code (required)
        date: Date in YYYY-MM-DD format (required)

    Example: /api/currencies/exchange-rate?from_currency=AUD&to_currency=USD&date=2024-01-15
    """
    from_currency = request.args.get('from_currency')
    to_currency = request.args.get('to_currency')
    date_str = request.args.get('date')

    if not from_currency or not to_currency or not date_str:
        return error_response('from_currency, to_currency, and date are required', 400)

    try:
        # Parse date
        from datetime import datetime
        rate_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        # Get exchange rate
        currency_service = CurrencyService()
        rate_result = currency_service.get_exchange_rate(from_currency, to_currency, rate_date)

        if rate_result[0] is None:
            return error_response(
                f'Could not fetch exchange rate for {from_currency}/{to_currency} on {date_str}',
                404
            )

        exchange_rate, from_cache = rate_result

        return success_response({
            'from_currency': from_currency.upper(),
            'to_currency': to_currency.upper(),
            'date': date_str,
            'exchange_rate': exchange_rate,
            'from_cache': from_cache
        })

    except ValueError as e:
        return error_response(f'Invalid date format. Use YYYY-MM-DD: {str(e)}', 400)
    except Exception as e:
        return error_response(f'Error fetching exchange rate: {str(e)}', 500)
