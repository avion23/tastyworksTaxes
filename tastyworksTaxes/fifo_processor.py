from dataclasses import dataclass
from tastyworksTaxes.constants import TransactionSubcode, Fields
from tastyworksTaxes.position import PositionType

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
    strike: float | None = None
    expiry: str | None = None
    opening_profit_usd: float = 0.0
    opening_profit_eur: float = 0.0
    closing_profit_usd: float = 0.0
    closing_profit_eur: float = 0.0
    opening_fees_usd: float = 0.0
    opening_fees_eur: float = 0.0
    closing_fees_usd: float = 0.0
    closing_fees_eur: float = 0.0
    settled_by_exercise: bool = False

class FifoProcessor:
    @staticmethod
    def create_trade_result(opening_lot, closing_transaction, consumed_quantity, consumed_values, opening_was_long: bool):
        closing_amounts = FifoProcessor._calculate_closing_amounts(closing_transaction, consumed_quantity)

        settled_by_exercise = (
            opening_was_long
            and closing_transaction.getType() in (PositionType.call, PositionType.put)
            and closing_transaction[Fields.TRANSACTION_SUBCODE.value] in {
                TransactionSubcode.EXERCISE.value,
                TransactionSubcode.ASSIGNMENT.value,
            }
        )

        signed_quantity = consumed_quantity if opening_was_long else -consumed_quantity
        
        trade_result = TradeResult(
            symbol=closing_transaction.getSymbol(),
            position_type=closing_transaction.getType(),
            opening_date=opening_lot.date.strftime('%Y-%m-%d %H:%M:%S'),
            closing_date=closing_transaction.getDateTime(),
            quantity=signed_quantity,
            profit_usd=0.0 if settled_by_exercise else consumed_values[Fields.AMOUNT.value] + closing_amounts['amount_usd'],
            profit_eur=0.0 if settled_by_exercise else consumed_values[Fields.AMOUNT_EURO.value] + closing_amounts['amount_eur'],
            fees_usd=consumed_values[Fields.FEES.value] + closing_amounts['fees_usd'],
            fees_eur=consumed_values[Fields.FEES_EURO.value] + closing_amounts['fees_eur'],
            worthless_expiry=(
                closing_transaction[Fields.TRANSACTION_SUBCODE.value] == TransactionSubcode.EXPIRATION.value
                and opening_was_long
            ),
            strike=closing_transaction.getStrike() if closing_transaction.getType() != PositionType.stock else None,
            expiry=closing_transaction.getExpiry().strftime('%Y-%m-%d') if closing_transaction.getType() != PositionType.stock else None,
            opening_profit_usd=consumed_values[Fields.AMOUNT.value],
            opening_profit_eur=consumed_values[Fields.AMOUNT_EURO.value],
            closing_profit_usd=closing_amounts['amount_usd'],
            closing_profit_eur=closing_amounts['amount_eur'],
            opening_fees_usd=consumed_values[Fields.FEES.value],
            opening_fees_eur=consumed_values[Fields.FEES_EURO.value],
            closing_fees_usd=closing_amounts['fees_usd'],
            closing_fees_eur=closing_amounts['fees_eur'],
            settled_by_exercise=settled_by_exercise,
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
