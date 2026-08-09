import sys
import os
import re
import pytest
import pandas as pd
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tastyworksTaxes.transaction import Transaction
from tastyworksTaxes.money import Money
from tastyworksTaxes.position import PositionType


def clean_numpy_str(s):
    """Remove np.float64 from string representation"""
    return re.sub(r'np\.float64\(([^)]+)\)', r'\1', s)


class TestTransaction:
    """Tests for the Transaction class"""
    
    @pytest.mark.parametrize("transaction_str,expected_attrs", [
        ("2023-04-21T19:31:00+0000,Trade,Sell to Open,SELL_TO_OPEN,WXYZ  230421P00012500,Equity Option,Sold 1 WXYZ 04/21/23 Put 12.50 @ 0.60,60,1,60.0,-1.00,0.12,100,WXYZ,WXYZ,4/21/23,12.5,PUT,123456,USD",
         {"Symbol": "WXYZ", "Strike": 12.5, "Call/Put": "P", "Price": 0.60, "Amount": 60.0}),
        ("2023-02-14T20:38:00+0000,Trade,Buy to Open,BUY_TO_OPEN,QRST,Equity,Bought 200 QRST @ 9.75,-1950,200,9.75,-1.00,0.16,,QRST,QRST,,,,123456,USD",
         {"Symbol": "QRST", "Price": 9.75, "Amount": -1950.0, "Fees": 1.16}),
    ])
    def test_transaction_from_string(self, transaction_str, expected_attrs):
        """Test creation of Transaction from a string"""
        t = Transaction.fromString(transaction_str)
        for attr, value in expected_attrs.items():
            assert t[attr] == value
        
        with pytest.raises(ValueError):
            Transaction.fromString("invalid,,,,,,,,,,0,0,,,,,,,123456,USD")

    def test_date_time_handling(self):
        """Test date/time handling methods"""
        t = Transaction.fromString("2023-01-17T15:36:00+0000,Trade,Sell to Open,SELL_TO_OPEN,MNOP  230203P00024000,Equity Option,Sold 1 MNOP 02/03/23 Put 24.00 @ 1.95,195,1,195.0,-1.00,0.14,100,MNOP,MNOP,2/3/23,24,PUT,123456,USD")
        
        assert t.getYear() == 2023
        
        assert t.getDate() == "2023-01-17"
        
        assert t.getDateTime() == "2023-01-17 15:36:00"
        
        assert t.getExpiry().strftime("%Y-%m-%d") == "2023-02-03"
        
        assert t.getStrike() == 24.0
        
        old_date = t["Date/Time"]
        
        t["Date/Time"] = pd.Timestamp("2000-01-01")
        with pytest.raises(ValueError, match="Date is less than the year 2010"):
            t.getYear()
        
        t["Date/Time"] = pd.Timestamp("2200-01-01")
        with pytest.raises(ValueError, match="Date is bigger than 2100"):
            t.getYear()
            
        t["Date/Time"] = old_date

    @pytest.mark.parametrize("transaction_str,expected_is_option,expected_is_stock", [
        ("2023-02-14T20:38:00+0000,Trade,Buy to Open,BUY_TO_OPEN,QRST,Equity,Bought 200 QRST @ 9.75,-1950,200,9.75,-1.00,0.16,,QRST,QRST,,,,123456,USD",
         False, True),
        ("2023-01-17T20:57:00+0000,Trade,Buy to Close,BUY_TO_CLOSE,MNOP  230203C00025000,Equity Option,Bought 1 MNOP 02/03/23 Call 25.00 @ 3.20,-320,1,320.0,-1.00,0.14,100,MNOP,MNOP,2/3/23,25,CALL,123456,USD",
         True, False),
        ("2023-01-17T15:36:00+0000,Trade,Sell to Open,SELL_TO_OPEN,MNOP  230203P00024000,Equity Option,Sold 1 MNOP 02/03/23 Put 24.00 @ 1.95,195,1,195.0,-1.00,0.14,100,MNOP,MNOP,2/3/23,24,PUT,123456,USD",
         True, False),
        ("2022-03-18T23:00:00+0000,Receive Deliver,Assignment,,KLMN  220318C00012500,Equity Option,Option removed on assignment,0,3,,0,0.00,100,KLMN,KLMN,3/18/22,12.5,CALL,123456,USD",
         True, False),
    ])
    def test_is_option_and_stock(self, transaction_str, expected_is_option, expected_is_stock):
        """Test isOption and isStock methods"""
        t = Transaction.fromString(transaction_str)
        assert t.isOption() == expected_is_option
        
        if expected_is_stock or t["Transaction Code"] == "Trade":
            assert t.isStock() == expected_is_stock

    @pytest.mark.parametrize("transaction_str,expected_type", [
        ("2023-02-14T20:38:00+0000,Trade,Buy to Open,BUY_TO_OPEN,QRST,Equity,Bought 200 QRST @ 9.75,-1950,200,9.75,-1.00,0.16,,QRST,QRST,,,,123456,USD",
         PositionType.stock),
        ("2023-01-17T20:57:00+0000,Trade,Buy to Close,BUY_TO_CLOSE,MNOP  230203C00025000,Equity Option,Bought 1 MNOP 02/03/23 Call 25.00 @ 3.20,-320,1,320.0,-1.00,0.14,100,MNOP,MNOP,2/3/23,25,CALL,123456,USD",
         PositionType.call),
        ("2023-01-17T15:36:00+0000,Trade,Sell to Open,SELL_TO_OPEN,MNOP  230203P00024000,Equity Option,Sold 1 MNOP 02/03/23 Put 24.00 @ 1.95,195,1,195.0,-1.00,0.14,100,MNOP,MNOP,2/3/23,24,PUT,123456,USD",
         PositionType.put),
    ])
    def test_get_type(self, transaction_str, expected_type):
        """Test getting the position type from a transaction"""
        t = Transaction.fromString(transaction_str)
        assert t.getType() == expected_type
    
    def test_assignment_type(self):
        """Test an assignment transaction with a call option - this is a special case"""
        t = Transaction.fromString("2022-03-18T23:00:00+0000,Receive Deliver,Assignment,,KLMN  220318C00012500,Equity Option,Option removed on assignment,0,3,,0,0.00,100,KLMN,KLMN,3/18/22,12.5,CALL,123456,USD")
        assert t.getType() == PositionType.call
        assert t.isOption()
        
    def test_get_symbol(self):
        """Test getting the symbol from a transaction"""
        t = Transaction.fromString("2023-02-14T20:38:00+0000,Trade,Buy to Open,BUY_TO_OPEN,QRST,Equity,Bought 200 QRST @ 9.75,-1950,200,9.75,-1.00,0.16,,QRST,QRST,,,,123456,USD")
        assert t.getSymbol() == "QRST"
        
        with pytest.raises(ValueError, match="This transaction doesn't have a symbol"):
            t = Transaction({"Symbol": "", "Date/Time": pd.Timestamp.now()})
            t.getSymbol()

    @pytest.mark.parametrize("transaction_str,expected_quantity", [
        ("2023-02-14T20:38:00+0000,Trade,Buy to Open,BUY_TO_OPEN,QRST,Equity,Bought 200 QRST @ 9.75,-1950,200,9.75,-1.00,0.16,,QRST,QRST,,,,123456,USD", 200),
        ("2022-09-14T19:59:00+0000,Trade,Sell to Close,SELL_TO_CLOSE,BCDE,Equity,Sold 100 BCDE @ 85.20,8520,100,85.2,-1.00,0.30,,BCDE,BCDE,,,,123456,USD", -100),
        ("2023-01-17T15:36:00+0000,Trade,Sell to Open,SELL_TO_OPEN,MNOP  230203P00024000,Equity Option,Sold 1 MNOP 02/03/23 Put 24.00 @ 1.95,195,1,195.0,-1.00,0.14,100,MNOP,MNOP,2/3/23,24,PUT,123456,USD", -1),
        ("2021-07-16T22:15:00+0000,Receive Deliver,Expiration,,DEFG  210716C00009000,Equity Option,Removal of 2 DEFG 07/16/21 Call 9.00 due to expiration.,0,2,,0,0.00,100,DEFG,DEFG,7/16/21,9,CALL,123456,USD", 2),
        ("2019-06-25T22:00:00+0000,Receive Deliver,Sell to Open,SELL_TO_OPEN,HJKL,Equity,Sell to Open 200 HJKL @ 45.50,9100,200,45.5,-1.00,3.90,,HJKL,HJKL,,,,123456,USD", -200),
        ("2022-05-06T12:35:00+0000,Receive Deliver,Reverse Split,SELL_TO_CLOSE,OPQR  220715P00001500,Equity Option,Reverse split: Close 6 OPQR   220715P00001500,210,6,,0,0.00,100,OPQR,OPQR,7/15/22,1.5,PUT,123456,USD", -6),
        ("2023-11-10T12:36:00+0000,Receive Deliver,Stock Merger,SELL_TO_OPEN,GHIJ  231117P00018000,Equity Option,Stock merger Open 6.0 GHIJ1 231117P00018000,1080,6,,0,0.00,100,GHIJ,GHIJ,11/17/23,18,PUT,123456,USD", -6),
    ])
    def test_get_quantity(self, transaction_str, expected_quantity):
        """Test getting the quantity from a transaction"""
        t = Transaction.fromString(transaction_str)
        assert t.getQuantity() == expected_quantity

    def test_quantity_manipulation(self):
        """Test setting and getting the quantity of a transaction"""
        test_cases = [
            {"from_str": "2022-09-14T19:59:00+0000,Trade,Sell to Close,SELL_TO_CLOSE,BCDE,Equity,Sold 100 BCDE @ 85.20,8520,100,85.2,-1.00,0.30,,BCDE,BCDE,,,,123456,USD",
             "initial_qty": -100, "new_qty": 200, "expected_buy_sell": "Buy", "expected_subcode": "Buy to Close"},
            {"from_str": "2019-09-10T17:08:00+0000,Trade,Buy to Open,BUY_TO_OPEN,HJKL  191220C00035000,Equity Option,Bought 2 HJKL 12/20/19 Call 35.00 @ 3.10,-620,2,310.0,-1.00,1.27,100,HJKL,HJKL,12/20/19,35,CALL,123456,USD",
             "initial_qty": 2, "new_qty": -3, "expected_buy_sell": "Sell", "expected_subcode": "Sell to Open"},
            {"from_str": "2021-07-16T22:15:00+0000,Receive Deliver,Expiration,,DEFG  210716C00009000,Equity Option,Removal of 2 DEFG 07/16/21 Call 9.00 due to expiration.,0,2,,0,0.00,100,DEFG,DEFG,7/16/21,9,CALL,123456,USD",
             "initial_qty": 2, "new_qty": -3, "expected_buy_sell": "", "expected_subcode": "Expiration"},
        ]
        
        for case in test_cases:
            t = Transaction.fromString(case["from_str"])
            assert t.getQuantity() == case["initial_qty"]
            
            t.setQuantity(case["new_qty"])
            assert t.getQuantity() == case["new_qty"]
            
            if case["expected_buy_sell"]:
                assert t["Buy/Sell"] == case["expected_buy_sell"]
            assert t["Transaction Subcode"] == case["expected_subcode"]
            
        t = Transaction.fromString("2019-09-10T17:08:00+0000,Trade,Buy to Open,BUY_TO_OPEN,HJKL  191220C00035000,Equity Option,Bought 2 HJKL 12/20/19 Call 35.00 @ 3.10,-620,2,310.0,-1.00,1.27,100,HJKL,HJKL,12/20/19,35,CALL,123456,USD")
        t.setQuantity(0)
        assert t.getQuantity() == 0

    def test_value_and_fees_handling(self):
        """Test getting and setting the value and fees of a transaction"""
        t = Transaction.fromString("2019-09-10T17:08:00+0000,Trade,Buy to Open,BUY_TO_OPEN,HJKL  191220C00035000,Equity Option,Bought 2 HJKL 12/20/19 Call 35.00 @ 3.10,-620,2,310.0,-1.00,1.27,100,HJKL,HJKL,12/20/19,35,CALL,123456,USD")
        
        value = t.getValue()
        assert value.usd == -620.0
        assert isinstance(value, Money)
        
        t.setValue(Money(usd=45, eur=20))
        value = t.getValue()
        assert value.usd == 45
        assert value.eur == 20
        
        fees = t.getFees()
        assert fees.usd == 2.27
        assert isinstance(fees, Money)
        
        t.setFees(Money(usd=45, eur=20))
        fees = t.getFees()
        assert fees.usd == 45
        assert fees.eur == 20

    def test_special_transaction_cases(self):
        """Test special transaction cases"""
        lfin_call = Transaction.fromString("2019-09-10T17:08:00+0000,Trade,Buy to Open,BUY_TO_OPEN,HJKL  191220C00035000,Equity Option,Bought 2 HJKL 12/20/19 Call 35.00 @ 3.10,-620,2,310.0,-1.00,1.27,100,HJKL,HJKL,12/20/19,35,CALL,123456,USD")
        assert lfin_call.getSymbol() == "HJKL"
        assert lfin_call.getType() == PositionType.call
        
        lfin_stock = Transaction.fromString("2019-06-25T22:00:00+0000,Receive Deliver,Sell to Open,SELL_TO_OPEN,HJKL,Equity,Sell to Open 200 HJKL @ 45.50,9100,200,45.5,-1.00,3.90,,HJKL,HJKL,,,,123456,USD")
        assert lfin_stock.getQuantity() == -200
        assert lfin_stock.getSymbol() == "HJKL"
        
        uvxy_transaction = Transaction.fromString("2023-04-21T19:31:00+0000,Trade,Sell to Open,SELL_TO_OPEN,WXYZ  230421P00012500,Equity Option,Sold 1 WXYZ 04/21/23 Put 12.50 @ 0.60,60,1,60.0,-1.00,0.12,100,WXYZ,WXYZ,4/21/23,12.5,PUT,123456,USD")
        assert uvxy_transaction.getQuantity() == -1
        assert uvxy_transaction.getSymbol() == "WXYZ"
        
        expiry_transaction = Transaction.fromString("2023-04-21T22:15:00+0000,Receive Deliver,Expiration,,WXYZ  230421P00012500,Equity Option,Removal of 1.0 WXYZ 04/21/23 Put 12.50 due to expiration.,0,1,,0,0.00,100,WXYZ,WXYZ,4/21/23,12.5,PUT,123456,USD")
        assert expiry_transaction.getQuantity() == 1
        
        symchange_transaction = Transaction.fromString("2024-02-16T12:48:00+0000,Receive Deliver,Symbol Change,BUY_TO_CLOSE,VWXY  240216C00008000,Equity Option,Symbol change:  Close 1.0 VWXY  240216C00008000,-25,1,,0,0.00,100,VWXY,VWXY,2/16/24,8,CALL,123456,USD")
        assert symchange_transaction.getSymbol() == "VWXY"
        assert symchange_transaction.getQuantity() == 1
        
        reverse_split = Transaction.fromString("2022-05-06T12:35:00+0000,Receive Deliver,Reverse Split,SELL_TO_CLOSE,OPQR  220715P00001500,Equity Option,Reverse split: Close 6 OPQR   220715P00001500,210,6,,0,0.00,100,OPQR,OPQR,7/15/22,1.5,PUT,123456,USD")
        assert reverse_split.getQuantity() == -6
        assert reverse_split.getSymbol() == "OPQR"
        
        merger = Transaction.fromString("2023-11-10T12:36:00+0000,Receive Deliver,Stock Merger,SELL_TO_OPEN,GHIJ  231117P00018000,Equity Option,Stock merger Open 6.0 GHIJ1 231117P00018000,1080,6,,0,0.00,100,GHIJ,GHIJ,11/17/23,18,PUT,123456,USD")
        assert merger.getQuantity() == -6
        assert merger.getSymbol() == "GHIJ"
def test_fractional_quantity_is_preserved():
    transaction = Transaction.fromString("2024-01-02T09:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,FRAC,Equity,Bought fractional FRAC,-5,0.5,10,-1,0,,FRAC,FRAC,,,,1,USD")
    assert transaction.getQuantity() == 0.5
    transaction.setQuantity(-1.9)
    assert transaction.getQuantity() == -1.9
