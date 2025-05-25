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

import pathlib
import math
import logging



logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Tasty:
    def __init__(self, path: Optional[pathlib.Path] = None) -> None:
        self.yearValues: Dict = {}
        self.history: History = History.fromFile(path) if path else History()
        self.closedTrades: pd.DataFrame = pd.DataFrame()
        self.positions: pd.DataFrame = pd.DataFrame()

    def year(self, year):
        if not year in self.yearValues:
            self.yearValues[year] = Values()
        return self.yearValues[year]

    def moneyMovement(self, row: Transaction):
        t = Transaction(row)
        m = Money(row=row)
        
        def handle_transfer(t, m):
            self.year(t.getYear()).transfer += m
            
        def handle_withdrawal(t, m):
            if "Wire Funds Received" in t.loc["Description"]:
                self.year(t.getYear()).deposit += m
            elif "FROM" in t.loc["Description"] and "THRU" in t.loc["Description"] and t.loc["Description"].index("FROM") < t.loc["Description"].index("THRU"):
                self.year(t.getYear()).debitInterest += m
            else:
                self.year(t.getYear()).withdrawal += m
                
        def handle_balance_adjustment(t, m):
            self.year(t.getYear()).balanceAdjustment += m
            
        def handle_fee(t, m):
            self.year(t.getYear()).fee += m
            
        def handle_deposit(t, m):
            if t.loc["Description"] == "INTEREST ON CREDIT BALANCE":
                self.year(t.getYear()).creditInterest += m
            else:
                self.year(t.getYear()).deposit += m
                
        def handle_credit_interest(t, m):
            self.year(t.getYear()).creditInterest += m
            
        def handle_debit_interest(t, m):
            self.year(t.getYear()).debitInterest += m
            
        def handle_dividend(t, m):
            self.year(t.getYear()).dividend += m
            
        def handle_stock_lending(t, m):
            self.year(t.getYear()).securitiesLendingIncome += m
        
        handlers = {
            "Transfer": handle_transfer,
            "Withdrawal": handle_withdrawal,
            "Balance Adjustment": handle_balance_adjustment,
            "Fee": handle_fee,
            "Deposit": handle_deposit,
            "Credit Interest": handle_credit_interest,
            "Debit Interest": handle_debit_interest,
            "Dividend": handle_dividend,
            "Fully Paid Stock Lending Income": handle_stock_lending
        }
        
        subcode = t.loc["Transaction Subcode"]
        if subcode in handlers:
            handlers[subcode](t, m)
        else:
            raise KeyError(f"Found unknown money movement subcode: '{subcode}'")

    def receiveDelivery(self, row):
        t = Transaction(row)
        
        def handle_symbol_change(t):
            logger.warning(
                f"Symbol Change not implemented yet: {t['Description']}. This is wrongly counted as a sale for tax purposes.")
            self.addPosition(t)
            
        def handle_stock_merger(t):
            logger.warning(
                f"Stock Merger not implemented yet: {t['Description']}. This is wrongly counted as a sale for tax purposes.")
            self.addPosition(t)
        
        handlers = {
            "Buy to Open": self.addPosition,
            "Sell to Close": self.addPosition,
            "Buy to Close": self.addPosition,
            "Sell to Open": self.addPosition,
            "Assignment": self.addPosition,
            "Expiration": self.addPosition,
            "Reverse Split": self.addPosition,
            "Symbol Change": handle_symbol_change,
            "Stock Merger": handle_stock_merger
        }
        
        subcode = t.loc["Transaction Subcode"]
        if subcode in handlers:
            handlers[subcode](t)
        else:
            raise ValueError(f"Unknown subcode for receive deliver: {subcode}")

    def trade(self, row):
        t = Transaction(row)
        
        handlers = {
            "Buy to Open": self.addPosition,
            "Sell to Close": self.addPosition,
            "Buy to Close": self.addPosition,
            "Sell to Open": self.addPosition
        }
        
        subcode = t.loc["Transaction Subcode"]
        if subcode in handlers:
            handlers[subcode](t)
        else:
            raise ValueError(f"Unknown subcode for Trade: {subcode}")

    def addPosition(self, transaction):

        def appendTrade(trade, target_df):
            trade_df = pd.DataFrame([trade])
            if 'Fees' in trade_df.columns:
                trade_df['Fees'] = trade_df['Fees'].astype(float)
            if 'FeesEuro' in trade_df.columns:
                trade_df['FeesEuro'] = trade_df['FeesEuro'].astype(float)
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

                    logger.debug(
                        f"Removal due to expiration detected. Quantity adjusted from {quantityOld} to {transaction.getQuantity()}. "
                        f"Details: Symbol: {transaction['Symbol']}, Strike: {transaction['Strike']}, Type: {transaction['Call/Put']} | "
                        f"Previous Transaction: Symbol: {entry['Symbol']}, Quantity: {entry.getQuantity()}, Strike: {entry['Strike']}, Type: {entry['Call/Put']}"
                    )
                    if entry["Transaction Subcode"] == "Buy to Open" and entry.isOption():
                        logger.debug(
                            f"Expiry for long position: Symbol: {entry['Symbol']}, Qty: {entry.getQuantity()}, Strike: {entry['Strike']}, Type: {entry['Call/Put']}. Value: {entry.getValue().usd} USD. Record this as total loss.")
                        trade["worthlessExpiry"] = True

                logger.info(
                    f"{entry.getDateTime():<19} found an open position: {entry.getQuantity():>4} {entry.getSymbol():<6} and adding {transaction.getQuantity():>4}")

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
                transaction.setQuantity(int(newTransactionQuantity))
                entry.setQuantity(int(newPositionQuantity))

                if 'Fees' in self.positions.columns and index in self.positions.index:
                    self.positions.loc[index, 'Fees'] = float(entry['Fees'])
                if 'FeesEuro' in self.positions.columns and index in self.positions.index:
                    self.positions.loc[index, 'FeesEuro'] = float(entry['FeesEuro'])
                if 'Quantity' in self.positions.columns and index in self.positions.index:
                    self.positions.loc[index, 'Quantity'] = int(entry['Quantity'])
                    
                for col in entry.index:
                    if col not in ['Fees', 'FeesEuro', 'Quantity']:
                        self.positions.loc[index, col] = entry[col]

                if math.isclose(entry.Quantity, 0):
                    self.positions.drop(index, inplace=True)
                if tradeQuantity != 0:
                    # logging.debug(trade)
                    self.closedTrades = appendTrade(trade, self.closedTrades)

                    logger.info(
                        "{:<19} - {:<19} closing {:>4} {:<6}".format(
                            trade["Opening Date"], trade["Closing Date"], trade["Quantity"], trade["Symbol"])
                    )
        if transaction.getQuantity() != 0:
            if transaction["Transaction Subcode"] == "Buy to Close" or transaction["Transaction Subcode"] == "Sell to Close" or transaction["Transaction Subcode"] == "Assignment" or transaction["Transaction Subcode"] == "Reverse Split" and transaction["Open/Close"] == "Close":
                raise ValueError(
                    "Tried to close a position but no previous position found for {}\nCurrent Positions:\n {}".format(transaction, self.positions))
            logger.info("{:<19} Adding '{:>4}' of '{:<6}' to the open positions".format(transaction.getDateTime(),
                                                                               transaction.getQuantity(), transaction.getSymbol()))
            self.positions = appendTrade(transaction, self.positions)

    @classmethod
    def _updatePosition(cls, oldPositionQuantity, transactionQuantity):
        newPositionQuantity = oldPositionQuantity + transactionQuantity

        if oldPositionQuantity * transactionQuantity < 0:
            tradeQuantity = min(abs(oldPositionQuantity), abs(transactionQuantity))
            tradeQuantity = tradeQuantity if transactionQuantity > 0 else -tradeQuantity
            newTransactionQuantity = transactionQuantity - tradeQuantity
        else:
            tradeQuantity = 0
            newTransactionQuantity = 0  # Ensure it's set to 0 when both quantities have the same sign

        return (int(newPositionQuantity), int(newTransactionQuantity), int(tradeQuantity))


    def print(self):
        for key, value in self.yearValues.items():
            print("Year " + str(key) + ":")
            print(value)

    def processTransactionHistory(self):
        for i, row in self.history.sort_index(ascending=False).iterrows():
            transaction_code = row.loc["Transaction Code"]
            if transaction_code == "Money Movement":
                self.moneyMovement(row)
            elif transaction_code == "Receive Deliver":
                self.receiveDelivery(row)
            elif transaction_code == "Trade":
                self.trade(row)

    def getYearlyTrades(self) -> List[pd.DataFrame]:
        if self.closedTrades.empty:
            return []
            
        def converter(x: str) -> PositionType:
            if isinstance(x, PositionType):
                return x
            return PositionType[x.split('.')[-1]]

        trades = self.closedTrades
        trades['Closing Date'] = pd.to_datetime(trades['Closing Date'])
        trades['year'] = trades['Closing Date'].dt.year
        trades['callPutStock'] = trades['callPutStock'].apply(converter)  # type: ignore
        return [trades[trades['year'] == y] for y in trades['year'].unique()]

    def _sumMoney(self, trades: pd.DataFrame, filter_condition=None) -> Money:
        """Helper to sum Amount and AmountEuro with optional filter"""
        if trades.empty:
            return Money()
        filtered_trades = trades[filter_condition] if filter_condition is not None else trades
        return Money(usd=filtered_trades['Amount'].sum(), eur=filtered_trades['AmountEuro'].sum())

    def getCombinedSum(self, trades: pd.DataFrame) -> Money:
        return self._sumMoney(trades)


    def getStockSum(self, trades: pd.DataFrame) -> Money:
        return self._sumMoney(trades, trades['callPutStock'] == PositionType.stock)

    def getOptionSum(self, trades: pd.DataFrame) -> Money:
        return self._sumMoney(trades, trades['callPutStock'].isin([PositionType.call, PositionType.put]))

    def getLongOptionsProfits(self, trades: pd.DataFrame) -> Money:
        condition = (
            trades['callPutStock'].isin([PositionType.call, PositionType.put]) &
            (trades['AmountEuro'] > 0) &
            (trades['Quantity'] > 0) &
            ~trades['worthlessExpiry']
        )
        return self._sumMoney(trades, condition)

    def getLongOptionLosses(self, trades: pd.DataFrame) -> Money:
        condition = (
            trades['callPutStock'].isin([PositionType.call, PositionType.put]) &
            (trades['AmountEuro'] <= 0) &
            (trades['Quantity'] > 0) &
            ~trades['worthlessExpiry']
        )
        return self._sumMoney(trades, condition)

    def getLongOptionTotalLosses(self, trades: pd.DataFrame) -> Money:
        condition = (
            trades['callPutStock'].isin([PositionType.call, PositionType.put]) &
            (trades['AmountEuro'] <= 0) &
            (trades['Quantity'] > 0) &
            trades['worthlessExpiry']
        )
        return self._sumMoney(trades, condition)

    def getShortOptionProfits(self, trades: pd.DataFrame) -> Money:
        condition = (
            trades['callPutStock'].isin([PositionType.call, PositionType.put]) &
            (trades['AmountEuro'] > 0) &
            (trades['Quantity'] < 0)
        )
        return self._sumMoney(trades, condition)

    def getShortOptionLosses(self, trades: pd.DataFrame) -> Money:
        condition = (
            trades['callPutStock'].isin([PositionType.call, PositionType.put]) &
            (trades['AmountEuro'] <= 0) &
            (trades['Quantity'] <= 0)
        )
        return self._sumMoney(trades, condition)

    def getOptionDifferential(self, trades: pd.DataFrame) -> Money:
        option_filter = trades['callPutStock'].isin([PositionType.call, PositionType.put])
        option_trades = trades[option_filter]
        
        if option_trades.empty:
            return Money()
            
        negative_sum = self._sumMoney(trades, option_filter & (trades['AmountEuro'] <= 0))
        positive_sum = self._sumMoney(trades, option_filter & (trades['AmountEuro'] > 0))

        return Money(
            usd=min(abs(negative_sum.usd), abs(positive_sum.usd)),
            eur=min(abs(negative_sum.eur), abs(positive_sum.eur))
        )

    def getStockLoss(self, trades: pd.DataFrame) -> Money:
        condition = (trades['callPutStock'] == PositionType.stock) & (trades['AmountEuro'] <= 0)
        return self._sumMoney(trades, condition)

    def _sumFees(self, trades: pd.DataFrame, filter_condition=None) -> Money:
        """Helper to sum Fees and FeesEuro with optional filter"""
        if trades.empty:
            return Money()
        filtered_trades = trades[filter_condition] if filter_condition is not None else trades
        return Money(usd=filtered_trades['Fees'].sum(), eur=filtered_trades['FeesEuro'].sum())

    def getStockFees(self, trades: pd.DataFrame) -> Money:
        return self._sumFees(trades, trades['callPutStock'] == PositionType.stock)

    def getOtherFees(self, trades: pd.DataFrame) -> Money:
        return self._sumFees(trades, trades['callPutStock'] != PositionType.stock)

    def getStockProfits(self, trades: pd.DataFrame) -> Money:
        condition = (trades['callPutStock'] == PositionType.stock) & (trades['AmountEuro'] > 0)
        return self._sumMoney(trades, condition)

    def getFeesSum(self, trades: pd.DataFrame) -> Money:
        return self._sumFees(trades)

    def run(self):
        self.processTransactionHistory()
        trades = self.getYearlyTrades()
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



