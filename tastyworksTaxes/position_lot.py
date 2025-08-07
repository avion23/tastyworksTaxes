from dataclasses import dataclass
from datetime import datetime
from tastyworksTaxes.constants import Fields
from tastyworksTaxes.position import PositionType

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
        
        percentage_consumed = quantity_to_consume / abs(self.quantity)
        
        consumed_values = {
            Fields.AMOUNT.value: self.amount_usd * percentage_consumed,
            Fields.AMOUNT_EURO.value: self.amount_eur * percentage_consumed,
            Fields.FEES.value: self.fees_usd * percentage_consumed,
            Fields.FEES_EURO.value: self.fees_eur * percentage_consumed,
        }

        sign = 1 if self.quantity > 0 else -1
        self.quantity -= sign * quantity_to_consume
        remaining_percentage = 1.0 - percentage_consumed
        self.amount_usd *= remaining_percentage 
        self.amount_eur *= remaining_percentage 
        self.fees_usd *= remaining_percentage 
        self.fees_eur *= remaining_percentage

        return consumed_values
    
    def adjust_for_split(self, ratio):
        self.quantity = int(self.quantity * ratio)
        if self.strike:
            self.strike = self.strike / ratio
    
    def is_empty(self):
        return abs(self.quantity) < 1e-6