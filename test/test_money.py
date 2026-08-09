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


def test_usd_to_eur_fails_when_no_rate_is_available():
    with pytest.raises(ValueError, match="no ECB reference rate is available"):
        convert_usd_to_eur(100, date(2100, 1, 1))


def test_usd_to_eur_uses_nearest_prior_rate_on_non_publication_day():
    assert convert_usd_to_eur(100, date(2021, 7, 4)) == pytest.approx(
        convert_usd_to_eur(100, date(2021, 7, 2))
    )


def test_zero_usd_does_not_require_an_exchange_rate():
    assert convert_usd_to_eur(0, date(2100, 1, 1)) == 0.0


def test_get_used_rate_returns_available_usd_to_eur_multiplier():
    assert get_used_rate(date(2021, 7, 6)) == pytest.approx(0.8447372867038352)


def test_debit_interest():
    t = Tasty()
    debit_interest_tx = Transaction.fromString(
        "2022-03-15T23:00:00+0000,Money Movement,Debit Interest,,,,FROM 02/16 THRU 03/15 @ 6    %,-1.25,0,,0,0.00,,,,,,,123456,USD"
    )
    t.moneyMovement(debit_interest_tx)
    assert (
        clean_numpy_str(str(t.year(2022).debitInterest))
        == "{'eur': -1.1372941497588938, 'usd': -1.25}"
    )


def test_dividend():
    t = Tasty()
    dividend_tx = Transaction.fromString(
        "2023-09-20T23:00:00+0000,Money Movement,Dividend,,TUVW,Equity,TUVW HOLDINGS CORPORATION,-4.0,0,,0,0.00,,TUVW,TUVW,,,,123456,USD"
    )
    t.moneyMovement(dividend_tx)
    assert (
        clean_numpy_str(str(t.year(2023).paidDividend))
        == "{'eur': -3.7376191366099794, 'usd': -4.0}"
    )


def test_deposit():
    t = Tasty()
    deposit_tx = Transaction.fromString(
        "2022-06-14T23:00:00+0000,Money Movement,Withdrawal,,,,Wire Funds Received,5125.0,0,,0,0.00,,,,,,,123456,USD"
    )
    t.moneyMovement(deposit_tx)
    assert (
        clean_numpy_str(str(t.year(2022).deposit))
        == "{'eur': 4903.367776502106, 'usd': 5125.0}"
    )
