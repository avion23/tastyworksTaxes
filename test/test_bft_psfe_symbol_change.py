import pytest
from pathlib import Path
from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.position_manager import PositionManager
from tastyworksTaxes.transaction import Transaction

# Skip tests that require the full dataset if it's not available (CI environment)
FULL_DATASET = Path("test/transactions_2018_to_2025.csv")


class TestBftPsfeSymbolChange:
    def test_bft_psfe_symbol_change_sequence(self):
        """
        Tests the broker's two-part symbol change process chronologically.
        1. Open BFT put.
        2. Process the 'Symbol Change' closing leg for BFT.
        3. Process the 'Symbol Change' opening leg for PSFE.
        4. Process the final, real 'Buy to Close' for PSFE.
        This should result in ONE final closed trade for PSFE, with the cost basis
        and profit calculated against the original BFT opening.
        """
        pm = PositionManager()

        bft_open = Transaction.fromString(
            "2021-03-18T20:19:00+0000,Trade,Sell to Open,SELL_TO_OPEN,BFT  210416P00015000,Equity Option,Sold 1 BFT 04/16/21 Put 15.00 @ 1.32,132,1,132.0,-1.00,0.1519999999999999,100,BFT,BFT,4/16/21,15,PUT,123456,USD"
        )
        pm.add_position(bft_open)
        all_lots = pm.get_all_open_lots()
        assert len(all_lots) == 1
        assert all_lots[0].symbol == "BFT"

        bft_accounting_close = Transaction.fromString(
            "2021-03-31T12:46:00+0000,Receive Deliver,Symbol Change,BUY_TO_CLOSE,BFT  210416P00015000,Equity Option,Symbol change: Close 1.0 BFT 210416P00015000,-132,1,,0,0.00,100,BFT,BFT,4/16/21,15,PUT,123456,USD"
        )
        psfe_accounting_open = Transaction.fromString(
            "2021-03-31T12:46:00+0000,Receive Deliver,Symbol Change,SELL_TO_OPEN,PSFE  210416P00015000,Equity Option,Symbol change: Open 1.0 PSFE 210416P00015000,132,1,,0,0.00,100,PSFE,PSFE,4/16/21,15,PUT,123456,USD"
        )

        pm.add_position(bft_accounting_close)
        assert len(pm.get_all_open_lots()) == 0
        assert len(pm.closed_trades) == 0, "Accounting close should NOT create a trade"

        pm.add_position(psfe_accounting_open)
        all_lots = pm.get_all_open_lots()
        assert len(all_lots) == 1
        assert all_lots[0].symbol == "PSFE"

        psfe_real_close = Transaction.fromString(
            "2021-04-07T16:23:00+0000,Trade,Buy to Close,BUY_TO_CLOSE,PSFE  210416P00015000,Equity Option,Bought 1 PSFE 04/16/21 Put 15.00 @ 0.80,-80,1,80.0,-1.00,0.13,100,PSFE,PSFE,4/16/21,15,PUT,123456,USD"
        )
        pm.add_position(psfe_real_close)

        assert len(pm.get_all_open_lots()) == 0, "The position should be fully closed"
        assert len(pm.closed_trades) == 1, "Should result in exactly one closed trade"

        final_trade = pm.closed_trades[0]
        assert final_trade.symbol == "PSFE"
        assert round(final_trade.profit_usd) == 52

    @pytest.mark.skipif(
        not FULL_DATASET.exists(), reason="Full dataset not available (CI environment)"
    )
    def test_full_integration_with_tasty_class(self):
        """Test the BFT->PSFE scenario using the full merged3.csv data."""
        t = Tasty(FULL_DATASET)

        result = t.run()

        assert len(result) > 0
