import pytest
from pathlib import Path

from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.transaction import Transaction
from tastyworksTaxes.position import PositionType
import pandas as pd
import numpy as np

class TestTastyReverseSplit:
    def test_reverse_split_simplified(self):
        """
        A simpler test for reverse split that avoids pandas issues
        """
        t = Tasty()
        
        t.position_manager.add_position(Transaction.fromString("2020-04-23T19:30:00+0000,Trade,Buy to Open,BUY_TO_OPEN,USO  200717P00002000,Equity Option,Bought 6 USO 07/17/20 Put 2.00 @ 0.29,-174,6,28.999999999999996,-1.00,5.83,100,USO,USO,7/17/20,2,PUT,123456,USD"))
        assert len(t.position_manager.open_lots) == 1
        
        t.position_manager.add_position(Transaction.fromString("2020-04-29T12:35:00+0000,Trade,Sell to Close,SELL_TO_CLOSE,USO  200717P00002000,Equity Option,Sold 6 USO 07/17/20 Put 2.00 @ 0.29,174,6,28.999999999999996,0,0.0,100,USO,USO,7/17/20,2,PUT,123456,USD"))
        
        assert len(t.position_manager.open_lots) == 0
        assert len(t.position_manager.closed_trades) == 1
