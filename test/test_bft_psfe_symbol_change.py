from tastyworksTaxes.position_manager import PositionManager
from tastyworksTaxes.transaction import Transaction


class TestSymbolChange:
    def test_option_symbol_change_transfers_basis_to_the_final_close(self):
        position_manager = PositionManager()
        position_manager.add_position(
            Transaction.fromString(
                "2022-01-03T15:00:00+0000,Trade,Sell to Open,SELL_TO_OPEN,"
                "OLD  220218P00010000,Equity Option,Synthetic open,120,1,120,"
                "0,0,100,OLD,OLD,02/18/22,10,PUT,1,USD"
            )
        )

        position_manager.add_position(
            Transaction.fromString(
                "2022-01-10T15:00:00+0000,Receive Deliver,Symbol Change,"
                "BUY_TO_CLOSE,OLD  220218P00010000,Equity Option,"
                "Synthetic symbol-change close,-120,1,,0,0,100,OLD,OLD,"
                "02/18/22,10,PUT,2,USD"
            )
        )

        assert position_manager.get_all_open_lots() == []
        assert position_manager.closed_trades == []

        position_manager.add_position(
            Transaction.fromString(
                "2022-01-10T15:00:00+0000,Receive Deliver,Symbol Change,"
                "SELL_TO_OPEN,NEW  220218P00010000,Equity Option,"
                "Synthetic symbol-change open,120,1,,0,0,100,NEW,NEW,"
                "02/18/22,10,PUT,3,USD"
            )
        )

        open_lots = position_manager.get_all_open_lots()
        assert len(open_lots) == 1
        assert open_lots[0].symbol == "NEW"
        assert position_manager.closed_trades == []

        position_manager.add_position(
            Transaction.fromString(
                "2022-01-17T15:00:00+0000,Trade,Buy to Close,BUY_TO_CLOSE,"
                "NEW  220218P00010000,Equity Option,Synthetic close,-50,1,50,"
                "0,0,100,NEW,NEW,02/18/22,10,PUT,4,USD"
            )
        )

        assert position_manager.get_all_open_lots() == []
        assert len(position_manager.closed_trades) == 1
        final_trade = position_manager.closed_trades[0]
        assert final_trade.symbol == "NEW"
        assert final_trade.profit_usd == 70
