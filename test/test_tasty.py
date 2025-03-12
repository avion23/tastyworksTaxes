import sys
import os
import pytest
from pathlib import Path

from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.transaction import Transaction
from tastyworksTaxes.position import PositionType

class TestTasty:
    def test_money_movement_debit_interest(self):
        t = Tasty()
        debit_interest_transaction = Transaction.fromString("08/16/2019 11:00 PM,Money Movement,Withdrawal,,,,0,,,,,0.00,-9.81,FROM 07/16 THRU 08/15 @ 8    %,Individual...39")
        t.moneyMovement(debit_interest_transaction)
        assert t.year(2019).debitInterest.eur == -8.856988082340196
        assert t.year(2019).debitInterest.usd == -9.81

    def test_money_movement_deposit_transfer(self):
        t = Tasty()
        deposit_transfer_transaction = Transaction.fromString("03/08/2018 11:00 PM,Money Movement,Transfer,,,,0,,,,,0.00,1200,Wire Funds Received,Individual...39")
        t.moneyMovement(deposit_transfer_transaction)
        assert t.year(2018).transfer.eur == 966.10578858385
        assert t.year(2018).transfer.usd == 1200.0

    def test_money_movement_balance_adjustment(self):
        t = Tasty()
        balance_adjustment_transaction = Transaction.fromString("03/24/2018 3:09 PM,Money Movement,Balance Adjustment,,,,0,,,,,0.00,-0.01,Regulatory fee adjustment,Individual...39")
        t.moneyMovement(balance_adjustment_transaction)
        assert t.year(2018).balanceAdjustment.eur == -0.008085599547206425
        assert t.year(2018).balanceAdjustment.usd == -0.01

    def test_money_movement_fee(self):
        t = Tasty()
        fee_transaction = Transaction.fromString("03/23/2018 10:00 PM,Money Movement,Fee,LFIN,,,0,,,,,0.00,-43.24,LONGFIN CORP,Individual...39")
        t.moneyMovement(fee_transaction)
        assert t.year(2018).fee.eur == -35.02348938927588
        assert t.year(2018).fee.usd == -43.24

    def test_money_movement_credit_interest(self):
        t = Tasty("test/merged.csv")
        credit_interest_transaction = Transaction.fromString("12/16/2020 11:00 PM,Money Movement,Credit Interest,,,,0,,,,,0.000,0.030,INTEREST ON CREDIT BALANCE,Individual...39")
        t.moneyMovement(credit_interest_transaction)
        assert t.year(2020).creditInterest.eur == pytest.approx(0.02461235540241201)
        assert t.year(2020).creditInterest.usd == 0.03

    def test_money_movement_credit_interest_via_deposit(self):
        t = Tasty("test/merged.csv")
        deposit_transaction = Transaction.fromString("10/16/2019 11:00 PM,Money Movement,Deposit,,,,0,,,,,0.000,0.010,INTEREST ON CREDIT BALANCE,Individual...39")
        t.moneyMovement(deposit_transaction)
        assert t.year(2019).creditInterest.eur == pytest.approx(0.009070294784580499)
        assert t.year(2019).creditInterest.usd == 0.01

    def test_money_movement_general_deposit(self):
        t = Tasty("test/merged.csv")
        deposit_transaction = Transaction.fromString("03/07/2024 8:03 PM,Money Movement,Deposit,,,,0,,,,,0.00,1000.00,DEPOSIT,Individual...39")
        t.moneyMovement(deposit_transaction)
        assert t.year(2024).deposit.eur == pytest.approx(917.8522257916476)
        assert t.year(2024).deposit.usd == 1000.0

    def test_money_movement_debit_interest_merged2(self):
        t = Tasty()
        debit_interest_transaction = Transaction.fromString("06/16/2021 11:00 PM,Money Movement,Debit Interest,,,,0,,,,,0.00,-0.87,FROM 05/16 THRU 06/15 @ 8    %,Individual...39")
        t.moneyMovement(debit_interest_transaction)
        assert t.year(2021).debitInterest.eur == pytest.approx(-0.7175849554602441)
        assert t.year(2021).debitInterest.usd == -0.87

    def test_money_movement_dividend(self):
        t = Tasty()
        dividend_transaction = Transaction.fromString("07/06/2021 11:00 PM,Money Movement,Dividend,UWMC,,,0,,,,,0.00,-3,UWM HOLDINGS CORPORATION,Individual...39")
        t.moneyMovement(dividend_transaction)
        assert t.year(2021).dividend.eur == pytest.approx(-2.5342118601115056)
        assert t.year(2021).dividend.usd == -3.0

    def test_money_movement_deposit_via_withdrawal(self):
        t = Tasty()
        deposit_withdrawal_transaction = Transaction.fromString("03/01/2021 11:00 PM,Money Movement,Withdrawal,,,,0,,,,,0.00,4770.4,Wire Funds Received,Individual...39")
        t.moneyMovement(deposit_withdrawal_transaction)
        assert t.year(2021).deposit.eur == pytest.approx(3957.8528167261256)
        assert t.year(2021).deposit.usd == 4770.4

    def test_money_movement_securities_lending_income(self):
        t = Tasty("test/merged3.csv")
        lending_income_transaction = Transaction.fromString("08/13/2024 11:00 PM,Money Movement,Fully Paid Stock Lending Income,,,,0,,,,,0.00,0.20,FULLYPAID LENDING REBATE,Individual...39")
        t.moneyMovement(lending_income_transaction)
        assert t.year(2024).securitiesLendingIncome.eur == pytest.approx(0.1829658768639649, abs=1e-5)
        assert t.year(2024).securitiesLendingIncome.usd == 0.2
