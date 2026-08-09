from tastyworksTaxes.values import Values
from tastyworksTaxes.transaction import Transaction
from tastyworksTaxes.money import Money
from tastyworksTaxes.history import History
from tastyworksTaxes.asset_classifier import AssetClassifier
from tastyworksTaxes.position_manager import PositionManager, OPTION_SETTLEMENT_FIELD
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.constants import (
    TransactionCode,
    TransactionSubcode,
    OpenClose,
    Fields,
)
from tastyworksTaxes.trade_calculator import (
    calculate_option_sum,
    calculate_long_option_profits,
    calculate_long_option_losses,
    calculate_long_option_total_losses,
    calculate_short_option_profits,
    calculate_short_option_losses,
    calculate_option_differential,
    calculate_stock_profits,
    calculate_stock_losses,
    calculate_fund_gross_profits,
    calculate_fund_profits,
    calculate_fund_losses,
    calculate_stock_fees,
    calculate_other_fees,
    calculate_fees_sum,
    get_stock_trades,
)
import copy
import logging
import math
from datetime import date, datetime

import pandas as pd

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Tasty:
    def __init__(self, path=None):
        self.yearValues = {}
        self.history = History.fromFile(path) if path else History()
        self.position_manager = PositionManager()
        self.classifier = AssetClassifier()
        self.unverified_asset_symbols_by_year = {}
        self.short_stock_trades_by_year = {}
        self._withholding_remaining = {}
        self._asset_classification_checks = set()

    def year(self, year):
        if year not in self.yearValues:
            self.yearValues[year] = Values()
        return self.yearValues[year]

    def _record_cash_dividend(self, transaction, money, year_values):
        pay_date = transaction.loc[Fields.DATE_TIME.value].date()
        symbol = transaction.getSymbol()
        self._checkAssetClassification(symbol, PositionType.stock, pay_date)

        if money.usd < 0:
            key = (transaction.getDate(), symbol)
            remaining = self._withholding_remaining.get(key, 0.0)
            negative_amount = -money.usd
            withholding_amount = min(negative_amount, remaining)
            withholding_ratio = withholding_amount / negative_amount
            year_values.withholdingTax += Money(
                usd=withholding_amount,
                eur=-money.eur * withholding_ratio,
            )
            year_values.paidDividend += Money(
                usd=-(negative_amount - withholding_amount),
                eur=money.eur * (1 - withholding_ratio),
            )
            self._withholding_remaining[key] = remaining - withholding_amount
            return

        classification = self.classifier.classify_for_tax(
            symbol, PositionType.stock, pay_date
        )
        if self.classifier.get_tax_category(classification) != "KAP-INV":
            year_values.dividend += money
            return

        exemption = self.classifier.get_exemption_percentage_for(
            symbol, PositionType.stock, pay_date
        ) / 100.0
        year_values.fundDistributions += money
        year_values.fundDistributionExempt += Money(
            usd=money.usd * exemption, eur=money.eur * exemption
        )
        year_values.fundDistributionTaxable += Money(
            usd=money.usd * (1 - exemption), eur=money.eur * (1 - exemption)
        )

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
                if t.isOption():
                    return
                self._record_cash_dividend(t, m, year_values)
            case "Dividend":
                self._record_cash_dividend(t, m, year_values)
            case "Fully Paid Stock Lending Income":
                year_values.securitiesLendingIncome += m
            case subcode:
                raise ValueError(
                    f"CRITICAL: Unknown money movement subcode '{subcode}' in transaction: {desc}. "
                    f"This could affect tax calculations."
                )

    def print(self):
        for key in sorted(self.yearValues):
            value = self.yearValues[key]
            print("Year " + str(key) + ":")
            print(value)

    def processTransactionHistory(self):
        manager = self.position_manager
        staged_manager = copy.deepcopy(manager)
        state_names = (
            "yearValues",
            "unverified_asset_symbols_by_year",
            "short_stock_trades_by_year",
            "_withholding_remaining",
            "_asset_classification_checks",
        )
        original_state = {name: getattr(self, name) for name in state_names}
        for name, value in original_state.items():
            setattr(self, name, copy.deepcopy(value))
        self.position_manager = staged_manager
        try:
            self._processTransactionHistory()
        except Exception:
            self.position_manager = manager
            for name, value in original_state.items():
                setattr(self, name, value)
            raise

        manager.__dict__.clear()
        manager.__dict__.update(staged_manager.__dict__)
        self.position_manager = manager

    def _processTransactionHistory(self):
        corporate_actions = self.history[Fields.TRANSACTION_SUBCODE.value].isin([
            TransactionSubcode.SYMBOL_CHANGE.value,
            TransactionSubcode.STOCK_MERGER.value,
            TransactionSubcode.SPECIAL_DIVIDEND.value,
        ])
        close_legs = corporate_actions & (
            self.history[Fields.OPEN_CLOSE.value] == OpenClose.CLOSE.value
        )
        open_legs = corporate_actions & (
            self.history[Fields.OPEN_CLOSE.value] == OpenClose.OPEN.value
        )
        receive_deliver = (
            self.history[Fields.TRANSACTION_CODE.value]
            == TransactionCode.RECEIVE_DELIVER.value
        )
        conversion_rows = self.history.loc[receive_deliver & corporate_actions]
        self.position_manager.validate_conversion_pairs(
            Transaction(row) for _, row in conversion_rows.iterrows()
        )
        physical_option_settlements = (
            receive_deliver
            & self.history[Fields.TRANSACTION_SUBCODE.value].isin([
                TransactionSubcode.EXERCISE.value,
                TransactionSubcode.ASSIGNMENT.value,
            ])
            & self.history[Fields.CALL_PUT.value].isin(["C", "P"])
        )
        stock_settlements = (
            receive_deliver
            & ~self.history[Fields.CALL_PUT.value].isin(["C", "P"])
            & self.history[Fields.TRANSACTION_SUBCODE.value].isin([
                TransactionSubcode.BUY_TO_OPEN.value,
                TransactionSubcode.SELL_TO_OPEN.value,
                TransactionSubcode.BUY_TO_CLOSE.value,
                TransactionSubcode.SELL_TO_CLOSE.value,
            ])
        )
        settlement_semantic = pd.Series("", index=self.history.index, dtype="object")
        option_groups = {}
        stock_groups = {}

        def settlement_number(value, field_name):
            try:
                number = abs(float(value))
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid option settlement {field_name}: {value!r}"
                ) from exc
            if not math.isfinite(number):
                raise ValueError(
                    f"Invalid option settlement {field_name}: {value!r}"
                )
            return round(number, 8)

        for index in range(len(self.history)):
            row = self.history.iloc[index]
            date_iso = str(row[Fields.DATE_TIME.value].date())
            if physical_option_settlements.iloc[index]:
                semantic = row[Fields.TRANSACTION_SUBCODE.value]
                call_put = row[Fields.CALL_PUT.value]
                if semantic == TransactionSubcode.EXERCISE.value:
                    direction = "buy" if call_put == "C" else "sell"
                else:
                    direction = "sell" if call_put == "C" else "buy"
                shares = settlement_number(
                    row[Fields.QUANTITY.value] * row[Fields.MULTIPLIER.value],
                    "share quantity",
                )
                notional = settlement_number(
                    row[Fields.STRIKE.value] * shares, "notional"
                )
                underlying = str(row[Fields.UNDERLYING_SYMBOL.value]).strip()
                key = (date_iso, underlying, direction, shares, notional)
                option_groups.setdefault(key, []).append((index, semantic))
                continue

            if not stock_settlements.iloc[index]:
                continue
            direction = str(row[Fields.BUY_SELL.value]).lower()
            shares = settlement_number(row[Fields.QUANTITY.value], "share quantity")
            notional = settlement_number(row[Fields.AMOUNT.value], "notional")
            symbol = str(row[Fields.SYMBOL.value]).strip()
            key = (date_iso, symbol, direction, shares, notional)
            stock_groups.setdefault(key, []).append(index)

        processing_datetime = self.history[Fields.DATE_TIME.value].copy()
        for key, option_entries in option_groups.items():
            stock_indices = stock_groups.get(key, [])
            if len(stock_indices) != len(option_entries):
                raise ValueError(
                    "UNMATCHED OPTION SETTLEMENT: option and stock delivery legs "
                    "do not have a unique quantity/notional match"
                )
            semantics = {semantic for _, semantic in option_entries}
            if len(semantics) != 1:
                raise ValueError(
                    "AMBIGUOUS OPTION SETTLEMENT: Exercise and Assignment share "
                    "the same date, symbol, direction, quantity, and notional"
                )
            semantic = next(iter(semantics))
            anchor = max(
                self.history.iloc[index][Fields.DATE_TIME.value]
                for index, _ in option_entries
            )
            for stock_index in stock_indices:
                settlement_semantic.iloc[stock_index] = semantic
                if processing_datetime.iloc[stock_index] < anchor:
                    processing_datetime.iloc[stock_index] = anchor

        settlement_order = physical_option_settlements.astype(int) * -1
        settlement_order += stock_settlements.astype(int)
        chronological_history = (
            self.history.assign(
                _corporate_action_order=close_legs.astype(int) * -1
                + open_legs.astype(int),
                _processing_datetime=processing_datetime,
                _settlement_order=settlement_order,
                **{OPTION_SETTLEMENT_FIELD: settlement_semantic},
            )
            .sort_values(
                by=[
                    "_processing_datetime",
                    "_settlement_order",
                    "_corporate_action_order",
                ],
                ascending=True,
                kind="stable",
            )
            .drop(columns=[
                "_corporate_action_order",
                "_processing_datetime",
                "_settlement_order",
            ])
        )
        cash_dividend_rows = (
            chronological_history[Fields.TRANSACTION_SUBCODE.value]
            == "Dividend"
        ) | (
            (
                chronological_history[Fields.TRANSACTION_SUBCODE.value]
                == TransactionSubcode.SPECIAL_DIVIDEND.value
            )
            & ~chronological_history[Fields.CALL_PUT.value].isin(["C", "P"])
        )
        dividends = chronological_history.loc[cash_dividend_rows]
        dividend_dates = dividends[Fields.DATE_TIME.value].dt.date.astype(str)
        amounts = dividends.assign(_pay_date=dividend_dates).groupby(
            ["_pay_date", Fields.SYMBOL.value]
        )[Fields.AMOUNT.value]
        self._withholding_remaining = {
            key: min(values[values > 0].sum(), -values[values < 0].sum())
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
        self.position_manager.validate_no_pending_adjustments()

    def getYearlyTrades(self):
        if not self.position_manager.closed_trades:
            return {}

        from datetime import datetime
        from collections import defaultdict
        from tastyworksTaxes.position import PositionType
        from tastyworksTaxes.fifo_processor import TradeResult

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
                open_year = _parse_year(trade.opening_date)
                close_year = _parse_year(trade.closing_date)
                if open_year != close_year:
                    opening_leg = TradeResult(
                        symbol=trade.symbol,
                        position_type=trade.position_type,
                        opening_date=trade.opening_date,
                        closing_date=trade.opening_date,
                        quantity=trade.quantity,
                        profit_usd=trade.opening_profit_usd,
                        profit_eur=trade.opening_profit_eur,
                        fees_usd=trade.opening_fees_usd,
                        fees_eur=trade.opening_fees_eur,
                        worthless_expiry=False,
                        strike=trade.strike,
                        expiry=trade.expiry,
                    )
                    closing_leg = TradeResult(
                        symbol=trade.symbol,
                        position_type=trade.position_type,
                        opening_date=trade.closing_date,
                        closing_date=trade.closing_date,
                        quantity=trade.quantity,
                        profit_usd=trade.closing_profit_usd,
                        profit_eur=trade.closing_profit_eur,
                        fees_usd=trade.closing_fees_usd,
                        fees_eur=trade.closing_fees_eur,
                        worthless_expiry=False,
                        strike=trade.strike,
                        expiry=trade.expiry,
                    )
                    trades_by_year[open_year].append(opening_leg)
                    trades_by_year[close_year].append(closing_leg)
                else:
                    trades_by_year[open_year].append(trade)
            else:
                year = _parse_year(trade.closing_date)
                trades_by_year[year].append(trade)

        return dict(trades_by_year)

    @staticmethod
    def _as_date(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value)[:10])

    def _checkAssetClassification(self, symbol, position_type, operation_date):
        operation_date = self._as_date(operation_date)
        if not self.classifier.is_verified(symbol, position_type, operation_date):
            self.unverified_asset_symbols_by_year.setdefault(
                operation_date.year, set()
            ).add(symbol)

        warning_state = self.classifier.unsupported_asset_state(symbol, operation_date)
        key = symbol, position_type, operation_date.year, warning_state
        if warning_state is None or key in self._asset_classification_checks:
            return
        self._asset_classification_checks.add(key)
        self.classifier.check_unsupported_assets([symbol], operation_date)

    def _stockHoldingPeriods(self):
        periods = [
            (
                trade.symbol,
                self._as_date(trade.opening_date),
                self._as_date(trade.closing_date),
            )
            for trade in self.position_manager.closed_trades
            if trade.position_type == PositionType.stock
        ]

        open_stock_lots = [
            lot for lot in self.position_manager.get_all_open_lots()
            if lot.position_type == PositionType.stock and not lot.is_empty()
        ]
        known_dates = [period_date for _, start, end in periods for period_date in (start, end)]
        known_dates.extend(self._as_date(lot.date) for lot in open_stock_lots)
        if not self.history.empty and Fields.DATE_TIME.value in self.history:
            history_dates = self.history[Fields.DATE_TIME.value].dropna()
            if not history_dates.empty:
                known_dates.append(self._as_date(history_dates.max()))
        if self.yearValues:
            known_dates.append(date(max(self.yearValues), 12, 31))

        scope_end = max(known_dates) if known_dates else None
        if scope_end is not None:
            periods.extend(
                (lot.symbol, self._as_date(lot.date), scope_end)
                for lot in open_stock_lots
            )
        return periods

    def _checkStockHoldingClassifications(self):
        exposure_years = set()
        for symbol, acquired, disposed_or_scope_end in self._stockHoldingPeriods():
            if disposed_or_scope_end < acquired:
                continue
            for year in range(acquired.year, disposed_or_scope_end.year + 1):
                exposure_years.add(year)
                period_start = max(acquired, date(year, 1, 1))
                period_end = min(disposed_or_scope_end, date(year, 12, 31))
                for checkpoint in self.classifier.effective_checkpoints(
                    symbol, period_start, period_end
                ):
                    self._checkAssetClassification(
                        symbol, PositionType.stock, checkpoint
                    )
        return exposure_years

    def _checkAssetClassifications(self, trades):
        stock_trades = get_stock_trades(trades)
        if not stock_trades:
            return

        for trade in stock_trades:
            self._checkAssetClassification(
                trade.symbol, trade.position_type, trade.closing_date
            )

    def run(self):
        self.unverified_asset_symbols_by_year = {}
        self.short_stock_trades_by_year = {}
        self._asset_classification_checks = set()
        self.processTransactionHistory()

        trades_by_year = self.getYearlyTrades()
        self.short_stock_trades_by_year = {
            year: [
                trade
                for trade in trades
                if trade.position_type == PositionType.stock and trade.quantity < 0
            ]
            for year, trades in trades_by_year.items()
            if any(
                trade.position_type == PositionType.stock and trade.quantity < 0
                for trade in trades
            )
        }
        fees = {
            year: -calculate_fees_sum(trades) for year, trades in trades_by_year.items()
        }

        holding_years = self._checkStockHoldingClassifications()
        years = (
            set(self.yearValues.keys())
            | set(trades_by_year.keys())
            | holding_years
            | set(self.unverified_asset_symbols_by_year.keys())
        )

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

            values_obj.stockProfits = calculate_stock_profits(
                yearly_trades, self.classifier
            )
            values_obj.stockLosses = calculate_stock_losses(
                yearly_trades, self.classifier
            )
            values_obj.fundGrossProfits = calculate_fund_gross_profits(
                yearly_trades, self.classifier
            )
            values_obj.fundProfits = calculate_fund_profits(
                yearly_trades, self.classifier
            )
            values_obj.fundLosses = calculate_fund_losses(
                yearly_trades, self.classifier
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
            values_obj.optionDifferential = calculate_option_differential(
                yearly_trades
            )
            values_obj.stockFees = -calculate_stock_fees(yearly_trades)
            values_obj.otherFees = -calculate_other_fees(yearly_trades)

            values_obj.z21_termingeschaefsgewinne = Money(
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
