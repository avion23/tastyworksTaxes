import pytest
from pathlib import Path

from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.transaction import Transaction
from tastyworksTaxes.position import PositionType

class TestTastyAddPosition:
    def test_lfin_calls_open_and_close(self):
        # Test opening and closing LFIN call positions
        t = Tasty()
        t.addPosition(Transaction.fromString("03/12/2018 5:08 PM,Trade,Buy to Open,LFIN,Buy,Open,2,06/15/2018,40,C,2.2,2.28,-440,Bought 2 LFIN 06/15/18 Call 40.00 @ 2.20,Individual...39"))
        assert t.positions.iloc[0]["Symbol"] == 'LFIN'
        assert t.positions.iloc[0]["Quantity"] == 2
        
        t.addPosition(Transaction.fromString("03/16/2018 4:09 PM,Trade,Sell to Close,LFIN,Sell,Close,1,06/15/2018,40,C,16.6,1.19,1660,Sold 1 LFIN 06/15/18 Call 40.00 @ 16.60,Individual...39"))
        assert t.positions.iloc[0]["Quantity"] == 1
        assert t.closedTrades.iloc[0]["Quantity"] == 1
        
        t.addPosition(Transaction.fromString("03/16/2018 4:09 PM,Trade,Sell to Close,LFIN,Sell,Close,1,06/15/2018,40,C,16.6,1.19,1660,Sold 1 LFIN 06/15/18 Call 40.00 @ 16.60,Individual...39"))
        assert t.positions.empty
        assert len(t.closedTrades) == 2
    
    def test_sprt_position(self):
        # Test simplest SPRT stock position
        t = Tasty()
        t.addPosition(Transaction.fromString("07/01/2021 8:57 PM,Trade,Buy to Open,SPRT,Buy,Open,200,,,,3.87,0.16,-774,Bought 200 SPRT @ 3.87,Individual...39"))
        assert t.positions.iloc[0]["Symbol"] == 'SPRT'
        assert t.positions.iloc[0]["Quantity"] == 200
        assert t.positions.iloc[0]["Amount"] == -774