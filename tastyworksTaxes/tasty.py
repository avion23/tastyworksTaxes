import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import logging
import math
import pathlib
import pprint
from dataclasses import dataclass
from typing import List, Callable

import pandas as pd
from dataclasses_json import dataclass_json

from tastyworksTaxes.history import History
from tastyworksTaxes.money import Money
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.transaction import Transaction
from tastyworksTaxes.values import Values


logger = logging.getLogger(__name__)
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.WARNING,
    datefmt='%Y-%m-%d %H:%M:%S')
for logKey in logging.Logger.manager.loggerDict:  # disable logging for imported modules
    temp = logging.getLogger(logKey)
    temp.propagate = True
    temp.setLevel(logging.INFO)
    if temp.name == "trade":
        temp.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.StreamHandler()
    logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


class Tasty(object):
    yearValues: dict = dict()
    history: History
    positions: pd.DataFrame
    closedTrades:  pd.DataFrame

    def __init__(self, path: pathlib.Path):
        self.yearValues.clear()
        self.history = History.fromFile(path)
        self.closedTrades: pd.DataFrame = pd.DataFrame()
        self.positions = pd.DataFrame()

    def year(self, year):
        """used to access the dictionary and create the year if it doesn't exist

        """
        if not year in self.yearValues:
            self.yearValues[year] = Values()
        return self.yearValues[year]

    def moneyMovement(self, row: Transaction):
        """handles moneyMovement entries

        >>> t = Tasty("test/merged.csv")

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
        >>> str(t.year(2020).creditInterest)
        "{'eur': 0.02461235540241201, 'usd': 0.03}"

        # debit interest
        >>> t = Tasty("test/merged2.csv")
        >>> t.moneyMovement(t.history.iloc[48])
        >>> str(t.year(2021).debitInterest)
        "{'eur': -0.7164621592687145, 'usd': -0.87}"

        # dividend
        >>> t = Tasty("test/merged2.csv")
        >>> t.moneyMovement(t.history.iloc[12])
        >>> str(t.year(2021).dividend)
        "{'eur': -2.470559169892119, 'usd': -3.0}"
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
            self.year(t.getYear()).creditInterest += m
        elif t.loc["Transaction Subcode"] == "Debit Interest":
            self.year(t.getYear()).debitInterest += m
        elif t.loc["Transaction Subcode"] == "Dividend":
            self.year(t.getYear()).dividend += m
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
        200
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

        # reverse split
        >>> t = Tasty("test/merged2.csv")
        >>> t.addPosition(Transaction(t.history.iloc[520])) # 6 P@2
        >>> t.addPosition(Transaction(t.history.iloc[519])) # -6 P@3.5
        >>> t.addPosition(Transaction(t.history.iloc[516])) # -6 P@3.5
        >>> t.addPosition(Transaction(t.history.iloc[514])) # 6 P@3.5
        >>> len(t.closedTrades.index)
        2
        >>> t.positions.size
        0

        # Symbol Change
        >>> t = Tasty("test/merged2.csv")
        >>> t.addPosition(Transaction(t.history.iloc[46])) 

        # Stock merger
        >>> t = Tasty("test/merged3.csv")
        >>> t.addPosition(Transaction(t.history.iloc[193]))
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
        elif t.loc["Transaction Subcode"] == "Reverse Split":
            self.addPosition(t)
        # TODO: That's incorrect. It's not really a sale for tax purposes.
        elif t.loc["Transaction Subcode"] == "Symbol Change":
            self.addPosition(t)
        # TODO: That's incorrect. It's not really a sale for tax purposes.
        elif t.loc["Transaction Subcode"] == "Stock Merger":
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
        1
        >>> t.closedTrades.iloc[0]["Quantity"]
        -1


        # close this up and check if it's gone from the positions
        >>> t.addPosition(Transaction(t.history.iloc[328]))
        >>> t.positions.size
        0
        >>> t.closedTrades.iloc[1]["Quantity"]
        -1

        # add nearly equal position but with different strike
        >>> t.addPosition(Transaction(t.history.iloc[333]))
        >>> wrongStrike = Transaction(t.history.iloc[328])
        >>> wrongStrike["Transaction Subcode"] = "Sell to Open"
        >>> wrongStrike.Strike = 5
        >>> wrongStrike.Quantity
        1
        >>> t.addPosition(wrongStrike)
        >>> t.positions.iloc[0].Quantity
        2
        >>> t.positions.iloc[1].Quantity
        1
        >>> t.positions.iloc[1].Strike
        5


        # multiple options of the same type
        >>> t = Tasty("test/merged2.csv")
        >>> t.addPosition(Transaction(t.history.iloc[238]))
        >>> t.positions.iloc[0].Quantity
        1
        >>> t.addPosition(Transaction(t.history.iloc[237]))
        >>> t.positions.iloc[0].Quantity
        2
        >>> t.addPosition(Transaction(t.history.iloc[236]))
        >>> t.positions.iloc[0].Quantity
        3


        # 2x receive deliver
        >>> t = Tasty("test/merged2.csv")
        >>> t.addPosition(Transaction(t.history.iloc[171]))
        >>> t.addPosition(Transaction(t.history.iloc[144]))
        >>> t.positions.iloc[0].Quantity
        400

        # blackberry BB
        >>> t = Tasty("test/merged2.csv")
        >>> t.addPosition(Transaction(t.history.iloc[263]))
        >>> t.addPosition(Transaction(t.history.iloc[249]))
        >>> t.addPosition(Transaction(t.history.iloc[238]))
        >>> t.addPosition(Transaction(t.history.iloc[237]))
        >>> t.addPosition(Transaction(t.history.iloc[236]))
        >>> t.addPosition(Transaction(t.history.iloc[229]))
        >>> t.addPosition(Transaction(t.history.iloc[197]))
        >>> t.addPosition(Transaction(t.history.iloc[171]))
        >>> t.addPosition(Transaction(t.history.iloc[170]))


        >>> t.addPosition(Transaction(t.history.iloc[168]))
        >>> t.addPosition(Transaction(t.history.iloc[167]))
        >>> t.addPosition(Transaction(t.history.iloc[161]))
        >>> t.addPosition(Transaction(t.history.iloc[159]))
        >>> t.addPosition(Transaction(t.history.iloc[144]))
        >>> t.addPosition(Transaction(t.history.iloc[143]))
        >>> t.addPosition(Transaction(t.history.iloc[141]))
        >>> t.addPosition(Transaction(t.history.iloc[132]))
        >>> t.addPosition(Transaction(t.history.iloc[130]))
        >>> t.addPosition(Transaction(t.history.iloc[120]))
        >>> t.addPosition(Transaction(t.history.iloc[119]))
        >>> t.addPosition(Transaction(t.history.iloc[118]))
        >>> t.addPosition(Transaction(t.history.iloc[106]))
        >>> t.addPosition(Transaction(t.history.iloc[98]))
        >>> t.addPosition(Transaction(t.history.iloc[97]))
        >>> t.addPosition(Transaction(t.history.iloc[92]))
        >>> t.addPosition(Transaction(t.history.iloc[85]))
        >>> t.addPosition(Transaction(t.history.iloc[80]))
        >>> t.addPosition(Transaction(t.history.iloc[78]))
        >>> t.addPosition(Transaction(t.history.iloc[38]))
        >>> t.addPosition(Transaction(t.history.iloc[37]))
        >>> t.addPosition(Transaction(t.history.iloc[35]))
        >>> t.addPosition(Transaction(t.history.iloc[32]))
        >>> t.addPosition(Transaction(t.history.iloc[31]))
        >>> t.addPosition(Transaction(t.history.iloc[30]))
        >>> t.addPosition(Transaction(t.history.iloc[23]))
        >>> t.addPosition(Transaction(t.history.iloc[22]))
        >>> len(t.positions.index)
        2

        # LFIN again
        >>> t = Tasty("test/merged2.csv")
        >>> t.addPosition(Transaction(t.history.iloc[679])) # Bought 2 LFIN 06/15/18 Call 40.00 @ 2.20
        >>> t.positions.iloc[0].Amount 
        -440.0
        >>> t.addPosition(Transaction(t.history.iloc[678])) # Sold 2 LFIN 06/15/18 Call 30.00 @ 7.10
        >>> t.positions.iloc[1].Amount
        1420.0
        >>> t.addPosition(Transaction(t.history.iloc[676])) # Sell to Open 200 LFIN @ 30.00
        >>> t.positions.iloc[2].Amount
        6000.0
        >>> t.addPosition(Transaction(t.history.iloc[675])) # Removal of option due to assignment Call @30
        >>> len(t.positions.index) #  removed
        2
        >>> t.closedTrades.iloc[0]["Amount"]
        1420.0
        >>> t.closedTrades.iloc[0]["Fees"]
        2.324
        >>> t.addPosition(Transaction(t.history.iloc[674])) # Sold 1 LFIN 06/15/18 Call 40.00 @ 16.78
        >>> t.positions.iloc[0].Amount # only half the opening value
        -220.0
        >>> t.positions.iloc[0].Fees # only half the opening value
        1.14
        >>> t.positions.iloc[1].Amount
        6000.0
        >>> t.closedTrades.iloc[1]["Fees"]
        1.3219999999999998

        >>> t.addPosition(Transaction(t.history.iloc[673])) # Bought 100 LFIN @ 56.76
        >>> t.positions.iloc[1].Amount # half remains open
        3000.0
        >>> t.positions.iloc[1].Fees # half remains open
        2.582
        >>> t.closedTrades.iloc[2].Amount # -3000 + 5676
        -2676.0
        >>> t.closedTrades.iloc[2].Fees # 2.582 + 0.08
        2.662
        >>> t.addPosition(Transaction(t.history.iloc[672])) # Bought 100 LFIN @ 57.20
        >>> t.addPosition(Transaction(t.history.iloc[671])) # Sold 1 LFIN 06/15/18 Call 40.00 @ 17.15
        >>> t.closedTrades["Amount"].sum()
        -1023.0
        >>> len(t.positions.index)
        0

        # SPRT
        >>> t = Tasty("test/merged2.csv")
        >>> t.addPosition(Transaction(t.history.iloc[21]))
        >>> t.addPosition(Transaction(t.history.iloc[20]))
        >>> t.addPosition(Transaction(t.history.iloc[19]))
        >>> t.addPosition(Transaction(t.history.iloc[18]))
        >>> t.addPosition(Transaction(t.history.iloc[17]))
        >>> t.addPosition(Transaction(t.history.iloc[16])) # this is the last buy
        >>> t.positions.iloc[0].Amount
        -1934.9999999999998
        >>> t.addPosition(Transaction(t.history.iloc[8]))
        >>> t.addPosition(Transaction(t.history.iloc[7]))
        >>> t.addPosition(Transaction(t.history.iloc[6]))
        >>> t.addPosition(Transaction(t.history.iloc[5]))
        >>> t.addPosition(Transaction(t.history.iloc[4]))
        >>> t.addPosition(Transaction(t.history.iloc[3]))
        >>> t.addPosition(Transaction(t.history.iloc[2]))
        >>> len(t.positions.index)
        0
        >>> t.closedTrades["Amount"].sum()
        469.99999999999994
        """

        for index, row in self.positions.iterrows():
            entry = Transaction(row)
            if entry.getSymbol() == transaction.getSymbol() and entry.getType() == transaction.getType() and transaction.getQuantity() != 0 and (entry.getType() == PositionType.stock or entry.getStrike() == transaction.getStrike() and
                                                                                                                                                 entry.getExpiry() == transaction.getExpiry()):
                trade = Transaction()
                logging.info("{} found an open position: {} {} and adding {}".format(
                             entry.getDateTime(), entry.getQuantity(), entry.getSymbol(), transaction.getQuantity()))

                if (transaction.getType() == PositionType.call or transaction.getType() == PositionType.put):
                    trade["Expiry"] = transaction.getExpiry()
                    trade["Strike"] = transaction.getStrike()

                (newPositionQuantity, newTransactionQuantity, tradeQuantity) = Tasty._updatePosition(
                    entry.getQuantity(), transaction.getQuantity())

                # percentage which is used in a trade
                # percentage = (entry.getQuantity() / transaction.getQuantity)
                percentageClosed = abs(tradeQuantity / entry.getQuantity())
                trade["Amount"] = percentageClosed * \
                    entry["Amount"] + transaction["Amount"]
                trade["AmountEuro"] = percentageClosed * \
                    entry["AmountEuro"] + transaction["AmountEuro"]
                trade["Fees"] = percentageClosed * \
                    entry["Fees"] + transaction["Fees"]
                trade["FeesEuro"] = percentageClosed * \
                    entry["FeesEuro"] + transaction["FeesEuro"]
                trade["Symbol"] = transaction.getSymbol()
                trade["callPutStock"] = transaction.getType()
                trade["Opening Date"] = entry.getDateTime()
                trade["Closing Date"] = transaction.getDateTime()

                percentage = (transaction.getQuantity() -
                              tradeQuantity) / transaction.getQuantity()

                entry["Amount"] = (1-percentageClosed) * entry["Amount"] + \
                    percentage * transaction["Amount"]
                entry["AmountEuro"] = (1-percentageClosed) * entry["AmountEuro"] + \
                    percentage * transaction["AmountEuro"]
                entry["Fees"] = (1-percentageClosed) * entry["Fees"] + \
                    percentage * transaction["Fees"]
                entry["FeesEuro"] = (1-percentageClosed) * entry["FeesEuro"] + \
                    percentage * transaction["FeesEuro"]

                # update the old values
                trade["Quantity"] = int(tradeQuantity)
                transaction.setQuantity(newTransactionQuantity)
                entry.setQuantity(newPositionQuantity)

                # write back
                self.positions.loc[index] = entry
                if math.isclose(entry.Quantity, 0):
                    self.positions.drop(index, inplace=True)

                if trade.Quantity != 0:
                    self.closedTrades = pd.concat([self.closedTrades,
                                                   trade.to_frame().T])
                    logging.info(
                        "{} - {} closing {} {}".format(
                            trade["Opening Date"], trade["Closing Date"], trade["Quantity"], trade["Symbol"])
                    )
        if transaction.getQuantity() != 0:
            if transaction["Transaction Subcode"] == "Buy to Close" or transaction["Transaction Subcode"] == "Sell to Close" or transaction["Transaction Subcode"] == "Assignment" or transaction["Transaction Subcode"] == "Reverse Split" and transaction["Open/Close"] == "Close":
                raise ValueError(
                    "Tried to close a position but no previous position found for {}\nCurrent Positions:\n {}".format(transaction, self.positions))
            logging.info("{} Adding '{}' of '{}' to the open positions".format(transaction.getDateTime(),
                                                                               transaction.getQuantity(), transaction.getSymbol()))

            self.positions = pd.concat(
                [self.positions, transaction.to_frame().T])

    @classmethod
    def _updatePosition(cls, oldPositionQuantity, transactionQuantity):
        """ helper method to calculate the resulting size of a position

        >>> Tasty._updatePosition(1, 1) # adding 1 to a previous position of 1
        (2, 0, 0)
        >>> Tasty._updatePosition(1, -1) # adding 1 to a previous position of -1
        (0, 0, -1)
        >>> Tasty._updatePosition(1, 0) # nop
        (1, 0, 0)
        >>> Tasty._updatePosition(-1, 1)
        (0, 0, 1)
        >>> Tasty._updatePosition(-3, 1)
        (-2, 0, 1)
        >>> Tasty._updatePosition(-3, 2)
        (-1, 0, 2)
        >>> Tasty._updatePosition(-16, 5)
        (-11, 0, 5)

        >>> Tasty._updatePosition(-1, 1) # test singage
        (0, 0, 1)
        >>> Tasty._updatePosition(-1, -1)
        (-2, 0, 0)
        >>> Tasty._updatePosition(16, -5)
        (11, 0, -5)
        >>> Tasty._updatePosition(3, -2)
        (1, 0, -2)
        >>> Tasty._updatePosition(3, -3)
        (0, 0, -3)


        """

        newPositionQuantity = oldPositionQuantity + transactionQuantity
        tradeQuantity = 0
        if abs(newPositionQuantity) < abs(oldPositionQuantity):
            tradeQuantity = min(abs(transactionQuantity),
                                abs(oldPositionQuantity))
            tradeQuantity = int(math.copysign(
                tradeQuantity, transactionQuantity))
        newTransactionQuantity = transactionQuantity - \
            (newPositionQuantity - oldPositionQuantity)
        return (newPositionQuantity, newTransactionQuantity, tradeQuantity)

    def print(self):
        """pretty prints the status"""
        for key, value in self.yearValues.items():
            print("Year " + str(key) + ":")
            print(value)

    def processTransactionHistory(self):
        """ takes the history and calculates the closed trades in self.closedTrades

        # >>> t = Tasty("test/merged2.csv")
        # >>> t.processTransactionHistory()
        # >>> t.print()
        # >>> t.closedTrades

        # >>> t.closedTrades.to_csv("test.csv", index=False)

        """
        # reverses the order and kills prefetching and caching
        for i, row in self.history.iloc[::-1].iterrows():
            # if row.loc["Symbol"] != "PLTR":
            #     continue
            # print(
            #     ">>> t.addPosition(Transaction(t.history.iloc[{}]))".format(i))
            # logging.info(row)
            if row.loc["Transaction Code"] == "Money Movement":
                self.moneyMovement(row)
            if row.loc["Transaction Code"] == "Receive Deliver":
                self.receiveDelivery(row)
            if row.loc["Transaction Code"] == "Trade":
                self.trade(row)
    def getYearlyTrades(self) -> List[pd.DataFrame]:
        """ returns the yearly trades which have been saved so far as pandas dataframe
        >>> t = Tasty("test/merged2.csv")
        >>> t.closedTrades = pd.read_csv("test/closed-trades.csv")
        >>> len(t.getYearlyTrades())
        4
        """
        
        def converter(x: str) -> PositionType:
            return PositionType[x.split('.')[-1]]
        
        trades = self.closedTrades
        trades['Closing Date'] = pd.to_datetime(trades['Closing Date'])
        trades['year'] = trades['Closing Date'].dt.year
        trades['callPutStock'] = trades['callPutStock'].apply(converter)  # type: ignore
        return [trades[trades['year'] == y] for y in trades['year'].unique()]


    def getCombinedSum(self, trades: pd.DataFrame) -> Money:
        """ returns the sum of all stock trades in the corresponding dataframe
        >>> t = Tasty("test/merged2.csv")
        >>> t.closedTrades = pd.read_csv("test/closed-trades.csv")
        >>> years = t.getYearlyTrades()
        >>> [t.getCombinedSum(y) for y in years][0].usd != 0
        True
        """
        m: Money = Money()
        m.usd = trades['Amount'].sum()
        m.eur = trades['AmountEuro'].sum()
        return m

    def getStockSum(self, trades: pd.DataFrame) -> Money:
        """ returns the sum of all stock trades in the corresponding dataframe
        >>> t = Tasty("test/merged2.csv")
        >>> t.closedTrades = pd.read_csv("test/closed-trades.csv")
        >>> years = t.getYearlyTrades()
        >>> [t.getStockSum(y) for y in years][0].usd != 0
        True
        """
        m: Money = Money()
        m.usd = trades.loc[(trades['callPutStock'] ==
                            PositionType.stock), 'Amount'].sum()
        m.eur = trades.loc[(trades['callPutStock'] ==
                            PositionType.stock), 'AmountEuro'].sum()
        return m

    def getOptionsSum(self, trades: pd.DataFrame) -> Money:
        """ returns the sum of all option trades in the corresponding dataframe
        >>> t = Tasty("test/merged2.csv")
        >>> t.closedTrades = pd.read_csv("test/closed-trades.csv")
        >>> years = t.getYearlyTrades()
        >>> [t.getOptionsSum(y) for y in years][0].usd != 0
        True
        """
        m: Money = Money()
        m.usd = trades.loc[(trades['callPutStock'] == PositionType.call) | (
            trades['callPutStock'] == PositionType.put), 'Amount'].sum()
        m.eur = trades.loc[(trades['callPutStock'] == PositionType.call) | (
            trades['callPutStock'] == PositionType.put), 'AmountEuro'].sum()
        return m

    def getOtherLoss(self, trades: pd.DataFrame) -> Money:
        """ returns the sum of all option losses
        >>> t = Tasty("test/merged2.csv")
        >>> t.closedTrades = pd.read_csv("test/closed-trades.csv")
        >>> years = t.getYearlyTrades()
        >>> [t.getOtherLoss(y) for y in years][0].usd != 0
        True
        """
        m: Money = Money()
        m.usd = trades.loc[((trades['callPutStock'] == PositionType.call) | (
            trades['callPutStock'] == PositionType.put)) & (trades['Amount'] < 0), 'Amount'].sum()
        m.eur = trades.loc[((trades['callPutStock'] == PositionType.call) | (
            trades['callPutStock'] == PositionType.put)) & (trades['AmountEuro'] < 0), 'AmountEuro'].sum()
        return m

    def getOptionsDifferential(self, trades: pd.DataFrame) -> Money:
        """ returns the highes difference in options, e.g. how many positive and how many negatives have occured 

        In Germany there is no net taxation for options. Instead, gross is taxed - but only if you are over 20k EUR per year. 
        I implemented this as follows:
        - sum the negatives
        - sum the positives
        - and take the min from the absolute value of both. That is how much they cancel each other out

        >>> t = Tasty("test/merged2.csv")
        >>> t.closedTrades = pd.read_csv("test/closed-trades.csv")
        >>> years = t.getYearlyTrades()
        >>> [t.getOptionsDifferential(y) for y in years][0].usd != 0
        True
        """
        negative: Money = Money()
        negative.usd = trades.loc[((trades['callPutStock'] == PositionType.call) | (
            trades['callPutStock'] == PositionType.put)) & (trades['Amount'] < 0), 'Amount'].sum()
        negative.eur = trades.loc[((trades['callPutStock'] == PositionType.call) | (
            trades['callPutStock'] == PositionType.put)) & (trades['AmountEuro'] < 0), 'AmountEuro'].sum()
        positive: Money = Money()
        positive.usd = trades.loc[((trades['callPutStock'] == PositionType.call) | (
            trades['callPutStock'] == PositionType.put)) & (trades['Amount'] >= 0), 'Amount'].sum()
        positive.eur = trades.loc[((trades['callPutStock'] == PositionType.call) | (
            trades['callPutStock'] == PositionType.put)) & (trades['AmountEuro'] >= 0), 'AmountEuro'].sum()

        r: Money = Money()
        r.usd = min(abs(negative.usd), abs(positive.usd))
        r.eur = min(abs(negative.eur), abs(positive.eur))
        return r

    def getStockLoss(self, trades: pd.DataFrame) -> Money:
        """ returns the sum of the negative stock trades
        >>> t = Tasty("test/merged2.csv")
        >>> t.closedTrades = pd.read_csv("test/closed-trades.csv")
        >>> years = t.getYearlyTrades()
        >>> [t.getStockLoss(y) for y in years][0].usd != 0
        True
        """
        m: Money = Money()
        m.usd = trades.loc[(trades['callPutStock'] == PositionType.stock) & (
            trades['Amount'] < 0), 'Amount'].sum()
        m.eur = trades.loc[(trades['callPutStock'] == PositionType.stock) & (
            trades['AmountEuro'] < 0), 'AmountEuro'].sum()
        return m

    def getStockFees(self, trades: pd.DataFrame) -> Money:
        """ returns the sum of all fees on stocks
        >>> t = Tasty("test/merged2.csv")
        >>> t.closedTrades = pd.read_csv("test/closed-trades.csv")
        >>> years = t.getYearlyTrades()
        >>> [t.getStockLoss(y) for y in years][0].usd != 0
        True
        """
        m: Money = Money()
        m.usd = trades.loc[(trades['callPutStock'] ==
                            PositionType.stock), 'Fees'].sum()
        m.eur = trades.loc[(trades['callPutStock'] ==
                            PositionType.stock), 'FeesEuro'].sum()
        return m

    def getOtherFees(self, trades: pd.DataFrame) -> Money:
        """ returns the sum of all fees on stocks
        >>> t = Tasty("test/merged2.csv")
        >>> t.closedTrades = pd.read_csv("test/closed-trades.csv")
        >>> years = t.getYearlyTrades()
        >>> [t.getStockLoss(y) for y in years][0].usd != 0
        True
        """
        m: Money = Money()
        m.usd = trades.loc[(trades['callPutStock'] !=
                            PositionType.stock), 'Fees'].sum()
        m.eur = trades.loc[(trades['callPutStock'] !=
                            PositionType.stock), 'FeesEuro'].sum()
        return m

    def getStockProfits(self, trades: pd.DataFrame) -> Money:
        """ returns the sum of the positive stock trades
        >>> t = Tasty("test/merged2.csv")
        >>> t.closedTrades = pd.read_csv("test/closed-trades.csv")
        >>> years = t.getYearlyTrades()
        >>> [t.getStockProfits(y) for y in years][3].usd != 0
        True
        """
        m: Money = Money()
        m.usd = trades.loc[(trades['callPutStock'] == PositionType.stock) & (
            trades['Amount'] > 0), 'Amount'].sum()
        m.eur = trades.loc[(trades['callPutStock'] == PositionType.stock) & (
            trades['AmountEuro'] > 0), 'AmountEuro'].sum()
        return m

    def getFeesSum(self, trades: pd.DataFrame) -> Money:
        """ sums up the yearly fees in the closed trades. So so on a yearly basis. Returns the fees 
        >>> t = Tasty("test/merged2.csv")
        >>> t.closedTrades = pd.read_csv("test/closed-trades.csv")
        >>> years = t.getYearlyTrades()
        >>> [t.getFeesSum(y) for y in years][0].usd != 0
        True
        """
        m: Money = Money()
        m.usd = trades['Fees'].sum()
        m.eur = trades['FeesEuro'].sum()
        return m

    def run(self):
        """ runs all functions for all years on the passed transaction file


        # >>> t = Tasty("test/merged3.csv")
        # >>> t.closedTrades = pd.read_csv("test/closed-trades.csv")
        # >>> pprint.PrettyPrinter(indent=True, compact=False)
        # >>> ret = t.run()
        # >>> print(pprint.pformat(ret))
        """
        self.processTransactionHistory()
        trades = self.getYearlyTrades()
        # add in the fees of the individual trades
        fees = [self.getFeesSum(y) for y in trades]
        for index, key in enumerate(self.yearValues):
            m = Money()
            m.usd = fees[index].usd
            m.eur = fees[index].eur
            self.year(key).fee += m

        ret = dict()
        for index, key in enumerate(self.yearValues):
            ret[key] = self.yearValues[key]
            ret[key].stockAndOptionsSum = self.getCombinedSum(trades[index])
            ret[key].stockSum = self.getStockSum(trades[index])
            ret[key].optionSum = self.getOptionsSum(trades[index])
            ret[key].grossOptionsDifferential = self.getOptionsDifferential(
                trades[index])
            ret[key].stockProfits = self.getStockProfits(trades[index])
            ret[key].stockLoss = self.getStockLoss(trades[index])
            ret[key].otherLoss = self.getOtherLoss(trades[index])
            ret[key].stockFees = self.getStockFees(trades[index])
            ret[key].otherFees = self.getOtherFees(trades[index])

        return ret


if __name__ == "__main__":
    import doctest

    doctest.testmod(extraglobs={"t": Tasty("test/merged.csv")})
    # doctest.run_docstring_examples(Tasty.run, globals())
