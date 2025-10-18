from datetime import datetime, date
from app import db
from app.utils.date_parser import DateParser


class CurrencyExchangeRate(db.Model):
    """Currency exchange rate dimension model for Kimball star schema"""
    __tablename__ = 'DIM_CURRENCY_EXCHANGE_RATES'

    exchange_rate_key = db.Column(db.Integer, primary_key=True)
    from_currency = db.Column(db.String(10), nullable=False)
    to_currency = db.Column(db.String(10), nullable=False)
    date_key = db.Column(db.Integer, db.ForeignKey('DIM_DATE.date_key'), nullable=False)
    exchange_rate = db.Column(db.Numeric(10, 6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    # Table constraints
    __table_args__ = (
        db.UniqueConstraint('from_currency', 'to_currency', 'date_key', name='uq_currency_date'),
    )

    def __repr__(self):
        return f'<CurrencyExchangeRate {self.from_currency}/{self.to_currency} @ {self.date_key}: {self.exchange_rate}>'

    def to_dict(self):
        return {
            'exchange_rate_key': self.exchange_rate_key,
            'from_currency': self.from_currency,
            'to_currency': self.to_currency,
            'date_key': self.date_key,
            'exchange_rate': float(self.exchange_rate) if self.exchange_rate else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

    @staticmethod
    def create(from_currency: str, to_currency: str, rate_date: date, exchange_rate: float):
        """
        Create a new currency exchange rate record.

        Args:
            from_currency: Source currency code (e.g., 'AUD')
            to_currency: Target currency code (e.g., 'USD')
            rate_date: Date for the exchange rate
            exchange_rate: Exchange rate value

        Returns:
            CurrencyExchangeRate: Created exchange rate object
        """
        # Convert date to date_key
        date_key = DateParser.date_to_raw_int(rate_date)

        rate = CurrencyExchangeRate(
            from_currency=from_currency.upper(),
            to_currency=to_currency.upper(),
            date_key=date_key,
            exchange_rate=exchange_rate
        )
        db.session.add(rate)
        db.session.commit()
        return rate

    @staticmethod
    def get_rate(from_currency: str, to_currency: str, rate_date: date):
        """
        Get exchange rate for a specific currency pair and date.

        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            rate_date: Date for the exchange rate

        Returns:
            CurrencyExchangeRate or None: Exchange rate record if found
        """
        date_key = DateParser.date_to_raw_int(rate_date)

        return CurrencyExchangeRate.query.filter_by(
            from_currency=from_currency.upper(),
            to_currency=to_currency.upper(),
            date_key=date_key
        ).first()

    @staticmethod
    def get_or_create(from_currency: str, to_currency: str, rate_date: date, exchange_rate: float):
        """
        Get existing exchange rate or create new one if it doesn't exist.

        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            rate_date: Date for the exchange rate
            exchange_rate: Exchange rate value to use if creating

        Returns:
            tuple: (CurrencyExchangeRate, bool) where bool indicates if created (True) or retrieved (False)
        """
        existing = CurrencyExchangeRate.get_rate(from_currency, to_currency, rate_date)

        if existing:
            return existing, False

        rate = CurrencyExchangeRate.create(from_currency, to_currency, rate_date, exchange_rate)
        return rate, True

    @staticmethod
    def bulk_create(rates_data: list, commit: bool = True):
        """
        Bulk create exchange rate records for efficiency.

        Args:
            rates_data: List of dicts with keys: from_currency, to_currency, rate_date, exchange_rate
            commit: Whether to commit immediately (default True)

        Returns:
            list: List of created CurrencyExchangeRate objects
        """
        rates = []
        for data in rates_data:
            date_key = DateParser.date_to_raw_int(data['rate_date'])

            rate = CurrencyExchangeRate(
                from_currency=data['from_currency'].upper(),
                to_currency=data['to_currency'].upper(),
                date_key=date_key,
                exchange_rate=data['exchange_rate']
            )
            rates.append(rate)
            db.session.add(rate)

        if commit:
            db.session.commit()

        return rates

    @staticmethod
    def get_all():
        """Get all exchange rates"""
        return CurrencyExchangeRate.query.all()

    @staticmethod
    def get_by_currency_pair(from_currency: str, to_currency: str):
        """Get all exchange rates for a specific currency pair"""
        return CurrencyExchangeRate.query.filter_by(
            from_currency=from_currency.upper(),
            to_currency=to_currency.upper()
        ).order_by(CurrencyExchangeRate.date_key.desc()).all()

    def update(self, exchange_rate: float):
        """Update exchange rate value"""
        self.exchange_rate = exchange_rate
        self.last_updated = datetime.utcnow()
        db.session.commit()
        return self

    def delete(self):
        """Delete exchange rate record"""
        db.session.delete(self)
        db.session.commit()
