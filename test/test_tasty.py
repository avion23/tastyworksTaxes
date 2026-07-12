import pytest
import pandas as pd

from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.transaction import Transaction

class TestTasty:
    def test_money_movement_debit_interest(self):
        t = Tasty()
        debit_interest_transaction = Transaction.fromString("2019-08-16T23:00:00+0000,Money Movement,Withdrawal,,,,FROM 07/16 THRU 08/15 @ 8    %,-9.81,0,,0,0.00,,,,,,,123456,USD")
        t.moneyMovement(debit_interest_transaction)
        assert t.year(2019).debitInterest.eur == -8.856988082340196
        assert t.year(2019).debitInterest.usd == -9.81

    def test_money_movement_deposit_transfer(self):
        t = Tasty()
        deposit_transfer_transaction = Transaction.fromString("2018-03-08T23:00:00+0000,Money Movement,Transfer,,,,Wire Funds Received,1200,0,,0,0.00,,,,,,,123456,USD")
        t.moneyMovement(deposit_transfer_transaction)
        assert t.year(2018).transfer.eur == 966.10578858385
        assert t.year(2018).transfer.usd == 1200.0

    def test_money_movement_balance_adjustment(self):
        t = Tasty()
        balance_adjustment_transaction = Transaction.fromString("2018-03-24T15:09:00+0000,Money Movement,Balance Adjustment,,,,Regulatory fee adjustment,-0.01,0,,0,0.00,,,,,,,123456,USD")
        t.moneyMovement(balance_adjustment_transaction)
        assert t.year(2018).balanceAdjustment.eur == -0.008085599547206425
        assert t.year(2018).balanceAdjustment.usd == -0.01

    def test_money_movement_fee(self):
        t = Tasty()
        fee_transaction = Transaction.fromString("2018-03-23T22:00:00+0000,Money Movement,Fee,,LFIN,Equity,LONGFIN CORP,-43.24,0,,0,0.00,,LFIN,LFIN,,,,123456,USD")
        t.moneyMovement(fee_transaction)
        assert t.year(2018).fee.eur == -35.02348938927588
        assert t.year(2018).fee.usd == -43.24

    def test_money_movement_credit_interest(self):
        t = Tasty()
        credit_interest_transaction = Transaction.fromString("2020-12-16T23:00:00+0000,Money Movement,Credit Interest,,,,INTEREST ON CREDIT BALANCE,0.030,0,,0,0.000,,,,,,,123456,USD")
        t.moneyMovement(credit_interest_transaction)
        assert t.year(2020).creditInterest.eur == pytest.approx(0.02461235540241201)
        assert t.year(2020).creditInterest.usd == 0.03

    def test_money_movement_credit_interest_via_deposit(self):
        t = Tasty()
        deposit_transaction = Transaction.fromString("2019-10-16T23:00:00+0000,Money Movement,Deposit,,,,INTEREST ON CREDIT BALANCE,0.010,0,,0,0.000,,,,,,,123456,USD")
        t.moneyMovement(deposit_transaction)
        assert t.year(2019).creditInterest.eur == pytest.approx(0.009070294784580499)
        assert t.year(2019).creditInterest.usd == 0.01

    def test_money_movement_general_deposit(self):
        t = Tasty()
        deposit_transaction = Transaction.fromString("2024-03-07T20:03:00+0000,Money Movement,Deposit,,,,DEPOSIT,1000.00,0,,0,0.00,,,,,,,123456,USD")
        t.moneyMovement(deposit_transaction)
        assert t.year(2024).deposit.eur == pytest.approx(917.8522257916476)
        assert t.year(2024).deposit.usd == 1000.0

    def test_money_movement_debit_interest_merged2(self):
        t = Tasty()
        debit_interest_transaction = Transaction.fromString("2021-06-16T23:00:00+0000,Money Movement,Debit Interest,,,,FROM 05/16 THRU 06/15 @ 8    %,-0.87,0,,0,0.00,,,,,,,123456,USD")
        t.moneyMovement(debit_interest_transaction)
        assert t.year(2021).debitInterest.eur == pytest.approx(-0.7175849554602441)
        assert t.year(2021).debitInterest.usd == -0.87

    def test_money_movement_dividend(self):
        t = Tasty()
        dividend_transaction = Transaction.fromString("2021-07-06T23:00:00+0000,Money Movement,Dividend,,UWMC,Equity,UWM HOLDINGS CORPORATION,-3,0,,0,0.00,,UWMC,UWMC,,,,123456,USD")
        t.moneyMovement(dividend_transaction)
        assert t.year(2021).paidDividend.eur == pytest.approx(-2.5342118601115056)
        assert t.year(2021).paidDividend.usd == -3.0
        assert t.year(2021).dividend.usd == 0

    def test_dividend_withholding_is_not_netted_from_income(self):
        income = Transaction.fromString(
            "2025-10-10T23:00:00+0000,Money Movement,Dividend,,NVDY,Equity,"
            "TIDAL TRUST II,397.70,0,,0,0.00,,NVDY,NVDY,,,,123456,USD"
        )
        withholding = Transaction.fromString(
            "2025-10-10T23:00:00+0000,Money Movement,Dividend,,NVDY,Equity,"
            "TIDAL TRUST II,-59.66,0,,0,0.00,,NVDY,NVDY,,,,123456,USD"
        )
        t = Tasty()
        t.history = pd.DataFrame([income, withholding])

        t.processTransactionHistory()

        assert t.year(2025).dividend.usd == 397.70
        assert t.year(2025).withholdingTax.usd == 59.66
        assert t.year(2025).paidDividend.usd == 0

    def test_money_movement_special_dividend_is_cash_income(self):
        t = Tasty()
        transaction = Transaction.fromString(
            "2025-12-17T19:00:00+0000,Money Movement,Special Dividend,,TECL,Equity,"
            "Cash special dividend,8.04,0,,0,0.00,,TECL,TECL,,,,123456,USD"
        )

        t.moneyMovement(transaction)

        assert t.year(2025).dividend.usd == 8.04

    def test_money_movement_deposit_via_withdrawal(self):
        t = Tasty()
        deposit_withdrawal_transaction = Transaction.fromString("2021-03-01T23:00:00+0000,Money Movement,Withdrawal,,,,Wire Funds Received,4770.4,0,,0,0.00,,,,,,,123456,USD")
        t.moneyMovement(deposit_withdrawal_transaction)
        assert t.year(2021).deposit.eur == pytest.approx(3957.8528167261256)
        assert t.year(2021).deposit.usd == 4770.4

    def test_money_movement_securities_lending_income(self):
        t = Tasty()
        lending_income_transaction = Transaction.fromString("2024-08-13T23:00:00+0000,Money Movement,Fully Paid Stock Lending Income,,,,FULLYPAID LENDING REBATE,0.20,0,,0,0.00,,,,,,,123456,USD")
        t.moneyMovement(lending_income_transaction)
        assert t.year(2024).securitiesLendingIncome.eur == pytest.approx(0.1829658768639649, abs=1e-5)
        assert t.year(2024).securitiesLendingIncome.usd == 0.2

    def test_symbol_change_close_is_processed_before_same_time_open(self):
        old_open = Transaction.fromString(
            "2024-01-01T09:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,OLD,Equity,Bought stock,-100,10,10,0,0,,OLD,OLD,,,,123456,USD"
        )
        new_open = Transaction.fromString(
            "2024-01-02T09:00:00+0000,Receive Deliver,Symbol Change,BUY_TO_OPEN,NEW,Equity,Symbol change open,-250,20,0,0,0,,NEW,NEW,,,,123456,USD"
        )
        old_close = Transaction.fromString(
            "2024-01-02T09:00:00+0000,Receive Deliver,Symbol Change,SELL_TO_CLOSE,OLD,Equity,Symbol change close,250,10,0,0,0,,OLD,OLD,,,,123456,USD"
        )
        t = Tasty()
        t.history = pd.DataFrame([old_open, new_open, old_close])

        t.processTransactionHistory()

        lots = t.position_manager.get_all_open_lots()
        assert [(lot.symbol, lot.quantity, lot.amount_usd) for lot in lots] == [
            ("NEW", 20, -100),
        ]
        assert t.position_manager._pending_symbol_change_lots == {}
