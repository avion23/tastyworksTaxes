import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tastyworksTaxes.values import Values
from tastyworksTaxes.transaction import Transaction
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.money import Money
from tastyworksTaxes.history import History
import pandas as pd
from typing import List, Callable, Optional, Dict

import pprint
import pathlib
import math
import logging
import json



logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S'
)

for logger_name, logger in logging.Logger.manager.loggerDict.items():
    if isinstance(logger, logging.Logger):
        if logger_name != "__main__":
            logger.setLevel(logging.WARNING)


class Tasty:
    def __init__(self, path: Optional[pathlib.Path] = None) -> None:
        self.yearValues: Dict = {}
        self.history: History = History.fromFile(path) if path else History()
        self.closedTrades: pd.DataFrame = pd.DataFrame()
        self.positions: pd.DataFrame = pd.DataFrame()

    def year(self, year):
        """used to access the dictionary and create the year if it doesn't exist        """
        if not year in self.yearValues:
            self.yearValues[year] = Values()
        return self.yearValues[year]

    def moneyMovement(self, row: Transaction):
        """handles moneyMovement entries

        >>> t = Tasty("test/merged.csv")

        # we are paying debit interest here
        # 932:08/16/2019 11:00 PM,Money Movement,Withdrawal,,,,0,,,,,0.00,-9.81,FROM 07/16 THRU 08/15 @ 8    %,Individual...39
        # 9.81 for 8% interest rate
        >>> t.moneyMovement(t.history.iloc[268])
        >>> str(t.year(2019).debitInterest)
        "{'eur': -8.856988082340196, 'usd': -9.81}"

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
        "{'eur': -0.7175849554602441, 'usd': -0.87}"

        # dividend
        >>> t = Tasty("test/merged2.csv")
        >>> t.moneyMovement(t.history.iloc[12])
        >>> str(t.year(2021).dividend)
        "{'eur': -2.5342118601115056, 'usd': -3.0}"

        # deposit, but via withdrawal
        >>> t = Tasty("test/merged3.csv")
        >>> t.moneyMovement(t.history.iloc[436])
        >>> str(t.year(2021).deposit)
        "{'eur': 3957.8528167261256, 'usd': 4770.4}"


        """
        t = Transaction(row)
        m = Money(row=row)
        if t.loc["Transaction Subcode"] == "Transfer":
            self.year(t.getYear()).transfer += m
        elif t.loc["Transaction Subcode"] == "Withdrawal":
            if "Wire Funds Received" in t.loc["Description"]:
                self.year(t.getYear()).deposit += m
            elif "FROM" in t.loc["Description"] and "THRU" in t.loc["Description"] and t.loc["Description"].index("FROM") < t.loc["Description"].index("THRU"):
                self.year(t.getYear()).debitInterest += m
            else:
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
            raise KeyError("Found unknown money movement subcode: '{}'".format(
                t.loc["Transaction Subcode"]))

    def receiveDelivery(self, row):
        """ sub function to process the column namend "Receive Deliver" in the csv file

        # assigned -200 LFIN stock
        >>> t = Tasty("test/merged.csv")
        >>> t.addPosition(Transaction.fromString("03/19/2018 10:00 PM,Receive Deliver,Sell to Open,LFIN,Sell,Open,200,,,,30,5.164,6000,Sell to Open 200 LFIN @ 30.00,Individual...39"))
        >>> t.positions.iloc[0]["Symbol"]
        'LFIN'
        >>> closing = (Transaction.fromString("03/19/2018 10:00 PM,Receive Deliver,Sell to Open,LFIN,Sell,Open,200,,,,30,5.164,6000,Sell to Open 200 LFIN @ 30.00,Individual...39"))
        >>> closing["Transaction Subcode"] = "Buy to Close"
        >>> t.addPosition(closing)
        >>> t.positions.size
        0
        
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

        # uvxy showed remaining positions, even thought they should have been closed
        >>> t = Tasty("test/merged3.csv")
        >>> t.addPosition(Transaction.fromString("01/29/2021 7:31 PM,Trade,Sell to Open,UVXY,Sell,Open,1,01/29/2021,14.5,P,0.56,1.152,56,Sold 1 UVXY 01/29/21 Put 14.50 @ 0.56,Individual...39"))
        >>> t.addPosition(Transaction.fromString("01/29/2021 10:15 PM,Receive Deliver,Expiration,UVXY,,,1,01/29/2021,14.5,P,,0.00,0,Removal of 1.0 UVXY 01/29/21 Put 14.50 due to expiration.,Individual...39"))
        >>> len(t.closedTrades)
        1
        >>> t.positions.empty
        True


        >>> t = Tasty("test/merged3.csv") 
        >>> t.addPosition(Transaction.fromString("05/22/2018 5:36 PM,Trade,Buy to Open,DERM,Buy,Open,2,07/20/2018,11,C,1.05,2.28,-210,Bought 2 DERM 07/20/18 Call 11.00 @ 1.05,Individual...39"))
        >>> t.addPosition(Transaction.fromString("07/20/2018 10:00 PM,Receive Deliver,Expiration,DERM,,,2,07/20/2018,11,C,,0.00,0,Removal of 2 DERM 07/20/18 Call 11.00 due to expiration.,Individual...39"))
        >>> len(t.closedTrades)
        1
        >>> t.positions.empty
        True

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
        elif t.loc["Transaction Subcode"] == "Symbol Change":
            logging.warning(
                f"Symbol Change not implemented yet: {t['Description']}. This is wrongly counted as a sale for tax purposes.")
            self.addPosition(t)
        elif t.loc["Transaction Subcode"] == "Stock Merger":
            logging.warning(
                f"Stock Merger not implemented yet: {t['Description']}. This is wrongly counted as a sale for tax purposes.")
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
        1


        # close this up and check if it's gone from the positions
        >>> t.addPosition(Transaction(t.history.iloc[328]))
        >>> t.positions.size
        0
        >>> t.closedTrades.iloc[1]["Quantity"]
        1

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
        5.0


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
        >>> t.addPosition(Transaction.fromString("12/23/2020 3:45 PM,Trade,Buy to Open,BB,Buy,Open,5,02/19/2021,7,C,1,5.68,-500,Bought 5 BB 02/19/21 Call 7.00 @ 1.00,Individual...39"))
        >>> t.addPosition(Transaction.fromString("01/11/2021 5:51 PM,Trade,Sell to Close,BB,Sell,Close,5,02/19/2021,7,C,1.09,0.71,545,Sold 5 BB 02/19/21 Call 7.00 @ 1.09,Individual...39"))
        >>> t.addPosition(Transaction.fromString("01/21/2021 3:34 PM,Trade,Sell to Open,BB,Sell,Open,1,03/19/2021,16,P,5.5,1.162,550,Sold 1 BB 03/19/21 Put 16.00 @ 5.50,Individual...39"))
        >>> t.addPosition(Transaction.fromString("01/21/2021 3:34 PM,Trade,Sell to Open,BB,Sell,Open,1,03/19/2021,16,P,5.5,1.162,550,Sold 1 BB 03/19/21 Put 16.00 @ 5.50,Individual...39"))
        >>> t.addPosition(Transaction.fromString("01/21/2021 3:34 PM,Trade,Sell to Open,BB,Sell,Open,1,03/19/2021,16,P,5.5,1.162,550,Sold 1 BB 03/19/21 Put 16.00 @ 5.50,Individual...39"))
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
        1

        # LFIN again
        >>> t = Tasty("test/merged2.csv")

        # Bought 2 LFIN 06/15/18 Call 40.00 @ 2.20
        >>> t.addPosition(Transaction.fromString("03/12/2018 5:08 PM,Trade,Buy to Open,LFIN,Buy,Open,2,06/15/2018,40,C,2.2,2.28,-440,Bought 2 LFIN 06/15/18 Call 40.00 @ 2.20,Individual...39"))
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
        >>> t.closedTrades.iloc[-1]["Quantity"]
        1

        # SPRT
        >>> t = Tasty("test/merged2.csv")
        >>> t.addPosition(Transaction.fromString("07/01/2021 8:57 PM,Trade,Buy to Open,SPRT,Buy,Open,200,,,,3.87,0.16,-774,Bought 200 SPRT @ 3.87,Individual...39"))
        >>> t.addPosition(Transaction.fromString("07/01/2021 9:03 PM,Trade,Buy to Open,SPRT,Buy,Open,44,,,,3.87,0.036,-170.28,Bought 44 SPRT @ 3.87,Individual...39"))
        >>> t.addPosition(Transaction.fromString("07/01/2021 9:03 PM,Trade,Buy to Open,SPRT,Buy,Open,100,,,,3.87,0.08,-387,Bought 100 SPRT @ 3.87,Individual...39"))
        >>> t.addPosition(Transaction.fromString("07/01/2021 9:03 PM,Trade,Buy to Open,SPRT,Buy,Open,1,,,,3.87,0.001,-3.87,Bought 1 SPRT @ 3.87,Individual...39"))
        >>> t.addPosition(Transaction.fromString("07/01/2021 9:03 PM,Trade,Buy to Open,SPRT,Buy,Open,100,,,,3.87,0.08,-387,Bought 100 SPRT @ 3.87,Individual...39"))
        >>> t.addPosition(Transaction.fromString("07/01/2021 9:03 PM,Trade,Buy to Open,SPRT,Buy,Open,55,,,,3.87,0.044,-212.85,Bought 55 SPRT @ 3.87,Individual...39"))
        >>> t.positions.iloc[0].Amount
        -1934.9999999999998
        >>> t.addPosition(Transaction.fromString("07/07/2021 3:45 PM,Trade,Sell to Close,SPRT,Sell,Close,51,,,,4.81,0.057,245.31,Sold 51 SPRT @ 4.81,Individual...39"))
        >>> t.addPosition(Transaction.fromString("07/07/2021 3:45 PM,Trade,Sell to Close,SPRT,Sell,Close,50,,,,4.81,0.056,240.5,Sold 50 SPRT @ 4.81,Individual...39"))
        >>> t.addPosition(Transaction.fromString("07/07/2021 3:45 PM,Trade,Sell to Close,SPRT,Sell,Close,50,,,,4.81,0.056,240.5,Sold 50 SPRT @ 4.81,Individual...39"))
        >>> t.addPosition(Transaction.fromString("07/07/2021 3:45 PM,Trade,Sell to Close,SPRT,Sell,Close,50,,,,4.81,0.056,240.5,Sold 50 SPRT @ 4.81,Individual...39"))
        >>> t.addPosition(Transaction.fromString("07/07/2021 3:45 PM,Trade,Sell to Close,SPRT,Sell,Close,5,,,,4.81,0.015,24.05,Sold 5 SPRT @ 4.81,Individual...39"))
        >>> t.addPosition(Transaction.fromString("07/07/2021 3:45 PM,Trade,Sell to Close,SPRT,Sell,Close,5,,,,4.81,0.015,24.05,Sold 5 SPRT @ 4.81,Individual...39"))
        >>> t.addPosition(Transaction.fromString("07/07/2021 3:45 PM,Trade,Sell to Close,SPRT,Sell,Close,289,,,,4.81,0.276,1390.09,Sold 289 SPRT @ 4.81,Individual...39"))
        >>> len(t.positions.index)
        0
        >>> t.closedTrades["Amount"].sum()
        469.99999999999994
        >>> t.closedTrades.iloc[-1]["Quantity"]
        289
        """

        def appendTrade(trade, target_df):
            trade_df = pd.DataFrame([trade])
            combined_df = pd.concat([target_df, trade_df])
            if 'worthlessExpiry' in combined_df.columns:
                combined_df['worthlessExpiry'] = combined_df['worthlessExpiry'].astype(bool)
            return combined_df

        for index, row in self.positions.iterrows():
            entry = Transaction(row)

            if entry.getSymbol() == transaction.getSymbol() and entry.getType() == transaction.getType() and transaction.getQuantity() != 0 and \
                    (entry.getType() == PositionType.stock or (entry.getStrike() == transaction.getStrike() and entry.getExpiry() == transaction.getExpiry())):

                trade = Transaction()
                trade["worthlessExpiry"] = False

                if transaction["Transaction Code"] == "Receive Deliver" and transaction["Transaction Subcode"] == "Expiration" and \
                        abs(transaction.getQuantity()) == abs(entry.getQuantity()):

                    quantityOld = transaction.getQuantity()
                    opposite_sign = -1 if entry.getQuantity() > 0 else 1
                    transaction.setQuantity(opposite_sign * abs(transaction.getQuantity()))

                    logging.debug(
                        f"Removal due to expiration detected. Quantity adjusted from {quantityOld} to {transaction.getQuantity()}. "
                        f"Details: Symbol: {transaction['Symbol']}, Strike: {transaction['Strike']}, Type: {transaction['Call/Put']} | "
                        f"Previous Transaction: Symbol: {entry['Symbol']}, Quantity: {entry.getQuantity()}, Strike: {entry['Strike']}, Type: {entry['Call/Put']}"
                    )
                    if entry["Transaction Subcode"] == "Buy to Open" and entry.isOption():
                        logging.debug(
                            f"Expiry for long position: Symbol: {entry['Symbol']}, Qty: {entry.getQuantity()}, Strike: {entry['Strike']}, Type: {entry['Call/Put']}. Value: {entry.getValue().usd} USD. Record this as total loss.")
                        trade["worthlessExpiry"] = True

                logging.info(
                    f"{entry.getDateTime()} found an open position: {entry.getQuantity()} {entry.getSymbol()} and adding {transaction.getQuantity()}")

                if transaction.getType() in [PositionType.call, PositionType.put]:
                    trade["Expiry"] = transaction.getExpiry()
                    trade["Strike"] = transaction.getStrike()

                (newPositionQuantity, newTransactionQuantity, tradeQuantity) = Tasty._updatePosition(
                    entry.getQuantity(), transaction.getQuantity())

                # percentage which is used in a trade
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
                trade["Quantity"] = int(-tradeQuantity)
                transaction.setQuantity(newTransactionQuantity)
                entry.setQuantity(newPositionQuantity)

                # write back
                self.positions.loc[index] = entry

                if math.isclose(entry.Quantity, 0):
                    self.positions.drop(index, inplace=True)
                if tradeQuantity != 0:
                    # logging.debug(trade)
                    self.closedTrades = appendTrade(trade, self.closedTrades)

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
            self.positions = appendTrade(transaction, self.positions)

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

        # >>> t = Tasty("test/merged4.csv")
        # >>> t.processTransactionHistory()
        # >>> t.print()
        # >>> t.closedTrades
        # >>> t.positions

        # >>> t.closedTrades.to_csv("test.csv", index=False)

        """
        # reverses the order and kills prefetching and caching
        for i, row in self.history.iloc[::-1].iterrows():
            transaction_code = row.loc["Transaction Code"]
            # if row.loc["Symbol"] != "PLTR":
            #     continue
            # print(
            #     ">>> t.addPosition(Transaction(t.history.iloc[{}]))".format(i))
            # logging.info(row)

            if transaction_code == "Money Movement":
                self.moneyMovement(row)
            elif transaction_code == "Receive Deliver":
                self.receiveDelivery(row)
            elif transaction_code == "Trade":
                self.trade(row)

    def getYearlyTrades(self) -> List[pd.DataFrame]:
        """ returns the yearly trades which have been saved so far as pandas dataframe
        >>> t = Tasty("test/merged2.csv")
        >>> t.closedTrades = pd.read_csv("test/closed-trades.csv")
        >>> len(t.getYearlyTrades())
        6
        """

        def converter(x: str) -> PositionType:
            if isinstance(x, PositionType):
                return x
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
        return Money(usd=trades['Amount'].sum(), eur=trades['AmountEuro'].sum())


    def getStockSum(self, trades: pd.DataFrame) -> Money:
        """ returns the sum of all stock trades in the corresponding dataframe
        >>> t = Tasty("test/merged2.csv")
        >>> t.closedTrades = pd.read_csv("test/closed-trades.csv")
        >>> years = t.getYearlyTrades()
        >>> [t.getStockSum(y) for y in years][0].usd != 0
        True
        >>> [t.getStockSum(y) for y in years][0].usd
        -5396.0
        """
        stock_trades = trades[trades['callPutStock'] == PositionType.stock]
        return Money(usd=stock_trades['Amount'].sum(), eur=stock_trades['AmountEuro'].sum())

    def getOptionSum(self, trades: pd.DataFrame) -> Money:
        """ returns the sum of all option trades in the corresponding dataframe
        >>> t = Tasty("test/merged2.csv")
        >>> t.closedTrades = pd.read_csv("test/closed-trades.csv")
        >>> years = t.getYearlyTrades()
        >>> [t.getOptionSum(y) for y in years][0].usd > 0
        True
        >>> [t.getOptionSum(y) for y in years][0].usd
        3728.0
        """
        option_trades = trades[trades['callPutStock'].isin([PositionType.call, PositionType.put])]
        return Money(usd=option_trades['Amount'].sum(), eur=option_trades['AmountEuro'].sum())

    def getLongOptionsProfits(self, trades: pd.DataFrame) -> Money:
        """ returns the sum of all positive option trades in the corresponding dataframe
        >>> t = Tasty("test/merged2.csv")
        >>> t.closedTrades = pd.read_csv("test/closed-trades.csv")
        >>> years = t.getYearlyTrades()
        >>> [t.getLongOptionsProfits(y) for y in years][0].usd > 0
        True
        >>> [t.getLongOptionsProfits(y) for y in years][0].usd
        2977.0
        """
        valid_trades = trades[
                trades['callPutStock'].isin([PositionType.call, PositionType.put]) &
                (trades['Amount'] > 0) & 
                (trades['Quantity'] > 0) &
                ~trades['worthlessExpiry']
            ]

        return Money(usd=valid_trades['Amount'].sum(), eur=valid_trades['AmountEuro'].sum())

    def getLongOptionLosses(self, trades: pd.DataFrame) -> Money:
        """ returns the sum of all negative option trades in the corresponding dataframe, but without total losses
        >>> t = Tasty("test/merged2.csv")
        >>> t.closedTrades = pd.read_csv("test/closed-trades.csv")
        >>> years = t.getYearlyTrades()
        >>> [t.getLongOptionLosses(y) for y in years][1].usd != 0
        True
        >>> [t.getLongOptionLosses(y) for y in years][1].usd < 0
        True
        >>> [t.getLongOptionLosses(y) for y in years][0].usd 
        -193.0
        """
        valid_trades = trades.loc[
            ((trades['callPutStock'] == PositionType.call) | (trades['callPutStock'] == PositionType.put)) &
            (trades['Amount'] < 0) &
            (trades['Quantity'] > 0) &
            ~trades['worthlessExpiry']
        ]
        
        m: Money = Money()
        m.usd = valid_trades['Amount'].sum()
        m.eur = valid_trades['AmountEuro'].sum()

        return m

    def getLongOptionTotalLosses(self, trades: pd.DataFrame) -> Money:
        """ returns the sum of all total losses

        we detect worthless expiry with the field worthlessExpiry.
        Unfortunately, we need to set this while processing the transactions,
        because only then we know if we get no money for the assignment or not.
        Also it's untested

        >>> t = Tasty("test/merged2.csv")
        >>> t.closedTrades = pd.read_csv("test/closed-trades.csv")
        >>> years = t.getYearlyTrades()
        >>> [t.getLongOptionTotalLosses(y) for y in years][0].usd
        -702.0
        """
        m = Money()
        m.usd = trades.loc[
            ((trades['callPutStock'] == PositionType.call) | (trades['callPutStock'] == PositionType.put)) &
            (trades['Amount'] != 0) & (trades['Quantity'] > 0) & (trades['worthlessExpiry']),
            'Amount'].sum()

        m.eur = trades.loc[
            ((trades['callPutStock'] == PositionType.call) | (trades['callPutStock'] == PositionType.put)) &
            (trades['AmountEuro'] != 0) & (trades['Quantity'] > 0) & (trades['worthlessExpiry']),
            'AmountEuro'].sum()
        return m

    def getShortOptionProfits(self, trades: pd.DataFrame) -> Money:
        """ returns the sum of all positive option trades for short options in the corresponding dataframe
        >>> t = Tasty("test/merged2.csv")
        >>> t.closedTrades = pd.read_csv("test/closed-trades.csv")
        >>> years = t.getYearlyTrades()
        >>> [t.getShortOptionProfits(y) for y in years][1].usd != 0
        True
        """
        m: Money = Money()
        m.usd = trades.loc[((trades['callPutStock'] == PositionType.call) | (
            trades['callPutStock'] == PositionType.put)) & (trades['Amount'] > 0) & (trades['Quantity'] < 0), 'Amount'].sum()
        m.eur = trades.loc[((trades['callPutStock'] == PositionType.call) | (
            trades['callPutStock'] == PositionType.put)) & (trades['AmountEuro'] > 0) & (trades['Quantity'] < 0), 'AmountEuro'].sum()
        return m

    def getShortOptionLosses(self, trades: pd.DataFrame) -> Money:
        """ returns the sum of all negative option trades for short options in the corresponding dataframe
        >>> t = Tasty("test/merged2.csv")
        >>> t.closedTrades = pd.read_csv("test/closed-trades.csv")
        >>> years = t.getYearlyTrades()
        >>> [t.getShortOptionLosses(y) for y in years][1].usd != 0
        True
        """
        m: Money = Money()
        m.usd = trades.loc[((trades['callPutStock'] == PositionType.call) | (
            trades['callPutStock'] == PositionType.put)) & (trades['Amount'] < 0) & (trades['Quantity'] < 0), 'Amount'].sum()
        m.eur = trades.loc[((trades['callPutStock'] == PositionType.call) | (
            trades['callPutStock'] == PositionType.put)) & (trades['AmountEuro'] < 0) & (trades['Quantity'] < 0), 'AmountEuro'].sum()
        return m

    def getOptionDifferential(self, trades: pd.DataFrame) -> Money:
        """ returns the highes difference in options, e.g. how many positive and how many negatives have occured 

        In Germany there is no net taxation for options. Instead, gross is taxed - but only if you are over 20k EUR per year. 
        I implemented this as follows:
        - sum the negatives
        - sum the positives
        - and take the min from the absolute value of both. That is how much they cancel each other out

        >>> t = Tasty("test/merged2.csv")
        >>> t.closedTrades = pd.read_csv("test/closed-trades.csv")
        >>> years = t.getYearlyTrades()
        >>> [t.getOptionDifferential(y) for y in years][0].usd != 0
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
            ret[key].optionSum = self.getOptionSum(trades[index])
            ret[key].longOptionProfits = self.getLongOptionsProfits(trades[index])
            ret[key].longOptionLosses = self.getLongOptionLosses(trades[index])
            ret[key].longOptionTotalLosses = self.getLongOptionTotalLosses(trades[index])
            ret[key].shortOptionProfits = self.getShortOptionProfits(trades[index])
            ret[key].shortOptionLosses = self.getShortOptionLosses(trades[index])
            ret[key].grossOptionDifferential = self.getOptionDifferential(
                trades[index])
            ret[key].stockProfits = self.getStockProfits(trades[index])
            ret[key].stockLoss = self.getStockLoss(trades[index])
            ret[key].stockFees = self.getStockFees(trades[index])
            ret[key].otherFees = self.getOtherFees(trades[index])

        return ret


if __name__ == "__main__":
    import doctest

    doctest.testmod(extraglobs={"t": Tasty("test/merged.csv")})
    # doctest.run_docstring_examples(Tasty.run, globals())
