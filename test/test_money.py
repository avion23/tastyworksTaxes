import sys
import os
import pytest
import re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tastyworksTaxes.money import Money
from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.transaction import Transaction
from tastyworksTaxes.position import PositionType

def clean_numpy_str(s):
    """Remove np.float64 from string representation"""
    return re.sub(r'np\.float64\(([^)]+)\)', r'\1', s)

# Money class tests
def test_money_init_and_repr():
    m = Money(eur=10.5, usd=12.7)
    assert clean_numpy_str(str(m)) == "{'eur': 10.5, 'usd': 12.7}"

def test_money_add():
    a = Money(eur=5, usd=6)
    b = Money(eur=7, usd=8) 
    c = a + b
    assert clean_numpy_str(str(c)) == "{'eur': 12, 'usd': 14}"

def test_money_sub():
    a = Money(eur=5, usd=6)
    b = Money(eur=7, usd=5)
    c = b - a
    assert clean_numpy_str(str(c)) == "{'eur': 2, 'usd': -1}"
    
def test_money_neg():
    m = Money(eur=10, usd=20)
    n = -m
    assert clean_numpy_str(str(n)) == "{'eur': -10, 'usd': -20}"

def test_money_fromUsdToEur():
    c = Money(usd=100)
    c.fromUsdToEur(date='2010-11-21')
    # Check approximate value due to possible rate differences
    assert 73 <= c.eur <= 74

# Tasty money_movement tests
def test_debit_interest():
    t = Tasty()
    debit_interest_tx = Transaction.fromString("06/16/2021 11:00 PM,Money Movement,Debit Interest,,,,0,,,,,0.00,-0.87,FROM 05/16 THRU 06/15 @ 8    %,Individual...39")
    t.moneyMovement(debit_interest_tx)
    assert clean_numpy_str(str(t.year(2021).debitInterest)) == "{'eur': -0.7175849554602441, 'usd': -0.87}"

def test_dividend():
    t = Tasty()
    dividend_tx = Transaction.fromString("07/06/2021 11:00 PM,Money Movement,Dividend,UWMC,,,0,,,,,0.00,-3,UWM HOLDINGS CORPORATION,Individual...39")
    t.moneyMovement(dividend_tx)
    assert clean_numpy_str(str(t.year(2021).dividend)) == "{'eur': -2.5342118601115056, 'usd': -3.0}"

def test_deposit():
    t = Tasty()
    deposit_tx = Transaction.fromString("03/01/2021 11:00 PM,Money Movement,Withdrawal,,,,0,,,,,0.00,4770.4,Wire Funds Received,Individual...39")
    t.moneyMovement(deposit_tx)
    assert clean_numpy_str(str(t.year(2021).deposit)) == "{'eur': 3957.8528167261256, 'usd': 4770.4}"

def test_securities_lending_income():
    t = Tasty("test/merged3.csv")
    lending_income_transaction = Transaction.fromString(
        "08/13/2024 11:00 PM,Money Movement,Fully Paid Stock Lending Income,,,,0,,,,,0.00,0.20,FULLYPAID LENDING REBATE,Individual...39")
    t.moneyMovement(lending_income_transaction)
    # Don't check exact value due to possible currency rate differences
    lending_income = t.year(2024).securitiesLendingIncome
    assert 0.18 <= float(clean_numpy_str(str(lending_income)).split(':')[1].split(',')[0]) <= 0.19
    assert "'usd': 0.2" in clean_numpy_str(str(lending_income))

# Tasty updatePosition tests
def test_update_position_calculations():
    assert Tasty._updatePosition(1, 1) == (2, 0, 0)
    assert Tasty._updatePosition(1, -1) == (0, 0, -1)
    assert Tasty._updatePosition(1, 0) == (1, 0, 0)
    assert Tasty._updatePosition(-1, 1) == (0, 0, 1)
    assert Tasty._updatePosition(-3, 1) == (-2, 0, 1)
    assert Tasty._updatePosition(-3, 2) == (-1, 0, 2)
    assert Tasty._updatePosition(-16, 5) == (-11, 0, 5)
