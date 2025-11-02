import pytest
from pathlib import Path

from tastyworksTaxes.position_manager import PositionManager
from tastyworksTaxes.transaction import Transaction
from tastyworksTaxes.position import PositionType

class TestPositionManager:
    def test_lfin_calls_open_and_close(self):
        pm = PositionManager()
        pm.add_position(Transaction.fromString("2018-03-12T17:08:00+0000,Trade,Buy to Open,BUY_TO_OPEN,LFIN  180615C00040000,Equity Option,Bought 2 LFIN 06/15/18 Call 40.00 @ 2.20,-440,2,220.00000000000003,-1.00,1.2799999999999998,100,LFIN,LFIN,6/15/18,40,CALL,123456,USD"))
        lot = pm.open_lots[0]
        assert lot.symbol == 'LFIN'
        assert lot.quantity == 2
        
        pm.add_position(Transaction.fromString("2018-03-16T16:09:00+0000,Trade,Sell to Close,SELL_TO_CLOSE,LFIN  180615C00040000,Equity Option,Sold 1 LFIN 06/15/18 Call 40.00 @ 16.60,1660,1,1660.0000000000002,-1.00,0.18999999999999995,100,LFIN,LFIN,6/15/18,40,CALL,123456,USD"))
        lot = pm.open_lots[0]
        assert lot.quantity == 1
        assert pm.closed_trades[0].quantity == 1
        
        pm.add_position(Transaction.fromString("2018-03-16T16:09:00+0000,Trade,Sell to Close,SELL_TO_CLOSE,LFIN  180615C00040000,Equity Option,Sold 1 LFIN 06/15/18 Call 40.00 @ 16.60,1660,1,1660.0000000000002,-1.00,0.18999999999999995,100,LFIN,LFIN,6/15/18,40,CALL,123456,USD"))
        assert len(pm.open_lots) == 0
        assert len(pm.closed_trades) == 2
    
    def test_sprt_position(self):
        pm = PositionManager()
        pm.add_position(Transaction.fromString("2021-07-01T20:57:00+0000,Trade,Buy to Open,BUY_TO_OPEN,SPRT,Equity,Bought 200 SPRT @ 3.87,-774,200,3.87,-1.00,0.16,,SPRT,SPRT,,,,123456,USD"))
        lot = pm.open_lots[0]
        assert lot.symbol == 'SPRT'
        assert lot.quantity == 200
        assert lot.amount_usd == -774
    
    def test_true_fifo_stock_logic(self):
        pm = PositionManager()

        buy1_str = "2024-01-01T10:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,FIFO,Equity,Bought 10 FIFO @ 10,-100,10,10,-1.00,0.00,,FIFO,FIFO,,,,123456,USD"

        buy2_str = "2024-01-02T10:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,FIFO,Equity,Bought 10 FIFO @ 20,-200,10,20,-1.00,0.00,,FIFO,FIFO,,,,123456,USD"

        sell1_str = "2024-01-03T10:00:00+0000,Trade,Sell to Close,SELL_TO_CLOSE,FIFO,Equity,Sold 15 FIFO @ 25,375,15,25,-1.00,0.00,,FIFO,FIFO,,,,123456,USD"

        pm.add_position(Transaction.fromString(buy1_str))
        pm.add_position(Transaction.fromString(buy2_str))
        pm.add_position(Transaction.fromString(sell1_str))
        
        total_profit = sum(t.profit_usd for t in pm.closed_trades)
        
        assert round(total_profit, 2) == 175.00
        
        remaining_lot = pm.open_lots[0]
        assert remaining_lot.quantity == 5
        
        remaining_cost_basis = remaining_lot.amount_usd
        assert round(remaining_cost_basis, 2) == -100.00
    
    def test_partial_closure_amounts(self):
        """Test correct prorating of values in partial position closures"""
        pm = PositionManager()
        
        pm.add_position(Transaction.fromString("2024-01-01T09:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,XYZ,Equity,Bought 100 XYZ @ 10,-1000,100,10,-1.00,4.0,,XYZ,XYZ,,,,123456,USD"))
        lot = pm.open_lots[0]
        assert lot.quantity == 100
        assert lot.amount_usd == -1000
        assert lot.fees_usd == 5
        
        pm.add_position(Transaction.fromString("2024-01-02T09:00:00+0000,Trade,Sell to Close,SELL_TO_CLOSE,XYZ,Equity,Sold 50 XYZ @ 12,600,50,12,-1.00,2.0,,XYZ,XYZ,,,,123456,USD"))
        
        lot = pm.open_lots[0]
        assert lot.quantity == 50
        assert lot.amount_usd == -500  # 50% of original cost
        assert lot.fees_usd == 2.5
        
        trade = pm.closed_trades[0]
        assert trade.quantity == 50
        assert trade.profit_usd == 100
        assert trade.fees_usd == 5.5
    
    def test_multiple_partial_closures(self):
        """Test that consecutive partial closures maintain proper accounting"""
        pm = PositionManager()
        
        pm.add_position(Transaction.fromString("2024-01-01T09:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,XYZ,Equity,Bought 100 XYZ @ 10,-1000,100,10,-1.00,4.0,,XYZ,XYZ,,,,123456,USD"))
        
        pm.add_position(Transaction.fromString("2024-01-02T09:00:00+0000,Trade,Sell to Close,SELL_TO_CLOSE,XYZ,Equity,Sold 30 XYZ @ 12,360,30,12,-1.00,2.0,,XYZ,XYZ,,,,123456,USD"))
        
        lot = pm.open_lots[0]
        assert lot.quantity == 70
        assert abs(lot.amount_usd - (-700)) < 0.01
        
        pm.add_position(Transaction.fromString("2024-01-03T09:00:00+0000,Trade,Sell to Close,SELL_TO_CLOSE,XYZ,Equity,Sold 40 XYZ @ 15,600,40,15,-1.00,3.0,,XYZ,XYZ,,,,123456,USD"))
        
        lot = pm.open_lots[0]
        assert lot.quantity == 30
        assert abs(lot.amount_usd - (-300)) < 0.01
        
        assert len(pm.closed_trades) == 2
        
    def test_overclosing_position(self):
        """Test what happens when trying to close more shares than exist in position"""
        pm = PositionManager()

        pm.add_position(Transaction.fromString(
            "2024-01-01T09:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,XYZ,Equity,Bought 10 XYZ @ 10,-100,10,10,-1.00,4.00,,XYZ,XYZ,,,,123456,USD"))

        with pytest.raises(ValueError, match="Tried to close more shares than available for XYZ"):
            pm.add_position(Transaction.fromString(
                "2024-01-02T09:00:00+0000,Trade,Sell to Close,SELL_TO_CLOSE,XYZ,Equity,Sold 20 XYZ @ 12,240,20,12,-1.00,2.00,,XYZ,XYZ,,,,123456,USD"))