import pytest
from pathlib import Path

from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.transaction import Transaction
from tastyworksTaxes.position import PositionType

class TestTastyReceiveDeliver:
    def test_assigned_stock(self):
        t = Tasty()
        t.position_manager.add_position(Transaction.fromString("03/19/2018 10:00 PM,Receive Deliver,Sell to Open,LFIN,Sell,Open,200,,,,30,5.164,6000,Sell to Open 200 LFIN @ 30.00,Individual...39"))
        assert t.position_manager.open_lots[0].symbol == 'LFIN'
        
        closing = Transaction.fromString("03/19/2018 10:00 PM,Receive Deliver,Sell to Open,LFIN,Sell,Open,200,,,,30,5.164,6000,Sell to Open 200 LFIN @ 30.00,Individual...39")
        closing["Transaction Subcode"] = "Buy to Close"
        t.position_manager.add_position(closing)
        assert len(t.position_manager.open_lots) == 0
    
    def test_close_positions(self):
        t = Tasty()
        t.position_manager.add_position(Transaction.fromString("03/19/2018 10:00 PM,Receive Deliver,Sell to Open,LFIN,Sell,Open,200,,,,30,5.164,6000,Sell to Open 200 LFIN @ 30.00,Individual...39"))
        t.position_manager.add_position(Transaction.fromString("03/21/2018 6:42 PM,Trade,Buy to Close,LFIN,Buy,Close,100,,,,56.76,0.08,-5676,Bought 100 LFIN @ 56.76,Individual...39"))
        assert len(t.position_manager.closed_trades) == 1
        assert len(t.position_manager.open_lots) > 0
    
    def test_expiration(self):
        t = Tasty()
        t.position_manager.add_position(Transaction.fromString("05/30/2018 6:24 PM,Trade,Buy to Open,MU,Buy,Open,1,07/20/2018,70,C,2.4,1.14,-240,Bought 1 MU 07/20/18 Call 70.00 @ 2.40,Individual...39"))
        t.position_manager.add_position(Transaction.fromString("07/20/2018 10:00 PM,Receive Deliver,Expiration,MU,,,1,07/20/2018,70,C,,0.00,0,Removal of 1 MU 07/20/18 Call 70.00 due to expiration.,Individual...39"))
        assert len(t.position_manager.closed_trades) == 1
        assert len(t.position_manager.closed_trades) == 1
        assert len(t.position_manager.open_lots) == 0
    
    def test_uvxy_expiration(self):
        t = Tasty()
        t.position_manager.add_position(Transaction.fromString("01/29/2021 7:31 PM,Trade,Sell to Open,UVXY,Sell,Open,1,01/29/2021,14.5,P,0.56,1.152,56,Sold 1 UVXY 01/29/21 Put 14.50 @ 0.56,Individual...39"))
        t.position_manager.add_position(Transaction.fromString("01/29/2021 10:15 PM,Receive Deliver,Expiration,UVXY,,,1,01/29/2021,14.5,P,,0.00,0,Removal of 1.0 UVXY 01/29/21 Put 14.50 due to expiration.,Individual...39"))
        assert len(t.position_manager.closed_trades) == 1
        assert len(t.position_manager.open_lots) == 0
    
    def test_derm_expiration(self):
        t = Tasty()
        t.position_manager.add_position(Transaction.fromString("05/22/2018 5:36 PM,Trade,Buy to Open,DERM,Buy,Open,2,07/20/2018,11,C,1.05,2.28,-210,Bought 2 DERM 07/20/18 Call 11.00 @ 1.05,Individual...39"))
        t.position_manager.add_position(Transaction.fromString("07/20/2018 10:00 PM,Receive Deliver,Expiration,DERM,,,2,07/20/2018,11,C,,0.00,0,Removal of 2 DERM 07/20/18 Call 11.00 due to expiration.,Individual...39"))
        assert len(t.position_manager.closed_trades) == 1
        assert len(t.position_manager.open_lots) == 0
