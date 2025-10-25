import yfinance as yf
import pandas as pd
from datetime import datetime, date, timedelta
import logging
from typing import Optional, Tuple
from decimal import Decimal
import time

from app.models.currency_exchange_rate import CurrencyExchangeRate
from app.models.date_dimension import DateDimension
from app.models.portfolio import Portfolio
from app.models.stock import Stock
from app.models.transaction import Transaction
from app.utils.date_parser import DateParser
from app import db

logger = logging.getLogger(__name__)


class CurrencyService:
    """
    Service for handling currency exchange rate operations including:
    - Yahoo Finance currency pair integration (e.g., AUDUSD=X)
    - Exchange rate caching in DIM_CURRENCY_EXCHANGE_RATES
    - Historical exchange rate fetching for transaction processing
    - Batch processing for date ranges
    """

    def __init__(self):
        self.timeout = 30
        self.retry_count = 3
        self.retry_delay = 2  # seconds between retries

    def get_exchange_rate(self, from_currency: str, to_currency: str, rate_date: date) -> Tuple[float, bool]:
        """
        Get exchange rate for a specific currency pair and date.

        First checks the database cache (DIM_CURRENCY_EXCHANGE_RATES), if not found
        fetches from Yahoo Finance and stores for future use.

        Args:
            from_currency: Source currency code (e.g., 'AUD')
            to_currency: Target currency code (e.g., 'USD')
            rate_date: Date for the exchange rate

        Returns:
            Tuple[float, bool]: (exchange_rate, from_cache) where from_cache indicates if rate was cached
        """
        # Normalize currency codes
        from_currency = from_currency.upper().strip()
        to_currency = to_currency.upper().strip()

        # If same currency, return 1.0
        if from_currency == to_currency:
            return 1.0, True

        # Check database cache first
        cached_rate = CurrencyExchangeRate.get_rate(from_currency, to_currency, rate_date)
        if cached_rate:
            logger.debug(f"Found cached rate for {from_currency}/{to_currency} on {rate_date}: {cached_rate.exchange_rate}")
            return float(cached_rate.exchange_rate), True

        # Not in cache, fetch from Yahoo Finance
        logger.info(f"Fetching exchange rate for {from_currency}/{to_currency} on {rate_date} from Yahoo Finance")

        try:
            exchange_rate = self._fetch_rate_from_yahoo(from_currency, to_currency, rate_date)

            if exchange_rate is None:
                logger.warning(f"Could not fetch exchange rate for {from_currency}/{to_currency} on {rate_date}")
                return None, False

            # Ensure date exists in DIM_DATE
            DateDimension.get_or_create_date_entry(rate_date, commit=False)

            # Store in database for future use
            CurrencyExchangeRate.create(
                from_currency=from_currency,
                to_currency=to_currency,
                rate_date=rate_date,
                exchange_rate=exchange_rate
            )

            logger.info(f"Stored exchange rate {from_currency}/{to_currency} on {rate_date}: {exchange_rate}")
            return exchange_rate, False

        except Exception as e:
            logger.error(f"Error getting exchange rate for {from_currency}/{to_currency} on {rate_date}: {str(e)}")
            return None, False

    def _fetch_rate_from_yahoo(self, from_currency: str, to_currency: str, rate_date: date) -> Optional[float]:
        """
        Fetch exchange rate from Yahoo Finance for a specific date.

        Yahoo Finance currency pair format: XXXYYY=X (e.g., AUDUSD=X for AUD to USD)

        IMPORTANT: Yahoo Finance doesn't support all currency pair directions.
        If the direct pair (e.g., USDAUD=X) is not available, this method
        automatically tries the inverse pair (e.g., AUDUSD=X) and inverts the rate.

        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            rate_date: Date for the exchange rate

        Returns:
            float or None: Exchange rate if successful, None otherwise
        """
        # Build Yahoo Finance currency pair symbol
        yahoo_symbol = f"{from_currency}{to_currency}=X"
        inverse_yahoo_symbol = f"{to_currency}{from_currency}=X"

        try:
            # Retry logic for Yahoo Finance API reliability
            for attempt in range(self.retry_count):
                try:
                    ticker = yf.Ticker(yahoo_symbol)

                    # Fetch historical data around the target date
                    # Get a wider window (2 weeks back) to handle weekends/holidays and data gaps
                    start_date = rate_date - timedelta(days=14)
                    end_date = rate_date + timedelta(days=1)

                    data = ticker.history(start=start_date, end=end_date, auto_adjust=False)

                    if data.empty:
                        logger.warning(f"No data returned from Yahoo for {yahoo_symbol} around {rate_date} (attempt {attempt + 1})")
                        if attempt < self.retry_count - 1:
                            time.sleep(self.retry_delay)
                            continue

                        # Direct pair failed - try inverse pair (e.g., try AUDUSD=X instead of USDAUD=X)
                        logger.info(f"Direct pair {yahoo_symbol} not available, trying inverse pair {inverse_yahoo_symbol}")
                        inverse_rate = self._try_inverse_pair(to_currency, from_currency, rate_date)
                        if inverse_rate is not None:
                            # Invert the rate: if AUDUSD=1.5, then USDAUD=1/1.5
                            direct_rate = 1.0 / inverse_rate
                            logger.info(f"Using inverted rate for {yahoo_symbol}: {direct_rate} (from {inverse_yahoo_symbol}={inverse_rate})")
                            return direct_rate

                        # If inverse also failed, try getting the most recent rate
                        return self._get_fallback_rate(from_currency, to_currency)

                    # Try to find exact date first
                    data.index = pd.to_datetime(data.index).date

                    if rate_date in data.index:
                        close_price = float(data.loc[rate_date]['Close'])
                        logger.info(f"Found exact rate for {yahoo_symbol} on {rate_date}: {close_price}")
                        return close_price

                    # If exact date not found, use nearest previous date (last known rate)
                    available_dates = [d for d in data.index if d <= rate_date]
                    if available_dates:
                        nearest_date = max(available_dates)
                        close_price = float(data.loc[nearest_date]['Close'])
                        logger.info(f"Using nearest rate for {yahoo_symbol} on {nearest_date} (requested {rate_date}): {close_price}")
                        return close_price

                    logger.warning(f"No suitable date found in data for {yahoo_symbol} around {rate_date}")
                    if attempt < self.retry_count - 1:
                        time.sleep(self.retry_delay)
                        continue

                    return self._get_fallback_rate(from_currency, to_currency)

                except Exception as e:
                    logger.warning(f"Yahoo Finance API error for {yahoo_symbol} (attempt {attempt + 1}): {str(e)}")
                    if attempt < self.retry_count - 1:
                        time.sleep(self.retry_delay)
                        continue
                    raise

            return None

        except Exception as e:
            logger.error(f"Error fetching exchange rate from Yahoo for {yahoo_symbol}: {str(e)}")
            return None

    def _try_inverse_pair(self, from_currency: str, to_currency: str, rate_date: date) -> Optional[float]:
        """
        Try fetching the inverse currency pair when direct pair is not available.

        This is a helper method that attempts to fetch the reverse currency pair
        from Yahoo Finance. The caller should invert the returned rate.

        Args:
            from_currency: Source currency code (inverse of original)
            to_currency: Target currency code (inverse of original)
            rate_date: Date for the exchange rate

        Returns:
            float or None: Exchange rate for inverse pair if successful
        """
        yahoo_symbol = f"{from_currency}{to_currency}=X"

        try:
            ticker = yf.Ticker(yahoo_symbol)
            # Use same wider window (2 weeks) for inverse pair
            start_date = rate_date - timedelta(days=14)
            end_date = rate_date + timedelta(days=1)

            data = ticker.history(start=start_date, end=end_date, auto_adjust=False)

            if data.empty:
                logger.warning(f"Inverse pair {yahoo_symbol} also has no data")
                return None

            # Convert index to date objects
            data.index = pd.to_datetime(data.index).date

            # Try exact date first
            if rate_date in data.index:
                close_price = float(data.loc[rate_date]['Close'])
                logger.info(f"Found exact inverse rate for {yahoo_symbol} on {rate_date}: {close_price}")
                return close_price

            # Use nearest previous date
            available_dates = [d for d in data.index if d <= rate_date]
            if available_dates:
                nearest_date = max(available_dates)
                close_price = float(data.loc[nearest_date]['Close'])
                logger.info(f"Using nearest inverse rate for {yahoo_symbol} on {nearest_date}: {close_price}")
                return close_price

            logger.warning(f"No suitable date found in inverse pair data for {yahoo_symbol}")
            return None

        except Exception as e:
            logger.warning(f"Error fetching inverse pair {yahoo_symbol}: {str(e)}")
            return None

    def _get_fallback_rate(self, from_currency: str, to_currency: str) -> Optional[float]:
        """
        Get current/latest exchange rate as fallback when historical rate unavailable.

        Args:
            from_currency: Source currency code
            to_currency: Target currency code

        Returns:
            float or None: Current exchange rate if available
        """
        yahoo_symbol = f"{from_currency}{to_currency}=X"

        try:
            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info

            # Try multiple fields for current rate
            if 'regularMarketPrice' in info and info['regularMarketPrice']:
                rate = float(info['regularMarketPrice'])
                logger.info(f"Using current market rate for {yahoo_symbol}: {rate}")
                return rate

            if 'previousClose' in info and info['previousClose']:
                rate = float(info['previousClose'])
                logger.info(f"Using previous close rate for {yahoo_symbol}: {rate}")
                return rate

            # Last resort: try to get most recent historical data
            data = ticker.history(period='5d')
            if not data.empty:
                rate = float(data['Close'].iloc[-1])
                logger.info(f"Using most recent historical rate for {yahoo_symbol}: {rate}")
                return rate

            logger.warning(f"No fallback rate available for {yahoo_symbol}")
            return None

        except Exception as e:
            logger.error(f"Error getting fallback rate for {yahoo_symbol}: {str(e)}")
            return None

    def fetch_rates_for_date_range(self, from_currency: str, to_currency: str,
                                   start_date: date, end_date: date = None) -> dict:
        """
        Fetch and store exchange rates for a date range.

        Useful for bulk fetching historical rates (e.g., for backfilling existing transactions).

        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            start_date: Start date for the range
            end_date: End date for the range (defaults to today)

        Returns:
            dict: Results containing success status, rates fetched, and errors
        """
        # Normalize inputs
        from_currency = from_currency.upper().strip()
        to_currency = to_currency.upper().strip()

        if end_date is None:
            end_date = date.today()

        if from_currency == to_currency:
            return {
                'success': True,
                'message': 'Same currency, no rates needed',
                'rates_fetched': 0,
                'rates_cached': 0,
                'errors': []
            }

        logger.info(f"[BULK_FETCH] Fetching exchange rates for {from_currency}/{to_currency} from {start_date} to {end_date}")

        yahoo_symbol = f"{from_currency}{to_currency}=X"
        inverse_yahoo_symbol = f"{to_currency}{from_currency}=X"
        rates_fetched = 0
        rates_cached = 0
        errors = []
        should_invert = False

        try:
            # Fetch bulk historical data from Yahoo Finance
            logger.info(f"[BULK_FETCH] Attempting to fetch {yahoo_symbol}...")
            ticker = yf.Ticker(yahoo_symbol)
            data = ticker.history(start=start_date, end=end_date + timedelta(days=1), auto_adjust=False)
            logger.info(f"[BULK_FETCH] {yahoo_symbol} returned {len(data)} rows")

            if data.empty:
                # Direct pair failed - try inverse pair (e.g., try AUDEUR=X instead of EURAUD=X)
                logger.warning(f"No data for {yahoo_symbol}, trying inverse pair {inverse_yahoo_symbol}")
                ticker = yf.Ticker(inverse_yahoo_symbol)
                data = ticker.history(start=start_date, end=end_date + timedelta(days=1), auto_adjust=False)

                if data.empty:
                    error_msg = f"No data returned from Yahoo Finance for {yahoo_symbol} or {inverse_yahoo_symbol}"
                    logger.error(error_msg)
                    return {
                        'success': False,
                        'error': error_msg,
                        'rates_fetched': 0,
                        'rates_cached': 0,
                        'errors': [error_msg]
                    }
                else:
                    # Inverse pair worked - we'll need to invert all rates
                    should_invert = True
                    logger.info(f"Using inverse pair {inverse_yahoo_symbol} - will invert rates")

            # Prepare batch data for insertion
            rates_to_create = []
            data.index = pd.to_datetime(data.index).date

            for idx_date, row in data.iterrows():
                try:
                    # Check if rate already exists
                    existing_rate = CurrencyExchangeRate.get_rate(from_currency, to_currency, idx_date)

                    if existing_rate:
                        rates_cached += 1
                        continue

                    # Ensure date exists in DIM_DATE
                    DateDimension.get_or_create_date_entry(idx_date, commit=False)

                    # Get exchange rate - invert if using inverse pair
                    raw_rate = float(row['Close'])
                    exchange_rate = (1.0 / raw_rate) if should_invert else raw_rate

                    # Prepare rate data (always stored as from_currency → to_currency)
                    rates_to_create.append({
                        'from_currency': from_currency,
                        'to_currency': to_currency,
                        'rate_date': idx_date,
                        'exchange_rate': exchange_rate
                    })

                except Exception as e:
                    error_msg = f"Error processing rate for {idx_date}: {str(e)}"
                    logger.warning(error_msg)
                    errors.append(error_msg)

            # Bulk create rates (don't commit - let caller decide)
            if rates_to_create:
                CurrencyExchangeRate.bulk_create(rates_to_create, commit=False)
                rates_fetched = len(rates_to_create)

                if should_invert:
                    logger.info(f"Prepared {rates_fetched} exchange rates for {from_currency}/{to_currency} "
                              f"(inverted from {inverse_yahoo_symbol})")
                else:
                    logger.info(f"Prepared {rates_fetched} exchange rates for {from_currency}/{to_currency}")

            message = f'Fetched {rates_fetched} new rates, {rates_cached} already cached'
            if should_invert:
                message += f' (inverted from {inverse_yahoo_symbol})'

            return {
                'success': True,
                'rates_fetched': rates_fetched,
                'rates_cached': rates_cached,
                'total_rates': rates_fetched + rates_cached,
                'errors': errors,
                'message': message
            }

        except Exception as e:
            error_msg = f"Error fetching exchange rates for {from_currency}/{to_currency}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'rates_fetched': rates_fetched,
                'rates_cached': rates_cached,
                'errors': errors + [error_msg]
            }

    def fetch_rates_for_date_range_with_interpolation(self, from_currency: str, to_currency: str,
                                                       start_date: date, end_date: date = None) -> dict:
        """
        Fetch exchange rates for a date range with weekend/holiday interpolation.

        This enhanced version of fetch_rates_for_date_range fills gaps in the data
        (weekends and holidays) by copying the nearest previous trading day's rate.
        This ensures complete date coverage for daily metrics calculations.

        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            start_date: Start date for the range
            end_date: End date for the range (defaults to today)

        Returns:
            dict: Results with rates_fetched, rates_cached, rates_interpolated, and success status
        """
        # First, fetch all available trading day rates
        base_result = self.fetch_rates_for_date_range(from_currency, to_currency, start_date, end_date)

        if not base_result['success']:
            return base_result

        if end_date is None:
            end_date = date.today()

        # Normalize currency codes
        from_currency = from_currency.upper().strip()
        to_currency = to_currency.upper().strip()

        # If same currency, no interpolation needed
        if from_currency == to_currency:
            base_result['rates_interpolated'] = 0
            return base_result

        logger.info(f"Starting weekend/holiday interpolation for {from_currency}/{to_currency} from {start_date} to {end_date}")

        # Get all existing rates in the range
        existing_rates = CurrencyExchangeRate.query.filter(
            CurrencyExchangeRate.from_currency == from_currency,
            CurrencyExchangeRate.to_currency == to_currency,
            CurrencyExchangeRate.date_key >= int(start_date.strftime('%Y%m%d')),
            CurrencyExchangeRate.date_key <= int(end_date.strftime('%Y%m%d'))
        ).order_by(CurrencyExchangeRate.date_key).all()

        # Build dict of existing rates by date
        existing_dates = {rate.date_key: float(rate.exchange_rate) for rate in existing_rates}

        # Generate all dates in range
        current_date = start_date
        dates_to_fill = []

        while current_date <= end_date:
            date_key = int(current_date.strftime('%Y%m%d'))
            if date_key not in existing_dates:
                dates_to_fill.append(current_date)
            current_date += timedelta(days=1)

        if not dates_to_fill:
            logger.info(f"No gaps found for {from_currency}/{to_currency}, interpolation not needed")
            base_result['rates_interpolated'] = 0
            return base_result

        logger.info(f"Found {len(dates_to_fill)} date gaps to interpolate for {from_currency}/{to_currency}")

        # Fill gaps with nearest previous trading day rate
        rates_to_create = []
        rates_interpolated = 0

        for gap_date in dates_to_fill:
            gap_date_key = int(gap_date.strftime('%Y%m%d'))

            # Find nearest previous trading day rate
            previous_rate = None
            previous_date_keys = [dk for dk in existing_dates.keys() if dk < gap_date_key]

            if previous_date_keys:
                nearest_prev_date_key = max(previous_date_keys)
                previous_rate = existing_dates[nearest_prev_date_key]

                # Ensure date exists in DIM_DATE
                DateDimension.get_or_create_date_entry(gap_date, commit=False)

                # Create interpolated rate
                rates_to_create.append({
                    'from_currency': from_currency,
                    'to_currency': to_currency,
                    'rate_date': gap_date,
                    'exchange_rate': previous_rate
                })

                # Add to existing_dates for subsequent gap fills
                existing_dates[gap_date_key] = previous_rate
                rates_interpolated += 1

                logger.debug(f"Interpolated {from_currency}/{to_currency} for {gap_date} using rate from {nearest_prev_date_key}: {previous_rate}")
            else:
                # No previous rate available, try finding next rate
                next_date_keys = [dk for dk in existing_dates.keys() if dk > gap_date_key]
                if next_date_keys:
                    nearest_next_date_key = min(next_date_keys)
                    next_rate = existing_dates[nearest_next_date_key]

                    DateDimension.get_or_create_date_entry(gap_date, commit=False)

                    rates_to_create.append({
                        'from_currency': from_currency,
                        'to_currency': to_currency,
                        'rate_date': gap_date,
                        'exchange_rate': next_rate
                    })

                    existing_dates[gap_date_key] = next_rate
                    rates_interpolated += 1

                    logger.warning(f"[DATA_GAP] No previous rate found for {gap_date}, using future rate from {nearest_next_date_key}: {next_rate}")
                else:
                    logger.error(f"[DATA_GAP] Cannot interpolate {from_currency}/{to_currency} for {gap_date}: no trading day rates available")

        # Bulk create interpolated rates
        if rates_to_create:
            try:
                CurrencyExchangeRate.bulk_create(rates_to_create, commit=False)
                logger.info(f"Created {rates_interpolated} interpolated rates for {from_currency}/{to_currency}")
            except Exception as e:
                error_msg = f"Error creating interpolated rates: {str(e)}"
                logger.error(error_msg)
                base_result['success'] = False
                base_result['errors'] = base_result.get('errors', []) + [error_msg]
                return base_result

        # Update result with interpolation info
        base_result['rates_interpolated'] = rates_interpolated
        base_result['total_rates'] = base_result.get('total_rates', 0) + rates_interpolated
        base_result['message'] = f"Fetched {base_result['rates_fetched']} new rates, {base_result['rates_cached']} cached, {rates_interpolated} interpolated"

        return base_result

    def get_supported_currencies(self) -> list:
        """
        Get list of commonly supported currency codes.

        Returns:
            list: List of currency codes that Yahoo Finance typically supports
        """
        return [
            'USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'CNY', 'HKD', 'NZD',
            'SEK', 'KRW', 'SGD', 'NOK', 'MXN', 'INR', 'RUB', 'ZAR', 'TRY', 'BRL',
            'TWD', 'DKK', 'PLN', 'THB', 'IDR', 'HUF', 'CZK', 'ILS', 'CLP', 'PHP',
            'AED', 'COP', 'SAR', 'MYR', 'RON', 'ARS', 'VND', 'PKR', 'EGP', 'NGN'
        ]

    def ensure_exchange_rates_for_portfolio(self, portfolio_key: int, start_date: date, end_date: date = None) -> dict:
        """
        Unified method to ensure all required exchange rates exist for a portfolio.

        This is the primary method for proactively fetching exchange rates before
        operations like transaction import or market data updates. It:
        1. Analyzes all stocks in the portfolio to identify currency pairs needed
        2. Batch fetches exchange rates for all pairs across the date range
        3. Implements weekend/holiday interpolation (copies nearest trading day rate)
        4. Returns detailed results for monitoring and error handling

        This method is idempotent - safe to call multiple times.

        Args:
            portfolio_key: Portfolio identifier
            start_date: Start date for exchange rate coverage
            end_date: End date for exchange rate coverage (defaults to today)

        Returns:
            dict: Results with detailed status per currency pair
                {
                    'success': bool,
                    'portfolio_key': int,
                    'base_currency': str,
                    'date_range': {'start': str, 'end': str},
                    'currency_pairs': [
                        {
                            'from_currency': str,
                            'to_currency': str,
                            'rates_fetched': int,
                            'rates_cached': int,
                            'rates_interpolated': int,
                            'success': bool,
                            'error': str (if failed)
                        }
                    ],
                    'total_rates_fetched': int,
                    'total_rates_cached': int,
                    'total_rates_interpolated': int,
                    'errors': [str]
                }
        """
        if end_date is None:
            end_date = date.today()

        # Get portfolio to determine base currency
        portfolio = Portfolio.get_by_id(portfolio_key)
        if not portfolio:
            error_msg = f"[INVALID_PORTFOLIO] Portfolio {portfolio_key} not found"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'errors': [error_msg]
            }

        base_currency = portfolio.base_currency.upper().strip()
        logger.info(f"Ensuring exchange rates for portfolio {portfolio_key} ({portfolio.portfolio_name}) - Base currency: {base_currency}")

        # Get all stocks in this portfolio (stocks with transactions)
        stock_keys = db.session.query(Transaction.stock_key).filter(
            Transaction.portfolio_key == portfolio_key
        ).distinct().all()

        stock_keys = [sk[0] for sk in stock_keys]

        if not stock_keys:
            logger.info(f"No stocks found for portfolio {portfolio_key}")
            return {
                'success': True,
                'portfolio_key': portfolio_key,
                'base_currency': base_currency,
                'message': 'No stocks in portfolio, no exchange rates needed',
                'currency_pairs': [],
                'total_rates_fetched': 0,
                'total_rates_cached': 0,
                'total_rates_interpolated': 0,
                'errors': []
            }

        # Get stock currencies
        stocks = Stock.query.filter(Stock.stock_key.in_(stock_keys)).all()

        # Identify unique currency pairs needed
        currency_pairs = set()
        for stock in stocks:
            stock_currency = stock.currency.upper().strip() if stock.currency else 'USD'
            if stock_currency != base_currency:
                currency_pairs.add((stock_currency, base_currency))

        if not currency_pairs:
            logger.info(f"All stocks in portfolio {portfolio_key} use base currency {base_currency}")
            return {
                'success': True,
                'portfolio_key': portfolio_key,
                'base_currency': base_currency,
                'message': 'All stocks use portfolio base currency, no conversion needed',
                'currency_pairs': [],
                'total_rates_fetched': 0,
                'total_rates_cached': 0,
                'total_rates_interpolated': 0,
                'errors': []
            }

        logger.info(f"Found {len(currency_pairs)} currency pairs to fetch: {currency_pairs}")

        # Fetch rates for each currency pair
        pair_results = []
        total_fetched = 0
        total_cached = 0
        total_interpolated = 0
        all_errors = []
        overall_success = True

        for from_curr, to_curr in currency_pairs:
            logger.info(f"Fetching rates for {from_curr}/{to_curr} from {start_date} to {end_date}")

            try:
                # Validate currency pair
                if from_curr not in self.get_supported_currencies():
                    error_msg = f"[INVALID_CURRENCY] Currency '{from_curr}' not in supported currencies list"
                    logger.error(error_msg)
                    pair_results.append({
                        'from_currency': from_curr,
                        'to_currency': to_curr,
                        'success': False,
                        'error': error_msg,
                        'rates_fetched': 0,
                        'rates_cached': 0,
                        'rates_interpolated': 0
                    })
                    all_errors.append(error_msg)
                    overall_success = False
                    continue

                # Fetch rates for this pair (with weekend/holiday interpolation)
                result = self.fetch_rates_for_date_range_with_interpolation(
                    from_currency=from_curr,
                    to_currency=to_curr,
                    start_date=start_date,
                    end_date=end_date
                )

                if result['success']:
                    pair_results.append({
                        'from_currency': from_curr,
                        'to_currency': to_curr,
                        'success': True,
                        'rates_fetched': result['rates_fetched'],
                        'rates_cached': result['rates_cached'],
                        'rates_interpolated': result.get('rates_interpolated', 0)
                    })
                    total_fetched += result['rates_fetched']
                    total_cached += result['rates_cached']
                    total_interpolated += result.get('rates_interpolated', 0)
                else:
                    error_msg = f"[YAHOO_API_ERROR] Failed to fetch {from_curr}/{to_curr}: {result.get('error', 'Unknown error')}"
                    logger.error(error_msg)
                    pair_results.append({
                        'from_currency': from_curr,
                        'to_currency': to_curr,
                        'success': False,
                        'error': error_msg,
                        'rates_fetched': 0,
                        'rates_cached': 0,
                        'rates_interpolated': 0
                    })
                    all_errors.append(error_msg)
                    overall_success = False

            except Exception as e:
                error_msg = f"[YAHOO_API_ERROR] Exception fetching {from_curr}/{to_curr}: {str(e)}"
                logger.error(error_msg)
                pair_results.append({
                    'from_currency': from_curr,
                    'to_currency': to_curr,
                    'success': False,
                    'error': error_msg,
                    'rates_fetched': 0,
                    'rates_cached': 0,
                    'rates_interpolated': 0
                })
                all_errors.append(error_msg)
                overall_success = False

        result_summary = {
            'success': overall_success,
            'portfolio_key': portfolio_key,
            'base_currency': base_currency,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'currency_pairs': pair_results,
            'total_rates_fetched': total_fetched,
            'total_rates_cached': total_cached,
            'total_rates_interpolated': total_interpolated,
            'errors': all_errors
        }

        logger.info(f"Exchange rate fetch complete for portfolio {portfolio_key}: "
                   f"{total_fetched} fetched, {total_cached} cached, {total_interpolated} interpolated")

        return result_summary
