import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import datetime
from currency_converter import CurrencyConverter

# Shared currency converter instance
_converter = CurrencyConverter(fallback_on_missing_rate=True, fallback_on_wrong_date=True)

def convert_usd_to_eur(amount: float, date) -> float:
    """Centralized USD to EUR conversion"""
    return _converter.convert(amount, 'USD', 'EUR', date=date)

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
