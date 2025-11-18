from tastyworksTaxes.values import Values
from tastyworksTaxes.transaction import Transaction
from tastyworksTaxes.money import Money
from tastyworksTaxes.history import History
from tastyworksTaxes.asset_classifier import AssetClassifier
from tastyworksTaxes.position_manager import PositionManager
from tastyworksTaxes.constants import TransactionCode, Fields
from tastyworksTaxes.trade_calculator import (
    calculate_combined_sum, calculate_option_sum, calculate_long_option_profits,
    calculate_long_option_losses, calculate_long_option_total_losses,
    calculate_short_option_profits, calculate_short_option_losses,
    calculate_option_differential, calculate_stock_loss, calculate_stock_fees,
    calculate_other_fees, calculate_fees_sum, get_stock_trades,
    calculate_gross_equity_etf_profits, calculate_equity_etf_profits,
    calculate_other_stock_and_bond_profits
)
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Tasty:
    def __init__(self, path=None):
        self.yearValues = {}
        self.history = History.fromFile(path) if path else History()
        self.position_manager = PositionManager()
        self.classifier = AssetClassifier()

    def year(self, year):
        if year not in self.yearValues:
            self.yearValues[year] = Values()
        return self.yearValues[year]

    def moneyMovement(self, row):
        import re
        t = Transaction(row)
        m = Money(row=row)
        year_values = self.year(t.getYear())
        desc = t.loc["Description"]

        match t.loc["Transaction Subcode"]:
            case "Transfer":
                year_values.transfer += m
            case "Withdrawal":
                if "Wire Funds Received" in desc:
                    year_values.deposit += m
                elif re.match(r'.*FROM \d{2}/\d{2} THRU \d{2}/\d{2} @.*', desc):
                    year_values.debitInterest += m
                else:
                    year_values.withdrawal += m
            case "Balance Adjustment":
                year_values.balanceAdjustment += m
            case "Fee":
                year_values.fee += m
            case "Deposit":
                if desc == "INTEREST ON CREDIT BALANCE":
                    year_values.creditInterest += m
                else:
                    year_values.deposit += m
            case "Credit Interest":
                year_values.creditInterest += m
            case "Debit Interest":
                year_values.debitInterest += m
            case "Dividend":
                year_values.dividend += m
            case "Fully Paid Stock Lending Income":
                year_values.securitiesLendingIncome += m
            case subcode:
                raise ValueError(f"CRITICAL: Unknown money movement subcode '{subcode}' in transaction: {desc}. "
                               f"This could affect tax calculations.")


    def print(self):
        for key, value in self.yearValues.items():
            print("Year " + str(key) + ":")
            print(value)

    def processTransactionHistory(self):
        chronological_history = self.history.sort_values(
            by=Fields.DATE_TIME.value, ascending=True, kind='stable'
        )
        for _, row in chronological_history.iterrows():
            transaction_code = row.loc["Transaction Code"]
            if transaction_code == TransactionCode.MONEY_MOVEMENT.value:
                self.moneyMovement(row)
            elif transaction_code in {TransactionCode.TRADE.value, TransactionCode.RECEIVE_DELIVER.value}:
                self.position_manager.add_position(Transaction(row))

    def getYearlyTrades(self):
        if not self.position_manager.closed_trades:
            return {}
            
        from datetime import datetime
        from collections import defaultdict
        
        trades_by_year = defaultdict(list)
        for trade in self.position_manager.closed_trades:
            if isinstance(trade.closing_date, str):
                year = datetime.strptime(trade.closing_date, '%Y-%m-%d %H:%M:%S').year
            else:
                year = trade.closing_date.year
            trades_by_year[year].append(trade)
        
        return dict(trades_by_year)
    



    def _checkAssetClassifications(self, trades):
        stock_trades = get_stock_trades(trades)
        if not stock_trades:
            return
        
        unique_symbols = list(set(trade.symbol for trade in stock_trades))
        self.classifier.check_unsupported_assets(unique_symbols)



    def run(self):
        self.processTransactionHistory()
        
        trades_by_year = self.getYearlyTrades()
        fees = {year: -calculate_fees_sum(trades) for year, trades in trades_by_year.items()}
        
        for key in self.yearValues:
            m = Money()
            if key in fees:
                m.usd = fees[key].usd
                m.eur = fees[key].eur
            self.year(key).fee += m

        ret = dict()
        for key in self.yearValues:
            yearly_trades = trades_by_year.get(key, [])
            self._checkAssetClassifications(yearly_trades)
            values_obj = self.yearValues[key]
            
            values_obj.stockAndOptionsSum = calculate_combined_sum(yearly_trades)
            values_obj.equityEtfGrossProfits = calculate_gross_equity_etf_profits(yearly_trades, self.classifier)
            values_obj.equityEtfProfits = calculate_equity_etf_profits(yearly_trades, self.classifier)
            values_obj.otherStockAndBondProfits = calculate_other_stock_and_bond_profits(yearly_trades, self.classifier)
            values_obj.stockAndEtfLosses = calculate_stock_loss(yearly_trades)
            
            values_obj.totalTaxableStockAndEtfProfits = Money(
                usd=values_obj.equityEtfProfits.usd + values_obj.otherStockAndBondProfits.usd,
                eur=values_obj.equityEtfProfits.eur + values_obj.otherStockAndBondProfits.eur
            )
            
            values_obj.optionSum = calculate_option_sum(yearly_trades)
            values_obj.longOptionProfits = calculate_long_option_profits(yearly_trades)
            values_obj.longOptionLosses = calculate_long_option_losses(yearly_trades)
            values_obj.longOptionTotalLosses = calculate_long_option_total_losses(yearly_trades)
            values_obj.shortOptionProfits = calculate_short_option_profits(yearly_trades)
            values_obj.shortOptionLosses = calculate_short_option_losses(yearly_trades)
            values_obj.grossOptionDifferential = calculate_option_differential(yearly_trades)
            values_obj.stockFees = -calculate_stock_fees(yearly_trades)
            values_obj.otherFees = -calculate_other_fees(yearly_trades)

            ret[key] = values_obj

        return ret