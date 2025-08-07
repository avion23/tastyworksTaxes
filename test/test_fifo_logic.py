import pytest
from tastyworksTaxes.position_manager import PositionManager
from tastyworksTaxes.transaction import Transaction

def test_true_fifo_stock_logic():
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