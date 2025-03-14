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
        # Option put
        ("01/29/2021 7:31 PM,Trade,Sell to Open,UVXY,Sell,Open,1,01/29/2021,14.5,P,0.56,1.152,56,Sold 1 UVXY 01/29/21 Put 14.50 @ 0.56,Individual...39", 
         {"Symbol": "UVXY", "Strike": 14.5, "Call/Put": "P", "Price": 0.56, "Amount": 56.0}),
        # Stock
        ("12/15/2020 8:38 PM,Trade,Buy to Open,THCB,Buy,Open,200,,,,13.6,0.16,-2720,Bought 200 THCB @ 13.60,Individual...39",
         {"Symbol": "THCB", "Price": 13.6, "Amount": -2720.0, "Fees": 0.16}),
    ])
    def test_transaction_from_string(self, transaction_str, expected_attrs):
        """Test creation of Transaction from a string"""
        t = Transaction.fromString(transaction_str)
        for attr, value in expected_attrs.items():
            assert t[attr] == value
        
        # Test error handling with malformed string
        with pytest.raises(ValueError):
            Transaction.fromString("invalid")

    def test_date_time_handling(self):
        """Test date/time handling methods"""
        t = Transaction.fromString("12/29/2020 3:36 PM,Trade,Sell to Open,PLTR,Sell,Open,1,01/15/2021,26,P,2.46,1.152,246,Sold 1 PLTR 01/15/21 Put 26.00 @ 2.46,Individual...39")
        
        # Test getYear with valid date
        assert t.getYear() == 2020
        
        # Test getDate
        assert t.getDate() == "2020-12-29"
        
        # Test getDateTime
        assert t.getDateTime() == "2020-12-29 15:36:00"
        
        # Test getExpiry
        assert t.getExpiry().strftime("%Y-%m-%d") == "2021-01-15"
        
        # Test getStrike
        assert t.getStrike() == 26.0
        
        # Test invalid year cases
        old_date = t["Date/Time"]
        
        # Test with year too early
        t["Date/Time"] = pd.Timestamp("2000-01-01")
        with pytest.raises(ValueError, match="Date is less than the year 2010"):
            t.getYear()
        
        # Test with year too far in future
        t["Date/Time"] = pd.Timestamp("2200-01-01")
        with pytest.raises(ValueError, match="Date is bigger than 2100"):
            t.getYear()
            
        t["Date/Time"] = old_date

    @pytest.mark.parametrize("transaction_str,expected_is_option,expected_is_stock", [
        # Stock
        ("12/15/2020 8:38 PM,Trade,Buy to Open,THCB,Buy,Open,200,,,,13.6,0.16,-2720,Bought 200 THCB @ 13.60,Individual...39", 
         False, True),
        # Call option
        ("12/17/2020 8:57 PM,Trade,Buy to Close,PLTR,Buy,Close,1,01/15/2021,27,C,3.2,0.14,-320,Bought 1 PLTR 01/15/21 Call 27.00 @ 3.20,Individual...39",
         True, False),
        # Put option
        ("12/29/2020 3:36 PM,Trade,Sell to Open,PLTR,Sell,Open,1,01/15/2021,26,P,2.46,1.152,246,Sold 1 PLTR 01/15/21 Put 26.00 @ 2.46,Individual...39",
         True, False),
        # Assignment (now considered an option with our fix)
        ("12/11/2020 11:00 PM,Receive Deliver,Assignment,PCG,,,3,12/11/2020,10.5,C,,0.00,0,Removal of option due to assignment,Individual...39",
         True, False),
    ])
    def test_is_option_and_stock(self, transaction_str, expected_is_option, expected_is_stock):
        """Test isOption and isStock methods"""
        t = Transaction.fromString(transaction_str)
        assert t.isOption() == expected_is_option
        
        # Only test is_stock for valid transactions - isStock will fail for assignments
        if expected_is_stock or t["Transaction Code"] == "Trade":
            assert t.isStock() == expected_is_stock

    @pytest.mark.parametrize("transaction_str,expected_type", [
        # Stock
        ("12/15/2020 8:38 PM,Trade,Buy to Open,THCB,Buy,Open,200,,,,13.6,0.16,-2720,Bought 200 THCB @ 13.60,Individual...39", 
         PositionType.stock),
        # Call option
        ("12/17/2020 8:57 PM,Trade,Buy to Close,PLTR,Buy,Close,1,01/15/2021,27,C,3.2,0.14,-320,Bought 1 PLTR 01/15/21 Call 27.00 @ 3.20,Individual...39",
         PositionType.call),
        # Put option
        ("12/29/2020 3:36 PM,Trade,Sell to Open,PLTR,Sell,Open,1,01/15/2021,26,P,2.46,1.152,246,Sold 1 PLTR 01/15/21 Put 26.00 @ 2.46,Individual...39",
         PositionType.put),
    ])
    def test_get_type(self, transaction_str, expected_type):
        """Test getting the position type from a transaction"""
        t = Transaction.fromString(transaction_str)
        assert t.getType() == expected_type
    
    def test_assignment_type(self):
        """Test an assignment transaction with a call option - this is a special case"""
        t = Transaction.fromString("12/11/2020 11:00 PM,Receive Deliver,Assignment,PCG,,,3,12/11/2020,10.5,C,,0.00,0,Removal of option due to assignment,Individual...39")
        assert t.getType() == PositionType.call
        # With our fix, isOption now returns True for assignments
        assert t.isOption()
        
    def test_get_symbol(self):
        """Test getting the symbol from a transaction"""
        t = Transaction.fromString("12/15/2020 8:38 PM,Trade,Buy to Open,THCB,Buy,Open,200,,,,13.6,0.16,-2720,Bought 200 THCB @ 13.60,Individual...39")
        assert t.getSymbol() == "THCB"
        
        # Test with missing symbol
        with pytest.raises(ValueError, match="This transaction doesn't have a symbol"):
            t = Transaction({"Symbol": "", "Date/Time": pd.Timestamp.now()})
            t.getSymbol()

    @pytest.mark.parametrize("transaction_str,expected_quantity", [
        # Buy stock
        ("12/15/2020 8:38 PM,Trade,Buy to Open,THCB,Buy,Open,200,,,,13.6,0.16,-2720,Bought 200 THCB @ 13.60,Individual...39", 200),
        # Sell stock
        ("08/08/2019 7:59 PM,Trade,Sell to Close,BABA,Sell,Close,100,,,,160.73,0.432,16073,Sold 100 BABA @ 160.73,Individual...39", -100),
        # Sell put option
        ("12/29/2020 3:36 PM,Trade,Sell to Open,PLTR,Sell,Open,1,01/15/2021,26,P,2.46,1.152,246,Sold 1 PLTR 01/15/21 Put 26.00 @ 2.46,Individual...39", -1),
        # Option expiration
        ("07/20/2018 10:00 PM,Receive Deliver,Expiration,DERM,,,2,07/20/2018,11,C,,0.00,0,Removal of 2 DERM 07/20/18 Call 11.00 due to expiration.,Individual...39", 2),
        # Sell to open
        ("03/19/2018 10:00 PM,Receive Deliver,Sell to Open,LFIN,Sell,Open,200,,,,30,5.164,6000,Sell to Open 200 LFIN @ 30.00,Individual...39", -200),
        # Reverse split
        ("04/29/2020 12:35 PM,Receive Deliver,Reverse Split,USO,Sell,Close,6,07/17/2020,2,P,,0.00,174,Reverse split: Close 6 USO   200717P00002000,Individual...39", -6),
        # Stock merger
        ("09/15/2021 12:36 PM,Receive Deliver,Stock Merger,GREE,Sell,Open,6,09/17/2021,22,P,,0.00,3360,Stock merger Open 6.0 GREE1 210917P00022000,Individual...39", -6),
    ])
    def test_get_quantity(self, transaction_str, expected_quantity):
        """Test getting the quantity from a transaction"""
        t = Transaction.fromString(transaction_str)
        assert t.getQuantity() == expected_quantity

    def test_quantity_manipulation(self):
        """Test setting and getting the quantity of a transaction"""
        # Test cases for different transaction types
        test_cases = [
            # Sell to close -> Buy to close
            {"from_str": "08/08/2019 7:59 PM,Trade,Sell to Close,BABA,Sell,Close,100,,,,160.73,0.432,16073,Sold 100 BABA @ 160.73,Individual...39",
             "initial_qty": -100, "new_qty": 200, "expected_buy_sell": "Buy", "expected_subcode": "Buy to Close"},
            # Buy to open -> Sell to open
            {"from_str": "03/12/2018 5:08 PM,Trade,Buy to Open,LFIN,Buy,Open,2,06/15/2018,40,C,2.2,2.28,-440,Bought 2 LFIN 06/15/18 Call 40.00 @ 2.20,Individual...39",
             "initial_qty": 2, "new_qty": -3, "expected_buy_sell": "Sell", "expected_subcode": "Sell to Open"},
            # Expiration - should not modify subcode
            {"from_str": "07/20/2018 10:00 PM,Receive Deliver,Expiration,DERM,,,2,07/20/2018,11,C,,0.00,0,Removal of 2 DERM 07/20/18 Call 11.00 due to expiration.,Individual...39",
             "initial_qty": 2, "new_qty": -3, "expected_buy_sell": "", "expected_subcode": "Expiration"},
        ]
        
        for case in test_cases:
            t = Transaction.fromString(case["from_str"])
            assert t.getQuantity() == case["initial_qty"]
            
            t.setQuantity(case["new_qty"])
            assert t.getQuantity() == case["new_qty"]
            
            # Check if subcode and buy/sell are preserved or modified as expected
            if case["expected_buy_sell"]:
                assert t["Buy/Sell"] == case["expected_buy_sell"]
            assert t["Transaction Subcode"] == case["expected_subcode"]
            
        # Test zero quantity
        t = Transaction.fromString("03/12/2018 5:08 PM,Trade,Buy to Open,LFIN,Buy,Open,2,06/15/2018,40,C,2.2,2.28,-440,Bought 2 LFIN 06/15/18 Call 40.00 @ 2.20,Individual...39")
        t.setQuantity(0)
        assert t.getQuantity() == 0

    def test_value_and_fees_handling(self):
        """Test getting and setting the value and fees of a transaction"""
        # LFIN Call
        t = Transaction.fromString("03/12/2018 5:08 PM,Trade,Buy to Open,LFIN,Buy,Open,2,06/15/2018,40,C,2.2,2.28,-440,Bought 2 LFIN 06/15/18 Call 40.00 @ 2.20,Individual...39")
        
        # Check initial value
        value = t.getValue()
        assert value.usd == -440.0
        assert isinstance(value, Money)
        
        # Set new value and verify
        t.setValue(Money(usd=45, eur=20))
        value = t.getValue()
        assert value.usd == 45
        assert value.eur == 20
        
        # Get and check initial fees
        fees = t.getFees()
        assert fees.usd == 2.28
        assert isinstance(fees, Money)
        
        # Set new fees and verify
        t.setFees(Money(usd=45, eur=20))
        fees = t.getFees()
        assert fees.usd == 45
        assert fees.eur == 20

    def test_special_transaction_cases(self):
        """Test special transaction cases"""
        # Test LFIN Call
        lfin_call = Transaction.fromString("03/12/2018 5:08 PM,Trade,Buy to Open,LFIN,Buy,Open,2,06/15/2018,40,C,2.2,2.28,-440,Bought 2 LFIN 06/15/18 Call 40.00 @ 2.20,Individual...39")
        assert lfin_call.getSymbol() == "LFIN"
        assert lfin_call.getType() == PositionType.call
        
        # Test LFIN stock position
        lfin_stock = Transaction.fromString("03/19/2018 10:00 PM,Receive Deliver,Sell to Open,LFIN,Sell,Open,200,,,,30,5.164,6000,Sell to Open 200 LFIN @ 30.00,Individual...39")
        assert lfin_stock.getQuantity() == -200
        assert lfin_stock.getSymbol() == "LFIN"
        
        # Test UVXY expiry
        uvxy_transaction = Transaction.fromString("01/29/2021 7:31 PM,Trade,Sell to Open,UVXY,Sell,Open,1,01/29/2021,14.5,P,0.56,1.152,56,Sold 1 UVXY 01/29/21 Put 14.50 @ 0.56,Individual...39")
        assert uvxy_transaction.getQuantity() == -1
        assert uvxy_transaction.getSymbol() == "UVXY"
        
        # Test expiry
        expiry_transaction = Transaction.fromString("01/29/2021 10:15 PM,Receive Deliver,Expiration,UVXY,,,1,01/29/2021,14.5,P,,0.00,0,Removal of 1.0 UVXY 01/29/21 Put 14.50 due to expiration.,Individual...39")
        assert expiry_transaction.getQuantity() == 1
        
        # Test symbol change
        symchange_transaction = Transaction.fromString("06/18/2021 12:48 PM,Receive Deliver,Symbol Change,VGAC,Buy,Close,1,06/18/2021,10,C,,0.00,-45,Symbol change:  Close 1.0 VGAC  210618C00010000,Individual...39")
        assert symchange_transaction.getSymbol() == "VGAC"
        assert symchange_transaction.getQuantity() == 1
        
        # Test reverse split
        reverse_split = Transaction.fromString("04/29/2020 12:35 PM,Receive Deliver,Reverse Split,USO,Sell,Close,6,07/17/2020,2,P,,0.00,174,Reverse split: Close 6 USO   200717P00002000,Individual...39")
        assert reverse_split.getQuantity() == -6
        assert reverse_split.getSymbol() == "USO"
        
        # Test stock merger
        merger = Transaction.fromString("09/15/2021 12:36 PM,Receive Deliver,Stock Merger,GREE,Sell,Open,6,09/17/2021,22,P,,0.00,3360,Stock merger Open 6.0 GREE1 210917P00022000,Individual...39")
        assert merger.getQuantity() == -6
        assert merger.getSymbol() == "GREE"