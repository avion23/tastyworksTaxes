import pytest
from tastyworksTaxes.position_manager import PositionManager
from tastyworksTaxes.transaction import Transaction

def test_true_fifo_stock_logic():
    pm = PositionManager()

    buy1_str = "2024-01-01T10:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,FIFO,Equity,Bought 10 FIFO @ 10,-100.00,10,,-1.00,9.0,,FIFO,FIFO,,,,123456,USD"

    buy2_str = "2024-01-02T10:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,FIFO,Equity,Bought 10 FIFO @ 20,-200.00,10,,-1.00,9.0,,FIFO,FIFO,,,,123456,USD"

    sell1_str = "2024-01-03T10:00:00+0000,Trade,Sell to Close,SELL_TO_CLOSE,FIFO,Equity,Sold 15 FIFO @ 25,375.00,15,,-1.00,9.0,,FIFO,FIFO,,,,123456,USD"

    pm.add_position(Transaction.fromString(buy1_str))
    pm.add_position(Transaction.fromString(buy2_str))
    pm.add_position(Transaction.fromString(sell1_str))
    
    total_profit = sum(t.profit_usd for t in pm.closed_trades)

    assert round(total_profit, 2) == 175.00

    remaining_lots = pm.get_all_open_lots()
    assert len(remaining_lots) == 1
    remaining_lot = remaining_lots[0]
    assert remaining_lot.quantity == 5

    remaining_cost_basis = remaining_lot.amount_usd
    assert round(remaining_cost_basis, 2) == -100.00