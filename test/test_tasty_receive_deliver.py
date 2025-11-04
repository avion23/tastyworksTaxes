import pytest
from pathlib import Path

from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.transaction import Transaction
from tastyworksTaxes.position import PositionType

class TestTastyReceiveDeliver:
    def test_assigned_stock(self):
        t = Tasty()
        t.position_manager.add_position(Transaction.fromString("2018-03-19T22:00:00+0000,Receive Deliver,Sell to Open,SELL_TO_OPEN,LFIN,Equity,Sell to Open 200 LFIN @ 30.00,6000,200,30,-1.00,4.164,,LFIN,LFIN,,,,123456,USD"))
        assert t.position_manager.get_all_open_lots()[0].symbol == 'LFIN'
        
        closing = Transaction.fromString("2018-03-19T22:00:00+0000,Receive Deliver,Sell to Open,SELL_TO_OPEN,LFIN,Equity,Sell to Open 200 LFIN @ 30.00,6000,200,30,-1.00,4.164,,LFIN,LFIN,,,,123456,USD")
        closing["Transaction Subcode"] = "Buy to Close"
        t.position_manager.add_position(closing)
        assert len(t.position_manager.open_lots) == 0
    
    def test_close_positions(self):
        t = Tasty()
        t.position_manager.add_position(Transaction.fromString("2018-03-19T22:00:00+0000,Receive Deliver,Sell to Open,SELL_TO_OPEN,LFIN,Equity,Sell to Open 200 LFIN @ 30.00,6000,200,30,-1.00,4.164,,LFIN,LFIN,,,,123456,USD"))
        t.position_manager.add_position(Transaction.fromString("2018-03-21T18:42:00+0000,Trade,Buy to Close,BUY_TO_CLOSE,LFIN,Equity,Bought 100 LFIN @ 56.76,-5676,100,56.76,-1.00,0.08,,LFIN,LFIN,,,,123456,USD"))
        assert len(t.position_manager.closed_trades) == 1
        assert len(t.position_manager.open_lots) > 0
    
    def test_expiration(self):
        t = Tasty()
        t.position_manager.add_position(Transaction.fromString("2018-05-30T18:24:00+0000,Trade,Buy to Open,BUY_TO_OPEN,MU  180720C00070000,Equity Option,Bought 1 MU 07/20/18 Call 70.00 @ 2.40,-240,1,240.0,-1.00,0.1399999999999999,100,MU,MU,7/20/18,70,CALL,123456,USD"))
        t.position_manager.add_position(Transaction.fromString("2018-07-20T22:00:00+0000,Receive Deliver,Expiration,,MU  180720C00070000,Equity Option,Removal of 1 MU 07/20/18 Call 70.00 due to expiration.,0,1,,0,0.00,100,MU,MU,7/20/18,70,CALL,123456,USD"))
        assert len(t.position_manager.closed_trades) == 1
        assert len(t.position_manager.closed_trades) == 1
        assert len(t.position_manager.open_lots) == 0
    
    def test_uvxy_expiration(self):
        t = Tasty()
        t.position_manager.add_position(Transaction.fromString("2021-01-29T19:31:00+0000,Trade,Sell to Open,SELL_TO_OPEN,UVXY  210129P00014500,Equity Option,Sold 1 UVXY 01/29/21 Put 14.50 @ 0.56,56,1,56.00000000000001,-1.00,0.1519999999999999,100,UVXY,UVXY,1/29/21,14.5,PUT,123456,USD"))
        t.position_manager.add_position(Transaction.fromString("2021-01-29T22:15:00+0000,Receive Deliver,Expiration,,UVXY  210129P00014500,Equity Option,Removal of 1.0 UVXY 01/29/21 Put 14.50 due to expiration.,0,1,,0,0.00,100,UVXY,UVXY,1/29/21,14.5,PUT,123456,USD"))
        assert len(t.position_manager.closed_trades) == 1
        assert len(t.position_manager.open_lots) == 0
    
    def test_derm_expiration(self):
        t = Tasty()
        t.position_manager.add_position(Transaction.fromString("2018-05-22T17:36:00+0000,Trade,Buy to Open,BUY_TO_OPEN,DERM  180720C00011000,Equity Option,Bought 2 DERM 07/20/18 Call 11.00 @ 1.05,-210,2,105.0,-1.00,1.2799999999999998,100,DERM,DERM,7/20/18,11,CALL,123456,USD"))
        t.position_manager.add_position(Transaction.fromString("2018-07-20T22:00:00+0000,Receive Deliver,Expiration,,DERM  180720C00011000,Equity Option,Removal of 2 DERM 07/20/18 Call 11.00 due to expiration.,0,2,,0,0.00,100,DERM,DERM,7/20/18,11,CALL,123456,USD"))
        assert len(t.position_manager.closed_trades) == 1
        assert len(t.position_manager.open_lots) == 0
