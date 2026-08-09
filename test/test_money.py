import sys
import os
import pytest
import re
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tastyworksTaxes.money import Money, convert_usd_to_eur, get_used_rate
from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.transaction import Transaction


def clean_numpy_str(s):
    """Remove np.float64 from string representation"""
    return re.sub(r"np\.float64\(([^)]+)\)", r"\1", s)


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
    c.fromUsdToEur(date="2010-11-22")
    assert 73 <= c.eur <= 74


def test_usd_to_eur_uses_available_weekday_rate():
    assert convert_usd_to_eur(100, date(2021, 7, 6)) == pytest.approx(
        84.47372867038351
    )


@pytest.mark.parametrize("conversion_date", [date(2021, 7, 4), date(2100, 1, 1)])
def test_usd_to_eur_fails_when_no_rate_is_available(conversion_date):
    with pytest.raises(ValueError, match="no ECB reference rate is available"):
        convert_usd_to_eur(100, conversion_date)


def test_zero_usd_does_not_require_an_exchange_rate():
    assert convert_usd_to_eur(0, date(2100, 1, 1)) == 0.0


def test_get_used_rate_returns_available_usd_to_eur_multiplier():
    assert get_used_rate(date(2021, 7, 6)) == pytest.approx(0.8447372867038352)


def test_debit_interest():
    t = Tasty()
    debit_interest_tx = Transaction.fromString(
        "2021-06-16T23:00:00+0000,Money Movement,Debit Interest,,,,FROM 05/16 THRU 06/15 @ 8    %,-0.87,0,,0,0.00,,,,,,,123456,USD"
    )
    t.moneyMovement(debit_interest_tx)
    assert (
        clean_numpy_str(str(t.year(2021).debitInterest))
        == "{'eur': -0.7175849554602441, 'usd': -0.87}"
    )


def test_dividend():
    t = Tasty()
    dividend_tx = Transaction.fromString(
        "2021-07-06T23:00:00+0000,Money Movement,Dividend,,UWMC,Equity,UWM HOLDINGS CORPORATION,-3,0,,0,0.00,,UWMC,UWMC,,,,123456,USD"
    )
    t.moneyMovement(dividend_tx)
    assert (
        clean_numpy_str(str(t.year(2021).paidDividend))
        == "{'eur': -2.5342118601115056, 'usd': -3.0}"
    )


def test_deposit():
    t = Tasty()
    deposit_tx = Transaction.fromString(
        "2021-03-01T23:00:00+0000,Money Movement,Withdrawal,,,,Wire Funds Received,4770.4,0,,0,0.00,,,,,,,123456,USD"
    )
    t.moneyMovement(deposit_tx)
    assert (
        clean_numpy_str(str(t.year(2021).deposit))
        == "{'eur': 3957.8528167261256, 'usd': 4770.4}"
    )
