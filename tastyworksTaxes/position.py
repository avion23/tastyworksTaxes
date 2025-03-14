import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from datetime import datetime
from enum import Enum

from tastyworksTaxes.money import Money


class PositionType(Enum):
    """put, call, or stock"""

    stock = "stock"
    put = "put"
    call = "call"
    def __repr__(self):
        return '<%s>' % (self.name)



class Position(object):
    symbol: str
    size: int
    value: Money
    type: PositionType
    date: datetime
    
    def __init__(self, symbol: str, size: int, value: Money):
        self.symbol = symbol
        self.size = size
        self.value = value
    def __repr__(self):
        return str(self.__dict__)
   
class Stock(Position):
    def __init__(self, symbol, size, value):
        super().__init__(symbol, size, value)
        self.type = PositionType.stock
    

class Option(Position):
    strike: float
    expiry: datetime
    def __init__(self, symbol, size, value, putOrCall, strike, expiry):
        super().__init__(symbol, size, value)
        self.type = putOrCall
        self.strike = strike
        self.expiry = expiry
       



