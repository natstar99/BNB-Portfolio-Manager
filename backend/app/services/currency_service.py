import yfinance as yf
import pandas as pd
from datetime import datetime, date, timedelta
import logging
from typing import Optional, Tuple
from decimal import Decimal
import time

from app.models.currency_exchange_rate import CurrencyExchangeRate
from app.models.date_dimension import DateDimension
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

        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            rate_date: Date for the exchange rate

        Returns:
            float or None: Exchange rate if successful, None otherwise
        """
        # Build Yahoo Finance currency pair symbol
        yahoo_symbol = f"{from_currency}{to_currency}=X"

        try:
            # Retry logic for Yahoo Finance API reliability
            for attempt in range(self.retry_count):
                try:
                    ticker = yf.Ticker(yahoo_symbol)

                    # Fetch historical data around the target date
                    # Get a few days around target to handle weekends/holidays
                    start_date = rate_date - timedelta(days=5)
                    end_date = rate_date + timedelta(days=1)

                    data = ticker.history(start=start_date, end=end_date, auto_adjust=False)

                    if data.empty:
                        logger.warning(f"No data returned from Yahoo for {yahoo_symbol} around {rate_date} (attempt {attempt + 1})")
                        if attempt < self.retry_count - 1:
                            time.sleep(self.retry_delay)
                            continue

                        # If no exact data, try getting the most recent rate
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

        logger.info(f"Fetching exchange rates for {from_currency}/{to_currency} from {start_date} to {end_date}")

        yahoo_symbol = f"{from_currency}{to_currency}=X"
        rates_fetched = 0
        rates_cached = 0
        errors = []

        try:
            # Fetch bulk historical data from Yahoo Finance
            ticker = yf.Ticker(yahoo_symbol)
            data = ticker.history(start=start_date, end=end_date + timedelta(days=1), auto_adjust=False)

            if data.empty:
                error_msg = f"No data returned from Yahoo Finance for {yahoo_symbol}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'rates_fetched': 0,
                    'rates_cached': 0,
                    'errors': [error_msg]
                }

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

                    # Prepare rate data
                    rates_to_create.append({
                        'from_currency': from_currency,
                        'to_currency': to_currency,
                        'rate_date': idx_date,
                        'exchange_rate': float(row['Close'])
                    })

                except Exception as e:
                    error_msg = f"Error processing rate for {idx_date}: {str(e)}"
                    logger.warning(error_msg)
                    errors.append(error_msg)

            # Bulk create rates (don't commit - let caller decide)
            if rates_to_create:
                CurrencyExchangeRate.bulk_create(rates_to_create, commit=False)
                rates_fetched = len(rates_to_create)
                logger.info(f"Prepared {rates_fetched} exchange rates for {from_currency}/{to_currency}")

            return {
                'success': True,
                'rates_fetched': rates_fetched,
                'rates_cached': rates_cached,
                'total_rates': rates_fetched + rates_cached,
                'errors': errors,
                'message': f'Fetched {rates_fetched} new rates, {rates_cached} already cached'
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
