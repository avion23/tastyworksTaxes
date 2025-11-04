import pytest
from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.transaction import Transaction

def test_long_option_quantity_sign_fix():
    """
    Test that long options (BUY_TO_OPEN) show positive quantities in TradeResults.

    This test verifies the fix for the bug where opening_lot.quantity was checked
    AFTER lot.consume() modified it to 0, causing long options to be misclassified
    as short options (negative quantity).

    Real data from NKLA 22C trades (2020-09-29 to 2020-10-01):
    - BUY_TO_OPEN 1 @ $85
    - BUY_TO_OPEN 2 @ $170
    - SELL_TO_CLOSE 2 @ $698 (closes the 2-contract lot)
    - SELL_TO_CLOSE 1 @ $349 (closes the 1-contract lot)

    Expected: Both trades should show POSITIVE quantities (long options)
    Bug would cause: Negative quantities (misclassified as short)
    """
    tasty = Tasty()

    buy1_str = "2020-09-29T16:30:52+0200,Trade,Buy to Open,BUY_TO_OPEN,NKLA  201009C00022000,Equity Option,Bought 1 NKLA 10/09/20 Call 22.00 @ 0.85,-85.00,1,-85.00,-1.00,-0.14,100.0,NKLA,NKLA,10/09/20,22.0,CALL,104942780.0,USD"

    buy2_str = "2020-09-29T16:30:52+0200,Trade,Buy to Open,BUY_TO_OPEN,NKLA  201009C00022000,Equity Option,Bought 2 NKLA 10/09/20 Call 22.00 @ 0.85,-170.00,2,-85.00,-2.00,-0.27,100.0,NKLA,NKLA,10/09/20,22.0,CALL,104942780.0,USD"

    sell1_str = "2020-10-01T16:24:05+0200,Trade,Sell to Close,SELL_TO_CLOSE,NKLA  201009C00022000,Equity Option,Sold 2 NKLA 10/09/20 Call 22.00 @ 3.49,698.00,2,349.00,0.00,-0.29,100.0,NKLA,NKLA,10/09/20,22.0,CALL,105398837.0,USD"

    sell2_str = "2020-10-01T16:24:05+0200,Trade,Sell to Close,SELL_TO_CLOSE,NKLA  201009C00022000,Equity Option,Sold 1 NKLA 10/09/20 Call 22.00 @ 3.49,349.00,1,349.00,0.00,-0.15,100.0,NKLA,NKLA,10/09/20,22.0,CALL,105398837.0,USD"

    tasty.position_manager.add_position(Transaction.fromString(buy1_str))
    tasty.position_manager.add_position(Transaction.fromString(buy2_str))
    tasty.position_manager.add_position(Transaction.fromString(sell1_str))
    tasty.position_manager.add_position(Transaction.fromString(sell2_str))

    closed_trades = tasty.position_manager.closed_trades

    assert len(closed_trades) == 3, f"Expected 3 closed trades, got {len(closed_trades)}"

    for i, trade in enumerate(closed_trades):
        assert trade.quantity > 0, (
            f"Trade {i+1} has negative quantity {trade.quantity}. "
            f"Long options (BUY_TO_OPEN) must have positive quantities. "
            f"This indicates the quantity sign bug is present."
        )

    quantities = sorted([trade.quantity for trade in closed_trades])
    assert quantities == [1, 1, 1], f"Expected quantities [1, 1, 1], got {quantities}"

    total_profit_usd = sum(t.profit_usd for t in closed_trades)
    assert 785 < total_profit_usd <= 792, (
        f"Unexpected profit calculation: {total_profit_usd}. "
        f"Expected approximately 788-792 USD"
    )

    assert len(tasty.position_manager.open_lots) == 0, "All positions should be closed"


def test_short_option_quantity_sign():
    """
    Test that short options (SELL_TO_OPEN) show negative quantities in TradeResults.

    This ensures the sign convention is consistent:
    - Long (BUY_TO_OPEN) = positive quantity
    - Short (SELL_TO_OPEN) = negative quantity
    """
    tasty = Tasty()

    sell_open_str = "2020-09-29T16:30:52+0200,Trade,Sell to Open,SELL_TO_OPEN,NKLA  201009C00017000,Equity Option,Sold 2 NKLA 10/09/20 Call 17.00 @ 3.01,602.00,2,301.00,-2.00,-0.29,100.0,NKLA,NKLA,10/09/20,17.0,CALL,104942780.0,USD"

    buy_close_str = "2020-10-05T19:06:32+0200,Trade,Buy to Close,BUY_TO_CLOSE,NKLA  201009C00017000,Equity Option,Bought 1 NKLA 10/09/20 Call 17.00 @ 6.04,-604.00,1,-604.00,0.00,-0.14,100.0,NKLA,NKLA,10/09/20,17.0,CALL,105952215.0,USD"

    tasty.position_manager.add_position(Transaction.fromString(sell_open_str))
    tasty.position_manager.add_position(Transaction.fromString(buy_close_str))

    closed_trades = tasty.position_manager.closed_trades

    assert len(closed_trades) == 1, f"Expected 1 closed trade, got {len(closed_trades)}"

    trade = closed_trades[0]
    assert trade.quantity < 0, (
        f"Short option has positive quantity {trade.quantity}. "
        f"Short options (SELL_TO_OPEN) must have negative quantities."
    )

    assert trade.quantity == -1, f"Expected quantity -1, got {trade.quantity}"

    assert -305 < trade.profit_usd < -300, (
        f"Unexpected profit: {trade.profit_usd}. Expected ~-303 USD"
    )


def test_partial_close_maintains_sign():
    """
    Test that partially closing a long position maintains positive quantity
    for both the closed trade and remaining open lot.

    This is an edge case: the bug only affected FULLY consumed lots (quantity = 0).
    Partial closes should always work correctly.
    """
    tasty = Tasty()

    buy_str = "2024-01-01T10:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,SPY  251219C00400000,Equity Option,Bought 10 SPY 400C @ 10.00,-10000.00,10,1000.0,-10.00,0.0,100,SPY,SPY,12/19/25,400,CALL,123456,USD"

    sell_str = "2024-01-02T10:00:00+0000,Trade,Sell to Close,SELL_TO_CLOSE,SPY  251219C00400000,Equity Option,Sold 3 SPY 400C @ 15.00,4500.00,3,1500.0,-3.00,0.0,100,SPY,SPY,12/19/25,400,CALL,123456,USD"

    tasty.position_manager.add_position(Transaction.fromString(buy_str))
    tasty.position_manager.add_position(Transaction.fromString(sell_str))

    closed_trades = tasty.position_manager.closed_trades
    assert len(closed_trades) == 1
    assert closed_trades[0].quantity == 3, "Closed trade quantity should be positive"

    open_lots = tasty.position_manager.get_all_open_lots()
    assert len(open_lots) == 1
    assert open_lots[0].quantity == 7, "Remaining lot should have 7 contracts (positive)"
