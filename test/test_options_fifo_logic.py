import pytest
from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.transaction import Transaction

def test_true_fifo_option_logic():
    tasty = Tasty()

    buy1_str = "2024-01-01T10:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,SPY  251219C00400000,Equity Option,Bought 10 SPY 400C @ 10.00,-10000.00,10,1000.0,-1.00,0.0,100,SPY,SPY,12/19/25,400,CALL,123456,USD"

    buy2_str = "2024-01-02T10:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,SPY  251219C00400000,Equity Option,Bought 10 SPY 400C @ 20.00,-20000.00,10,2000.0,-1.00,0.0,100,SPY,SPY,12/19/25,400,CALL,123456,USD"

    sell1_str = "2024-01-03T10:00:00+0000,Trade,Sell to Close,SELL_TO_CLOSE,SPY  251219C00400000,Equity Option,Sold 15 SPY 400C @ 25.00,37500.00,15,2500.0,-1.00,0.0,100,SPY,SPY,12/19/25,400,CALL,123456,USD"

    tasty.position_manager.add_position(Transaction.fromString(buy1_str))
    tasty.position_manager.add_position(Transaction.fromString(buy2_str))
    tasty.position_manager.add_position(Transaction.fromString(sell1_str))

    total_profit = sum(t.profit_usd for t in tasty.position_manager.closed_trades)
    assert round(total_profit, 2) == 17500.00

    remaining_lot = tasty.position_manager.open_lots[0]
    assert remaining_lot.quantity == 5

    remaining_cost_basis = remaining_lot.amount_usd
    assert round(remaining_cost_basis, 2) == -10000.00
