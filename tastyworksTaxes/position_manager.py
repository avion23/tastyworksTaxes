import logging
from tastyworksTaxes.position_lot import PositionLot
from tastyworksTaxes.constants import TransactionSubcode, OpenClose, Fields, CLOSING_SUBCODES
from tastyworksTaxes.fifo_processor import FifoProcessor, TradeResult

logger = logging.getLogger(__name__)

class PositionManager:
    def __init__(self):
        self.open_lots = []
        self.closed_trades = []
    
    def add_position(self, transaction):
        subcode = transaction[Fields.TRANSACTION_SUBCODE.value]

        # Intercept Symbol Change and Stock Merger events specifically to prevent them from being treated as trades.
        if subcode in {TransactionSubcode.SYMBOL_CHANGE.value, TransactionSubcode.STOCK_MERGER.value}:
            # The broker uses a "close" on the old symbol and an "open" on the new symbol.
            # We must treat this not as a trade, but as an atomic mutation.

            # If this is the "close" leg, we find the matching lot and simply remove it from the open lots
            # without generating a closed trade. It is effectively "staged" for the mutation.
            if self._is_closing_transaction(transaction):
                matching_lots = self._find_matching_lots(transaction)
                if not matching_lots:
                    logger.warning(f"Symbol Change 'close' leg for {transaction.getSymbol()} found no open position to mutate.")
                    return

                # Assuming the first match is the correct one in a chronological scan.
                lot_to_remove = matching_lots[0]
                self.open_lots.remove(lot_to_remove)
                logger.debug(f"Symbol Change: Consumed lot {lot_to_remove.symbol} in preparation for mutation.")

            # If this is the "open" leg, we treat it as a normal opening trade.
            # Crucially, its cost basis (amount) will be the opposite of the "close" leg,
            # effectively transferring the basis. The FIFO logic will correctly match these later.
            # In a tax context, this is a wash sale, but for our FIFO queue, it's just a new lot
            # that will be matched against the final, real closing trade.
            else: # It's an opening transaction
                self._open_position(transaction)
            
            # In either case, we stop processing here for Symbol Change events.
            return

        # --- Standard processing for all other transaction types ---
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
        
        self.open_lots.append(lot)
    
    def _close_position(self, transaction):
        quantity_to_close = abs(transaction.getQuantity())
        closing_quantity = transaction.getQuantity()
        
        matching_lots = self._find_matching_lots(transaction)
        
        if not matching_lots:
            raise ValueError(f"Tried to close a position but no previous position found for {transaction}")
        
        lots_to_remove = []
        
        for lot in matching_lots:
            if quantity_to_close < 1e-6:
                break
                
            subcode = transaction[Fields.TRANSACTION_SUBCODE.value]
            if subcode not in {'Expiration', 'Assignment'} and not lot.can_close_with(closing_quantity):
                continue
                
            closable_quantity = lot.get_closable_quantity(quantity_to_close)
            
            consumed_values = lot.consume(closable_quantity)
            
            trade_result = FifoProcessor.create_trade_result(lot, transaction, closable_quantity, consumed_values)
            self.closed_trades.append(trade_result)
            
            logger.info(f"{trade_result.opening_date:<19} - {trade_result.closing_date:<19} closing {trade_result.quantity:>4} {trade_result.symbol:<6}")
            
            if lot.is_empty():
                lots_to_remove.append(lot)
            
            quantity_to_close -= closable_quantity
        
        for lot in lots_to_remove:
            self.open_lots.remove(lot)
        
        if quantity_to_close > 1e-6:
            raise ValueError(f"Tried to close more shares than available for {transaction.getSymbol()}")
    
    def _find_matching_lots(self, transaction):
        symbol = transaction.getSymbol()
        position_type = transaction.getType()
        strike = transaction.getStrike() if position_type.name != 'stock' else None
        expiry = transaction.getExpiry() if position_type.name != 'stock' else None
        call_put = transaction.loc[Fields.CALL_PUT.value] if position_type.name != 'stock' else None
        
        matching_lots = []
        for lot in self.open_lots:
            if lot.matches(symbol, position_type, strike, expiry, call_put):
                matching_lots.append(lot)
        
        return sorted(matching_lots, key=lambda x: x.date)
    
    def _handle_reverse_split(self, transaction):
        # Guard Clause: If the description contains option symbols (not ratio information),
        # it's a mislabeled trade, not a pure corporate action. Do not handle it here.
        description = transaction.loc['Description']
        # Look for option symbol patterns like "200717P00002000" (6 digits + letter + 8 digits)
        import re
        if re.search(r'\d{6}[CP]\d{8}', description):
            logger.debug(f"Reverse split is a trade, not a mutation: {description}")
            return False # Fall back to standard trade processing.
        symbol_to_split = transaction.getSymbol()
        
        ratio_patterns = [
            r'(\d+):(\d+)',  # "1:8" or "8:1"
            r'(\d+)-for-(\d+)',  # "1-for-8"
            r'(\d+)\s*for\s*(\d+)',  # "1 for 8"
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
            logger.warning(f"Applying reverse split ratio {ratio} to all open '{symbol_to_split}' lots.")
            
            for lot in self.open_lots:
                if lot.symbol == symbol_to_split:
                    lot.adjust_for_split(ratio)
            return True # Event was handled successfully.
        else:
            logger.warning(f"Reverse split for {symbol_to_split} was not handled due to unparsable description: {description}")
            return False # Fall back to standard trade processing.
    
    
