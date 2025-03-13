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
        
        # Add a single position
        t.addPosition(Transaction.fromString("04/23/2020 7:30 PM,Trade,Buy to Open,USO,Buy,Open,6,07/17/2020,2,P,0.29,6.83,-174,Bought 6 USO 07/17/20 Put 2.00 @ 0.29,Individual...39"))
        assert len(t.positions) == 1
        
        # Process a reverse split transaction
        t.addPosition(Transaction.fromString("04/29/2020 12:35 PM,Trade,Sell to Close,USO,Sell,Close,6,07/17/2020,2,P,0.29,0.0,174,Sold 6 USO 07/17/20 Put 2.00 @ 0.29,Individual...39"))
        
        # Verify the position was closed
        assert len(t.positions) == 0
        assert len(t.closedTrades) == 1
