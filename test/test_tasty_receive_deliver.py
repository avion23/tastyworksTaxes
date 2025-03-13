import pytest
from pathlib import Path

from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.transaction import Transaction
from tastyworksTaxes.position import PositionType

class TestTastyReceiveDeliver:
    def test_assigned_stock(self):
        t = Tasty()
        t.addPosition(Transaction.fromString("03/19/2018 10:00 PM,Receive Deliver,Sell to Open,LFIN,Sell,Open,200,,,,30,5.164,6000,Sell to Open 200 LFIN @ 30.00,Individual...39"))
        assert Transaction(t.positions.squeeze()).getSymbol() == 'LFIN'
        
        closing = Transaction.fromString("03/19/2018 10:00 PM,Receive Deliver,Sell to Open,LFIN,Sell,Open,200,,,,30,5.164,6000,Sell to Open 200 LFIN @ 30.00,Individual...39")
        closing["Transaction Subcode"] = "Buy to Close"
        t.addPosition(closing)
        assert t.positions.size == 0
    
    def test_close_positions(self):
        t = Tasty()
        # From merged.csv line 334 (iloc[332])
        t.addPosition(Transaction.fromString("03/19/2018 10:00 PM,Receive Deliver,Sell to Open,LFIN,Sell,Open,200,,,,30,5.164,6000,Sell to Open 200 LFIN @ 30.00,Individual...39"))
        # From merged.csv line 331 (iloc[329])
        t.addPosition(Transaction.fromString("03/21/2018 6:42 PM,Trade,Buy to Close,LFIN,Buy,Close,100,,,,56.76,0.08,-5676,Bought 100 LFIN @ 56.76,Individual...39"))
        assert len(t.closedTrades.index) == 1
        assert t.positions.size > 0
    
    def test_expiration(self):
        t = Tasty()
        # From merged.csv line 317 (iloc[315])
        t.addPosition(Transaction.fromString("05/30/2018 6:24 PM,Trade,Buy to Open,MU,Buy,Open,1,07/20/2018,70,C,2.4,1.14,-240,Bought 1 MU 07/20/18 Call 70.00 @ 2.40,Individual...39"))
        # From merged.csv line 306 (iloc[304])
        t.addPosition(Transaction.fromString("07/20/2018 10:00 PM,Receive Deliver,Expiration,MU,,,1,07/20/2018,70,C,,0.00,0,Removal of 1 MU 07/20/18 Call 70.00 due to expiration.,Individual...39"))
        assert len(t.closedTrades.index) == 1
        assert len(t.closedTrades) == 1
        assert t.positions.size == 0
    
    def test_reverse_split(self):
        t = Tasty()
        # Just verify that adding a Reverse Split transaction works (without error)
        reverse_split_transaction = Transaction.fromString("04/29/2020 12:35 PM,Receive Deliver,Reverse Split,USO,Buy,Open,6,07/17/2020,2,P,,0.00,-174,Reverse split: Open 6 USO1  200717P00002000,Individual...39")
        t.receiveDelivery(reverse_split_transaction)
    
    def test_symbol_change(self):
        t = Tasty()
        # From merged2.csv line 48 (iloc[46])
        t.addPosition(Transaction.fromString("06/18/2021 12:48 PM,Receive Deliver,Symbol Change,VGAC,Sell,Close,100,,,,,0.00,1750,Symbol change:  Close 100.0 VGAC,Individual...39"))
    
    def test_stock_merger(self):
        t = Tasty()
        # From merged3.csv line 195 (iloc[193])
        t.addPosition(Transaction.fromString("09/15/2021 12:36 PM,Receive Deliver,Stock Merger,GREE,Sell,Open,6,09/17/2021,22,P,,0.00,3360,Stock merger Open 6.0 GREE1 210917P00022000,Individual...39"))
    
    def test_uvxy_expiration(self):
        t = Tasty()
        t.addPosition(Transaction.fromString("01/29/2021 7:31 PM,Trade,Sell to Open,UVXY,Sell,Open,1,01/29/2021,14.5,P,0.56,1.152,56,Sold 1 UVXY 01/29/21 Put 14.50 @ 0.56,Individual...39"))
        t.addPosition(Transaction.fromString("01/29/2021 10:15 PM,Receive Deliver,Expiration,UVXY,,,1,01/29/2021,14.5,P,,0.00,0,Removal of 1.0 UVXY 01/29/21 Put 14.50 due to expiration.,Individual...39"))
        assert len(t.closedTrades) == 1
        assert t.positions.empty == True
    
    def test_derm_expiration(self):
        t = Tasty()
        t.addPosition(Transaction.fromString("05/22/2018 5:36 PM,Trade,Buy to Open,DERM,Buy,Open,2,07/20/2018,11,C,1.05,2.28,-210,Bought 2 DERM 07/20/18 Call 11.00 @ 1.05,Individual...39"))
        t.addPosition(Transaction.fromString("07/20/2018 10:00 PM,Receive Deliver,Expiration,DERM,,,2,07/20/2018,11,C,,0.00,0,Removal of 2 DERM 07/20/18 Call 11.00 due to expiration.,Individual...39"))
        assert len(t.closedTrades) == 1
        assert t.positions.empty == True
