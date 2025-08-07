import pytest
from pathlib import Path

from tastyworksTaxes.position_manager import PositionManager
from tastyworksTaxes.transaction import Transaction
from tastyworksTaxes.position import PositionType

class TestPositionManager:
    def test_lfin_calls_open_and_close(self):
        pm = PositionManager()
        pm.add_position(Transaction.fromString("03/12/2018 5:08 PM,Trade,Buy to Open,LFIN,Buy,Open,2,06/15/2018,40,C,2.2,2.28,-440,Bought 2 LFIN 06/15/18 Call 40.00 @ 2.20,Individual...39"))
        lot = pm.open_lots[0]
        assert lot.symbol == 'LFIN'
        assert lot.quantity == 2
        
        pm.add_position(Transaction.fromString("03/16/2018 4:09 PM,Trade,Sell to Close,LFIN,Sell,Close,1,06/15/2018,40,C,16.6,1.19,1660,Sold 1 LFIN 06/15/18 Call 40.00 @ 16.60,Individual...39"))
        lot = pm.open_lots[0]
        assert lot.quantity == 1
        assert pm.closed_trades[0].quantity == 1
        
        pm.add_position(Transaction.fromString("03/16/2018 4:09 PM,Trade,Sell to Close,LFIN,Sell,Close,1,06/15/2018,40,C,16.6,1.19,1660,Sold 1 LFIN 06/15/18 Call 40.00 @ 16.60,Individual...39"))
        assert len(pm.open_lots) == 0
        assert len(pm.closed_trades) == 2
    
    def test_sprt_position(self):
        pm = PositionManager()
        pm.add_position(Transaction.fromString("07/01/2021 8:57 PM,Trade,Buy to Open,SPRT,Buy,Open,200,,,,3.87,0.16,-774,Bought 200 SPRT @ 3.87,Individual...39"))
        lot = pm.open_lots[0]
        assert lot.symbol == 'SPRT'
        assert lot.quantity == 200
        assert lot.amount_usd == -774
    
    def test_true_fifo_stock_logic(self):
        pm = PositionManager()

        buy1_str = "01/01/2024 10:00 AM,Trade,Buy to Open,FIFO,Buy,Open,10,,,,,10.00,-100.00,Bought 10 FIFO @ 10,acc"
        
        buy2_str = "01/02/2024 10:00 AM,Trade,Buy to Open,FIFO,Buy,Open,10,,,,,10.00,-200.00,Bought 10 FIFO @ 20,acc"
        
        sell1_str = "01/03/2024 10:00 AM,Trade,Sell to Close,FIFO,Sell,Close,15,,,,,10.00,375.00,Sold 15 FIFO @ 25,acc"

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
        
        pm.add_position(Transaction.fromString("01/01/2024 9:00 AM,Trade,Buy to Open,XYZ,Buy,Open,100,,,,10,5,-1000,Bought 100 XYZ @ 10,Individual...39"))
        lot = pm.open_lots[0]
        assert lot.quantity == 100
        assert lot.amount_usd == -1000
        assert lot.fees_usd == 5
        
        pm.add_position(Transaction.fromString("01/02/2024 9:00 AM,Trade,Sell to Close,XYZ,Sell,Close,50,,,,12,3,600,Sold 50 XYZ @ 12,Individual...39"))
        
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
        
        pm.add_position(Transaction.fromString("01/01/2024 9:00 AM,Trade,Buy to Open,XYZ,Buy,Open,100,,,,10,5,-1000,Bought 100 XYZ @ 10,Individual...39"))
        
        pm.add_position(Transaction.fromString("01/02/2024 9:00 AM,Trade,Sell to Close,XYZ,Sell,Close,30,,,,12,3,360,Sold 30 XYZ @ 12,Individual...39"))
        
        lot = pm.open_lots[0]
        assert lot.quantity == 70
        assert abs(lot.amount_usd - (-700)) < 0.01
        
        pm.add_position(Transaction.fromString("01/03/2024 9:00 AM,Trade,Sell to Close,XYZ,Sell,Close,40,,,,15,4,600,Sold 40 XYZ @ 15,Individual...39"))
        
        lot = pm.open_lots[0]
        assert lot.quantity == 30
        assert abs(lot.amount_usd - (-300)) < 0.01
        
        assert len(pm.closed_trades) == 2
        
    def test_overclosing_position(self):
        """Test what happens when trying to close more shares than exist in position"""
        pm = PositionManager()
        
        pm.add_position(Transaction.fromString(
            "01/01/2024 9:00 AM,Trade,Buy to Open,XYZ,Buy,Open,10,,,,10,5,-100,Bought 10 XYZ @ 10,Individual...39"))
        
        with pytest.raises(ValueError, match="Tried to close more shares than available for XYZ"):
            pm.add_position(Transaction.fromString(
                "01/02/2024 9:00 AM,Trade,Sell to Close,XYZ,Sell,Close,20,,,,12,3,240,Sold 20 XYZ @ 12,Individual...39"))