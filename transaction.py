from datetime import datetime
import pandas as pd
from history import History
from position import PositionType, Position, Stock, Option
from money import Money


class Transaction(pd.core.series.Series):
    """a single entry from the transaction history"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def getYear(self) -> str:
        """returns the year as string from a csv entry


        >>> Transaction(h.iloc[-1]).getYear()
        2018
        """
        temp = self.loc["Date/Time"].year
        if temp < 2010:
            raise ValueError(
                "Date is less than the year 2010. That's very improbable")
        if temp > 2100:
            raise ValueError(
                "Date is bigger than 2100. That's very improbable")
        return temp

    def getDate(self) -> str:
        """returns 2018-04-02 date format


        >>> print(Transaction(h.iloc[-1]).getDate())
        2018-03-08
        """
        temp = self.loc["Date/Time"].date()
        return str(temp)

    def getDateTime(self) -> str:
        """returns the exact date


        >>> print(Transaction(h.iloc[-1]).getDateTime())
        2018-03-08 23:00:00
        """
        temp = self.loc["Date/Time"]
        return str(temp)

    def isOption(self) -> bool:
        """returns true if the transaction is an option

        >>> Transaction(h.iloc[0]).isOption()
        True

        # is an assignment
        >>> Transaction(h.iloc[13]).isOption()
        False
        >>> Transaction(h.iloc[20]).isOption()
        True

        """
        option = self.loc["Call/Put"]
        subcode = self.loc["Transaction Subcode"]
        if (option == "P" or option == "C") and (
            subcode == "Sell to Open"
            or subcode == "Buy to Open"
            or subcode == "Sell to Close"
            or subcode == "Buy to Close"
        ):
            return True
        else:
            return False

    def isStock(self) -> bool:
        """returns true if the symbol is a stock ticker

        >>> Transaction(h.iloc[13]).isStock()
        False
        >>> Transaction(h.iloc[10]).isStock()
        True
        """
        return not not self.getSymbol() and pd.isnull(self["Strike"])

    def getSymbol(self) -> str:
        """returns the Ticker symbol

        >>> Transaction(h.iloc[13]).getSymbol()
        'PCG'

        # Receive Deliver
        >>> Transaction(h.iloc[330]).getSymbol()
        'LFIN'
        >>> Transaction(h.iloc[12]).getSymbol()
        Traceback (most recent call last):
        ...
        ValueError: This transaction doesn't have a symbol. That's wrong
        """
        symbol: str = str(self.loc["Symbol"])
        if 'nan' == symbol or symbol == '':
            raise ValueError(
                "This transaction doesn't have a symbol. That's wrong")

        return symbol

    def getType(self) -> PositionType:
        """returns put, call or stock

        >>> Transaction(h.iloc[10]).getType().name
        'stock'
        >>> Transaction(h.iloc[13]).getType().name
        'call'
        >>> Transaction(h.iloc[12]).getType().name
        Traceback (most recent call last):
        ...
        ValueError: This transaction doesn't have a symbol. That's wrong
        >>> Transaction(h.iloc[329]).getType().name
        'call'
        >>> Transaction(h.iloc[328]).getType()
        <call>
        >>> Transaction(h.iloc[333]).getType()
        <call>

        # this was a SPAC which resulted in quantity ! % 100
        >>> h = History.fromFile("test/merged2.csv")
        >>> Transaction(h.iloc[277]).getSymbol()
        'THCBW'
        >>> Transaction(h.iloc[277]).getType()
        <stock>
        """
        callOrPut = self.loc["Call/Put"]

        if self.isStock():
            return PositionType.stock
        elif callOrPut == "C":
            return PositionType.call
        elif callOrPut == "P":
            return PositionType.put
        else:
            raise ValueError(
                "Couldn't identify if it is stock, call or put. Entry was '{}".format(self))

    def getQuantity(self) -> int:
        """ returns the size of the transaction if applicable

        >>> Transaction(h.iloc[11]).getSymbol()
        'NKLA'
        >>> Transaction(h.iloc[11]).getQuantity()
        -1
        >>> Transaction(h.iloc[10]).getQuantity()
        200
        >>> Transaction(h.iloc[123]).getQuantity()
        300
        >>> Transaction(h.iloc[270]).getQuantity()
        -100
        >>> Transaction(h.iloc[330]).getQuantity()
        -200
        >>> Transaction(h.iloc[329]).getQuantity()
        2

        # expiration
        >>> Transaction(h.iloc[304]).getQuantity()
        -1

        # reverse split
        >>> h = History.fromFile("test/merged2.csv")
        >>> Transaction(h.iloc[516]).getQuantity()
        6

        """
        validTransactionCodes = ["Trade", "Receive Deliver"]
        if self.loc["Transaction Code"] not in validTransactionCodes:
            raise KeyError(
                "Transaction Code is '{}' and not in '{}'.".format(self.loc["Transaction Code"], validTransactionCodes))

        subcode = self.loc["Transaction Subcode"]

        sign = 1
        if subcode == "Buy to Open" or subcode == "Buy to Close":
            sign = 1
        elif subcode == "Sell to Open" or subcode == "Sell to Close":
            sign = -1
        elif subcode == "Assignment":
            sign = +1
        elif subcode == "Expiration":
            sign = -1  # TODO
        # TODO: Handle this without realizing a trade
        elif subcode == "Reverse Split":
            if self.loc["Buy/Sell"] == "Buy":
                sign = 1
            elif self.loc["Buy/Sell"] == "Sell":
                sign = -1
            else:
                raise ValueError(
                    "Unhandled case for '{}'. Transaction was: '{}'".format(subcode, self))
        else:
            raise ValueError(
                "Transaction Subcode is invalid: '{}'".format(subcode))
        q = self.loc["Quantity"]

        size = sign * q
        return size

    def setQuantity(self, quantity: int):
        """ Signage is decided with the subcode
        >>> t = Transaction(h.iloc[270])
        >>> t.getQuantity()
        -100
        >>> t.setQuantity(200)
        >>> t.getQuantity()
        200
        >>> t = Transaction(h.iloc[0])
        >>> t.getQuantity()
        -1
        >>> t.setQuantity(200)
        >>> t.getQuantity()
        200
        >>> t.setQuantity(-200)
        >>> t.getQuantity()
        -200
        >>> t = Transaction(h.iloc[123])
        >>> t.getQuantity()
        300
        >>> t.setQuantity(-200)
        >>> t.getQuantity()
        -200
        >>> t.setQuantity(0)
        >>> t.getQuantity()
        0

        """
        validTransactionCodes = ["Trade", "Receive Deliver"]
        if self.loc["Transaction Code"] not in ["Trade", "Receive Deliver"]:
            raise KeyError(
                "Transaction Code is '{}' and not in '{}'.".format(self.loc["Transaction Code"], validTransactionCodes))

        self.loc["Quantity"] = abs(quantity)

        if quantity < 0:
            self.loc["Buy/Sell"] == "Sell"

            if self.loc["Open/Close"] == "Open":
                self.loc["Transaction Subcode"] = "Sell to Open"
            elif self.loc["Open/Close"] == "Close":
                self.loc["Transaction Subcode"] = "Sell to Close"
            else:
                raise ValueError(
                    "Unexpected value in 'Open/Close': {}".format(self.loc["Open/Close"]))
        elif quantity >= 0:
            self.loc["Buy/Sell"] == "Buy"

            if self.loc["Open/Close"] == "Open":
                self.loc["Transaction Subcode"] = "Buy to Open"
            elif self.loc["Open/Close"] == "Close":
                self.loc["Transaction Subcode"] = "Buy to Close"
            else:
                raise ValueError(
                    "Unexpected value in 'Open/Close': {}".format(self.loc["Open/Close"]))

    def getValue(self) -> Money:
        """ returns the value of the transaction at that specific point of time

        >>> print(Transaction(h.iloc[10]).getValue())
        {'usd': -2720.0, 'eur': -2240.527182866557}
        """
        v = Money(row=self)
        return v

    def setValue(self, money: Money):
        """ sets the individual values for euro in AmountEuro and usd in Amount

        >>> print(Transaction(h.iloc[10]).getValue())
        {'usd': -2720.0, 'eur': -2240.527182866557}

        >>> t =  Transaction(h.iloc[10])
        >>> t.setValue(Money(usd=45, eur=20))
        >>> print(t.getValue())
        {'usd': 45, 'eur': 20}
        """
        self["Amount"] = money.usd
        self["AmountEuro"] = money.eur

    def getFees(self) -> Money:
        """ returns the feets of the transaction at that specific point of time

        >>> print(Transaction(h.iloc[10]).getFees())
        {'usd': 0.16, 'eur': 0.13179571663920922}
        """
        v = Money()
        v.usd = self["Fees"]
        v.eur = self["FeesEuro"]
        return v

    def setFees(self, money: Money):
        """ sets the individual values for euro in FeesEuro and usd 

        >>> t =  Transaction(h.iloc[10])
        >>> t.setFees(Money(usd=45, eur=20))
        >>> print(t.getFees())
        {'usd': 45, 'eur': 20}
        """
        self["Fees"] = money.usd
        self["FeesEuro"] = money.eur

    def getExpiry(self) -> datetime:
        """ returns the expiry date if it exists

        >>> print(Transaction(h.iloc[0]).getExpiry())
        2021-01-15 00:00:00
        """

        d = self.loc["Expiration Date"]
        return d

    def getStrike(self) -> float:
        """ returns the strike of the option


        >>> print(Transaction(h.iloc[0]).getStrike())
        26.0
        """
        strike = self.loc["Strike"]
        return strike


if __name__ == "__main__":
    import doctest

    doctest.testmod(extraglobs={"h": History.fromFile("test/merged.csv")})
