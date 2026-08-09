"""
Position Manager for German Tax Calculation (§ 20 EStG)

German Tax Treatment of Option Assignments:
===========================================

This implementation follows German tax law (§ 20 EStG - Income Tax Act) for the treatment
of physically settled option assignments, which differs fundamentally from US tax treatment.

Legal Framework:

1. SHORT OPTIONS (Stillhalter - Premium Seller):
   § 20 Abs. 1 Nr. 11 EStG: "Premiums for granting options (Stillhalterprämien)"

   BMF-Schreiben vom 18.01.2016, Az. IV C 1 – S 2252/08/10004 :017:
   - Short call assigned: Rz. 26
   - Short put assigned: Rz. 33
   The Stillhalter premium remains separate income and is excluded from the share gain.

   BFH vom 20.10.2016, Az. VIII R 55/13, BStBl II 2017, 264:
   "Der Tatbestand des § 20 Abs. 1 Nr. 11 EStG ist mit dem Zufluss der Prämie verwirklicht."

   This separate treatment applies ONLY to SHORT (Stillhalter) options: their premium
   does not adjust the stock cost basis or proceeds.

2. LONG OPTIONS (Inhaber - Premium Buyer):
   § 20 Abs. 4 Satz 1 EStG: Cost basis calculation

   BMF-Schreiben vom 18.01.2016:
   - Long call exercised: Rz. 22; premium increases Anschaffungskosten.
   - Long put exercised: Rz. 29; premium reduces Veräußerungserlös.

Implementation:
- Short option assignments: Close option normally → premium as separate income (§ 20 Abs. 1 Nr. 11)
- Stock from assignment: Booked at strike price (§ 20 Abs. 2 Nr. 1)
- No premium integration for short assignments (unlike US tax treatment)
- Long option exercise: Premium integrated into stock cost/proceeds (BMF Rz. 22/29)
"""

import logging
import math
import re
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
import csv
from importlib.resources import files
from tastyworksTaxes.position_lot import PositionLot
from tastyworksTaxes.constants import (
    TransactionSubcode,
    TransactionCode,
    OpenClose,
    Fields,
    CLOSING_SUBCODES,
)
from tastyworksTaxes.fifo_processor import FifoProcessor
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.money import Money

logger = logging.getLogger(__name__)
OPTION_SETTLEMENT_FIELD = "_Option Settlement"
ACTUAL_DELIVERED_SHARES_FIELD = "_Actual Delivered Shares"


@dataclass(frozen=True)
class InstrumentKey:
    """Immutable key for uniquely identifying an instrument"""

    symbol: str
    position_type: PositionType
    strike: float | None = None
    expiry: datetime | None = None
    call_put: str | None = None


@dataclass
class PendingExercise:
    """Unmatched physical-delivery premium, consumed in share FIFO order."""

    date_iso: str
    symbol: str
    direction: str
    remaining_shares: float
    per_share_amount_usd: float
    per_share_amount_eur: float
    per_share_fees_usd: float
    per_share_fees_eur: float


class PositionManager:
    def __init__(self):
        self.open_lots: dict[InstrumentKey, deque[PositionLot]] = defaultdict(deque)
        self.closed_trades = []
        self._corporate_actions_config = self._load_corporate_actions_config()
        self._pending_symbol_change_lots: dict[tuple, list[PositionLot]] = {}
        self._pending_special_dividend_lots: dict[tuple, list[PositionLot]] = {}
        self._pending_exercises: dict[
            tuple[str, str, str], deque[PendingExercise]
        ] = defaultdict(deque)

    @staticmethod
    def _load_corporate_actions_config() -> dict:
        """Load and validate the packaged corporate-action configuration."""
        try:
            config_resource = files("tastyworksTaxes").joinpath(
                "corporate_actions.csv"
            )
            with config_resource.open("r", encoding="utf-8") as source:
                lines = [
                    line
                    for line in source
                    if line.strip() and not line.lstrip().startswith("#")
                ]
        except (FileNotFoundError, ModuleNotFoundError, OSError) as exc:
            raise ValueError(
                "Corporate actions configuration is unavailable"
            ) from exc

        try:
            reader = csv.DictReader(lines, strict=True)
            if reader.fieldnames != ["date", "symbol", "ratio", "source"]:
                raise ValueError

            splits = []
            configured_events = set()
            for row in reader:
                if set(row) != {"date", "symbol", "ratio", "source"}:
                    raise ValueError
                event_date = row["date"].strip()
                symbol = row["symbol"].strip()
                source = row["source"].strip()
                parsed_date = datetime.strptime(event_date, "%Y-%m-%d")
                if parsed_date.strftime("%Y-%m-%d") != event_date:
                    raise ValueError
                if not symbol or not source:
                    raise ValueError
                ratio = float(row["ratio"])
                if not math.isfinite(ratio) or ratio <= 0:
                    raise ValueError
                event = event_date, symbol
                if event in configured_events:
                    raise ValueError
                configured_events.add(event)
                splits.append(
                    {
                        "date": event_date,
                        "symbol": symbol,
                        "ratio": ratio,
                        "source": source,
                    }
                )
        except (csv.Error, KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                "Corporate actions configuration is invalid"
            ) from exc

        return {"reverse_splits": splits}

    def reset_calculation_state(self) -> None:
        """Clear derived position state while preserving validated configuration."""
        self.open_lots = defaultdict(deque)
        self.closed_trades = []
        self._pending_symbol_change_lots = {}
        self._pending_special_dividend_lots = {}
        self._pending_exercises = defaultdict(deque)

    @staticmethod
    def _absolute_datetime(transaction):
        absolute_time = transaction.get("_Absolute Date/Time")
        if absolute_time is None or absolute_time != absolute_time:
            raise ValueError("Absolute transaction timestamp is required")
        return absolute_time

    @classmethod
    def _absolute_date(cls, transaction) -> str:
        absolute_time = cls._absolute_datetime(transaction)
        if hasattr(absolute_time, "date"):
            return str(absolute_time.date())
        return str(absolute_time)[:10]

    def _get_reverse_split_ratio_from_config(
        self, symbol: str, date: datetime
    ) -> float | None:
        """
        Look up reverse split ratio from config file.

        Args:
            symbol: Stock/option symbol
            date: Transaction date

        Returns:
            Ratio if found in config, None otherwise
        """
        reverse_splits = self._corporate_actions_config.get("reverse_splits", [])
        date_str = (
            date.strftime("%Y-%m-%d") if isinstance(date, datetime) else str(date)[:10]
        )

        for split in reverse_splits:
            if split.get("symbol") == symbol and split.get("date") == date_str:
                ratio = split.get("ratio")
                logger.info("Using configured corporate action")
                return float(ratio)

        return None

    def _get_key_from_transaction(self, transaction) -> InstrumentKey:
        """Generate InstrumentKey from transaction for O(1) lot lookup"""
        position_type = transaction.getType()
        if position_type == PositionType.stock:
            return InstrumentKey(
                transaction.getSymbol(), position_type, None, None, None
            )
        return InstrumentKey(
            transaction.getSymbol(),
            position_type,
            transaction.getStrike(),
            transaction.getExpiry(),
            transaction.loc[Fields.CALL_PUT.value],
        )

    def get_all_open_lots(self) -> list[PositionLot]:
        """Return flat list of all open lots (for testing/debugging)"""
        all_lots = []
        for lots_queue in self.open_lots.values():
            all_lots.extend(lots_queue)
        return sorted(all_lots, key=lambda x: x.date)

    def add_lot_directly(self, lot: PositionLot):
        """Add a lot directly to open_lots (for testing only)"""
        key = InstrumentKey(
            lot.symbol, lot.position_type, lot.strike, lot.expiry, lot.call_put
        )
        self.open_lots[key].append(lot)

    def validate_conversion_pairs(self, transactions):
        """Fail before processing if conversion legs cannot be paired uniquely."""
        pairs = defaultdict(lambda: {OpenClose.CLOSE.value: 0, OpenClose.OPEN.value: 0})
        for transaction in transactions:
            open_close = transaction.get(Fields.OPEN_CLOSE.value, "")
            if open_close not in {OpenClose.CLOSE.value, OpenClose.OPEN.value}:
                raise ValueError(
                    "Corporate action requires an explicit Open/Close operation"
                )
            quantity = abs(float(transaction.getQuantity()))
            if not math.isfinite(quantity) or quantity <= 1e-6:
                raise ValueError(
                    "Corporate action requires a finite nonzero quantity; "
                    "zero-quantity basis or cash rows cannot be allocated safely"
                )
            pairs[self._get_conversion_key(transaction)][open_close] += 1

        for key, counts in pairs.items():
            if counts == {OpenClose.CLOSE.value: 1, OpenClose.OPEN.value: 1}:
                continue
            raise ValueError(
                "AMBIGUOUS OR UNMATCHED CORPORATE ACTION: expected exactly one "
                f"close and one open leg for {key!r}, found {counts!r}"
            )

    def add_position(self, transaction):
        subcode = transaction[Fields.TRANSACTION_SUBCODE.value]

        if subcode in {
            TransactionSubcode.SYMBOL_CHANGE.value,
            TransactionSubcode.STOCK_MERGER.value,
            TransactionSubcode.SPECIAL_DIVIDEND.value,
        }:
            quantity = abs(float(transaction.getQuantity()))
            if not math.isfinite(quantity) or quantity <= 1e-6:
                raise ValueError(
                    f"Corporate action '{subcode}' requires a finite nonzero quantity; "
                    "zero-quantity basis or cash rows cannot be allocated safely"
                )
            key = self._get_key_from_transaction(transaction)
            open_close = transaction.get(Fields.OPEN_CLOSE.value, "")
            if open_close == OpenClose.CLOSE.value:
                is_conversion_close = True
            elif open_close == OpenClose.OPEN.value:
                is_conversion_close = False
            else:
                conversion_key = self._get_conversion_key(transaction)
                is_conversion_close = (
                    conversion_key not in self._pending_symbol_change_lots
                    and not self._pending_special_dividend_lots.get(conversion_key)
                    and any(
                        lot.can_close_with(transaction.getQuantity())
                        for lot in self.open_lots.get(key, ())
                    )
                )
            if is_conversion_close:
                self._close_position_for_symbol_change(transaction)

            else:
                self._open_position_from_symbol_change(transaction)

            return

        if subcode == TransactionSubcode.REVERSE_SPLIT.value:
            if self._handle_reverse_split(transaction):
                return

        if self._is_closing_transaction(transaction):
            self._close_position(transaction)
        else:
            self._open_position(transaction)

    def _is_closing_transaction(self, transaction):
        subcode = transaction[Fields.TRANSACTION_SUBCODE.value]
        open_close = transaction.get(Fields.OPEN_CLOSE.value, "")
        return subcode in CLOSING_SUBCODES or open_close == OpenClose.CLOSE.value

    @classmethod
    def _get_conversion_key(cls, transaction) -> tuple:
        """Identify one broker conversion pair without trusting replacement basis."""
        position_type = transaction.getType()
        event = transaction[Fields.TRANSACTION_SUBCODE.value]
        event_time = cls._absolute_datetime(transaction)
        if position_type == PositionType.stock:
            return event, event_time, position_type

        quantity = abs(float(transaction.getQuantity()))
        if not math.isfinite(quantity):
            raise ValueError("Corporate action quantity must be finite")
        return (
            event,
            event_time,
            position_type,
            transaction.getExpiry(),
            transaction.loc[Fields.CALL_PUT.value],
            quantity,
        )

    def _open_position(self, transaction):
        logger.info("Opened position")

        lot = PositionLot(
            symbol=transaction.getSymbol(),
            position_type=transaction.getType(),
            quantity=transaction.getQuantity(),
            amount_usd=transaction.getValue().usd,
            amount_eur=transaction.getValue().eur,
            fees_usd=transaction.getFees().usd,
            fees_eur=transaction.getFees().eur,
            date=transaction.loc[Fields.DATE_TIME.value],
            strike=transaction.getStrike()
            if transaction.getType().name != "stock"
            else None,
            expiry=transaction.getExpiry()
            if transaction.getType().name != "stock"
            else None,
            call_put=transaction.loc[Fields.CALL_PUT.value]
            if transaction.getType().name != "stock"
            else None,
        )

        if (
            lot.position_type == PositionType.stock
            and transaction[Fields.TRANSACTION_CODE.value]
            == TransactionCode.RECEIVE_DELIVER.value
            and transaction.get(OPTION_SETTLEMENT_FIELD)
            == TransactionSubcode.EXERCISE.value
        ):
            direction = "buy" if lot.quantity > 0 else "sell"
            adjustment, exercise_fees = self._consume_pending_exercise(
                self._absolute_date(transaction),
                lot.symbol,
                direction,
                abs(lot.quantity),
            )
            if adjustment.usd or adjustment.eur or exercise_fees.usd or exercise_fees.eur:
                # The paid option premium is a negative signed cash flow for every
                # resulting stock lifecycle: buy/sell and open/close alike.
                lot.amount_usd += adjustment.usd
                lot.amount_eur += adjustment.eur
                lot.fees_usd += exercise_fees.usd
                lot.fees_eur += exercise_fees.eur
                logger.info("Applied option exercise adjustment")

        key = self._get_key_from_transaction(transaction)
        self.open_lots[key].append(lot)

    def _open_position_from_symbol_change(self, transaction):
        conversion_key = self._get_conversion_key(transaction)
        if (
            transaction[Fields.TRANSACTION_SUBCODE.value]
            == TransactionSubcode.SPECIAL_DIVIDEND.value
        ):
            old_lots = self._pending_special_dividend_lots.pop(
                conversion_key, None
            )
        else:
            old_lots = self._pending_symbol_change_lots.pop(conversion_key, None)
        if not old_lots:
            raise ValueError(
                f"Corporate action open leg for {transaction.getSymbol()} has no "
                "unique matching close leg; refusing replacement CSV basis"
            )

        key = self._get_key_from_transaction(transaction)
        total_old_quantity = sum(abs(lot.quantity) for lot in old_lots)
        new_quantity = transaction.getQuantity()
        for old_lot in old_lots:
            quantity = abs(new_quantity) * abs(old_lot.quantity) / total_old_quantity
            lot = PositionLot(
                symbol=transaction.getSymbol(), position_type=transaction.getType(),
                quantity=quantity if new_quantity >= 0 else -quantity,
                amount_usd=old_lot.amount_usd, amount_eur=old_lot.amount_eur,
                fees_usd=old_lot.fees_usd, fees_eur=old_lot.fees_eur, date=old_lot.date,
                strike=transaction.getStrike() if transaction.getType() != PositionType.stock else None,
                expiry=transaction.getExpiry() if transaction.getType() != PositionType.stock else None,
                call_put=transaction.loc[Fields.CALL_PUT.value] if transaction.getType() != PositionType.stock else None,
            )
            self.open_lots[key].append(lot)
            logger.debug("Applied corporate action")

    def _close_position_for_symbol_change(self, transaction):
        """Move the requested FIFO slices to the pending conversion buffer."""
        conversion_key = self._get_conversion_key(transaction)
        is_special_dividend = (
            transaction[Fields.TRANSACTION_SUBCODE.value]
            == TransactionSubcode.SPECIAL_DIVIDEND.value
        )
        pending_store = (
            self._pending_special_dividend_lots
            if is_special_dividend
            else self._pending_symbol_change_lots
        )
        if conversion_key in pending_store:
            raise ValueError(
                "AMBIGUOUS CORPORATE ACTION: multiple close legs share the same "
                "event time, type, and stable instrument fields"
            )

        key = self._get_key_from_transaction(transaction)
        matching_lots = self.open_lots.get(key)
        if not matching_lots:
            raise ValueError(f"Symbol Change 'close' leg for {transaction.getSymbol()} found no open position to mutate.")

        quantity_to_move = abs(transaction.getQuantity())
        closing_quantity = transaction.getQuantity()
        candidates = [lot for lot in matching_lots if lot.can_close_with(closing_quantity)]
        if sum(abs(lot.quantity) for lot in candidates) + 1e-6 < quantity_to_move:
            raise ValueError(f"Tried to convert more shares than available for {transaction.getSymbol()}")

        pending, remaining = [], deque()
        for lot in matching_lots:
            if quantity_to_move > 1e-6 and lot.can_close_with(closing_quantity):
                quantity = lot.get_closable_quantity(quantity_to_move)
                new_lot, values = lot.consume(quantity)
                pending.append(PositionLot(
                    symbol=lot.symbol, position_type=lot.position_type, quantity=lot.quantity - new_lot.quantity,
                    amount_usd=values[Fields.AMOUNT.value], amount_eur=values[Fields.AMOUNT_EURO.value],
                    fees_usd=values[Fields.FEES.value], fees_eur=values[Fields.FEES_EURO.value], date=lot.date,
                    strike=lot.strike, expiry=lot.expiry, call_put=lot.call_put,
                ))
                quantity_to_move -= quantity
                if not new_lot.is_empty():
                    remaining.append(new_lot)
            else:
                remaining.append(lot)
        if remaining:
            self.open_lots[key] = remaining
        else:
            del self.open_lots[key]
        pending_store[conversion_key] = pending

    def _close_position(self, transaction):
        """
        Close position using FIFO method.

        GERMAN TAX LAW - OPTION ASSIGNMENTS (§ 20 EStG):

        Short call assignments follow BMF 18.01.2016 Rz. 26 and short put
        assignments follow Rz. 33: the Stillhalter premium remains separate
        § 20 Abs. 1 Nr. 11 EStG income and is excluded from the share gain.

        A long call exercise follows Rz. 22: the paid premium increases the
        delivered shares' Anschaffungskosten. A long put exercise follows Rz. 29:
        the premium reduces the delivered shares' Veräußerungserlös. Tastytrade
        should use the explicit "Exercise" subcode. "Assignment" is also accepted
        as physical exercise only when the consumed option lot is long.

        BFH 20.10.2016 – VIII R 55/13 remains applicable to Stillhalter premiums.
        """
        quantity_to_close = abs(transaction.getQuantity())
        closing_quantity = transaction.getQuantity()

        key = self._get_key_from_transaction(transaction)
        matching_lots = self.open_lots.get(key)

        if not matching_lots:
            raise ValueError(
                f"Tried to close a position but no previous position found for {transaction}"
            )

        subcode = transaction[Fields.TRANSACTION_SUBCODE.value]

        def can_consume(lot):
            if subcode == TransactionSubcode.ASSIGNMENT.value:
                return lot.quantity < 0
            if subcode == TransactionSubcode.EXERCISE.value:
                return lot.quantity > 0
            if subcode == TransactionSubcode.EXPIRATION.value:
                return True
            return lot.can_close_with(closing_quantity)

        candidates = [lot for lot in matching_lots if can_consume(lot)]
        if sum(abs(lot.quantity) for lot in candidates) + 1e-6 < quantity_to_close:
            if subcode == TransactionSubcode.ASSIGNMENT.value:
                raise ValueError("ASSIGNMENT REQUIRES SUFFICIENT SHORT OPTION LOTS")
            if subcode == TransactionSubcode.EXERCISE.value:
                raise ValueError("EXERCISE REQUIRES SUFFICIENT LONG OPTION LOTS")
            raise ValueError(f"Tried to close more shares than available for {transaction.getSymbol()}")

        exercise_shares_per_contract = None
        if subcode == TransactionSubcode.EXERCISE.value:
            multiplier_value = transaction.get(Fields.MULTIPLIER.value, 100)
            delivered_value = transaction.get(ACTUAL_DELIVERED_SHARES_FIELD)
            try:
                multiplier = abs(float(multiplier_value))
                delivered_shares = abs(float(delivered_value))
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "Exercise requires valid multiplier and matched delivered shares"
                ) from exc
            if (
                not math.isfinite(multiplier)
                or multiplier <= 0
                or not math.isfinite(delivered_shares)
                or delivered_shares <= 0
            ):
                raise ValueError(
                    "Exercise requires valid multiplier and matched delivered shares"
                )
            exercise_shares_per_contract = delivered_shares / quantity_to_close

        closing_transaction = transaction
        pending_adjustment = Money()
        pending_exercise_fees = Money()
        is_exercise_stock_delivery = (
            transaction.getType() == PositionType.stock
            and transaction[Fields.TRANSACTION_CODE.value]
            == TransactionCode.RECEIVE_DELIVER.value
            and transaction.get(OPTION_SETTLEMENT_FIELD)
            == TransactionSubcode.EXERCISE.value
        )
        if is_exercise_stock_delivery:
            direction = "sell" if closing_quantity < 0 else "buy"
            pending_adjustment, pending_exercise_fees = self._consume_pending_exercise(
                self._absolute_date(transaction),
                transaction.getSymbol(),
                direction,
                quantity_to_close,
            )
            if (
                pending_adjustment.usd
                or pending_adjustment.eur
                or pending_exercise_fees.usd
                or pending_exercise_fees.eur
            ):
                closing_transaction = type(transaction)(transaction.copy())
                closing_transaction.setValue(
                    transaction.getValue() + pending_adjustment
                )
                closing_transaction.setFees(
                    transaction.getFees() + pending_exercise_fees
                )

        # Validate the full close before mutating lots or creating trade results.
        remaining_lots = deque()
        while matching_lots:
            lot_to_process = matching_lots.popleft()
            if quantity_to_close <= 1e-6 or not can_consume(lot_to_process):
                remaining_lots.append(lot_to_process)
                continue

            closable_quantity = lot_to_process.get_closable_quantity(quantity_to_close)

            opening_was_long = lot_to_process.quantity > 0
            lot_before = f"{lot_to_process.quantity} @ {lot_to_process.amount_usd:.2f}"

            new_lot, consumed_values = lot_to_process.consume(closable_quantity)

            lot_after = (
                f"{new_lot.quantity} @ {new_lot.amount_usd:.2f}"
                if not new_lot.is_empty()
                else "empty"
            )

            trade_result = FifoProcessor.create_trade_result(
                lot_to_process,
                closing_transaction,
                closable_quantity,
                consumed_values,
                opening_was_long,
            )

            is_long_physical_exercise = (
                opening_was_long
                and lot_to_process.position_type in (PositionType.call, PositionType.put)
                and subcode == TransactionSubcode.EXERCISE.value
            )
            if is_long_physical_exercise:
                option_amount = Money(
                    usd=trade_result.opening_profit_usd + trade_result.closing_profit_usd,
                    eur=trade_result.opening_profit_eur + trade_result.closing_profit_eur,
                )
                option_fees = Money(
                    usd=trade_result.fees_usd,
                    eur=trade_result.fees_eur,
                )
                underlying_value = transaction.get(Fields.UNDERLYING_SYMBOL.value)
                underlying = str(underlying_value).strip()
                if not underlying or underlying.lower() == "nan":
                    underlying = transaction.getSymbol()
                shares = closable_quantity * exercise_shares_per_contract
                direction = (
                    "buy" if lot_to_process.position_type == PositionType.call else "sell"
                )
                exercise_key = (self._absolute_date(transaction), underlying, direction)
                self._pending_exercises[exercise_key].append(PendingExercise(
                    date_iso=exercise_key[0],
                    symbol=underlying,
                    direction=direction,
                    remaining_shares=shares,
                    per_share_amount_usd=option_amount.usd / shares,
                    per_share_amount_eur=option_amount.eur / shares,
                    per_share_fees_usd=option_fees.usd / shares,
                    per_share_fees_eur=option_fees.eur / shares,
                ))
                trade_result.settled_by_exercise = True
                trade_result.profit_usd = 0.0
                trade_result.profit_eur = 0.0
                trade_result.fees_usd = 0.0
                trade_result.fees_eur = 0.0
                trade_result.opening_fees_usd = 0.0
                trade_result.opening_fees_eur = 0.0
                trade_result.closing_fees_usd = 0.0
                trade_result.closing_fees_eur = 0.0
                logger.info("Recorded option exercise adjustment")
            self.closed_trades.append(trade_result)

            logger.info("Closed position")
            logger.debug("Consumed position lot")

            if not new_lot.is_empty():
                remaining_lots.append(new_lot)

            quantity_to_close -= closable_quantity

        if remaining_lots:
            self.open_lots[key] = remaining_lots
        else:
            del self.open_lots[key]

        if pending_adjustment.usd or pending_adjustment.eur:
            logger.info("Applied option exercise adjustment")

    def _consume_pending_exercise(
        self,
        date_iso: str,
        symbol: str,
        direction: str,
        stock_shares: float,
    ) -> tuple[Money, Money]:
        """Consume matching signed cash and fees by share quantity in FIFO order."""
        exercise_key = (date_iso, symbol, direction)
        pending = self._pending_exercises.get(exercise_key)
        adjustment = Money()
        fees = Money()
        shares_left = abs(stock_shares)
        if not pending:
            return adjustment, fees

        available = sum(entry.remaining_shares for entry in pending)
        if available + 1e-6 < shares_left:
            raise ValueError(
                "PARTIAL EXERCISE ADJUSTMENT: stock delivery exceeds the matching "
                f"exercised-option shares ({shares_left} > {available})"
            )

        while pending and shares_left > 1e-6:
            entry = pending[0]
            consumed_shares = min(entry.remaining_shares, shares_left)
            adjustment.usd += consumed_shares * entry.per_share_amount_usd
            adjustment.eur += consumed_shares * entry.per_share_amount_eur
            fees.usd += consumed_shares * entry.per_share_fees_usd
            fees.eur += consumed_shares * entry.per_share_fees_eur
            entry.remaining_shares -= consumed_shares
            shares_left -= consumed_shares
            if entry.remaining_shares <= 1e-6:
                pending.popleft()
        if not pending:
            del self._pending_exercises[exercise_key]
        return adjustment, fees

    def validate_no_pending_adjustments(self):
        """Fail before reporting if any basis/proceeds transfer is incomplete."""
        if self._pending_symbol_change_lots or self._pending_special_dividend_lots:
            raise ValueError(
                "UNMATCHED CORPORATE ACTION: a close leg has no unique open leg"
            )
        if self._pending_exercises:
            remaining = sum(
                entry.remaining_shares
                for pending in self._pending_exercises.values()
                for entry in pending
            )
            raise ValueError(
                "UNMATCHED EXERCISE ADJUSTMENT: no complete paired stock delivery "
                f"for {remaining} shares"
            )

    def _handle_reverse_split(self, transaction):
        description = str(transaction.loc[Fields.DESCRIPTION.value])

        # Tastytrade represents option reverse splits as paired Close/Open records.
        declared_option = transaction.get(Fields.CALL_PUT.value, "") in {"C", "P"}
        option_text = f"{transaction.getSymbol()} {description}"
        has_occ_token = re.search(
            r"(?<!\d)\d{6}[CP]\d{8}(?!\d)", option_text, re.IGNORECASE
        ) is not None
        try:
            resolved_type = transaction.getType()
        except (KeyError, ValueError):
            resolved_type = None
        if resolved_type in {PositionType.call, PositionType.put}:
            # OCC option identifiers plus an explicit Open/Close operation are the
            # established broker shape. Description prose varies, so do not require
            # the exact "Reverse split: Close/Open" prefix. Anything less is
            # ambiguous and must not mutate stock lots or silently become a trade.
            open_close = transaction.get(Fields.OPEN_CLOSE.value, "")
            expected_call_put = "C" if resolved_type == PositionType.call else "P"
            try:
                strike = float(transaction.getStrike())
                valid_strike = math.isfinite(strike) and strike > 0
            except (KeyError, TypeError, ValueError):
                valid_strike = False
            try:
                expiry = transaction.getExpiry()
                if isinstance(expiry, str):
                    datetime.fromisoformat(expiry)
                    valid_expiry = True
                else:
                    valid_expiry = (
                        expiry is not None
                        and expiry == expiry
                        and getattr(expiry, "year", None) is not None
                    )
            except (KeyError, TypeError, ValueError):
                valid_expiry = False
            valid_option_fields = (
                transaction.get(Fields.CALL_PUT.value, "") == expected_call_put
                and valid_strike
                and valid_expiry
            )
            if valid_option_fields and has_occ_token and open_close in {
                OpenClose.CLOSE.value,
                OpenClose.OPEN.value,
            }:
                logger.debug("Processing option corporate action")
                return False
            raise ValueError(
                "AMBIGUOUS OPTION REVERSE SPLIT: expected an OCC option token and "
                "an explicit Open/Close operation with valid option fields; "
                f"refusing to process '{description}'"
            )
        if declared_option or has_occ_token:
            raise ValueError(
                "AMBIGUOUS OPTION REVERSE SPLIT: option metadata or an OCC token "
                "was present, but the transaction's resolved type was not an option; "
                f"refusing to process '{description}'"
            )
        symbol_to_split = transaction.getSymbol()

        ratio_patterns = [
            r"(\d+):(\d+)",
            r"(\d+)-for-(\d+)",
            r"(\d+)\s*for\s*(\d+)",
        ]

        parsed_ratios = []
        for pattern in ratio_patterns:
            for match in re.finditer(pattern, description, re.IGNORECASE):
                num1, num2 = int(match.group(1)), int(match.group(2))
                if num2:
                    parsed_ratios.append(num1 / num2)

        # Use only an explicit, internally consistent ratio. In particular, do
        # not silently invert "8 for 1 reverse split" into 1:8; that wording is
        # contradictory and requires an authoritative configured ratio.
        unique_ratios = set(parsed_ratios)
        ratio = next(iter(unique_ratios)) if len(unique_ratios) == 1 else None
        if "reverse" in description.lower() and ratio is not None and ratio >= 1:
            ratio = None

        if ratio is None:
            transaction_date = transaction.get("Date/Time") or transaction.get("Date")
            ratio = self._get_reverse_split_ratio_from_config(
                symbol_to_split, transaction_date
            )

        if ratio is not None:
            try:
                ratio = float(ratio)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid split ratio for {symbol_to_split}: {ratio!r}; "
                    "ratio must be finite and greater than zero"
                ) from exc
            if not math.isfinite(ratio) or ratio <= 0:
                raise ValueError(
                    f"Invalid split ratio for {symbol_to_split}: {ratio!r}; "
                    "ratio must be finite and greater than zero"
                )

            affected_keys = [
                key
                for key in self.open_lots
                if key.symbol == symbol_to_split
                and key.position_type == PositionType.stock
            ]
            affected_lots = [
                lot for key in affected_keys for lot in self.open_lots[key]
            ]
            for side, quantity in (
                ("long", sum(lot.quantity for lot in affected_lots if lot.quantity > 0)),
                ("short", sum(lot.quantity for lot in affected_lots if lot.quantity < 0)),
            ):
                target = quantity * ratio
                if quantity and not math.isclose(
                    target, round(target), rel_tol=0, abs_tol=1e-6
                ):
                    raise ValueError(
                        "REVERSE SPLIT FRACTIONAL RESIDUAL UNKNOWN: "
                        f"{symbol_to_split} {side} aggregate would become {target} shares; "
                        "cash-in-lieu basis and proceeds are not available"
                    )

            logger.warning("Applying configured reverse split")
            for lot in affected_lots:
                lot.adjust_for_split(ratio)
            return True
        else:
            affected_keys = [
                key
                for key in self.open_lots
                if key.symbol == symbol_to_split
                and key.position_type == PositionType.stock
            ]
            affected_lots = sum(len(self.open_lots[key]) for key in affected_keys)
            transaction_date = transaction.get("Date/Time") or transaction.get("Date")
            date_str = (
                transaction_date.strftime("%Y-%m-%d")
                if hasattr(transaction_date, "strftime")
                else str(transaction_date)[:10]
            )

            raise ValueError(
                f"\n{'=' * 80}\n"
                f"REVERSE SPLIT RATIO UNKNOWN: {symbol_to_split}\n"
                f"{'=' * 80}\n\n"
                f"Cannot automatically determine split ratio from:\n"
                f"  Date: {date_str}\n"
                f"  Description: '{description}'\n"
                f"  Open lots affected: {affected_lots}\n\n"
                f"REQUIRED ACTION:\n"
                f"Add this line to corporate_actions.csv in the tastyworksTaxes package:\n\n"
                f"{date_str},{symbol_to_split},???,Broker announcement or SEC filing\n\n"
                f"Replace ??? with the actual ratio:\n"
                f"  - 1:8 reverse split → 0.125\n"
                f"  - 1:5 reverse split → 0.2\n"
                f"  - 2:1 forward split → 2.0\n\n"
                f"Then re-run the program.\n"
                f"{'=' * 80}\n"
            )
