import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime
import logging
import pandas as pd
from io import StringIO
from tastyworksTaxes.history import History
from tastyworksTaxes.money import Money, convert_usd_to_eur
from tastyworksTaxes.position import Option, Position, PositionType, Stock

logger = logging.getLogger(__name__)

class Transaction(pd.core.series.Series):

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
        def addEuroConversion(df):
            df['Date/Time'] = pd.to_datetime(df['Date/Time'])
            df['Expiration Date'] = pd.to_datetime(df['Expiration Date'])
            
            df['AmountEuro'] = df.apply(lambda row: convert_usd_to_eur(row['Amount'], row['Date/Time']), axis=1)
            df['FeesEuro'] = df.apply(lambda row: convert_usd_to_eur(row['Fees'], row['Date/Time']), axis=1)

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
        return Transaction(df.squeeze())

    def getYear(self) -> str:
        temp = self.loc["Date/Time"].year
        if temp < 2010:
            raise ValueError("Date is less than the year 2010. That's very improbable")
        if temp > 2100:
            raise ValueError("Date is bigger than 2100. That's very improbable")
        return temp

    def getDate(self) -> str:
        temp = self.loc["Date/Time"].date()
        return str(temp)

    def getDateTime(self) -> str:
        temp = self.loc["Date/Time"]
        return str(temp)

    def isType(self, type_column: str, valid_values: set) -> bool:
        value = self.loc[type_column]
        return value in valid_values

    def isOption(self) -> bool:
        valid_options = {"P", "C"}
        valid_subcodes = {"Sell to Open", "Buy to Open", "Sell to Close", "Buy to Close", "Assignment", "Expiration"}
        return self.isType("Call/Put", valid_options) and self.isType("Transaction Subcode", valid_subcodes)

    def isStock(self) -> bool:
        return not not self.getSymbol() and pd.isnull(self["Strike"])

    def getSymbol(self) -> str:
        symbol: str = str(self.loc["Symbol"])
        if 'nan' == symbol or symbol == '':
            raise ValueError("This transaction doesn't have a symbol. That's wrong")
        return symbol

    def getType(self) -> PositionType:
        callOrPut = self.loc["Call/Put"]

        if self.isStock():
            return PositionType.stock
        elif callOrPut == "C":
            return PositionType.call
        elif callOrPut == "P":
            return PositionType.put
        else:
            raise ValueError(f"Couldn't identify if it is stock, call or put. Entry was '{self}")

    def getQuantity(self) -> int:
        def get_sign_based_on_subcode(subcode: str, buy_sell: str) -> int:
            sign_mapping = {
                "Buy to Open": 1,
                "Buy to Close": 1,
                "Sell to Open": -1,
                "Sell to Close": -1,
                "Assignment": 1,
                "Expiration": 1
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
        transaction_code = self.loc["Transaction Code"]
        transaction_subcode = self.loc["Transaction Subcode"]
        open_close = self.loc["Open/Close"]
        
        valid_transaction_codes = ["Trade", "Receive Deliver"]
        if transaction_code not in valid_transaction_codes:
            raise KeyError(f"Transaction Code is '{transaction_code}' and not in '{valid_transaction_codes}'.")

        if transaction_code == "Receive Deliver" and transaction_subcode in ["Assignment", "Expiration"]:
            self.loc["Quantity"] = int(quantity)
            return

        self.loc["Quantity"] = int(abs(quantity))
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
        v = Money(row=self)
        return v

    def setValue(self, money: Money):
        self["Amount"] = money.usd
        self["AmountEuro"] = money.eur

    def getFees(self) -> Money:
        v = Money()
        v.usd = self["Fees"]
        v.eur = self["FeesEuro"]
        return v

    def setFees(self, money: Money):
        self["Fees"] = money.usd
        self["FeesEuro"] = money.eur

    def getExpiry(self) -> datetime:
        d = self.loc["Expiration Date"]
        return d

    def getStrike(self) -> float:
        strike = self.loc["Strike"]
        return strike


