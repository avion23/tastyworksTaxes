import pytest
from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.transaction import Transaction


class TestNaNDescriptionEdgeCases:
    """Tests for handling NaN/empty Description fields in Money Movement transactions"""

    def test_withdrawal_with_empty_description_should_not_crash(self):
        """
        Fixed: Empty Description now handled gracefully with defensive guards
        Location: tasty.py:45, 47
        Empty description falls through to withdrawal (default behavior)
        """
        t = Tasty()
        # Empty description becomes NaN in pandas
        csv = "2020-01-01T00:00:00+0000,Money Movement,Withdrawal,,,,,100.0,0,,0,0.00,,,,,,,123456,USD"
        trans = Transaction.fromString(csv)

        # Should NOT crash, should be treated as normal withdrawal
        t.moneyMovement(trans)
        assert t.year(2020).withdrawal.usd == 100.0
        assert t.year(2020).deposit.usd == 0.0
        assert t.year(2020).debitInterest.usd == 0.0

    def test_withdrawal_with_normal_description(self):
        """Baseline: Normal withdrawal with description works"""
        t = Tasty()
        csv = "2020-01-01T00:00:00+0000,Money Movement,Withdrawal,,,,Normal Withdrawal,100.0,0,,0,0.00,,,,,,,123456,USD"
        trans = Transaction.fromString(csv)
        t.moneyMovement(trans)

        assert t.year(2020).withdrawal.usd == 100.0

    def test_withdrawal_with_wire_funds_received(self):
        """Baseline: Wire Funds Received is correctly classified as deposit"""
        t = Tasty()
        csv = "2020-01-01T00:00:00+0000,Money Movement,Withdrawal,,,,Wire Funds Received,100.0,0,,0,0.00,,,,,,,123456,USD"
        trans = Transaction.fromString(csv)
        t.moneyMovement(trans)

        assert t.year(2020).deposit.usd == 100.0
        assert t.year(2020).withdrawal.usd == 0.0

    def test_withdrawal_with_debit_interest_pattern(self):
        """Baseline: Debit interest regex pattern works"""
        t = Tasty()
        csv = "2020-01-01T00:00:00+0000,Money Movement,Withdrawal,,,,FROM 01/01 THRU 01/31 @ 8%,-10.0,0,,0,0.00,,,,,,,123456,USD"
        trans = Transaction.fromString(csv)
        t.moneyMovement(trans)

        assert t.year(2020).debitInterest.usd == -10.0
        assert t.year(2020).withdrawal.usd == 0.0

    def test_deposit_with_empty_description(self):
        """Empty description in Deposit (also uses desc check at line 56)"""
        t = Tasty()
        csv = "2020-01-01T00:00:00+0000,Money Movement,Deposit,,,,,100.0,0,,0,0.00,,,,,,,123456,USD"
        trans = Transaction.fromString(csv)

        # This should work - no string comparison on empty desc
        t.moneyMovement(trans)
        assert t.year(2020).deposit.usd == 100.0

    def test_fee_with_empty_description(self):
        """Empty description in Fee should work (no desc check)"""
        t = Tasty()
        csv = "2020-01-01T00:00:00+0000,Money Movement,Fee,,,,,-10.0,0,,0,0.00,,,,,,,123456,USD"
        trans = Transaction.fromString(csv)

        t.moneyMovement(trans)
        assert t.year(2020).fee.usd == -10.0

    def test_positive_fee_rebate(self):
        """Positive fees (rebates) should be handled correctly"""
        t = Tasty()
        csv = "2020-01-01T00:00:00+0000,Money Movement,Fee,,,,FEE REBATE,10.0,0,,0,0.00,,,,,,,123456,USD"
        trans = Transaction.fromString(csv)

        t.moneyMovement(trans)
        assert t.year(2020).fee.usd == 10.0  # Positive = rebate
