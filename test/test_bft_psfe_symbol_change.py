import pytest
from pathlib import Path
from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.position_manager import PositionManager
from tastyworksTaxes.transaction import Transaction

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

        # 1. Open BFT put position (chronologically first)
        bft_open = Transaction.fromString("03/18/2021 8:19 PM,Trade,Sell to Open,BFT,Sell,Open,1,04/16/2021,15,P,1.32,1.152,132,Sold 1 BFT 04/16/21 Put 15.00 @ 1.32,Individual...39")
        pm.add_position(bft_open)
        assert len(pm.open_lots) == 1
        assert pm.open_lots[0].symbol == 'BFT'

        # 2. Process the two legs of the "Symbol Change" event
        bft_accounting_close = Transaction.fromString("03/31/2021 12:46 PM,Receive Deliver,Symbol Change,BFT,Buy,Close,1,04/16/2021,15,P,,0.00,-132,Symbol change: Close 1.0 BFT 210416P00015000,Individual...39")
        psfe_accounting_open = Transaction.fromString("03/31/2021 12:46 PM,Receive Deliver,Symbol Change,PSFE,Sell,Open,1,04/16/2021,15,P,,0.00,132,Symbol change: Open 1.0 PSFE 210416P00015000,Individual...39")

        # Process the closing leg: This should remove the BFT lot without creating a trade
        pm.add_position(bft_accounting_close)
        assert len(pm.open_lots) == 0
        assert len(pm.closed_trades) == 0, "Accounting close should NOT create a trade"

        # Process the opening leg: This should create a new PSFE lot
        pm.add_position(psfe_accounting_open)
        assert len(pm.open_lots) == 1
        assert pm.open_lots[0].symbol == 'PSFE'

        # 3. Process the final, real closing trade
        psfe_real_close = Transaction.fromString("04/07/2021 4:23 PM,Trade,Buy to Close,PSFE,Buy,Close,1,04/16/2021,15,P,0.8,0.13,-80,Bought 1 PSFE 04/16/21 Put 15.00 @ 0.80,Individual...39")
        pm.add_position(psfe_real_close)

        # Final verification
        assert len(pm.open_lots) == 0, "The position should be fully closed"
        assert len(pm.closed_trades) == 1, "Should result in exactly one closed trade"

        # The final trade should be between the PSFE accounting open and the PSFE real close
        final_trade = pm.closed_trades[0]
        assert final_trade.symbol == 'PSFE'
        # Profit = 132 (from accounting open) - 80 (from real close) = 52
        assert round(final_trade.profit_usd) == 52

    def test_full_integration_with_tasty_class(self):
        """Test the BFT->PSFE scenario using the full merged3.csv data."""
        t = Tasty(Path("test/merged3.csv"))

        # This should no longer raise a ValueError
        result = t.run()

        # Verify we got results
        assert len(result) > 0