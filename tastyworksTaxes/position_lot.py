from dataclasses import dataclass
from datetime import datetime
import logging
from tastyworksTaxes.constants import Fields
from tastyworksTaxes.position import PositionType

logger = logging.getLogger(__name__)

@dataclass
class PositionLot:
    symbol: str
    position_type: PositionType
    quantity: int
    amount_usd: float
    amount_eur: float
    fees_usd: float
    fees_eur: float
    date: datetime
    strike: float = None
    expiry: datetime = None
    call_put: str = None
    
    def matches(self, symbol, position_type, strike=None, expiry=None, call_put=None):
        if self.symbol != symbol or self.position_type != position_type:
            return False
            
        if position_type == PositionType.stock:
            return True
            
        return (self.strike == strike and 
                self.expiry == expiry and 
                self.call_put == call_put)
    
    def can_close_with(self, closing_quantity):
        return (self.quantity * closing_quantity) < 0
    
    def get_closable_quantity(self, requested_quantity):
        return min(abs(requested_quantity), abs(self.quantity))
    
    def consume(self, quantity_to_consume):
        if abs(quantity_to_consume) > abs(self.quantity):
            raise ValueError(f"Cannot consume {quantity_to_consume} from lot with quantity {self.quantity}")
        
        abs_original_quantity = abs(self.quantity)
        percentage_consumed = quantity_to_consume / abs_original_quantity
        
        consumed_amount_usd = self.amount_usd * percentage_consumed
        consumed_amount_eur = self.amount_eur * percentage_consumed  
        consumed_fees_usd = self.fees_usd * percentage_consumed
        consumed_fees_eur = self.fees_eur * percentage_consumed
        
        consumed_values = {
            Fields.AMOUNT.value: consumed_amount_usd,
            Fields.AMOUNT_EURO.value: consumed_amount_eur,
            Fields.FEES.value: consumed_fees_usd,
            Fields.FEES_EURO.value: consumed_fees_eur,
        }

        sign = 1 if self.quantity > 0 else -1
        self.quantity -= sign * quantity_to_consume
        
        self.amount_usd -= consumed_amount_usd
        self.amount_eur -= consumed_amount_eur
        self.fees_usd -= consumed_fees_usd  
        self.fees_eur -= consumed_fees_eur

        return consumed_values
    
    def adjust_for_split(self, ratio):
        new_qty = int(round(self.quantity * ratio))
        if new_qty == 0 and self.quantity != 0:
            logger.warning(f"Split rounding produced 0 from {self.quantity} with ratio {ratio}")
        self.amount_usd *= (new_qty / self.quantity) if self.quantity else 0.0
        self.amount_eur *= (new_qty / self.quantity) if self.quantity else 0.0
        self.fees_usd   *= (new_qty / self.quantity) if self.quantity else 0.0
        self.fees_eur   *= (new_qty / self.quantity) if self.quantity else 0.0
        self.quantity = new_qty
        if self.strike:
            self.strike = self.strike / ratio
    
    def is_empty(self):
        return abs(self.quantity) < 1e-6