from tastyworksTaxes.values import Values
from tastyworksTaxes.transaction import Transaction
from tastyworksTaxes.money import Money
from tastyworksTaxes.history import History
from tastyworksTaxes.asset_classifier import AssetClassifier
from tastyworksTaxes.position_manager import PositionManager
from tastyworksTaxes.constants import (
    TransactionCode,
    TransactionSubcode,
    OpenClose,
    Fields,
)
from tastyworksTaxes.trade_calculator import (
    calculate_combined_sum,
    calculate_option_sum,
    calculate_long_option_profits,
    calculate_long_option_losses,
    calculate_long_option_total_losses,
    calculate_short_option_profits,
    calculate_short_option_losses,
    calculate_option_differential,
    calculate_stock_loss,
    calculate_stock_fees,
    calculate_other_fees,
    calculate_fees_sum,
    get_stock_trades,
    calculate_gross_equity_etf_profits,
    calculate_equity_etf_profits,
    calculate_other_stock_and_bond_profits,
)
import logging
from datetime import date

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Tasty:
    def __init__(self, path=None):
        self.yearValues = {}
        self.history = History.fromFile(path) if path else History()
        self.position_manager = PositionManager()
        self.classifier = AssetClassifier()
        self.unverified_asset_symbols = set()

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
                if isinstance(desc, str) and "Wire Funds Received" in desc:
                    year_values.deposit += m
                elif isinstance(desc, str) and re.match(
                    r".*FROM \d{2}/\d{2} THRU \d{2}/\d{2} @.*", desc
                ):
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
            case "Special Dividend":
                # Tastytrade also uses this subcode for paired option/corporate-
                # action bookkeeping entries. Preserve their signed net amount;
                # treating the negative leg as withholding would create fictitious
                # dividend income and foreign tax.
                year_values.dividend += m
            case "Dividend":
                if m.usd < 0:
                    key = (t.loc["Date/Time"], t.getSymbol())
                    if key in getattr(self, "_withholding_dividend_keys", set()):
                        year_values.withholdingTax += -m
                    else:
                        year_values.paidDividend += m
                else:
                    year_values.dividend += m
            case "Fully Paid Stock Lending Income":
                year_values.securitiesLendingIncome += m
            case subcode:
                raise ValueError(
                    f"CRITICAL: Unknown money movement subcode '{subcode}' in transaction: {desc}. "
                    f"This could affect tax calculations."
                )

    def print(self):
        for key, value in self.yearValues.items():
            print("Year " + str(key) + ":")
            print(value)

    def processTransactionHistory(self):
        corporate_actions = self.history[Fields.TRANSACTION_SUBCODE.value].isin({
            TransactionSubcode.SYMBOL_CHANGE.value,
            TransactionSubcode.STOCK_MERGER.value,
            TransactionSubcode.SPECIAL_DIVIDEND.value,
        })
        close_legs = corporate_actions & (
            self.history[Fields.OPEN_CLOSE.value] == OpenClose.CLOSE.value
        )
        open_legs = corporate_actions & (
            self.history[Fields.OPEN_CLOSE.value] == OpenClose.OPEN.value
        )
        chronological_history = (
            self.history.assign(
                _corporate_action_order=close_legs.astype(int) * -1
                + open_legs.astype(int)
            )
            .sort_values(
                by=[Fields.DATE_TIME.value, "_corporate_action_order"],
                ascending=True,
                kind="stable",
            )
            .drop(columns="_corporate_action_order")
        )
        dividends = chronological_history[
            chronological_history[Fields.TRANSACTION_SUBCODE.value] == "Dividend"
        ]
        amounts = dividends.groupby(
            [Fields.DATE_TIME.value, Fields.SYMBOL.value]
        )[Fields.AMOUNT.value]
        self._withholding_dividend_keys = {
            key
            for key, values in amounts
            if (values > 0).any() and (values < 0).any()
        }
        for _, row in chronological_history.iterrows():
            transaction_code = row.loc["Transaction Code"]
            if transaction_code == TransactionCode.MONEY_MOVEMENT.value:
                self.moneyMovement(row)
            elif transaction_code in {
                TransactionCode.TRADE.value,
                TransactionCode.RECEIVE_DELIVER.value,
            }:
                self.position_manager.add_position(Transaction(row))

    def getYearlyTrades(self):
        if not self.position_manager.closed_trades:
            return {}

        from datetime import datetime
        from collections import defaultdict
        from tastyworksTaxes.position import PositionType

        def _parse_year(date_str):
            if isinstance(date_str, str):
                return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").year
            return date_str.year

        trades_by_year = defaultdict(list)
        for trade in self.position_manager.closed_trades:
            is_short_option = (
                trade.quantity < 0
                and trade.position_type in (PositionType.call, PositionType.put)
            )
            if is_short_option:
                year = _parse_year(trade.opening_date)
            else:
                year = _parse_year(trade.closing_date)
            trades_by_year[year].append(trade)

        return dict(trades_by_year)

    def _checkAssetClassifications(self, trades):
        stock_trades = get_stock_trades(trades)
        if not stock_trades:
            return

        checked = set()
        for trade in stock_trades:
            closing_date = date.fromisoformat(str(trade.closing_date)[:10])
            key = trade.symbol, closing_date
            if key in checked:
                continue
            checked.add(key)
            if not self.classifier.is_verified(
                trade.symbol, trade.position_type, closing_date
            ):
                self.unverified_asset_symbols.add(trade.symbol)
            self.classifier.check_unsupported_assets([trade.symbol], closing_date)

    def run(self):
        self.processTransactionHistory()

        trades_by_year = self.getYearlyTrades()
        fees = {
            year: -calculate_fees_sum(trades) for year, trades in trades_by_year.items()
        }

        years = set(self.yearValues.keys()) | set(trades_by_year.keys())

        for key in sorted(years):
            values_obj = self.year(key)
            m = Money()
            if key in fees:
                m.usd = fees[key].usd
                m.eur = fees[key].eur
            values_obj.fee += m

        ret = dict()
        for key in sorted(years):
            yearly_trades = trades_by_year.get(key, [])
            self._checkAssetClassifications(yearly_trades)
            values_obj = self.year(key)

            values_obj.stockAndOptionsSum = calculate_combined_sum(yearly_trades)
            values_obj.equityEtfGrossProfits = calculate_gross_equity_etf_profits(
                yearly_trades, self.classifier
            )
            values_obj.equityEtfProfits = calculate_equity_etf_profits(
                yearly_trades, self.classifier
            )
            values_obj.otherStockAndBondProfits = (
                calculate_other_stock_and_bond_profits(yearly_trades, self.classifier)
            )
            values_obj.stockAndEtfLosses = calculate_stock_loss(
                yearly_trades, self.classifier
            )

            values_obj.totalTaxableStockAndEtfProfits = Money(
                usd=values_obj.equityEtfProfits.usd
                + values_obj.otherStockAndBondProfits.usd,
                eur=values_obj.equityEtfProfits.eur
                + values_obj.otherStockAndBondProfits.eur,
            )

            values_obj.optionSum = calculate_option_sum(yearly_trades)
            values_obj.longOptionProfits = calculate_long_option_profits(yearly_trades)
            values_obj.longOptionLosses = calculate_long_option_losses(yearly_trades)
            values_obj.longOptionTotalLosses = calculate_long_option_total_losses(
                yearly_trades
            )
            values_obj.shortOptionProfits = calculate_short_option_profits(
                yearly_trades
            )
            values_obj.shortOptionLosses = calculate_short_option_losses(yearly_trades)
            values_obj.grossOptionDifferential = calculate_option_differential(
                yearly_trades
            )
            values_obj.stockFees = -calculate_stock_fees(yearly_trades)
            values_obj.otherFees = -calculate_other_fees(yearly_trades)

            values_obj.z21_termingeschaefsgewinne_stillhalter = Money(
                usd=values_obj.shortOptionProfits.usd + values_obj.longOptionProfits.usd,
                eur=values_obj.shortOptionProfits.eur + values_obj.longOptionProfits.eur,
            )
            values_obj.z24_termingeschaefte_verluste = Money(
                usd=values_obj.shortOptionLosses.usd
                + values_obj.longOptionLosses.usd
                + values_obj.longOptionTotalLosses.usd,
                eur=values_obj.shortOptionLosses.eur
                + values_obj.longOptionLosses.eur
                + values_obj.longOptionTotalLosses.eur,
            )

            ret[key] = values_obj

        return ret
