import pytest
from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.transaction import Transaction

def test_true_fifo_option_logic():
    tasty = Tasty()

    buy1_str = "01/01/2024 10:00 AM,Trade,Buy to Open,SPY,Buy,Open,10,2025-12-19,400,C,10.00,1.00,-10000.00,Bought 10 SPY 400C @ 10.00,acc"

    buy2_str = "01/02/2024 10:00 AM,Trade,Buy to Open,SPY,Buy,Open,10,2025-12-19,400,C,20.00,1.00,-20000.00,Bought 10 SPY 400C @ 20.00,acc"

    sell1_str = "01/03/2024 10:00 AM,Trade,Sell to Close,SPY,Sell,Close,15,2025-12-19,400,C,25.00,1.00,37500.00,Sold 15 SPY 400C @ 25.00,acc"

    tasty.position_manager.add_position(Transaction.fromString(buy1_str))
    tasty.position_manager.add_position(Transaction.fromString(buy2_str))
    tasty.position_manager.add_position(Transaction.fromString(sell1_str))

    total_profit = sum(t.profit_usd for t in tasty.position_manager.closed_trades)
    assert round(total_profit, 2) == 17500.00

    remaining_lot = tasty.position_manager.open_lots[0]
    assert remaining_lot.quantity == 5

    remaining_cost_basis = remaining_lot.amount_usd
    assert round(remaining_cost_basis, 2) == -10000.00
