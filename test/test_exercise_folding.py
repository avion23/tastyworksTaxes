from datetime import datetime

import pytest

from tastyworksTaxes.history import History
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.position_lot import PositionLot
from tastyworksTaxes.position_manager import PositionManager, OPTION_SETTLEMENT_FIELD
from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.trade_calculator import (
    calculate_long_option_losses,
    calculate_long_option_profits,
    calculate_option_differential,
    calculate_option_sum,
    calculate_short_option_losses,
    calculate_short_option_profits,
)
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
    commissions=0,
    fees=0,
    option_settlement=None,
):
    line = (
        f"{date},{transaction_type},{subcode},{action},{symbol},{instrument_type},"
        f"Synthetic {subcode},{amount},{quantity},0,{commissions},{fees},100,{underlying},{underlying},"
        f"{expiry},{strike},{call_put},123456,USD"
    )
    result = Transaction.fromString(line)
    if option_settlement is not None:
        result[OPTION_SETTLEMENT_FIELD] = option_settlement
    return result


def option_tax_values(trades):
    tasty = Tasty()
    tasty.processTransactionHistory = lambda: None
    tasty.position_manager.closed_trades = trades
    return tasty.run()[2025]


def assert_exercise_excluded_from_option_tax(trade):
    trades = [trade]
    assert calculate_option_sum(trades).usd == 0
    assert calculate_long_option_profits(trades).usd == 0
    assert calculate_long_option_losses(trades).usd == 0
    assert calculate_short_option_profits(trades).usd == 0
    assert calculate_short_option_losses(trades).usd == 0
    assert calculate_option_differential(trades).usd == 0
    values = option_tax_values(trades)
    assert values.z21_termingeschaefsgewinne.usd == pytest.approx(0, abs=1e-12)
    assert values.z21_termingeschaefsgewinne.eur == pytest.approx(0, abs=1e-12)
    assert values.z24_termingeschaefte_verluste.usd == pytest.approx(0, abs=1e-12)
    assert values.z24_termingeschaefte_verluste.eur == pytest.approx(0, abs=1e-12)


def test_long_call_exercise_folds_premium_into_stock_basis():
    pm = PositionManager()
    option_open = transaction(
        "2025-01-02T10:00:00+0000", "Buy to Open", "BUY_TO_OPEN",
        "TECL  250117C00050000", "Equity Option", -500, 1, "TECL",
        "1/17/25", 50, "CALL", commissions=0.50,
    )
    pm.add_position(option_open)
    pm.add_position(transaction(
        "2025-01-17T10:00:00+0000", "Exercise", "EXERCISE",
        "TECL  250117C00050000", "Equity Option", 0, 1, "TECL",
        "1/17/25", 50, "CALL", "Receive Deliver",
    ))
    stock_delivery = transaction(
        "2025-01-17T10:00:00+0000", "Buy to Open", "BUY_TO_OPEN",
        "TECL", "Equity", -5000, 100, "TECL",
        transaction_type="Receive Deliver", commissions=1.25,
        option_settlement="Exercise",
    )
    pm.add_position(stock_delivery)

    option_trade = pm.closed_trades[0]
    assert option_trade.settled_by_exercise is True
    assert option_trade.profit_usd == 0
    assert option_trade.opening_profit_usd == -500
    assert_exercise_excluded_from_option_tax(option_trade)
    stock_lot = pm.get_all_open_lots()[0]
    assert stock_lot.amount_usd == -5500
    assert stock_lot.amount_eur == pytest.approx(
        stock_delivery.getValue().eur + option_open.getValue().eur
    )
    assert stock_lot.fees_usd == 1.75
    assert option_trade.fees_usd == 0

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
    option_open = transaction(
        "2025-01-03T10:00:00+0000", "Buy to Open", "BUY_TO_OPEN",
        "TECL  250117P00055000", "Equity Option", -400, 1, "TECL",
        "1/17/25", 55, "PUT", commissions=0.50,
    )
    pm.add_position(option_open)
    pm.add_position(transaction(
        "2025-01-17T10:00:00+0000", "Exercise", "EXERCISE",
        "TECL  250117P00055000", "Equity Option", 0, 1, "TECL",
        "1/17/25", 55, "PUT", "Receive Deliver",
    ))
    stock_delivery = transaction(
        "2025-01-17T10:00:00+0000", "Sell to Close", "SELL_TO_CLOSE",
        "TECL", "Equity", 5500, 100, "TECL", transaction_type="Receive Deliver",
        commissions=1.25, option_settlement="Exercise",
    )
    pm.add_position(stock_delivery)

    option_trade, stock_trade = pm.closed_trades
    assert option_trade.settled_by_exercise is True
    assert option_trade.profit_usd == 0
    assert_exercise_excluded_from_option_tax(option_trade)
    assert stock_trade.closing_profit_usd == 5100
    assert stock_trade.closing_profit_eur == pytest.approx(
        stock_delivery.getValue().eur + option_open.getValue().eur
    )
    assert stock_trade.closing_fees_usd == 1.75
    assert option_trade.fees_usd == 0
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
        option_settlement="Assignment",
    ))

    option_trade, stock_trade = pm.closed_trades
    assert option_trade.settled_by_exercise is False
    assert option_trade.profit_usd == 570
    assert calculate_option_sum(pm.closed_trades).usd == 570
    assert option_tax_values([option_trade]).z21_termingeschaefsgewinne.usd == 570
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
        option_settlement="Assignment",
    ))

    assert pm.closed_trades[0].settled_by_exercise is False
    assert pm.closed_trades[0].profit_usd == 1380
    assert calculate_option_sum(pm.closed_trades).usd == 1380
    assert option_tax_values([pm.closed_trades[0]]).z21_termingeschaefsgewinne.usd == 1380
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
    assert pm._pending_exercises == {}


def test_long_assignment_is_rejected_without_mutation():
    pm = PositionManager()
    pm.add_position(transaction(
        "2025-01-02T10:00:00+0000", "Buy to Open", "BUY_TO_OPEN",
        "ONE  250117C00050000", "Equity Option", -500, 1, "ONE",
        "1/17/25", 50, "CALL",
    ))
    assignment = transaction(
        "2025-01-17T10:00:00+0000", "Assignment", "ASSIGNMENT",
        "ONE  250117C00050000", "Equity Option", 0, 1, "ONE",
        "1/17/25", 50, "CALL", "Receive Deliver",
    )

    with pytest.raises(ValueError, match="LONG OPTION ASSIGNMENT IS AMBIGUOUS"):
        pm.add_position(assignment)

    assert pm.closed_trades == []
    assert pm.get_all_open_lots()[0].quantity == 1
    assert pm._pending_exercises == {}


def test_multiple_same_day_exercises_fold_by_quantity_fifo():
    pm = PositionManager()
    for strike, premium in ((50, 100), (60, 200)):
        pm.add_position(transaction(
            "2025-01-02T10:00:00+0000", "Buy to Open", "BUY_TO_OPEN",
            f"TECL  250117C000{strike}000", "Equity Option", -premium, 1,
            "TECL", "1/17/25", strike, "CALL",
        ))
        pm.add_position(transaction(
            "2025-01-17T10:00:00+0000", "Exercise", "EXERCISE",
            f"TECL  250117C000{strike}000", "Equity Option", 0, 1,
            "TECL", "1/17/25", strike, "CALL", "Receive Deliver",
        ))

    pm.add_position(transaction(
        "2025-01-17T10:01:00+0000", "Buy to Open", "BUY_TO_OPEN",
        "TECL", "Equity", -5000, 100, "TECL",
        transaction_type="Receive Deliver", commissions=1.25,
        option_settlement="Exercise",
    ))
    pm.add_position(transaction(
        "2025-01-17T10:02:00+0000", "Buy to Open", "BUY_TO_OPEN",
        "TECL", "Equity", -6000, 100, "TECL",
        transaction_type="Receive Deliver", commissions=1.50,
        option_settlement="Exercise",
    ))

    lots = pm.get_all_open_lots()
    assert [lot.amount_usd for lot in lots] == [-5100, -6200]
    assert [lot.fees_usd for lot in lots] == [1.25, 1.50]
    assert pm._pending_exercises == {}


def test_receive_deliver_exercise_precedes_earlier_timestamp_stock_row():
    option_open = transaction(
        "2025-01-17T12:00:00+0000", "Buy to Open", "BUY_TO_OPEN",
        "TECL  250117C00050000", "Equity Option", -500, 1, "TECL",
        "1/17/25", 50, "CALL",
    )
    stock_delivery = transaction(
        "2025-01-17T08:00:00+0000", "Buy to Open", "BUY_TO_OPEN",
        "TECL", "Equity", -5000, 100, "TECL",
        transaction_type="Receive Deliver",
    )
    exercise = transaction(
        "2025-01-17T16:00:00+0000", "Exercise", "EXERCISE",
        "TECL  250117C00050000", "Equity Option", 0, 1, "TECL",
        "1/17/25", 50, "CALL", "Receive Deliver",
    )
    tasty = Tasty()
    tasty.history = History([option_open, stock_delivery, exercise])

    tasty.processTransactionHistory()

    assert tasty.position_manager.get_all_open_lots()[0].amount_usd == -5500
    assert tasty.position_manager._pending_exercises == {}


@pytest.mark.parametrize(
    "call_put,existing_stock,delivery_subcode,delivery_action,opening_cash,"
    "delivery_cash,premium,expected_stock_cash,expected_profit",
    [
        ("CALL", None, "Buy to Open", "BUY_TO_OPEN", None, -5000, -500, -5500, None),
        ("CALL", "short", "Buy to Close", "BUY_TO_CLOSE", 6000, -5000, -500, -5500, 500),
        ("PUT", "long", "Sell to Close", "SELL_TO_CLOSE", -6000, 5500, -400, 5100, -900),
        ("PUT", None, "Sell to Open", "SELL_TO_OPEN", None, 5500, -400, 5100, None),
    ],
)
def test_long_exercise_cash_and_fees_conserve_for_every_stock_state(
    call_put,
    existing_stock,
    delivery_subcode,
    delivery_action,
    opening_cash,
    delivery_cash,
    premium,
    expected_stock_cash,
    expected_profit,
):
    pm = PositionManager()
    if existing_stock:
        opening_subcode = "Sell to Open" if existing_stock == "short" else "Buy to Open"
        opening_action = "SELL_TO_OPEN" if existing_stock == "short" else "BUY_TO_OPEN"
        pm.add_position(transaction(
            "2025-01-01T10:00:00+0000", opening_subcode, opening_action,
            "XYZ", "Equity", opening_cash, 100, "XYZ",
        ))

    letter = "C" if call_put == "CALL" else "P"
    option_open = transaction(
        "2025-01-02T10:00:00+0000", "Buy to Open", "BUY_TO_OPEN",
        f"XYZ  250117{letter}00050000", "Equity Option", premium, 1,
        "XYZ", "1/17/25", 50, call_put, commissions=2,
    )
    pm.add_position(option_open)
    pm.add_position(transaction(
        "2025-01-17T10:00:00+0000", "Exercise", "EXERCISE",
        f"XYZ  250117{letter}00050000", "Equity Option", 0, 1,
        "XYZ", "1/17/25", 50, call_put, "Receive Deliver",
    ))
    stock_delivery = transaction(
        "2025-01-17T10:00:00+0000", delivery_subcode, delivery_action,
        "XYZ", "Equity", delivery_cash, 100, "XYZ",
        transaction_type="Receive Deliver", commissions=1,
        option_settlement="Exercise",
    )
    pm.add_position(stock_delivery)
    pm.validate_no_pending_adjustments()

    option_trade = next(
        trade for trade in pm.closed_trades if trade.position_type != PositionType.stock
    )
    assert option_trade.settled_by_exercise is True
    assert option_trade.fees_usd == 0
    expected_fees = option_open.getFees().usd + stock_delivery.getFees().usd
    expected_fees_eur = option_open.getFees().eur + stock_delivery.getFees().eur
    expected_cash_eur = option_open.getValue().eur + stock_delivery.getValue().eur

    if existing_stock:
        stock_trade = next(
            trade for trade in pm.closed_trades
            if trade.position_type == PositionType.stock
        )
        assert stock_trade.closing_profit_usd == expected_stock_cash
        assert stock_trade.closing_profit_eur == pytest.approx(expected_cash_eur)
        assert stock_trade.closing_fees_usd == expected_fees
        assert stock_trade.closing_fees_eur == pytest.approx(expected_fees_eur)
        assert stock_trade.profit_usd == expected_profit
        return

    stock_lot = next(
        lot for lot in pm.get_all_open_lots()
        if lot.position_type == PositionType.stock
    )
    assert stock_lot.amount_usd == expected_stock_cash
    assert stock_lot.amount_eur == pytest.approx(expected_cash_eur)
    assert stock_lot.fees_usd == expected_fees
    assert stock_lot.fees_eur == pytest.approx(expected_fees_eur)


def test_partial_exercise_delivery_fails_before_stock_mutation():
    pm = PositionManager()
    pm.add_position(transaction(
        "2025-01-02T10:00:00+0000", "Buy to Open", "BUY_TO_OPEN",
        "XYZ  250117C00050000", "Equity Option", -500, 1, "XYZ",
        "1/17/25", 50, "CALL", commissions=2,
    ))
    pm.add_position(transaction(
        "2025-01-17T10:00:00+0000", "Exercise", "EXERCISE",
        "XYZ  250117C00050000", "Equity Option", 0, 1, "XYZ",
        "1/17/25", 50, "CALL", "Receive Deliver",
    ))
    delivery = transaction(
        "2025-01-17T10:00:00+0000", "Buy to Open", "BUY_TO_OPEN",
        "XYZ", "Equity", -7500, 150, "XYZ",
        transaction_type="Receive Deliver", commissions=1,
        option_settlement="Exercise",
    )

    with pytest.raises(ValueError, match="PARTIAL EXERCISE ADJUSTMENT"):
        pm.add_position(delivery)

    assert not any(
        lot.position_type == PositionType.stock
        for lot in pm.get_all_open_lots()
    )
    assert pm._pending_exercises[("2025-01-17", "XYZ", "buy")][0].remaining_shares == 100


@pytest.mark.parametrize("assignment_stock_first", [True, False])
def test_same_day_exercise_and_assignment_use_only_exercise_stock_leg(
    assignment_stock_first,
):
    long_call = transaction(
        "2025-01-02T10:00:00+0000", "Buy to Open", "BUY_TO_OPEN",
        "XYZ  250117C00050000", "Equity Option", -500, 1, "XYZ",
        "1/17/25", 50, "CALL", commissions=2,
    )
    short_put = transaction(
        "2025-01-03T10:00:00+0000", "Sell to Open", "SELL_TO_OPEN",
        "XYZ  250117P00060000", "Equity Option", 300, 1, "XYZ",
        "1/17/25", 60, "PUT",
    )
    exercise = transaction(
        "2025-01-17T12:00:00+0000", "Exercise", "EXERCISE",
        "XYZ  250117C00050000", "Equity Option", 0, 1, "XYZ",
        "1/17/25", 50, "CALL", "Receive Deliver",
    )
    assignment = transaction(
        "2025-01-17T13:00:00+0000", "Assignment", "ASSIGNMENT",
        "XYZ  250117P00060000", "Equity Option", 0, 1, "XYZ",
        "1/17/25", 60, "PUT", "Receive Deliver",
    )
    exercise_stock = transaction(
        "2025-01-17T09:00:00+0000", "Buy to Open", "BUY_TO_OPEN",
        "XYZ", "Equity", -5000, 100, "XYZ",
        transaction_type="Receive Deliver", commissions=1,
    )
    assignment_stock = transaction(
        "2025-01-17T08:00:00+0000", "Buy to Open", "BUY_TO_OPEN",
        "XYZ", "Equity", -6000, 100, "XYZ",
        transaction_type="Receive Deliver", commissions=1,
    )
    stock_rows = (
        [assignment_stock, exercise_stock]
        if assignment_stock_first
        else [exercise_stock, assignment_stock]
    )
    tasty = Tasty()
    tasty.history = History([
        long_call, short_put, *stock_rows, assignment, exercise,
    ])

    tasty.processTransactionHistory()

    stock_lots = [
        lot for lot in tasty.position_manager.get_all_open_lots()
        if lot.position_type == PositionType.stock
    ]
    assert sorted((lot.amount_usd, lot.fees_usd) for lot in stock_lots) == [
        (-6000, 1), (-5500, 3),
    ]
    option_trades = [
        trade for trade in tasty.position_manager.closed_trades
        if trade.position_type != PositionType.stock
    ]
    assert sorted((trade.profit_usd, trade.fees_usd) for trade in option_trades) == [
        (0, 0), (300, 0),
    ]
    assert sum(lot.amount_usd for lot in stock_lots) + sum(
        trade.profit_usd for trade in option_trades
    ) == -11200
    assert sum(lot.fees_usd for lot in stock_lots) + sum(
        trade.fees_usd for trade in option_trades
    ) == 4


def test_short_assignment_ignores_later_long_lot_and_invalid_multiplier():
    pm = PositionManager()
    expiry = Transaction.fromString(
        "2025-01-17T10:00:00+0000,Trade,Sell to Open,SELL_TO_OPEN,XYZ  250117P00050000,Equity Option,open,100,1,100,0,0,100,XYZ,XYZ,1/17/25,50,PUT,1,USD"
    ).getExpiry()
    short_lot = PositionLot(
        "XYZ", PositionType.put, -1, 100, 90, 0, 0,
        datetime(2025, 1, 2), 50, expiry, "P",
    )
    long_lot = PositionLot(
        "XYZ", PositionType.put, 1, -50, -45, 0, 0,
        datetime(2025, 1, 3), 50, expiry, "P",
    )
    pm.add_lot_directly(short_lot)
    pm.add_lot_directly(long_lot)
    assignment = transaction(
        "2025-01-17T10:00:00+0000", "Assignment", "ASSIGNMENT",
        "XYZ  250117P00050000", "Equity Option", 0, 1, "XYZ",
        "1/17/25", 50, "PUT", "Receive Deliver",
    )
    assignment["Multiplier"] = "invalid-but-unused"

    pm.add_position(assignment)

    assert pm.closed_trades[0].quantity == -1
    assert pm.closed_trades[0].profit_usd == 100
    assert pm.get_all_open_lots() == [long_lot]
