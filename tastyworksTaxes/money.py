import bisect
import datetime
import math
from numbers import Real

from currency_converter import CurrencyConverter, RateNotFoundError


_converter = CurrencyConverter(
    fallback_on_missing_rate=False,
    fallback_on_wrong_date=False,
)

_RATE_UNAVAILABLE_MESSAGE = (
    "USD to EUR conversion failed because no ECB reference rate is available. "
    "Check that the transaction date is within the bundled rate range and is an ECB publication day."
)

# Sorted ECB USD->EUR publication dates (rows without an actual rate are
# excluded), cached once so money movements can bisect to the nearest earlier
# rate when the exact date is a non-publication day.
_USD_RATE_DATES = tuple(
    sorted(
        rate_date
        for rate_date, rate in _converter._rates['USD'].items()
        if rate is not None
    )
)


def _normalise_conversion_date(value) -> datetime.date:
    if isinstance(value, bool) or value is None:
        raise TypeError("Conversion date must be an explicit calendar date.")
    if isinstance(value, datetime.datetime):
        normalised = value.date()
    elif isinstance(value, datetime.date):
        normalised = value
    else:
        date_method = getattr(value, "date", None)
        if not callable(date_method):
            raise TypeError("Conversion date must be an explicit calendar date.")
        normalised = date_method()

    if isinstance(normalised, datetime.datetime) or not isinstance(
        normalised, datetime.date
    ):
        raise TypeError("Conversion date must be an explicit calendar date.")
    return normalised


def _nearest_earlier_rate_date(conversion_date: datetime.date) -> datetime.date:
    index = bisect.bisect_right(_USD_RATE_DATES, conversion_date) - 1
    if index < 0:
        raise ValueError(_RATE_UNAVAILABLE_MESSAGE)
    return _USD_RATE_DATES[index]


def _convert_with_available_rate(
    amount: float, conversion_date: datetime.date, *, money_movement: bool = False
) -> float:
    try:
        return _converter.convert(amount, 'USD', 'EUR', date=conversion_date)
    except RateNotFoundError:
        if not money_movement:
            raise ValueError(_RATE_UNAVAILABLE_MESSAGE) from None
        return _converter.convert(
            amount, 'USD', 'EUR', date=_nearest_earlier_rate_date(conversion_date)
        )


def get_used_rate(date) -> float:
    """Return the USD→EUR multiplier for an explicit date with an ECB rate."""
    conversion_date = _normalise_conversion_date(date)
    return _convert_with_available_rate(1, conversion_date)


def convert_usd_to_eur(
    amount: float, date, *, money_movement: bool = False
) -> float:
    """Convert a finite real USD amount for an explicit date with an ECB rate.

    Securities amounts fail closed when the exact date has no ECB reference
    rate. With money_movement=True, cash flows on non-publication or
    out-of-range dates convert at the nearest earlier available ECB reference
    rate. Zero amounts return 0.0 before any rate lookup.
    """
    if isinstance(amount, bool) or not isinstance(amount, Real):
        raise TypeError("USD amount must be a finite real number.")
    if not math.isfinite(amount):
        raise ValueError("USD amount must be finite.")

    conversion_date = _normalise_conversion_date(date)
    if amount == 0:
        return 0.0
    return _convert_with_available_rate(
        amount, conversion_date, money_movement=money_movement
    )


class Money:
    """replaces eur and usd"""

    def __init__(self, eur=0.0, usd=0.0, row=None, date=''):
        self.eur = eur
        self.usd = usd
        self.row = row if row is not None else {}
        self.date = date

        if self.usd:
            pass
        elif 'Amount' in self.row:
            self.usd = self.row['Amount']
        if self.eur:
            pass
        elif 'AmountEuro' in self.row:
            self.eur = self.row['AmountEuro']
        if self.date and self.usd:
            self.fromUsdToEur(self.date)

    def fromUsdToEur(self, date):
        """converts from USD to eur at a certain date"""
        d = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        self.eur = convert_usd_to_eur(self.usd, d)

    def __repr__(self):
        return str({'eur': self.eur, 'usd': self.usd})

    def __add__(self, x):
        """overloads + operator for Money class"""
        m = Money()
        m.eur = self.eur + x.eur
        m.usd = self.usd + x.usd
        return m

    def __sub__(self, x):
        """overloads - operator for Money class"""
        m = Money()
        m.eur = self.eur - x.eur
        m.usd = self.usd - x.usd
        return m

    def __neg__(self):
        """Returns a new Money instance with negated eur and usd values."""
        return Money(eur=-self.eur, usd=-self.usd)
