from dataclasses import dataclass
from tastyworksTaxes.constants import TransactionSubcode, Fields
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.position_lot import PositionLot

@dataclass
class TradeResult:
    symbol: str
    position_type: PositionType
    opening_date: str
    closing_date: str
    quantity: float
    profit_usd: float
    profit_eur: float
    fees_usd: float
    fees_eur: float
    worthless_expiry: bool
    strike: float = None
    expiry: str = None

class FifoProcessor:
    @staticmethod
    def create_trade_result(opening_lot, closing_transaction, consumed_quantity, consumed_values):
        closing_amounts = FifoProcessor._calculate_closing_amounts(closing_transaction, consumed_quantity)
        
        signed_quantity = consumed_quantity if opening_lot.quantity > 0 else -consumed_quantity
        
        trade_result = TradeResult(
            symbol=closing_transaction.getSymbol(),
            position_type=closing_transaction.getType(),
            opening_date=opening_lot.date.strftime('%Y-%m-%d %H:%M:%S'),
            closing_date=closing_transaction.getDateTime(),
            quantity=signed_quantity,
            profit_usd=consumed_values[Fields.AMOUNT.value] + closing_amounts['amount_usd'],
            profit_eur=consumed_values[Fields.AMOUNT_EURO.value] + closing_amounts['amount_eur'],
            fees_usd=consumed_values[Fields.FEES.value] + closing_amounts['fees_usd'],
            fees_eur=consumed_values[Fields.FEES_EURO.value] + closing_amounts['fees_eur'],
            worthless_expiry=(closing_transaction[Fields.TRANSACTION_SUBCODE.value] == TransactionSubcode.EXPIRATION.value 
                            and opening_lot.quantity > 0),
            strike=closing_transaction.getStrike() if closing_transaction.getType() != PositionType.stock else None,
            expiry=closing_transaction.getExpiry().strftime('%Y-%m-%d') if closing_transaction.getType() != PositionType.stock else None
        )
        
        return trade_result
    
    @staticmethod
    def _calculate_closing_amounts(transaction, quantity):
        closing_qty_abs = abs(transaction.getQuantity())
        percentage = quantity / closing_qty_abs if closing_qty_abs > 0 else 0
        
        return {
            'amount_usd': transaction.getValue().usd * percentage,
            'amount_eur': transaction.getValue().eur * percentage,
            'fees_usd': transaction.getFees().usd * percentage,
            'fees_eur': transaction.getFees().eur * percentage
        }