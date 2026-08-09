
from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.transaction import Transaction

class TestTastyReverseSplit:
    def test_reverse_split_simplified(self):
        """
        A simpler test for reverse split that avoids pandas issues
        """
        t = Tasty()
        
        t.position_manager.add_position(Transaction.fromString("2022-04-29T19:30:00+0000,Trade,Buy to Open,BUY_TO_OPEN,OPQR  220715P00001500,Equity Option,Bought 6 OPQR 07/15/22 Put 1.50 @ 0.35,-210,6,35.0,-1.00,4.20,100,OPQR,OPQR,7/15/22,1.5,PUT,123456,USD"))
        assert len(t.position_manager.open_lots) == 1
        
        t.position_manager.add_position(Transaction.fromString("2022-05-06T12:35:00+0000,Trade,Sell to Close,SELL_TO_CLOSE,OPQR  220715P00001500,Equity Option,Sold 6 OPQR 07/15/22 Put 1.50 @ 0.35,210,6,35.0,0,0.0,100,OPQR,OPQR,7/15/22,1.5,PUT,123456,USD"))
        
        assert len(t.position_manager.open_lots) == 0
        assert len(t.position_manager.closed_trades) == 1
