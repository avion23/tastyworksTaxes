
from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.transaction import Transaction

class TestTastyReceiveDeliver:
    def test_assigned_stock(self):
        t = Tasty()
        t.position_manager.add_position(Transaction.fromString("2019-06-25T22:00:00+0000,Receive Deliver,Sell to Open,SELL_TO_OPEN,HJKL,Equity,Sell to Open 200 HJKL @ 45.50,9100,200,45.5,-1.00,3.90,,HJKL,HJKL,,,,123456,USD"))
        assert t.position_manager.get_all_open_lots()[0].symbol == 'HJKL'
        
        closing = Transaction.fromString("2019-06-25T22:00:00+0000,Receive Deliver,Sell to Open,SELL_TO_OPEN,HJKL,Equity,Sell to Open 200 HJKL @ 45.50,9100,200,45.5,-1.00,3.90,,HJKL,HJKL,,,,123456,USD")
        closing["Transaction Subcode"] = "Buy to Close"
        t.position_manager.add_position(closing)
        assert len(t.position_manager.open_lots) == 0
    
    def test_close_positions(self):
        t = Tasty()
        t.position_manager.add_position(Transaction.fromString("2019-06-25T22:00:00+0000,Receive Deliver,Sell to Open,SELL_TO_OPEN,HJKL,Equity,Sell to Open 200 HJKL @ 45.50,9100,200,45.5,-1.00,3.90,,HJKL,HJKL,,,,123456,USD"))
        t.position_manager.add_position(Transaction.fromString("2019-07-02T18:42:00+0000,Trade,Buy to Close,BUY_TO_CLOSE,HJKL,Equity,Bought 100 HJKL @ 48.25,-4825,100,48.25,-1.00,0.08,,HJKL,HJKL,,,,123456,USD"))
        assert len(t.position_manager.closed_trades) == 1
        assert len(t.position_manager.open_lots) > 0
    
    def test_expiration(self):
        t = Tasty()
        t.position_manager.add_position(Transaction.fromString("2021-06-15T18:24:00+0000,Trade,Buy to Open,BUY_TO_OPEN,LMNO  210716C00055000,Equity Option,Bought 1 LMNO 07/16/21 Call 55.00 @ 2.15,-215,1,215.0,-1.00,0.14,100,LMNO,LMNO,7/16/21,55,CALL,123456,USD"))
        t.position_manager.add_position(Transaction.fromString("2021-07-16T22:15:00+0000,Receive Deliver,Expiration,,LMNO  210716C00055000,Equity Option,Removal of 1 LMNO 07/16/21 Call 55.00 due to expiration.,0,1,,0,0.00,100,LMNO,LMNO,7/16/21,55,CALL,123456,USD"))
        assert len(t.position_manager.closed_trades) == 1
        assert len(t.position_manager.closed_trades) == 1
        assert len(t.position_manager.open_lots) == 0
    
    def test_uvxy_expiration(self):
        t = Tasty()
        t.position_manager.add_position(Transaction.fromString("2023-04-21T19:31:00+0000,Trade,Sell to Open,SELL_TO_OPEN,WXYZ  230421P00012500,Equity Option,Sold 1 WXYZ 04/21/23 Put 12.50 @ 0.60,60,1,60.0,-1.00,0.12,100,WXYZ,WXYZ,4/21/23,12.5,PUT,123456,USD"))
        t.position_manager.add_position(Transaction.fromString("2023-04-21T22:15:00+0000,Receive Deliver,Expiration,,WXYZ  230421P00012500,Equity Option,Removal of 1.0 WXYZ 04/21/23 Put 12.50 due to expiration.,0,1,,0,0.00,100,WXYZ,WXYZ,4/21/23,12.5,PUT,123456,USD"))
        assert len(t.position_manager.closed_trades) == 1
        assert len(t.position_manager.open_lots) == 0
    
    def test_derm_expiration(self):
        t = Tasty()
        t.position_manager.add_position(Transaction.fromString("2021-06-15T17:36:00+0000,Trade,Buy to Open,BUY_TO_OPEN,DEFG  210716C00009000,Equity Option,Bought 2 DEFG 07/16/21 Call 9.00 @ 1.35,-270,2,135.0,-1.00,1.28,100,DEFG,DEFG,7/16/21,9,CALL,123456,USD"))
        t.position_manager.add_position(Transaction.fromString("2021-07-16T22:15:00+0000,Receive Deliver,Expiration,,DEFG  210716C00009000,Equity Option,Removal of 2 DEFG 07/16/21 Call 9.00 due to expiration.,0,2,,0,0.00,100,DEFG,DEFG,7/16/21,9,CALL,123456,USD"))
        assert len(t.position_manager.closed_trades) == 1
        assert len(t.position_manager.open_lots) == 0

    def test_special_dividend_option_adjustment_preserves_basis(self):
        """Special-dividend close/open legs roll an option without realizing P&L."""
        t = Tasty()
        t.position_manager.add_position(Transaction.fromString(
            "2025-12-01T15:00:00+0000,Trade,Sell to Open,SELL_TO_OPEN,TECL  251219C00140000,Equity Option,"
            "Sold 1 TECL 12/19/25 Call 140.00 @ 2.75,275,1,275,-1,0,100,TECL,TECL,12/19/25,140,CALL,123456,USD"
        ))
        t.position_manager.add_position(Transaction.fromString(
            "2025-12-10T11:47:06+0000,Receive Deliver,Special Dividend,BUY_TO_CLOSE,TECL  251219C00140000,Equity Option,"
            "Special dividend: Close 1.0 TECL  251219C00140000,-275,1,,0,0.00,100,TECL,TECL,12/19/25,140,CALL,123456,USD"
        ))
        t.position_manager.add_position(Transaction.fromString(
            "2025-12-10T11:47:06+0000,Receive Deliver,Special Dividend,SELL_TO_OPEN,TECL  251219C00131960,Equity Option,"
            "Special dividend: Open 1.0 TECL  251219C00131960,275,1,,0,0.00,100,TECL,TECL,12/19/25,131.96,CALL,123456,USD"
        ))

        lots = t.position_manager.get_all_open_lots()
        assert len(lots) == 1
        assert lots[0].symbol == "TECL"
        assert lots[0].strike == 131.96
        assert lots[0].quantity == -1
        assert lots[0].amount_usd == 275
        assert t.position_manager.closed_trades == []

    def test_special_dividend_option_adjustment_ignores_csv_replacement_basis(self):
        t = Tasty()
        t.position_manager.add_position(Transaction.fromString(
            "2025-12-01T15:00:00+0000,Trade,Sell to Open,SELL_TO_OPEN,TECL  251219C00140000,Equity Option,"
            "Sold 0.5 TECL calls,137.50,0.5,275,-1,0,100,TECL,TECL,12/19/25,140,CALL,123456,USD"
        ))
        t.position_manager.add_position(Transaction.fromString(
            "2025-12-10T11:47:06+0000,Receive Deliver,Special Dividend,BUY_TO_CLOSE,TECL  251219C00140000,Equity Option,"
            "Special dividend close,-999,0.5,,0,0,100,TECL,TECL,12/19/25,140,CALL,,USD"
        ))
        t.position_manager.add_position(Transaction.fromString(
            "2025-12-10T11:47:06+0000,Receive Deliver,Special Dividend,SELL_TO_OPEN,TECL  251219C00131960,Equity Option,"
            "Special dividend open,999,0.5,,0,0,100,TECL,TECL,12/19/25,131.96,CALL,,USD"
        ))

        lots = t.position_manager.get_all_open_lots()
        assert len(lots) == 1
        assert lots[0].quantity == -0.5
        assert lots[0].strike == 131.96
        assert lots[0].amount_usd == 137.5
        assert lots[0].fees_usd == 1
        assert t.position_manager.closed_trades == []
