import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from tastyworksTaxes.position_lot import PositionLot
from tastyworksTaxes.constants import TransactionSubcode, OpenClose, Fields, CLOSING_SUBCODES
from tastyworksTaxes.fifo_processor import FifoProcessor, TradeResult
from tastyworksTaxes.position import PositionType

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class InstrumentKey:
    """Immutable key for uniquely identifying an instrument"""
    symbol: str
    position_type: PositionType
    strike: float | None = None
    expiry: datetime | None = None
    call_put: str | None = None

class PositionManager:
    def __init__(self):
        self.open_lots: dict[InstrumentKey, deque[PositionLot]] = defaultdict(deque)
        self.closed_trades = []

    def _get_key_from_transaction(self, transaction) -> InstrumentKey:
        """Generate InstrumentKey from transaction for O(1) lot lookup"""
        position_type = transaction.getType()
        if position_type == PositionType.stock:
            return InstrumentKey(transaction.getSymbol(), position_type, None, None, None)
        return InstrumentKey(
            transaction.getSymbol(),
            position_type,
            transaction.getStrike(),
            transaction.getExpiry(),
            transaction.loc[Fields.CALL_PUT.value]
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
            lot.symbol,
            lot.position_type,
            lot.strike,
            lot.expiry,
            lot.call_put
        )
        self.open_lots[key].append(lot)
    
    def add_position(self, transaction):
        subcode = transaction[Fields.TRANSACTION_SUBCODE.value]

        if subcode in {TransactionSubcode.SYMBOL_CHANGE.value, TransactionSubcode.STOCK_MERGER.value}:
            if self._is_closing_transaction(transaction):
                key = self._get_key_from_transaction(transaction)
                matching_lots = self.open_lots.get(key)
                if not matching_lots:
                    logger.warning(f"Symbol Change 'close' leg for {transaction.getSymbol()} found no open position to mutate.")
                    return

                lot_to_remove = matching_lots[0]
                matching_lots.popleft()
                if not matching_lots:
                    del self.open_lots[key]
                self._pending_symbol_change_lot = lot_to_remove
                logger.debug(f"Symbol Change: Removed lot {lot_to_remove.symbol} qty={lot_to_remove.quantity} basis={lot_to_remove.amount_usd:.2f}")

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
        open_close = transaction.get(Fields.OPEN_CLOSE.value, '')
        return subcode in CLOSING_SUBCODES or open_close == OpenClose.CLOSE.value
    
    def _open_position(self, transaction):
        logger.info(f"{transaction.getDateTime():<19} Adding '{transaction.getQuantity():>4}' of '{transaction.getSymbol():<6}' to positions")

        lot = PositionLot(
            symbol=transaction.getSymbol(),
            position_type=transaction.getType(),
            quantity=transaction.getQuantity(),
            amount_usd=transaction.getValue().usd,
            amount_eur=transaction.getValue().eur,
            fees_usd=transaction.getFees().usd,
            fees_eur=transaction.getFees().eur,
            date=transaction.loc[Fields.DATE_TIME.value],
            strike=transaction.getStrike() if transaction.getType().name != 'stock' else None,
            expiry=transaction.getExpiry() if transaction.getType().name != 'stock' else None,
            call_put=transaction.loc[Fields.CALL_PUT.value] if transaction.getType().name != 'stock' else None
        )

        key = self._get_key_from_transaction(transaction)
        self.open_lots[key].append(lot)

    def _open_position_from_symbol_change(self, transaction):
        old_lot = getattr(self, '_pending_symbol_change_lot', None)
        if old_lot is None:
            logger.warning(f"Symbol Change 'open' leg for {transaction.getSymbol()} has no pending lot to transfer basis from. Using CSV values.")
            self._open_position(transaction)
            return

        lot = PositionLot(
            symbol=transaction.getSymbol(),
            position_type=transaction.getType(),
            quantity=transaction.getQuantity(),
            amount_usd=old_lot.amount_usd,
            amount_eur=old_lot.amount_eur,
            fees_usd=old_lot.fees_usd,
            fees_eur=old_lot.fees_eur,
            date=old_lot.date,
            strike=transaction.getStrike() if transaction.getType().name != 'stock' else None,
            expiry=transaction.getExpiry() if transaction.getType().name != 'stock' else None,
            call_put=transaction.loc[Fields.CALL_PUT.value] if transaction.getType().name != 'stock' else None
        )

        key = self._get_key_from_transaction(transaction)
        self.open_lots[key].append(lot)
        logger.debug(f"Symbol Change: Added new lot {transaction.getSymbol()} qty={lot.quantity} basis={lot.amount_usd:.2f} (preserved from {old_lot.symbol})")
        self._pending_symbol_change_lot = None

    def _close_position(self, transaction):
        quantity_to_close = abs(transaction.getQuantity())
        closing_quantity = transaction.getQuantity()

        key = self._get_key_from_transaction(transaction)
        matching_lots = self.open_lots.get(key)

        if not matching_lots:
            raise ValueError(f"Tried to close a position but no previous position found for {transaction}")

        while quantity_to_close > 1e-6 and matching_lots:
            lot_to_process = matching_lots[0]

            subcode = transaction[Fields.TRANSACTION_SUBCODE.value]
            if subcode not in {'Expiration', 'Assignment'} and not lot_to_process.can_close_with(closing_quantity):
                break

            matching_lots.popleft()

            closable_quantity = lot_to_process.get_closable_quantity(quantity_to_close)

            opening_was_long = (lot_to_process.amount_usd < 0)
            lot_before = f"{lot_to_process.quantity} @ {lot_to_process.amount_usd:.2f}"

            new_lot, consumed_values = lot_to_process.consume(closable_quantity)

            lot_after = f"{new_lot.quantity} @ {new_lot.amount_usd:.2f}" if not new_lot.is_empty() else "empty"

            trade_result = FifoProcessor.create_trade_result(lot_to_process, transaction, closable_quantity, consumed_values, opening_was_long)
            self.closed_trades.append(trade_result)

            logger.info(f"{trade_result.opening_date:<19} - {trade_result.closing_date:<19} closing {trade_result.quantity:>4} {trade_result.symbol:<6}")
            logger.debug(f"Consumed {closable_quantity} from lot: {lot_before} -> {lot_after}")

            if not new_lot.is_empty():
                matching_lots.appendleft(new_lot)

            quantity_to_close -= closable_quantity

        if not matching_lots:
            del self.open_lots[key]

        if quantity_to_close > 1e-6:
            raise ValueError(f"Tried to close more shares than available for {transaction.getSymbol()}")
    
    def _handle_reverse_split(self, transaction):
        description = transaction.loc['Description']
        import re
        if re.search(r'\d{6}[CP]\d{8}', description):
            logger.debug(f"Reverse split is a trade, not a mutation: {description}")
            return False
        symbol_to_split = transaction.getSymbol()
        
        ratio_patterns = [
            r'(\d+):(\d+)',
            r'(\d+)-for-(\d+)',
            r'(\d+)\s*for\s*(\d+)',
        ]
        
        ratio = None
        for pattern in ratio_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                num1, num2 = int(match.group(1)), int(match.group(2))
                if 'reverse' in description.lower():
                    ratio = min(num1, num2) / max(num1, num2)
                else:
                    ratio = max(num1, num2) / min(num1, num2)
                break
        
        if ratio is None and symbol_to_split == 'USO':
            ratio = 1.0 / 8.0
            logger.warning(f"Using hardcoded ratio for {symbol_to_split}")
        
        if ratio is not None:
            affected_keys = [key for key in self.open_lots.keys() if key.symbol == symbol_to_split]
            total_lots = sum(len(self.open_lots[key]) for key in affected_keys)
            logger.warning(f"Applying reverse split ratio {ratio} to {total_lots} open '{symbol_to_split}' lots.")

            for key in affected_keys:
                lots_queue = self.open_lots[key]
                original_count = len(lots_queue)

                for lot in lots_queue:
                    old_qty = lot.quantity
                    old_strike = getattr(lot, 'strike', None)
                    lot.adjust_for_split(ratio)
                    logger.debug(f"Split adjusted lot: qty {old_qty} -> {lot.quantity}, strike {old_strike} -> {getattr(lot, 'strike', None)}")

            return True
        else:
            logger.error(f"CRITICAL: Reverse split for {symbol_to_split} could not be parsed from description: '{description}'. This may result in incorrect position tracking. Manual verification required.")
            return False
    
    
