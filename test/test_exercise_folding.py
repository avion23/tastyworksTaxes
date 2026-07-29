import pytest

from tastyworksTaxes.position import PositionType
from tastyworksTaxes.position_manager import PositionManager
from tastyworksTaxes.trade_calculator import calculate_option_sum
from tastyworksTaxes.transaction import Transaction


def transaction(
    date,
    subcode,
    action,
    symbol,
    instrument_type,
    amount,
    quantity,
    underlying,
    expiry="",
    strike="",
    call_put="",
    transaction_type="Trade",
):
    line = (
        f"{date},{transaction_type},{subcode},{action},{symbol},{instrument_type},"
        f"Synthetic {subcode},{amount},{quantity},0,0,0,100,{underlying},{underlying},"
        f"{expiry},{strike},{call_put},123456,USD"
    )
    return Transaction.fromString(line)


def test_long_call_exercise_folds_premium_into_stock_basis():
    pm = PositionManager()
    pm.add_position(transaction(
        "2025-01-02T10:00:00+0000", "Buy to Open", "BUY_TO_OPEN",
        "TECL  250117C00050000", "Equity Option", -500, 1, "TECL",
        "1/17/25", 50, "CALL",
    ))
    pm.add_position(transaction(
        "2025-01-17T10:00:00+0000", "Exercise", "EXERCISE",
        "TECL  250117C00050000", "Equity Option", 0, 1, "TECL",
        "1/17/25", 50, "CALL", "Receive Deliver",
    ))
    pm.add_position(transaction(
        "2025-01-17T10:00:00+0000", "Buy to Open", "BUY_TO_OPEN",
        "TECL", "Equity", -5000, 100, "TECL",
    ))

    option_trade = pm.closed_trades[0]
    assert option_trade.settled_by_exercise is True
    assert option_trade.profit_usd == 0
    assert option_trade.opening_profit_usd == -500
    assert calculate_option_sum(pm.closed_trades).usd == 0
    stock_lot = pm.get_all_open_lots()[0]
    assert stock_lot.amount_usd == -5500

    pm.add_position(transaction(
        "2025-02-03T10:00:00+0000", "Sell to Close", "SELL_TO_CLOSE",
        "TECL", "Equity", 6000, 100, "TECL",
    ))
    assert pm.closed_trades[-1].profit_usd == 500


def test_long_put_exercise_reduces_stock_proceeds():
    pm = PositionManager()
    pm.add_position(transaction(
        "2025-01-02T10:00:00+0000", "Buy to Open", "BUY_TO_OPEN",
        "TECL", "Equity", -6000, 100, "TECL",
    ))
    pm.add_position(transaction(
        "2025-01-03T10:00:00+0000", "Buy to Open", "BUY_TO_OPEN",
        "TECL  250117P00055000", "Equity Option", -400, 1, "TECL",
        "1/17/25", 55, "PUT",
    ))
    pm.add_position(transaction(
        "2025-01-17T10:00:00+0000", "Exercise", "EXERCISE",
        "TECL  250117P00055000", "Equity Option", 0, 1, "TECL",
        "1/17/25", 55, "PUT", "Receive Deliver",
    ))
    pm.add_position(transaction(
        "2025-01-17T10:00:00+0000", "Sell to Close", "SELL_TO_CLOSE",
        "TECL", "Equity", 5500, 100, "TECL", transaction_type="Receive Deliver",
    ))

    option_trade, stock_trade = pm.closed_trades
    assert option_trade.settled_by_exercise is True
    assert option_trade.profit_usd == 0
    assert calculate_option_sum(pm.closed_trades).usd == 0
    assert stock_trade.closing_profit_usd == 5100
    assert stock_trade.profit_usd == -900


def test_short_call_assignment_keeps_premium_separate():
    pm = PositionManager()
    pm.add_position(transaction(
        "2025-04-01T10:00:00+0000", "Buy to Open", "BUY_TO_OPEN",
        "TECL", "Equity", -4000, 100, "TECL",
    ))
    pm.add_position(transaction(
        "2025-05-01T10:00:00+0000", "Sell to Open", "SELL_TO_OPEN",
        "TECL  250516C00047000", "Equity Option", 570, 1, "TECL",
        "5/16/25", 47, "CALL",
    ))
    pm.add_position(transaction(
        "2025-05-16T10:00:00+0000", "Assignment", "ASSIGNMENT",
        "TECL  250516C00047000", "Equity Option", 0, 1, "TECL",
        "5/16/25", 47, "CALL", "Receive Deliver",
    ))
    pm.add_position(transaction(
        "2025-05-16T10:00:00+0000", "Sell to Close", "SELL_TO_CLOSE",
        "TECL", "Equity", 4700, 100, "TECL", transaction_type="Receive Deliver",
    ))

    option_trade, stock_trade = pm.closed_trades
    assert option_trade.settled_by_exercise is False
    assert option_trade.profit_usd == 570
    assert calculate_option_sum(pm.closed_trades).usd == 570
    assert stock_trade.closing_profit_usd == 4700


def test_short_put_assignment_keeps_premium_separate():
    pm = PositionManager()
    pm.add_position(transaction(
        "2025-03-01T10:00:00+0000", "Sell to Open", "SELL_TO_OPEN",
        "TECL  250321P00095000", "Equity Option", 1380, 1, "TECL",
        "3/21/25", 95, "PUT",
    ))
    pm.add_position(transaction(
        "2025-03-21T10:00:00+0000", "Assignment", "ASSIGNMENT",
        "TECL  250321P00095000", "Equity Option", 0, 1, "TECL",
        "3/21/25", 95, "PUT", "Receive Deliver",
    ))
    pm.add_position(transaction(
        "2025-03-21T10:00:00+0000", "Buy to Open", "BUY_TO_OPEN",
        "TECL", "Equity", -9500, 100, "TECL", transaction_type="Receive Deliver",
    ))

    assert pm.closed_trades[0].settled_by_exercise is False
    assert pm.closed_trades[0].profit_usd == 1380
    assert calculate_option_sum(pm.closed_trades).usd == 1380
    assert pm.get_all_open_lots()[0].position_type == PositionType.stock
    assert pm.get_all_open_lots()[0].amount_usd == -9500


def test_normal_option_closes_and_expiration_do_not_fold():
    pm = PositionManager()
    pm.add_position(transaction(
        "2025-01-02T10:00:00+0000", "Buy to Open", "BUY_TO_OPEN",
        "ONE  250117C00050000", "Equity Option", -500, 1, "ONE",
        "1/17/25", 50, "CALL",
    ))
    pm.add_position(transaction(
        "2025-01-10T10:00:00+0000", "Sell to Close", "SELL_TO_CLOSE",
        "ONE  250117C00050000", "Equity Option", 700, 1, "ONE",
        "1/17/25", 50, "CALL",
    ))
    pm.add_position(transaction(
        "2025-01-02T10:00:00+0000", "Buy to Open", "BUY_TO_OPEN",
        "TWO  250117P00040000", "Equity Option", -300, 1, "TWO",
        "1/17/25", 40, "PUT",
    ))
    pm.add_position(transaction(
        "2025-01-17T10:00:00+0000", "Expiration", "EXPIRED",
        "TWO  250117P00040000", "Equity Option", 0, 1, "TWO",
        "1/17/25", 40, "PUT", "Receive Deliver",
    ))

    assert [trade.profit_usd for trade in pm.closed_trades] == [200, -300]
    assert all(not trade.settled_by_exercise for trade in pm.closed_trades)
    assert pm._pending_exercise_basis == {}
    assert pm._pending_exercise_proceeds == {}


def test_long_assignment_is_accepted_as_exercise_and_unpaired_stays_pending(caplog):
    pm = PositionManager()
    pm.add_position(transaction(
        "2025-01-02T10:00:00+0000", "Buy to Open", "BUY_TO_OPEN",
        "ONE  250117C00050000", "Equity Option", -500, 1, "ONE",
        "1/17/25", 50, "CALL",
    ))
    pm.add_position(transaction(
        "2025-01-17T10:00:00+0000", "Assignment", "ASSIGNMENT",
        "ONE  250117C00050000", "Equity Option", 0, 1, "ONE",
        "1/17/25", 50, "CALL", "Receive Deliver",
    ))
    pm.warn_unmatched_exercise_adjustments()

    assert pm.closed_trades[0].settled_by_exercise is True
    assert pm._pending_exercise_basis[("2025-01-17", "ONE")].usd == 500
    assert "no paired stock delivery" in caplog.text
