from position import PositionType
import pandas as pd
from history import History
from transaction import Transaction
import math
from money import Money
from typing import List
import logging


class Values:
    """store all data here"""
    withdrawal: Money = Money()
    transfer: Money = Money()
    balanceAdjustment: Money = Money()
    fee: Money = Money()
    deposit: Money = Money()
    interest: Money = Money()
    def __str__(self):
        """pretty prints all the contained Values"""

        out: str = ""
        if self.withdrawal:
            out += "Withdrawal: " + str(self.withdrawal) + "\n"
        if self.transfer:
            out += "Transfer: " + str(self.transfer) + "\n"
        if self.balanceAdjustment:
            out += "Balance Adjustment: " + str(self.balanceAdjustment) + "\n"
        if self.fee:
            out += "Fee: " + str(self.fee) + "\n"
        if self.deposit:
            out += "Deposit: " + str(self.deposit) + "\n"
        if self.interest:
            out += "Credit Interest: " + str(self.interest) + "\n"
        return out


class Tasty(object):
    yearValues = dict()
    history: History
    positions: pd.DataFrame
    closedTrades:  pd.DataFrame

    def __init__(self, path: str):
        logger = logging.getLogger()
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s %(name)-12s %(levelname)-8s %(message)s")
            handler.setFormatter(formatter)
            logger.handlers
            logger.addHandler(handler)

        logger.setLevel(logging.DEBUG)
        self.history = History.fromFile(path)
        self.closedTrades: pd.DataFrame = pd.DataFrame()
        self.positions = pd.DataFrame()

    def year(self, year):
        """used to access the dictionary and create the year if it doesn't exist

        >>> type(t.year(2018))
        <class '__main__.Values'>
        """
        if not year in self.yearValues:
            self.yearValues[year] = Values()
        return self.yearValues[year]

    def moneyMovement(self, row: Transaction):
        """handles moneyMovement entries

        # known good entry of 2020
        >>> t.moneyMovement(t.history.iloc[117])
        >>> str(t.year(2020).withdrawal)
        "{'eur': 1980.251453985631, 'usd': 2315.31}"

        # first entry is deposit -> transfer
        >>> t.moneyMovement(t.history.iloc[-1])
        >>> str(t.year(2018).transfer)
        "{'eur': 966.10578858385, 'usd': 1200.0}"

        # balance adjustment
        >>> t.moneyMovement(t.history.iloc[322])
        >>> str(t.year(2018).balanceAdjustment)
        "{'eur': -0.008085599547206425, 'usd': -0.01}"

        # fee
        >>> t.moneyMovement(t.history.iloc[323])
        >>> str(t.year(2018).fee)
        "{'eur': -35.02348938927588, 'usd': -43.24}"

        # deposit
        >>> t.moneyMovement(t.history.iloc[262])
        >>> str(t.year(2019).deposit)
        "{'eur': 0.009070294784580499, 'usd': 0.01}"

        # credit interest
        >>> t.moneyMovement(t.history.iloc[8])
        >>> str(t.year(2020).interest)
        "{'eur': 0.02461235540241201, 'usd': 0.03}"

        """
        t = Transaction(row)
        m = Money(row=row)
        if t.loc["Transaction Subcode"] == "Transfer":
            self.year(t.getYear()).transfer += m
        elif t.loc["Transaction Subcode"] == "Withdrawal":
            self.year(t.getYear()).withdrawal += m
        elif t.loc["Transaction Subcode"] == "Balance Adjustment":
            self.year(t.getYear()).balanceAdjustment += m
        elif t.loc["Transaction Subcode"] == "Fee":
            self.year(t.getYear()).fee += m
        elif t.loc["Transaction Subcode"] == "Deposit" and t.loc["Description"] == "INTEREST ON CREDIT BALANCE":
            self.year(t.getYear()).deposit += m
        elif t.loc["Transaction Subcode"] == "Credit Interest":
            self.year(t.getYear()).interest += m
        else:
            raise KeyError("Found unkonwn money movement subcode: '{}'".format(
                t.loc["Transaction Subcode"]))

    def receiveDelivery(self, row):
        """ sub function to process the column namend "Receive Deliver" in the csv file
        # assigned -200 LFIN stock
        >>> t = Tasty("test/merged.csv")
        >>> t.addPosition(Transaction(t.history.iloc[330]))
        >>> t.positions.iloc[0]["Symbol"]
        'LFIN'
        >>> closing = Transaction(t.history.iloc[330])
        >>> closing["Transaction Subcode"] = "Buy to Close"
        >>> t.addPosition(closing)
        >>> t.positions.size
        0
        >>> t.closedTrades.iloc[0]["Quantity"]
        200.0
        >>> t = Tasty("test/merged.csv")
        >>> t.addPosition(Transaction(t.history.iloc[332]))
        >>> t.addPosition(Transaction(t.history.iloc[329]))
        >>> len(t.closedTrades.index)
        1
        >>> t.positions.size
        0

        # Expiration
        >>> t = Tasty("test/merged.csv")
        >>> t.addPosition(Transaction(t.history.iloc[315]))
        >>> t.addPosition(Transaction(t.history.iloc[304]))
        >>> len(t.closedTrades.index)
        1
        >>> len(t.closedTrades)
        1
        >>> t.positions.size
        0

        """
        t = Transaction(row)
        if t.loc["Transaction Subcode"] == "Buy to Open":
            self.addPosition(t)
        elif t.loc["Transaction Subcode"] == "Sell to Close":
            self.addPosition(t)
        elif t.loc["Transaction Subcode"] == "Buy to Close":
            self.addPosition(t)
        elif t.loc["Transaction Subcode"] == "Sell to Open":
            self.addPosition(t)
        elif t.loc["Transaction Subcode"] == "Assignment":
            self.addPosition(t)
        elif t.loc["Transaction Subcode"] == "Expiration":
            self.addPosition(t)
        else:
            raise ValueError("unknown subcode for receive deliver: {}".format(
                t.loc["Transaction Subcode"]))

    def trade(self, row):
        t = Transaction(row)
        if t.loc["Transaction Subcode"] == "Buy to Open":
            self.addPosition(t)
        elif t.loc["Transaction Subcode"] == "Sell to Close":
            self.addPosition(t)
        elif t.loc["Transaction Subcode"] == "Buy to Close":
            self.addPosition(t)
        elif t.loc["Transaction Subcode"] == "Sell to Open":
            self.addPosition(t)
        else:
            raise ValueError("unknown subcode for Trade:{}".format(
                t.loc["Transaction Subcode"]))

    def addPosition(self, transaction):
        """ adds a position to the internal ledger. If it resolves against a previous position, profit and loss is calculated and recorded

        # 2 LFIN calls open, 
        >>> t.addPosition(Transaction(t.history.iloc[333]))
        >>> t.positions.iloc[0]["Symbol"]
        'LFIN'

        # one closing, absolute positions should be 1 afterwards
        >>> t.addPosition(Transaction(t.history.iloc[328]))
        >>> t.positions.iloc[0]["Quantity"]
        1.0
        >>> t.closedTrades.iloc[0]["Quantity"]
        1.0


        # close this up and check if it's gone from the positions
        >>> t.addPosition(Transaction(t.history.iloc[328]))
        >>> t.positions.size
        0
        >>> t.closedTrades.iloc[1]["Quantity"]
        1.0

        # add nearly equal position but with different strike
        >>> t.addPosition(Transaction(t.history.iloc[333]))
        >>> wrongStrike = Transaction(t.history.iloc[328])
        >>> wrongStrike["Transaction Subcode"] = "Sell to Open"
        >>> wrongStrike.Strike = 5
        >>> wrongStrike.Quantity
        1
        >>> t.addPosition(wrongStrike)
        >>> t.positions.iloc[0].Quantity
        2.0
        >>> t.positions.iloc[1].Quantity
        1.0
        >>> t.positions.iloc[1].Strike
        5.0


        >>> Transaction(t.history.iloc[328])["Fees"]
        0.182
        >>> Transaction(t.history.iloc[333])["Fees"]
        2.28
        >>> t.closedTrades.iloc[0]["Fees"]
        2.4619999999999997
        >>> t.closedTrades.iloc[0]["FeesEuro"]
        2.0014932675530592

        # try overclosing the position, i.e. opening a new position
        >>> t = Tasty("test/merged.csv")
        >>> t.addPosition(Transaction(t.history.iloc[333]))
        >>> transaction = Transaction(t.history.iloc[328])
        >>> transaction.setQuantity(500)
        >>> transaction["Transaction Subcode"] = "Sell to Open"
        >>> t.addPosition(transaction)
        >>> t.positions.iloc[0].Quantity
        -498.0
        >>> t.closedTrades.iloc[0].Quantity
        2.0

        """

        for index, row in self.positions.iterrows():
            entry = Transaction(row)
            if entry.getSymbol() == transaction.getSymbol() and entry.getType() == transaction.getType() and transaction.getQuantity() != 0:
                trade = Transaction()
                logging.info("{} found a previous position: {} {} ".format(
                             transaction.getDateTime(), transaction.getQuantity(), transaction.getSymbol()))
                trade["Symbol"] = transaction.getSymbol()
                trade["callPutStock"] = transaction.getType()
                trade["Opening Date"] = entry.getDateTime()
                trade["Closing Date"] = transaction.getDateTime()
                trade["Fees"] = transaction["Fees"] + entry["Fees"]
                trade["FeesEuro"] = transaction["FeesEuro"] + \
                    entry["FeesEuro"]
                if (transaction.getType() == PositionType.call or transaction.getType() == PositionType.put):
                    if (entry.getStrike() == transaction.getStrike() and
                            entry.getExpiry() == transaction.getExpiry()):
                        trade["Expiry"] = transaction.getExpiry()
                        trade["Strike"] = transaction.getStrike()
                    else:  # option, but not matching
                        continue

                # good case, uses up the transaction
                if abs(transaction.getQuantity()) <= abs(entry.getQuantity()):
                    trade["Quantity"] = abs(transaction.getQuantity())
                    entry.setQuantity(
                        entry.getQuantity() + transaction.getQuantity())
                    transaction.setQuantity(0)
                else:  # bad case: we have some rest
                    trade["Quantity"] = entry.getQuantity()
                    entry.setQuantity(
                        entry.getQuantity() + transaction.getQuantity())
                    transaction.setQuantity(
                        transaction.getQuantity() - entry.getQuantity())

                oldValue = Money(entry)
                trade.setValue(oldValue + transaction.getValue())
                if trade.Quantity == 0:
                    raise ValueError(
                        "This trade's Quantity is 0 after closing which is not possible")
                self.closedTrades = self.closedTrades.append(
                    trade, ignore_index=True)

                # write back
                self.positions.loc[index] = entry
                if math.isclose(entry.Quantity, 0):
                    self.positions.drop(index, inplace=True)

                logging.info(
                    "{} - {} closing {} {}".format(
                        trade["Opening Date"], trade["Closing Date"], trade["Quantity"], trade["Symbol"])
                )
        if transaction.getQuantity() != 0:
            if transaction["Transaction Subcode"] == "Buy to Close" or transaction["Transaction Subcode"] == "Sell to Close" or transaction["Transaction Subcode"] == "Assignment":
                raise ValueError(
                    "Tried to close a position but no previous position found for {}\nCurrent Positions:\n {}".format(transaction, self.positions))
            logging.info("{} Appending '{}' of '{}'".format(transaction.getDateTime(),
                transaction.getQuantity(), transaction.getSymbol()))
            self.positions = self.positions.append(
                transaction, ignore_index=True)

    def print(self):
        """pretty prints the status"""
        for key, value in self.yearValues.items():
            print("Year " + str(key) + ":")
            print(value)

    def processTransactionHistory(self):
        """does everything

        >>> t = Tasty("test/merged.csv")
        >>> #t.processTransactionHistory()
        >>> #t.print()


        """
        # reverses the order and kills prefetching and caching
        for i, row in self.history.iloc[::-1].iterrows():
            if row.loc["Transaction Code"] == "Money Movement":
                self.moneyMovement(row)
            if row.loc["Transaction Code"] == "Receive Deliver":
                self.receiveDelivery(row)
            if row.loc["Transaction Code"] == "Trade":
                self.trade(row)
        pass


if __name__ == "__main__":
    import doctest

    doctest.testmod(extraglobs={"t": Tasty("test/merged.csv")})
