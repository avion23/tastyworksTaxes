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
        """Processes money movement transactions and updates the appropriate balance fields"""
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
        elif t.loc["Transaction Subcode"] == "Deposit":
            if t.loc["Description"] == "INTEREST ON CREDIT BALANCE":
                self.year(t.getYear()).creditInterest += m
            else:
                self.year(t.getYear()).deposit += m
        elif t.loc["Transaction Subcode"] == "Credit Interest":
            self.year(t.getYear()).creditInterest += m
        elif t.loc["Transaction Subcode"] == "Debit Interest":
            self.year(t.getYear()).debitInterest += m
        elif t.loc["Transaction Subcode"] == "Dividend":
            self.year(t.getYear()).dividend += m
        elif t.loc["Transaction Subcode"] == "Fully Paid Stock Lending Income":
            self.year(t.getYear()).securitiesLendingIncome += m
        else:
            raise KeyError(
                f"Found unknown money movement subcode: '{t.loc['Transaction Subcode']}'")

    def receiveDelivery(self, row):
        """ sub function to process the column namend "Receive Deliver" in the csv file
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

                # Calculate percentageClosed once and derive related percentages
                percentageClosed = abs(tradeQuantity / entry.getQuantity())
                remainingPercentage = 1 - percentageClosed
                percentage = (transaction.getQuantity() - tradeQuantity) / transaction.getQuantity()

                # Update trade dictionary
                tradeKeys = ["Amount", "AmountEuro", "Fees", "FeesEuro"]
                for key in tradeKeys:
                    trade[key] = percentageClosed * entry[key] + transaction[key]

                trade["Symbol"] = transaction.getSymbol()
                trade["callPutStock"] = transaction.getType()
                trade["Opening Date"] = entry.getDateTime()
                trade["Closing Date"] = transaction.getDateTime()

                # Update entry dictionary
                for key in tradeKeys:
                    entry[key] = remainingPercentage * entry[key] + percentage * transaction[key]


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
        """
        newPositionQuantity = oldPositionQuantity + transactionQuantity

        if oldPositionQuantity * transactionQuantity < 0:
            tradeQuantity = min(abs(oldPositionQuantity), abs(transactionQuantity))
            tradeQuantity = tradeQuantity if transactionQuantity > 0 else -tradeQuantity
            newTransactionQuantity = transactionQuantity - tradeQuantity
        else:
            tradeQuantity = 0
            newTransactionQuantity = 0  # Ensure it's set to 0 when both quantities have the same sign

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
        for i, row in self.history.sort_index(ascending=False).iterrows():
            transaction_code = row.loc["Transaction Code"]
            if transaction_code == "Money Movement":
                self.moneyMovement(row)
            elif transaction_code == "Receive Deliver":
                self.receiveDelivery(row)
            elif transaction_code == "Trade":
                self.trade(row)

    def getYearlyTrades(self) -> List[pd.DataFrame]:
        """ returns the yearly trades which have been saved so far as pandas dataframe
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
        return Money(usd=trades['Amount'].sum(), eur=trades['AmountEuro'].sum())


    def getStockSum(self, trades: pd.DataFrame) -> Money:
        stock_trades = trades[trades['callPutStock'] == PositionType.stock]
        return Money(usd=stock_trades['Amount'].sum(), eur=stock_trades['AmountEuro'].sum())

    def getOptionSum(self, trades: pd.DataFrame) -> Money:
        option_trades = trades[trades['callPutStock'].isin([PositionType.call, PositionType.put])]
        return Money(usd=option_trades['Amount'].sum(), eur=option_trades['AmountEuro'].sum())

    def getLongOptionsProfits(self, trades: pd.DataFrame) -> Money:
        valid_trades = trades[
                trades['callPutStock'].isin([PositionType.call, PositionType.put]) &
            (trades['AmountEuro'] > 0) &
                (trades['Quantity'] > 0) &
                ~trades['worthlessExpiry']
            ]

        return Money(usd=valid_trades['Amount'].sum(), eur=valid_trades['AmountEuro'].sum())

    def getLongOptionLosses(self, trades: pd.DataFrame) -> Money:
        valid_trades = trades.loc[
            ((trades['callPutStock'] == PositionType.call) | (trades['callPutStock'] == PositionType.put)) &
            (trades['AmountEuro'] <= 0) &
            (trades['Quantity'] > 0) &
            ~trades['worthlessExpiry']
        ]
        
        m: Money = Money()
        m.usd = valid_trades['Amount'].sum()
        m.eur = valid_trades['AmountEuro'].sum()

        return m

    def getLongOptionTotalLosses(self, trades: pd.DataFrame) -> Money:
        valid_trades = trades[
                trades['callPutStock'].isin([PositionType.call, PositionType.put]) &
            (trades['AmountEuro'] <= 0) &
                (trades['Quantity'] > 0) & 
                trades['worthlessExpiry']
            ]

        return Money(usd=valid_trades['Amount'].sum(), eur=valid_trades['AmountEuro'].sum())


    def getShortOptionProfits(self, trades: pd.DataFrame) -> Money:
        valid_trades = trades[
            trades['callPutStock'].isin([PositionType.call, PositionType.put]) &
            (trades['AmountEuro'] > 0) &
            (trades['Quantity'] < 0)
        ]

        return Money(usd=valid_trades['Amount'].sum(), eur=valid_trades['AmountEuro'].sum())


    def getShortOptionLosses(self, trades: pd.DataFrame) -> Money:
        valid_trades = trades[
                trades['callPutStock'].isin([PositionType.call, PositionType.put]) &
            (trades['AmountEuro'] <= 0) &
                (trades['Quantity'] <= 0)
            ]

        return Money(usd=valid_trades['Amount'].sum(), eur=valid_trades['AmountEuro'].sum())

    def getOptionDifferential(self, trades: pd.DataFrame) -> Money:
        option_filter = trades['callPutStock'].isin([PositionType.call, PositionType.put])
        
        negative = Money(
            usd=trades.loc[option_filter & (trades['Amount'] <= 0), 'Amount'].sum(),
            eur=trades.loc[option_filter & (trades['AmountEuro'] <= 0), 'AmountEuro'].sum()
        )
        
        positive = Money(
            usd=trades.loc[option_filter & (trades['Amount'] > 0), 'Amount'].sum(),
            eur=trades.loc[option_filter & (trades['AmountEuro'] > 0), 'AmountEuro'].sum()
        )

        return Money(
            usd=min(abs(negative.usd), abs(positive.usd)),
            eur=min(abs(negative.eur), abs(positive.eur))
        )

    def getStockLoss(self, trades: pd.DataFrame) -> Money:
        stock_filter = trades['callPutStock'] == PositionType.stock

        return Money(
            usd=trades.loc[stock_filter & (trades['Amount'] <= 0), 'Amount'].sum(),
            eur=trades.loc[stock_filter & (trades['AmountEuro'] <= 0), 'AmountEuro'].sum()
        )

    def getStockFees(self, trades: pd.DataFrame) -> Money:
        stock_filter = trades['callPutStock'] == PositionType.stock

        return Money(
            usd=trades.loc[stock_filter, 'Fees'].sum(),
            eur=trades.loc[stock_filter, 'FeesEuro'].sum()
        )

    def getOtherFees(self, trades: pd.DataFrame) -> Money:
        not_stock_filter = trades['callPutStock'] != PositionType.stock
        return Money(
            usd=trades.loc[not_stock_filter, 'Fees'].sum(),
            eur=trades.loc[not_stock_filter, 'FeesEuro'].sum()
        )

    def getStockProfits(self, trades: pd.DataFrame) -> Money:
        stock_positive_filter = (trades['callPutStock'] == PositionType.stock) & (
            trades['AmountEuro'] > 0)

        return Money(
            usd=trades.loc[stock_positive_filter, 'Amount'].sum(),
            eur=trades.loc[stock_positive_filter, 'AmountEuro'].sum()
        )

    def getFeesSum(self, trades: pd.DataFrame) -> Money:
        return Money(
            usd=trades['Fees'].sum(),
            eur=trades['FeesEuro'].sum()
        )

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
        fees = [- self.getFeesSum(y) for y in trades]
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
            ret[key].stockFees = - self.getStockFees(trades[index])
            ret[key].otherFees = - self.getOtherFees(trades[index])

        return ret



