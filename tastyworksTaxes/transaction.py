import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime
import logging
import pandas as pd
from io import StringIO
from currency_converter import CurrencyConverter

from tastyworksTaxes.history import History
from tastyworksTaxes.money import Money
from tastyworksTaxes.position import Option, Position, PositionType, Stock



logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S'
)

for logger_name, logger in logging.Logger.manager.loggerDict.items():
    if isinstance(logger, logging.Logger):
        if logger_name != "__main__":
            logger.setLevel(logging.WARNING)


class Transaction(pd.core.series.Series):
    """a single entry from the transaction history"""
    c = CurrencyConverter(fallback_on_missing_rate=True, fallback_on_wrong_date=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, dtype='object')

    def __repr__(self):
        excluded_attrs = ['Fees', 'FeesEuro']
        key_mapping = {'Transaction Code': 'TCode', 'Transaction Subcode': 'TSubcode'}
        repr_str = "Transaction("
        
        attributes = []
        for attr in self.keys():
            if attr in excluded_attrs:
                continue
            value = self.get(attr, 'N/A')
            if attr == 'AmountEuro':
                value = f"{value:.2f}" 
            attributes.append(f"{key_mapping.get(attr, attr)}: \"{value}\"")
        
        repr_str += ', '.join(attributes)  
        repr_str += ')'
        return repr_str


    @classmethod
    def fromString(cls, line: str):
        """ returns a Transaction from a csv string

        >>> Transaction.fromString("01/29/2021 7:31 PM,Trade,Sell to Open,UVXY,Sell,Open,1,01/29/2021,14.5,P,0.56,1.152,56,Sold 1 UVXY 01/29/21 Put 14.50 @ 0.56,Individual...39")  # doctest: +NORMALIZE_WHITESPACE
        Transaction(Date/Time: "2021-01-29 19:31:00", TCode: "Trade", TSubcode: "Sell to Open", Symbol: "UVXY", Buy/Sell: "Sell", Open/Close: "Open", Quantity: "1", Expiration Date: "2021-01-29 00:00:00", Strike: "14.5", Call/Put: "P", Price: "0.56", Amount: "56.0", Description: "Sold 1 UVXY 01/29/21 Put 14.50 @ 0.56", AmountEuro: "46.14")        """
        def addEuroConversion(df):
            """ adds new columns called "AmountEuro" and "FeesEuro" to the DataFrame"""
            df['Date/Time'] = pd.to_datetime(df['Date/Time'])
            df['Expiration Date'] = pd.to_datetime(df['Expiration Date'])
            
            df['AmountEuro'] = df.apply(lambda row: cls.c.convert(row['Amount'], 'USD', 'EUR', date=row['Date/Time']), axis=1)
            df['FeesEuro'] = df.apply(lambda row: cls.c.convert(row['Fees'], 'USD', 'EUR', date=row['Date/Time']), axis=1)

        header = "Date/Time,Transaction Code,Transaction Subcode,Symbol,Buy/Sell,Open/Close,Quantity,Expiration Date,Strike,Call/Put,Price,Fees,Amount,Description,Account Reference"
        csv = header + "\n" + line

        try:
            df = pd.read_csv(StringIO(csv))
        except pd.errors.ParserError as e:
            raise ValueError(f"Could not parse '{line}' as Transaction. Original error: {str(e)}") from e

        df = df.drop(columns=['Account Reference'])
        df['Strike'] = df['Strike'].astype(float)
        df['Amount'] = df['Amount'].astype(float)

        addEuroConversion(df)
        return Transaction(df.iloc[0])

    def getYear(self) -> str:
        """returns the year as string from a csv entry

        >>> Transaction.fromString("12/29/2020 3:36 PM,Trade,Sell to Open,PLTR,Sell,Open,1,01/15/2021,26,P,2.46,1.152,246,Sold 1 PLTR 01/15/21 Put 26.00 @ 2.46,Individual...39").getYear()
        2020
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

        >>> print(Transaction.fromString("12/29/2020 3:36 PM,Trade,Sell to Open,PLTR,Sell,Open,1,01/15/2021,26,P,2.46,1.152,246,Sold 1 PLTR 01/15/21 Put 26.00 @ 2.46,Individual...39").getDate())
        2020-12-29
        """
        temp = self.loc["Date/Time"].date()
        return str(temp)

    def getDateTime(self) -> str:
        """returns the exact date

        >>> print(Transaction.fromString("12/29/2020 3:36 PM,Trade,Sell to Open,PLTR,Sell,Open,1,01/15/2021,26,P,2.46,1.152,246,Sold 1 PLTR 01/15/21 Put 26.00 @ 2.46,Individual...39").getDateTime())
        2020-12-29 15:36:00
        """
        temp = self.loc["Date/Time"]
        return str(temp)

    def isType(self, type_column: str, valid_values: set) -> bool:
        value = self.loc[type_column]
        return value in valid_values

    def isOption(self) -> bool:
        """returns true if the transaction is an option

        >>> Transaction.fromString("12/29/2020 3:36 PM,Trade,Sell to Open,PLTR,Sell,Open,1,01/15/2021,26,P,2.46,1.152,246,Sold 1 PLTR 01/15/21 Put 26.00 @ 2.46,Individual...39").isOption()
        True

        # is an assignment  
        >>> Transaction.fromString("12/11/2020 11:00 PM,Receive Deliver,Assignment,PCG,,,3,12/11/2020,10.5,C,,0.00,0,Removal of option due to assignment,Individual...39").isOption()
        False
        >>> Transaction.fromString("12/17/2020 8:57 PM,Trade,Buy to Close,PLTR,Buy,Close,1,01/15/2021,27,P,3.2,0.14,-320,Bought 1 PLTR 01/15/21 Put 27.00 @ 3.20,Individual...39").isOption()
        True
        """
        valid_options = {"P", "C"}
        valid_subcodes = {"Sell to Open", "Buy to Open", "Sell to Close", "Buy to Close"}
        return self.isType("Call/Put", valid_options) and self.isType("Transaction Subcode", valid_subcodes)

    def isStock(self) -> bool:
        """returns true if the symbol is a stock ticker

        >>> Transaction.fromString("12/11/2020 11:00 PM,Receive Deliver,Assignment,PCG,,,3,12/11/2020,10.5,C,,0.00,0,Removal of option due to assignment,Individual...39").isStock()  
        False
        >>> Transaction.fromString("12/15/2020 8:38 PM,Trade,Buy to Open,THCB,Buy,Open,200,,,,13.6,0.16,-2720,Bought 200 THCB @ 13.60,Individual...39").isStock()
        True
        """
        return not not self.getSymbol() and pd.isnull(self["Strike"])

    def getSymbol(self) -> str:
        """returns the Ticker symbol
        >>> h = History.fromFile("test/merged.csv")
        >>> Transaction.fromString("12/11/2020 11:00 PM,Receive Deliver,Assignment,PCG,,,3,12/11/2020,10.5,C,,0.00,0,Removal of option due to assignment,Individual...39").getSymbol()
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

        >>> h = History.fromFile("test/merged.csv")
        >>> Transaction.fromString("12/15/2020 8:38 PM,Trade,Buy to Open,THCB,Buy,Open,200,,,,13.6,0.16,-2720,Bought 200 THCB @ 13.60,Individual...39").getType().name
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
        >>> Transaction(h.iloc[171]).getType()
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

        >>> Transaction.fromString("12/14/2020 4:21 PM,Trade,Sell to Close,NKLA,Sell,Close,1,01/15/2021,20,P,4.4,0.152,440,Sold 1 NKLA 01/15/21 Put 20.00 @ 4.40,Individual...39").getSymbol()
        'NKLA'
        >>> Transaction.fromString("12/14/2020 4:21 PM,Trade,Sell to Close,NKLA,Sell,Close,1,01/15/2021,20,P,4.4,0.152,440,Sold 1 NKLA 01/15/21 Put 20.00 @ 4.40,Individual...39").getQuantity()
        -1
        >>> Transaction.fromString("12/15/2020 8:38 PM,Trade,Buy to Open,THCB,Buy,Open,200,,,,13.6,0.16,-2720,Bought 200 THCB @ 13.60,Individual...39").getQuantity()
        200
        >>> Transaction.fromString("09/21/2020 3:34 PM,Trade,Buy to Close,KODK,Buy,Close,300,,,,10.070,0.240,-3021,Bought 300 KODK @ 10.07,Individual...39").getQuantity()
        300
        >>> Transaction.fromString("08/08/2019 7:59 PM,Trade,Sell to Close,BABA,Sell,Close,100,,,,160.73,0.432,16073,Sold 100 BABA @ 160.73,Individual...39").getQuantity()
        -100
        >>> Transaction.fromString("03/19/2018 10:00 PM,Receive Deliver,Sell to Open,LFIN,Sell,Open,200,,,,30,5.164,6000,Sell to Open 200 LFIN @ 30.00,Individual...39").getQuantity()
        -200
        >>> Transaction.fromString("03/19/2018 10:00 PM,Receive Deliver,Assignment,LFIN,,,2,06/15/2018,30,C,,0.00,0,Removal of option due to assignment,Individual...39").getQuantity()
        2

        # expiration
        >>> Transaction.fromString("07/20/2018 10:00 PM,Receive Deliver,Expiration,MU,,,1,07/20/2018,70,C,,0.00,0,Removal of 1 MU 07/20/18 Call 70.00 due to expiration.,Individual...39").getQuantity()
        1

        # reverse split
        >>> h = History.fromFile("test/merged2.csv")
        >>> Transaction(h.iloc[516]).getQuantity()
        6

        # Symbol change
        >>> h = History.fromFile("test/merged2.csv")
        >>> Transaction(h.iloc[46]).getQuantity()
        -100
        >>> Transaction(h.iloc[45]).getQuantity()
        100

        # Stock merger
        >>> h = History.fromFile("test/merged3.csv") 
        >>> Transaction(h.iloc[194]).getQuantity()
        6
        >>> Transaction(h.iloc[195]).getQuantity()
        -6

        # expiry
        >>> Transaction.fromString("01/29/2021 10:15 PM,Receive Deliver,Expiration,UVXY,,,1,01/29/2021,14.5,P,,0.00,0,Removal of 1.0 UVXY 01/29/21 Put 14.50 due to expiration.,Individual...39").getQuantity()
        1

        # expiry
        >>> Transaction.fromString("07/20/2018 10:00 PM,Receive Deliver,Expiration,DERM,,,2,07/20/2018,11,C,,0.00,0,Removal of 2 DERM 07/20/18 Call 11.00 due to expiration.,Individual...39").getQuantity()
        2

        # size was shown as 1 in testing
        >>> Transaction.fromString("01/29/2021 7:31 PM,Trade,Sell to Open,UVXY,Sell,Open,1,01/29/2021,14.5,P,0.56,1.152,56,Sold 1 UVXY 01/29/21 Put 14.50 @ 0.56,Individual...39").getQuantity()
        -1
        """
        def get_sign_based_on_subcode(subcode: str, buy_sell: str) -> int:
            """Determine the sign of the quantity based on the transaction subcode."""
            sign_mapping = {
                "Buy to Open": 1,
                "Buy to Close": 1,
                "Sell to Open": -1,
                "Sell to Close": -1,
                "Assignment": 1,
                "Expiration": 1  # This is wrong. It's stateful and depends on the previous trade
            }

            if subcode in ["Reverse Split", "Symbol Change", "Stock Merger"]:
                return 1 if buy_sell == "Buy" else -1

            try:
                return sign_mapping[subcode]
            except KeyError as exc:
                raise ValueError(f"Invalid Transaction Subcode: {subcode}") from exc

        valid_transaction_codes = ["Trade", "Receive Deliver"]
        if self.loc["Transaction Code"] not in valid_transaction_codes:
            raise KeyError(f"Invalid Transaction Code: {self.loc['Transaction Code']}")

        subcode = self.loc["Transaction Subcode"]
        buy_sell = self.loc["Buy/Sell"]
        sign = get_sign_based_on_subcode(subcode, buy_sell)
        quantity = self.loc["Quantity"]

        return int(sign * quantity)

    def setQuantity(self, quantity: int):
        """Update the 'Quantity' field and related transaction codes based on the provided quantity
        signage is decided with the subcode
        
        >>> h = History.fromFile("test/merged.csv")
        >>> t = Transaction.fromString("08/08/2019 7:59 PM,Trade,Sell to Close,BABA,Sell,Close,100,,,,160.73,0.432,16073,Sold 100 BABA @ 160.73,Individual...39")
        >>> t.getQuantity()
        -100
        >>> t.setQuantity(200)
        >>> t.getQuantity()
        200
        >>> t = Transaction.fromString("12/29/2020 3:36 PM,Trade,Sell to Open,PLTR,Sell,Open,1,01/15/2021,26,P,2.46,1.152,246,Sold 1 PLTR 01/15/21 Put 26.00 @ 2.46,Individual...39")
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
        >>> h = History.fromFile("test/merged2.csv")
        >>> t = Transaction(h.iloc[170])
        >>> t.getQuantity()
        3
        >>> t.setQuantity(8)
        >>> t.getQuantity()
        8
        >>> t = Transaction.fromString("07/20/2018 10:00 PM,Receive Deliver,Expiration,DERM,,,2,07/20/2018,11,C,,0.00,0,Removal of 2 DERM 07/20/18 Call 11.00 due to expiration.,Individual...39")
        >>> t.getQuantity()
        2
        >>> t.setQuantity(-3)
        >>> t.getQuantity()
        -3
        """
        # Cache frequently accessed values
        transaction_code = self.loc["Transaction Code"]
        transaction_subcode = self.loc["Transaction Subcode"]
        open_close = self.loc["Open/Close"]
        
        valid_transaction_codes = ["Trade", "Receive Deliver"]
        if transaction_code not in valid_transaction_codes:
            raise KeyError(f"Transaction Code is '{transaction_code}' and not in '{valid_transaction_codes}'.")

        if transaction_code == "Receive Deliver" and transaction_subcode in ["Assignment", "Expiration"]:
            self.loc["Quantity"] = quantity
            return

        self.loc["Quantity"] = abs(quantity)
        self.loc["Buy/Sell"] = "Sell" if quantity < 0 else "Buy"

        subcode_mapping = {
            "Open": f"{self.loc['Buy/Sell']} to Open",
            "Close": f"{self.loc['Buy/Sell']} to Close"
        }
        
        if open_close in subcode_mapping:
            self.loc["Transaction Subcode"] = subcode_mapping[open_close]
        else:
            raise ValueError(f"Unexpected value in 'Open/Close': {open_close}")


    def getValue(self) -> Money:
        """ returns the value of the transaction at that specific point of time

        >>> print(Transaction.fromString("12/15/2020 8:38 PM,Trade,Buy to Open,THCB,Buy,Open,200,,,,13.6,0.16,-2720,Bought 200 THCB @ 13.60,Individual...39").getValue())
        {'eur': -2240.527182866557, 'usd': -2720.0}

        >>> t =  Transaction.fromString("12/15/2020 8:38 PM,Trade,Buy to Open,THCB,Buy,Open,200,,,,13.6,0.16,-2720,Bought 200 THCB @ 13.60,Individual...39")
        >>> t.setValue(Money(usd=45, eur=20))
        >>> print(t.getValue())
        {'eur': 20, 'usd': 45}
        """
        v = Money(row=self)
        return v


    def setValue(self, money: Money):
        """ sets the individual values for euro in AmountEuro and usd in Amount

        >>> print(Transaction.fromString("12/15/2020 8:38 PM,Trade,Buy to Open,THCB,Buy,Open,200,,,,13.6,0.16,-2720,Bought 200 THCB @ 13.60,Individual...39").getValue())
        {'eur': -2240.527182866557, 'usd': -2720.0}

        >>> t =  Transaction.fromString("12/15/2020 8:38 PM,Trade,Buy to Open,THCB,Buy,Open,200,,,,13.6,0.16,-2720,Bought 200 THCB @ 13.60,Individual...39")
        >>> t.setValue(Money(usd=45, eur=20))
        >>> print(t.getValue())
        {'eur': 20, 'usd': 45}
        """
        self["Amount"] = money.usd
        self["AmountEuro"] = money.eur


    def getFees(self) -> Money:
        """ returns the fees of the transaction at that specific point of time

        >>> print(Transaction.fromString("12/15/2020 8:38 PM,Trade,Buy to Open,THCB,Buy,Open,200,,,,13.6,0.16,-2720,Bought 200 THCB @ 13.60,Individual...39").getFees())
        {'eur': 0.13179571663920922, 'usd': 0.16}
        """
        v = Money()
        v.usd = self["Fees"]
        v.eur = self["FeesEuro"]
        return v


    def setFees(self, money: Money):
        """ sets the individual values for euro in FeesEuro and usd 

        >>> t =  Transaction.fromString("12/15/2020 8:38 PM,Trade,Buy to Open,THCB,Buy,Open,200,,,,13.6,0.16,-2720,Bought 200 THCB @ 13.60,Individual...39")
        >>> t.setFees(Money(usd=45, eur=20))
        >>> print(t.getFees())
        {'eur': 20, 'usd': 45}
        """
        self["Fees"] = money.usd
        self["FeesEuro"] = money.eur


    def getExpiry(self) -> datetime:
        """ returns the expiry date if it exists

        >>> print(Transaction.fromString("12/29/2020 3:36 PM,Trade,Sell to Open,PLTR,Sell,Open,1,01/15/2021,26,P,2.46,1.152,246,Sold 1 PLTR 01/15/21 Put 26.00 @ 2.46,Individual...39").getExpiry())
        2021-01-15 00:00:00
        """
        d = self.loc["Expiration Date"]
        return d


    def getStrike(self) -> float:
        """ returns the strike of the option

        >>> print(Transaction.fromString("12/29/2020 3:36 PM,Trade,Sell to Open,PLTR,Sell,Open,1,01/15/2021,26,P,2.46,1.152,246,Sold 1 PLTR 01/15/21 Put 26.00 @ 2.46,Individual...39").getStrike())
        26.0
        """
        strike = self.loc["Strike"]
        return strike


if __name__ == "__main__":
    import doctest
    doctest.testmod()
