import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import datetime
from currency_converter import CurrencyConverter

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
        """converts from USD to eur at a certain date

        >>> c = Money(usd=100)
        >>> c.fromUsdToEur(date='2010-11-21')
        >>> c.eur
        73.22788517867605
        """
        d = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        c = CurrencyConverter(fallback_on_missing_rate=True)
        usd = c.convert(self.usd, "USD", "EUR", date=d)
        self.eur = usd

    def __repr__(self):
        return str({'eur': self.eur, 'usd': self.usd})

    def __add__(self, x):
        """overloads + operator for Money class

        >>> a = Money()
        >>> a.eur = 5
        >>> a.usd = 6
        >>> b = Money()
        >>> b.eur = 7
        >>> b.usd = 8
        >>> print(a + b)
        {'eur': 12, 'usd': 14}
        """
        m = Money()
        m.eur = self.eur + x.eur
        m.usd = self.usd + x.usd
        return m

    def __sub__(self, x):
        """overloads - operator for Money class

        >>> a = Money()
        >>> a.eur = 5
        >>> a.usd = 6
        >>> b = Money()
        >>> b.eur = 7
        >>> b.usd = 5
        >>> print(b - a)
        {'eur': 2, 'usd': -1}
        """
        m = Money()
        m.eur = self.eur - x.eur
        m.usd = self.usd - x.usd
        return m
    
    def __neg__(self):
        """Returns a new Money instance with negated eur and usd values.

        >>> m = Money(eur=10, usd=20)
        >>> n = -m
        >>> print(n)
        {'eur': -10, 'usd': -20}
        """
        return Money(eur=-self.eur, usd=-self.usd)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
