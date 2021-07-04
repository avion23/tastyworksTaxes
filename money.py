
from currency_converter import CurrencyConverter
from datetime import date
import datetime

class Money:
    """replaces eur and usd"""

    eur: float = 0
    usd: float = 0

    def __init__(self, row = None, date=None, usd=None, eur=None):
        """converts directly if usd and date are set

        >>> str(Money(date='2010-11-21', usd=100))
        "{'usd': 100, 'eur': 73.22788517867605}"
                """
        if usd:
            self.usd = usd
        if eur:
            self.eur = eur
        if date and usd:
            self.fromUsdToEur(date)
        if row is not None:
            self.usd = row['Amount']
            self.eur = row['AmountEuro']

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
        return str(self.__dict__)

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

        m: Money = Money()
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

        m: Money = Money()
        m.eur = self.eur - x.eur
        m.usd = self.usd - x.usd
        return m

if __name__ == "__main__":
    import doctest
    doctest.testmod()
