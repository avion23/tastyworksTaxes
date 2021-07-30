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
    creditInterest: Money = Money()
    debitInterest: Money = Money()
    dividend: Money = Money()

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
        if self.creditInterest:
            out += "Credit Interest: " + str(self.creditInterest) + "\n"
        if self.creditInterest:
            out += "Debit Interest: " + str(self.debitInterest) + "\n"
        if self.dividend:
            out += "Dividend: " + str(self.dividend) + "\n"
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
        elif t.loc["Transaction Subcode"] == "Symbol Change": # That's incorrect. It's not really a sale
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
        -1.0


        # close this up and check if it's gone from the positions
        >>> t.addPosition(Transaction(t.history.iloc[328]))
        >>> t.positions.size
        0
        >>> t.closedTrades.iloc[1]["Quantity"]
        -1.0

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
        2.6439999999999997
        >>> t.closedTrades.iloc[0]["FeesEuro"]
        2.7582721797167506

   

        # multiple options of the same type
        >>> t = Tasty("test/merged2.csv")
        >>> t.addPosition(Transaction(t.history.iloc[238]))
        >>> t.positions.iloc[0].Quantity
        1.0
        >>> t.addPosition(Transaction(t.history.iloc[237]))
        >>> t.positions.iloc[0].Quantity
        2.0
        >>> t.addPosition(Transaction(t.history.iloc[236]))
        >>> t.positions.iloc[0].Quantity
        3.0


        # 2x receive deliver
        >>> t = Tasty("test/merged2.csv")
        >>> t.addPosition(Transaction(t.history.iloc[171]))
        >>> t.addPosition(Transaction(t.history.iloc[144]))
        >>> t.positions.iloc[0].Quantity
        400.0

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

                (newPositionQuantity, newTransactionQuantity, tradeQuantity) = Tasty._updatePosition(entry.getQuantity(), transaction.getQuantity())

                # take a percentage of the position over to the new position
                entry["Amount"] = (entry["Amount"] + (newTransactionQuantity - transaction.getQuantity())  * transaction["Amount"])
                entry["AmountEuro"] = (entry["AmountEuro"] + (newTransactionQuantity - transaction.getQuantity())  * transaction["AmountEuro"])
                entry["Fees"] = (entry["Fees"] + (newTransactionQuantity - transaction.getQuantity())  * transaction["Fees"])
                entry["FeesEuro"] = (entry["Fees"] + (newTransactionQuantity - transaction.getQuantity())  * transaction["FeesEuro"])
                trade["Fees"] = tradeQuantity / transaction.getQuantity() *transaction["Fees"] + entry["Fees"]
                trade["FeesEuro"] = tradeQuantity / transaction.getQuantity() * transaction["FeesEuro"] + \
                    entry["FeesEuro"]
                trade["Symbol"] = transaction.getSymbol()
                trade["callPutStock"] = transaction.getType()
                trade["Opening Date"] = entry.getDateTime()
                trade["Closing Date"] = transaction.getDateTime()
                
                # update the old values
                trade["Quantity"] = int(tradeQuantity)
                transaction.setQuantity(newTransactionQuantity)
                entry.setQuantity(newPositionQuantity)
                
                oldValue = Money(entry)
                trade.setValue(oldValue + transaction.getValue())
                if trade.Quantity != 0:
                    self.closedTrades = self.closedTrades.append(
                        trade, ignore_index=True)

                # write back
                self.positions.loc[index] = entry
                if math.isclose(entry.Quantity, 0):
                    self.positions.drop(index, inplace=True)
                
                if trade.Quantity != 0:
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
            self.positions = self.positions.append(
                transaction, ignore_index=True)

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
            tradeQuantity = min(abs(transactionQuantity), abs(oldPositionQuantity))
            tradeQuantity = int(math.copysign(tradeQuantity, transactionQuantity))
        newTransactionQuantity = transactionQuantity -(newPositionQuantity - oldPositionQuantity)
        return (newPositionQuantity, newTransactionQuantity, tradeQuantity)




    def print(self):
        """pretty prints the status"""
        for key, value in self.yearValues.items():
            print("Year " + str(key) + ":")
            print(value)

    def processTransactionHistory(self):
        """does everything

        >>> t = Tasty("test/merged2.csv")
        >>> t.processTransactionHistory()
        >>> t.print()


        """
        # reverses the order and kills prefetching and caching
        for i, row in self.history.iloc[::-1].iterrows():
            # if row.loc["Symbol"] != "BB":
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
        


if __name__ == "__main__":
    import doctest
    doctest.testmod(extraglobs={"t": Tasty("test/merged.csv")})
    # doctest.run_docstring_examples(Tasty.moneyMovement, globals())
