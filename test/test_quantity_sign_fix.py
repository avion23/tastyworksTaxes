from tastyworksTaxes.position_manager import PositionManager
from tastyworksTaxes.transaction import Transaction


def test_long_option_closes_keep_positive_quantities_and_fifo_results():
    position_manager = PositionManager()
    transactions = [
        "2022-01-03T15:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,"
        "TESTA  220218C00010000,Equity Option,Synthetic long open,-100,1,100,"
        "0,0,100,TESTA,TESTA,02/18/22,10,CALL,ORDER-A,USD",
        "2022-01-04T15:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,"
        "TESTA  220218C00010000,Equity Option,Synthetic long open,-400,2,200,"
        "0,0,100,TESTA,TESTA,02/18/22,10,CALL,ORDER-B,USD",
        "2022-01-10T15:00:00+0000,Trade,Sell to Close,SELL_TO_CLOSE,"
        "TESTA  220218C00010000,Equity Option,Synthetic long close,600,2,300,"
        "0,0,100,TESTA,TESTA,02/18/22,10,CALL,ORDER-C,USD",
        "2022-01-11T15:00:00+0000,Trade,Sell to Close,SELL_TO_CLOSE,"
        "TESTA  220218C00010000,Equity Option,Synthetic long close,250,1,250,"
        "0,0,100,TESTA,TESTA,02/18/22,10,CALL,ORDER-D,USD",
    ]

    for row in transactions:
        position_manager.add_position(Transaction.fromString(row))

    closed_trades = position_manager.closed_trades
    assert [trade.quantity for trade in closed_trades] == [1, 1, 1]
    assert [trade.profit_usd for trade in closed_trades] == [200, 100, 50]
    assert sum(trade.profit_usd for trade in closed_trades) == 350
    assert position_manager.get_all_open_lots() == []


def test_short_option_close_keeps_negative_quantity_and_exact_result():
    position_manager = PositionManager()
    position_manager.add_position(
        Transaction.fromString(
            "2022-03-01T15:00:00+0000,Trade,Sell to Open,SELL_TO_OPEN,"
            "TESTB  220415P00020000,Equity Option,Synthetic short open,400,2,"
            "200,0,0,100,TESTB,TESTB,04/15/22,20,PUT,ORDER-E,USD"
        )
    )
    position_manager.add_position(
        Transaction.fromString(
            "2022-03-02T15:00:00+0000,Trade,Buy to Close,BUY_TO_CLOSE,"
            "TESTB  220415P00020000,Equity Option,Synthetic short close,-250,"
            "1,250,0,0,100,TESTB,TESTB,04/15/22,20,PUT,ORDER-F,USD"
        )
    )

    assert len(position_manager.closed_trades) == 1
    closed_trade = position_manager.closed_trades[0]
    assert closed_trade.quantity == -1
    assert closed_trade.profit_usd == -50
    assert len(position_manager.get_all_open_lots()) == 1
    open_lot = position_manager.get_all_open_lots()[0]
    assert open_lot.quantity == -1
    assert open_lot.amount_usd == 200


def test_partial_long_close_keeps_positive_closed_and_open_quantities():
    position_manager = PositionManager()
    position_manager.add_position(
        Transaction.fromString(
            "2023-01-03T15:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,"
            "TESTC  230217C00030000,Equity Option,Synthetic partial open,-1000,"
            "10,100,0,0,100,TESTC,TESTC,02/17/23,30,CALL,ORDER-G,USD"
        )
    )
    position_manager.add_position(
        Transaction.fromString(
            "2023-01-04T15:00:00+0000,Trade,Sell to Close,SELL_TO_CLOSE,"
            "TESTC  230217C00030000,Equity Option,Synthetic partial close,450,"
            "3,150,0,0,100,TESTC,TESTC,02/17/23,30,CALL,ORDER-H,USD"
        )
    )

    assert len(position_manager.closed_trades) == 1
    closed_trade = position_manager.closed_trades[0]
    assert closed_trade.quantity == 3
    assert closed_trade.profit_usd == 150
    assert len(position_manager.get_all_open_lots()) == 1
    open_lot = position_manager.get_all_open_lots()[0]
    assert open_lot.quantity == 7
    assert open_lot.amount_usd == -700
