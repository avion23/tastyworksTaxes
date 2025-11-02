import sys
import os
import re
import pytest
import pandas as pd
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tastyworksTaxes.transaction import Transaction
from tastyworksTaxes.money import Money
from tastyworksTaxes.history import History
from tastyworksTaxes.position import PositionType


def clean_numpy_str(s):
    """Remove np.float64 from string representation"""
    return re.sub(r'np\.float64\(([^)]+)\)', r'\1', s)


class TestTransaction:
    """Tests for the Transaction class"""
    
    @pytest.mark.parametrize("transaction_str,expected_attrs", [
        ("2021-01-29T19:31:00+0000,Trade,Sell to Open,SELL_TO_OPEN,UVXY  210129P00014500,Equity Option,Sold 1 UVXY 01/29/21 Put 14.50 @ 0.56,56,1,56.00000000000001,-1.00,0.1519999999999999,100,UVXY,UVXY,1/29/21,14.5,PUT,123456,USD",
         {"Symbol": "UVXY", "Strike": 14.5, "Call/Put": "P", "Price": 0.56, "Amount": 56.0}),
        ("2020-12-15T20:38:00+0000,Trade,Buy to Open,BUY_TO_OPEN,THCB,Equity,Bought 200 THCB @ 13.60,-2720,200,13.6,-1.00,0.16,,THCB,THCB,,,,123456,USD",
         {"Symbol": "THCB", "Price": 13.6, "Amount": -2720.0, "Fees": 1.16}),
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
        t = Transaction.fromString("2020-12-29T15:36:00+0000,Trade,Sell to Open,SELL_TO_OPEN,PLTR  210115P00026000,Equity Option,Sold 1 PLTR 01/15/21 Put 26.00 @ 2.46,246,1,246.0,-1.00,0.1519999999999999,100,PLTR,PLTR,1/15/21,26,PUT,123456,USD")
        
        assert t.getYear() == 2020
        
        assert t.getDate() == "2020-12-29"
        
        assert t.getDateTime() == "2020-12-29 15:36:00"
        
        assert t.getExpiry().strftime("%Y-%m-%d") == "2021-01-15"
        
        assert t.getStrike() == 26.0
        
        old_date = t["Date/Time"]
        
        t["Date/Time"] = pd.Timestamp("2000-01-01")
        with pytest.raises(ValueError, match="Date is less than the year 2010"):
            t.getYear()
        
        t["Date/Time"] = pd.Timestamp("2200-01-01")
        with pytest.raises(ValueError, match="Date is bigger than 2100"):
            t.getYear()
            
        t["Date/Time"] = old_date

    @pytest.mark.parametrize("transaction_str,expected_is_option,expected_is_stock", [
        ("2020-12-15T20:38:00+0000,Trade,Buy to Open,BUY_TO_OPEN,THCB,Equity,Bought 200 THCB @ 13.60,-2720,200,13.6,-1.00,0.16,,THCB,THCB,,,,123456,USD", 
         False, True),
        ("2020-12-17T20:57:00+0000,Trade,Buy to Close,BUY_TO_CLOSE,PLTR  210115C00027000,Equity Option,Bought 1 PLTR 01/15/21 Call 27.00 @ 3.20,-320,1,320.0,-1.00,0.14,100,PLTR,PLTR,1/15/21,27,CALL,123456,USD",
         True, False),
        ("2020-12-29T15:36:00+0000,Trade,Sell to Open,SELL_TO_OPEN,PLTR  210115P00026000,Equity Option,Sold 1 PLTR 01/15/21 Put 26.00 @ 2.46,246,1,246.0,-1.00,0.1519999999999999,100,PLTR,PLTR,1/15/21,26,PUT,123456,USD",
         True, False),
        ("2020-12-11T23:00:00+0000,Receive Deliver,Assignment,,PCG  201211C00010500,Equity Option,Removal of option due to assignment,0,3,,0,0.00,100,PCG,PCG,12/11/20,10.5,CALL,123456,USD",
         True, False),
    ])
    def test_is_option_and_stock(self, transaction_str, expected_is_option, expected_is_stock):
        """Test isOption and isStock methods"""
        t = Transaction.fromString(transaction_str)
        assert t.isOption() == expected_is_option
        
        if expected_is_stock or t["Transaction Code"] == "Trade":
            assert t.isStock() == expected_is_stock

    @pytest.mark.parametrize("transaction_str,expected_type", [
        ("2020-12-15T20:38:00+0000,Trade,Buy to Open,BUY_TO_OPEN,THCB,Equity,Bought 200 THCB @ 13.60,-2720,200,13.6,-1.00,0.16,,THCB,THCB,,,,123456,USD", 
         PositionType.stock),
        ("2020-12-17T20:57:00+0000,Trade,Buy to Close,BUY_TO_CLOSE,PLTR  210115C00027000,Equity Option,Bought 1 PLTR 01/15/21 Call 27.00 @ 3.20,-320,1,320.0,-1.00,0.14,100,PLTR,PLTR,1/15/21,27,CALL,123456,USD",
         PositionType.call),
        ("2020-12-29T15:36:00+0000,Trade,Sell to Open,SELL_TO_OPEN,PLTR  210115P00026000,Equity Option,Sold 1 PLTR 01/15/21 Put 26.00 @ 2.46,246,1,246.0,-1.00,0.1519999999999999,100,PLTR,PLTR,1/15/21,26,PUT,123456,USD",
         PositionType.put),
    ])
    def test_get_type(self, transaction_str, expected_type):
        """Test getting the position type from a transaction"""
        t = Transaction.fromString(transaction_str)
        assert t.getType() == expected_type
    
    def test_assignment_type(self):
        """Test an assignment transaction with a call option - this is a special case"""
        t = Transaction.fromString("2020-12-11T23:00:00+0000,Receive Deliver,Assignment,,PCG  201211C00010500,Equity Option,Removal of option due to assignment,0,3,,0,0.00,100,PCG,PCG,12/11/20,10.5,CALL,123456,USD")
        assert t.getType() == PositionType.call
        assert t.isOption()
        
    def test_get_symbol(self):
        """Test getting the symbol from a transaction"""
        t = Transaction.fromString("2020-12-15T20:38:00+0000,Trade,Buy to Open,BUY_TO_OPEN,THCB,Equity,Bought 200 THCB @ 13.60,-2720,200,13.6,-1.00,0.16,,THCB,THCB,,,,123456,USD")
        assert t.getSymbol() == "THCB"
        
        with pytest.raises(ValueError, match="This transaction doesn't have a symbol"):
            t = Transaction({"Symbol": "", "Date/Time": pd.Timestamp.now()})
            t.getSymbol()

    @pytest.mark.parametrize("transaction_str,expected_quantity", [
        ("2020-12-15T20:38:00+0000,Trade,Buy to Open,BUY_TO_OPEN,THCB,Equity,Bought 200 THCB @ 13.60,-2720,200,13.6,-1.00,0.16,,THCB,THCB,,,,123456,USD", 200),
        ("2019-08-08T19:59:00+0000,Trade,Sell to Close,SELL_TO_CLOSE,BABA,Equity,Sold 100 BABA @ 160.73,16073,100,160.73,-1.00,0.432,,BABA,BABA,,,,123456,USD", -100),
        ("2020-12-29T15:36:00+0000,Trade,Sell to Open,SELL_TO_OPEN,PLTR  210115P00026000,Equity Option,Sold 1 PLTR 01/15/21 Put 26.00 @ 2.46,246,1,246.0,-1.00,0.1519999999999999,100,PLTR,PLTR,1/15/21,26,PUT,123456,USD", -1),
        ("2018-07-20T22:00:00+0000,Receive Deliver,Expiration,,DERM  180720C00011000,Equity Option,Removal of 2 DERM 07/20/18 Call 11.00 due to expiration.,0,2,,0,0.00,100,DERM,DERM,7/20/18,11,CALL,123456,USD", 2),
        ("2018-03-19T22:00:00+0000,Receive Deliver,Sell to Open,SELL_TO_OPEN,LFIN,Equity,Sell to Open 200 LFIN @ 30.00,6000,200,30,-1.00,4.164,,LFIN,LFIN,,,,123456,USD", -200),
        ("2020-04-29T12:35:00+0000,Receive Deliver,Reverse Split,SELL_TO_CLOSE,USO  200717P00002000,Equity Option,Reverse split: Close 6 USO   200717P00002000,174,6,,0,0.00,100,USO,USO,7/17/20,2,PUT,123456,USD", -6),
        ("2021-09-15T12:36:00+0000,Receive Deliver,Stock Merger,SELL_TO_OPEN,GREE  210917P00022000,Equity Option,Stock merger Open 6.0 GREE1 210917P00022000,3360,6,,0,0.00,100,GREE,GREE,9/17/21,22,PUT,123456,USD", -6),
    ])
    def test_get_quantity(self, transaction_str, expected_quantity):
        """Test getting the quantity from a transaction"""
        t = Transaction.fromString(transaction_str)
        assert t.getQuantity() == expected_quantity

    def test_quantity_manipulation(self):
        """Test setting and getting the quantity of a transaction"""
        test_cases = [
            {"from_str": "2019-08-08T19:59:00+0000,Trade,Sell to Close,SELL_TO_CLOSE,BABA,Equity,Sold 100 BABA @ 160.73,16073,100,160.73,-1.00,0.432,,BABA,BABA,,,,123456,USD",
             "initial_qty": -100, "new_qty": 200, "expected_buy_sell": "Buy", "expected_subcode": "Buy to Close"},
            {"from_str": "2018-03-12T17:08:00+0000,Trade,Buy to Open,BUY_TO_OPEN,LFIN  180615C00040000,Equity Option,Bought 2 LFIN 06/15/18 Call 40.00 @ 2.20,-440,2,220.00000000000003,-1.00,1.2799999999999998,100,LFIN,LFIN,6/15/18,40,CALL,123456,USD",
             "initial_qty": 2, "new_qty": -3, "expected_buy_sell": "Sell", "expected_subcode": "Sell to Open"},
            {"from_str": "2018-07-20T22:00:00+0000,Receive Deliver,Expiration,,DERM  180720C00011000,Equity Option,Removal of 2 DERM 07/20/18 Call 11.00 due to expiration.,0,2,,0,0.00,100,DERM,DERM,7/20/18,11,CALL,123456,USD",
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
            
        t = Transaction.fromString("2018-03-12T17:08:00+0000,Trade,Buy to Open,BUY_TO_OPEN,LFIN  180615C00040000,Equity Option,Bought 2 LFIN 06/15/18 Call 40.00 @ 2.20,-440,2,220.00000000000003,-1.00,1.2799999999999998,100,LFIN,LFIN,6/15/18,40,CALL,123456,USD")
        t.setQuantity(0)
        assert t.getQuantity() == 0

    def test_value_and_fees_handling(self):
        """Test getting and setting the value and fees of a transaction"""
        t = Transaction.fromString("2018-03-12T17:08:00+0000,Trade,Buy to Open,BUY_TO_OPEN,LFIN  180615C00040000,Equity Option,Bought 2 LFIN 06/15/18 Call 40.00 @ 2.20,-440,2,220.00000000000003,-1.00,1.2799999999999998,100,LFIN,LFIN,6/15/18,40,CALL,123456,USD")
        
        value = t.getValue()
        assert value.usd == -440.0
        assert isinstance(value, Money)
        
        t.setValue(Money(usd=45, eur=20))
        value = t.getValue()
        assert value.usd == 45
        assert value.eur == 20
        
        fees = t.getFees()
        assert fees.usd == 2.28
        assert isinstance(fees, Money)
        
        t.setFees(Money(usd=45, eur=20))
        fees = t.getFees()
        assert fees.usd == 45
        assert fees.eur == 20

    def test_special_transaction_cases(self):
        """Test special transaction cases"""
        lfin_call = Transaction.fromString("2018-03-12T17:08:00+0000,Trade,Buy to Open,BUY_TO_OPEN,LFIN  180615C00040000,Equity Option,Bought 2 LFIN 06/15/18 Call 40.00 @ 2.20,-440,2,220.00000000000003,-1.00,1.2799999999999998,100,LFIN,LFIN,6/15/18,40,CALL,123456,USD")
        assert lfin_call.getSymbol() == "LFIN"
        assert lfin_call.getType() == PositionType.call
        
        lfin_stock = Transaction.fromString("2018-03-19T22:00:00+0000,Receive Deliver,Sell to Open,SELL_TO_OPEN,LFIN,Equity,Sell to Open 200 LFIN @ 30.00,6000,200,30,-1.00,4.164,,LFIN,LFIN,,,,123456,USD")
        assert lfin_stock.getQuantity() == -200
        assert lfin_stock.getSymbol() == "LFIN"
        
        uvxy_transaction = Transaction.fromString("2021-01-29T19:31:00+0000,Trade,Sell to Open,SELL_TO_OPEN,UVXY  210129P00014500,Equity Option,Sold 1 UVXY 01/29/21 Put 14.50 @ 0.56,56,1,56.00000000000001,-1.00,0.1519999999999999,100,UVXY,UVXY,1/29/21,14.5,PUT,123456,USD")
        assert uvxy_transaction.getQuantity() == -1
        assert uvxy_transaction.getSymbol() == "UVXY"
        
        expiry_transaction = Transaction.fromString("2021-01-29T22:15:00+0000,Receive Deliver,Expiration,,UVXY  210129P00014500,Equity Option,Removal of 1.0 UVXY 01/29/21 Put 14.50 due to expiration.,0,1,,0,0.00,100,UVXY,UVXY,1/29/21,14.5,PUT,123456,USD")
        assert expiry_transaction.getQuantity() == 1
        
        symchange_transaction = Transaction.fromString("2021-06-18T12:48:00+0000,Receive Deliver,Symbol Change,BUY_TO_CLOSE,VGAC  210618C00010000,Equity Option,Symbol change:  Close 1.0 VGAC  210618C00010000,-45,1,,0,0.00,100,VGAC,VGAC,6/18/21,10,CALL,123456,USD")
        assert symchange_transaction.getSymbol() == "VGAC"
        assert symchange_transaction.getQuantity() == 1
        
        reverse_split = Transaction.fromString("2020-04-29T12:35:00+0000,Receive Deliver,Reverse Split,SELL_TO_CLOSE,USO  200717P00002000,Equity Option,Reverse split: Close 6 USO   200717P00002000,174,6,,0,0.00,100,USO,USO,7/17/20,2,PUT,123456,USD")
        assert reverse_split.getQuantity() == -6
        assert reverse_split.getSymbol() == "USO"
        
        merger = Transaction.fromString("2021-09-15T12:36:00+0000,Receive Deliver,Stock Merger,SELL_TO_OPEN,GREE  210917P00022000,Equity Option,Stock merger Open 6.0 GREE1 210917P00022000,3360,6,,0,0.00,100,GREE,GREE,9/17/21,22,PUT,123456,USD")
        assert merger.getQuantity() == -6
        assert merger.getSymbol() == "GREE"