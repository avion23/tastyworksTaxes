import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import datetime
import logging
import math
from currency_converter import CurrencyConverter

logger = logging.getLogger(__name__)

# Shared currency converter instance
_converter = CurrencyConverter(fallback_on_missing_rate=True, fallback_on_wrong_date=True)
_strict_converter = CurrencyConverter(
    fallback_on_missing_rate=False, fallback_on_wrong_date=False
)


def _normalise_date(date):
    try:
        return date.date()
    except AttributeError:
        return date


def _fallback_reason(date):
    first_date, last_date = _strict_converter.bounds['USD']
    if date < first_date or date > last_date:
        return 'date out of range'
    return 'missing rate for date'


def get_used_rate(date) -> float:
    """Return the USD→EUR multiplier applied to a USD amount."""
    return _converter.convert(1, 'USD', 'EUR', date=date)

def convert_usd_to_eur(amount: float, date) -> float:
    """Centralized USD to EUR conversion"""
    converted_amount = _converter.convert(amount, 'USD', 'EUR', date=date)

    if not math.isfinite(amount):
        return converted_amount

    fallback_used = False
    try:
        _strict_converter.convert(amount, 'USD', 'EUR', date=date)
    except Exception:
        fallback_used = True

    if fallback_used:
        used_date = _normalise_date(date)
        logger.warning(
            'USD to EUR conversion used fallback: date=%s amount=%s rate=%s reason=%s',
            used_date,
            amount,
            get_used_rate(date),
            _fallback_reason(used_date),
        )
    return converted_amount

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
