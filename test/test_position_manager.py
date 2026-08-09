import pytest
from datetime import datetime

from tastyworksTaxes.position_manager import PositionManager
from tastyworksTaxes.transaction import Transaction
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.position_lot import PositionLot

class TestPositionManager:
    def test_lfin_calls_open_and_close(self):
        pm = PositionManager()
        pm.add_position(Transaction.fromString("2018-03-12T17:08:00+0000,Trade,Buy to Open,BUY_TO_OPEN,LFIN  180615C00040000,Equity Option,Bought 2 LFIN 06/15/18 Call 40.00 @ 2.20,-440,2,220.00000000000003,-1.00,1.2799999999999998,100,LFIN,LFIN,6/15/18,40,CALL,123456,USD"))
        lot = pm.get_all_open_lots()[0]
        assert lot.symbol == 'LFIN'
        assert lot.quantity == 2
        
        pm.add_position(Transaction.fromString("2018-03-16T16:09:00+0000,Trade,Sell to Close,SELL_TO_CLOSE,LFIN  180615C00040000,Equity Option,Sold 1 LFIN 06/15/18 Call 40.00 @ 16.60,1660,1,1660.0000000000002,-1.00,0.18999999999999995,100,LFIN,LFIN,6/15/18,40,CALL,123456,USD"))
        lot = pm.get_all_open_lots()[0]
        assert lot.quantity == 1
        assert pm.closed_trades[0].quantity == 1
        
        pm.add_position(Transaction.fromString("2018-03-16T16:09:00+0000,Trade,Sell to Close,SELL_TO_CLOSE,LFIN  180615C00040000,Equity Option,Sold 1 LFIN 06/15/18 Call 40.00 @ 16.60,1660,1,1660.0000000000002,-1.00,0.18999999999999995,100,LFIN,LFIN,6/15/18,40,CALL,123456,USD"))
        assert len(pm.open_lots) == 0
        assert len(pm.closed_trades) == 2
    
    def test_sprt_position(self):
        pm = PositionManager()
        pm.add_position(Transaction.fromString("2021-07-01T20:57:00+0000,Trade,Buy to Open,BUY_TO_OPEN,SPRT,Equity,Bought 200 SPRT @ 3.87,-774,200,3.87,-1.00,0.16,,SPRT,SPRT,,,,123456,USD"))
        lot = pm.get_all_open_lots()[0]
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
        
        remaining_lot = pm.get_all_open_lots()[0]
        assert remaining_lot.quantity == 5
        
        remaining_cost_basis = remaining_lot.amount_usd
        assert round(remaining_cost_basis, 2) == -100.00
    
    def test_partial_closure_amounts(self):
        """Test correct prorating of values in partial position closures"""
        pm = PositionManager()
        
        pm.add_position(Transaction.fromString("2024-01-01T09:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,XYZ,Equity,Bought 100 XYZ @ 10,-1000,100,10,-1.00,4.0,,XYZ,XYZ,,,,123456,USD"))
        lot = pm.get_all_open_lots()[0]
        assert lot.quantity == 100
        assert lot.amount_usd == -1000
        assert lot.fees_usd == 5
        
        pm.add_position(Transaction.fromString("2024-01-02T09:00:00+0000,Trade,Sell to Close,SELL_TO_CLOSE,XYZ,Equity,Sold 50 XYZ @ 12,600,50,12,-1.00,2.0,,XYZ,XYZ,,,,123456,USD"))
        
        lot = pm.get_all_open_lots()[0]
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
        
        lot = pm.get_all_open_lots()[0]
        assert lot.quantity == 70
        assert abs(lot.amount_usd - (-700)) < 0.01
        
        pm.add_position(Transaction.fromString("2024-01-03T09:00:00+0000,Trade,Sell to Close,SELL_TO_CLOSE,XYZ,Equity,Sold 40 XYZ @ 15,600,40,15,-1.00,3.0,,XYZ,XYZ,,,,123456,USD"))
        
        lot = pm.get_all_open_lots()[0]
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
    def test_overclose_is_atomic(self):
        pm = PositionManager()
        pm.add_position(Transaction.fromString("2024-01-01T09:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,XYZ,Equity,Bought 10 XYZ @ 10,-100,10,10,-1.00,0,,XYZ,XYZ,,,,123456,USD"))
        with pytest.raises(ValueError):
            pm.add_position(Transaction.fromString("2024-01-02T09:00:00+0000,Trade,Sell to Close,SELL_TO_CLOSE,XYZ,Equity,Sold 20 XYZ @ 12,240,20,12,-1.00,0,,XYZ,XYZ,,,,123456,USD"))
        assert pm.get_all_open_lots()[0].quantity == 10
        assert pm.closed_trades == []

    def test_closes_matching_direction_when_long_and_short_lots_coexist(self):
        pm = PositionManager()
        pm.add_lot_directly(PositionLot("MIX", PositionType.stock, 10, -100, -100, 0, 0, datetime(2024, 1, 1)))
        pm.add_lot_directly(PositionLot("MIX", PositionType.stock, -5, 50, 50, 0, 0, datetime(2024, 1, 2)))
        pm.add_position(Transaction.fromString("2024-01-03T09:00:00+0000,Trade,Buy to Close,BUY_TO_CLOSE,MIX,Equity,Bought 5 MIX @ 9,-45,5,9,-1.00,0,,MIX,MIX,,,,123456,USD"))
        assert [lot.quantity for lot in pm.get_all_open_lots()] == [10]
        assert pm.closed_trades[0].quantity == -5

    def test_close_direction_uses_quantity_not_cash_sign(self):
        pm = PositionManager()
        pm.add_lot_directly(PositionLot("DIR", PositionType.stock, 1, 100, 100, 0, 0, datetime(2024, 1, 1)))
        pm.add_position(Transaction.fromString("2024-01-02T09:00:00+0000,Trade,Sell to Close,SELL_TO_CLOSE,DIR,Equity,Sold 1 DIR @ 90,90,1,90,-1.00,0,,DIR,DIR,,,,123456,USD"))
        assert pm.closed_trades[0].quantity == 1

    def test_symbol_change_moves_multiple_lots_and_partial_basis(self):
        pm = PositionManager()
        pm.add_position(Transaction.fromString("2024-01-01T09:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,OLD,Equity,Bought 10 OLD @ 10,-100,10,10,-1.00,0,,OLD,OLD,,,,123456,USD"))
        pm.add_position(Transaction.fromString("2024-01-02T09:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,OLD,Equity,Bought 10 OLD @ 20,-200,10,20,-1.00,0,,OLD,OLD,,,,123456,USD"))
        pm.add_position(Transaction.fromString("2024-01-03T09:00:00+0000,Receive Deliver,Symbol Change,SELL,OLD,Equity,Symbol change,0,15,0,0,0,,OLD,OLD,,,,123456,USD"))
        pm.add_position(Transaction.fromString("2024-01-03T09:00:00+0000,Receive Deliver,Symbol Change,BUY,NEW,Equity,Symbol change,0,30,0,0,0,,NEW,NEW,,,,123456,USD"))
        old, new = [lot for lot in pm.get_all_open_lots() if lot.symbol == "OLD"], [lot for lot in pm.get_all_open_lots() if lot.symbol == "NEW"]
        assert [(lot.quantity, lot.amount_usd) for lot in old] == [(5, -100)]
        assert [(lot.quantity, lot.amount_usd) for lot in new] == [(20, -100), (10, -100)]

    def test_stock_shaped_reverse_split_does_not_adjust_option(self):
        pm = PositionManager()
        expiry = datetime(2024, 6, 21)
        option = PositionLot(
            "OPT", PositionType.call, 2, -100, -100, 0, 0,
            datetime(2024, 1, 1), 100, expiry, "C",
        )
        pm.add_lot_directly(option)

        pm.add_position(Transaction.fromString(
            "2024-02-01T09:00:00+0000,Receive Deliver,Reverse Split,BUY,OPT,Equity,OPT reverse split 1:2,0,0,0,0,0,,OPT,OPT,,,,123456,USD"
        ))

        assert pm.get_all_open_lots() == [option]
        assert (option.quantity, option.strike, option.amount_usd) == (2, 100, -100)

    def test_symbol_change_open_does_not_consume_existing_new_symbol_lot(self):
        pm = PositionManager()
        pm.add_position(Transaction.fromString("2024-01-01T09:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,OLD,Equity,Bought 10 OLD @ 10,-100,10,10,-1.00,0,,OLD,OLD,,,,123456,USD"))
        pm.add_position(Transaction.fromString("2024-01-01T09:01:00+0000,Trade,Sell to Open,SELL_TO_OPEN,NEW,Equity,Sold 5 NEW @ 15,75,5,15,-1.00,0,,NEW,NEW,,,,123456,USD"))
        pm.add_position(Transaction.fromString("2024-01-02T09:00:00+0000,Receive Deliver,Symbol Change,SELL_TO_CLOSE,OLD,Equity,Symbol change close,0,10,0,0,0,,OLD,OLD,,,,123456,USD"))
        pm.add_position(Transaction.fromString("2024-01-02T09:00:00+0000,Receive Deliver,Symbol Change,BUY_TO_OPEN,NEW,Equity,Symbol change open,0,10,0,0,0,,NEW,NEW,,,,123456,USD"))

        assert sorted((lot.quantity, lot.amount_usd) for lot in pm.get_all_open_lots()) == [
            (-5, 75),
            (10, -100),
        ]
        assert pm._pending_symbol_change_lots == {}

    def test_simultaneous_stock_and_option_symbol_changes_keep_bases_separate(self):
        pm = PositionManager()
        stock_open = Transaction.fromString("2024-01-01T09:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,OLD,Equity,Bought stock,-100,10,10,0,0,,OLD,OLD,,,,123456,USD")
        option_open = Transaction.fromString("2024-01-01T09:01:00+0000,Trade,Sell to Open,SELL_TO_OPEN,OLD  240621P00010000,Equity Option,Sold put,50,1,50,0,0,100,OLD,OLD,6/21/24,10,PUT,123456,USD")
        pm.add_position(stock_open)
        pm.add_position(option_open)

        pm.add_position(Transaction.fromString("2024-01-02T09:00:00+0000,Receive Deliver,Symbol Change,SELL_TO_CLOSE,OLD,Equity,Stock close,0,10,0,0,0,,OLD,OLD,,,,123456,USD"))
        pm.add_position(Transaction.fromString("2024-01-02T09:00:00+0000,Receive Deliver,Symbol Change,BUY_TO_CLOSE,OLD  240621P00010000,Equity Option,Option close,0,1,0,0,0,100,OLD,OLD,6/21/24,10,PUT,123456,USD"))
        pm.add_position(Transaction.fromString("2024-01-02T09:00:00+0000,Receive Deliver,Symbol Change,BUY_TO_OPEN,NEW,Equity,Stock open,0,10,0,0,0,,NEW,NEW,,,,123456,USD"))
        pm.add_position(Transaction.fromString("2024-01-02T09:00:00+0000,Receive Deliver,Symbol Change,SELL_TO_OPEN,NEW  240621P00010000,Equity Option,Option open,0,1,0,0,0,100,NEW,NEW,6/21/24,10,PUT,123456,USD"))

        lots = pm.get_all_open_lots()
        assert [(lot.position_type, lot.amount_usd) for lot in lots] == [
            (PositionType.stock, -100),
            (PositionType.put, 50),
        ]
        assert pm._pending_symbol_change_lots == {}
