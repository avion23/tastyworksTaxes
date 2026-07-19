import sys
import os
import logging
import math
import pytest
import re
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tastyworksTaxes.money import Money, _converter, convert_usd_to_eur, get_used_rate
from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.transaction import Transaction

# Skip tests that require the full dataset if it's not available (CI environment)
FULL_DATASET = Path("test/transactions_2018_to_2025.csv")


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
    c.fromUsdToEur(date="2010-11-21")
    assert 73 <= c.eur <= 74


def test_usd_to_eur_weekday_conversion_does_not_warn(caplog):
    with caplog.at_level(logging.WARNING, logger='tastyworksTaxes.money'):
        convert_usd_to_eur(100, date(2021, 7, 6))
    assert not caplog.records


def test_usd_to_eur_weekend_conversion_warns(caplog):
    with caplog.at_level(logging.WARNING, logger='tastyworksTaxes.money'):
        convert_usd_to_eur(100, date(2021, 7, 4))
    assert 'date=2021-07-04' in caplog.text
    assert 'amount=100' in caplog.text
    assert f'rate={get_used_rate(date(2021, 7, 4))}' in caplog.text
    assert 'reason=missing rate for date' in caplog.text


def test_usd_to_eur_out_of_range_conversion_warns(caplog):
    with caplog.at_level(logging.WARNING, logger='tastyworksTaxes.money'):
        convert_usd_to_eur(100, date(1995, 1, 1))
    assert 'reason=date out of range' in caplog.text


@pytest.mark.parametrize(
    ('amount', 'conversion_date'),
    [
        (-100, date(2021, 7, 6)),
        (0, date(2021, 7, 6)),
        (100, date(1995, 1, 1)),
        (100, date(2100, 1, 1)),
    ],
)
def test_usd_to_eur_conversion_value_is_unchanged(amount, conversion_date):
    expected = _converter.convert(amount, 'USD', 'EUR', date=conversion_date)
    assert convert_usd_to_eur(amount, conversion_date) == expected


def test_usd_to_eur_nan_conversion_does_not_warn(caplog):
    with caplog.at_level(logging.WARNING, logger='tastyworksTaxes.money'):
        converted_amount = convert_usd_to_eur(float('nan'), date(2021, 7, 6))

    assert math.isnan(converted_amount)
    assert not [
        record
        for record in caplog.records
        if record.levelno == logging.WARNING
        and 'USD to EUR conversion used fallback' in record.getMessage()
    ]


def test_get_used_rate_returns_usd_to_eur_multiplier():
    assert get_used_rate(date(2021, 7, 4)) == pytest.approx(0.8437631837997469)


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


@pytest.mark.skipif(
    not FULL_DATASET.exists(), reason="Full dataset not available (CI environment)"
)
def test_securities_lending_income():
    t = Tasty(FULL_DATASET)
    lending_income_transaction = Transaction.fromString(
        "2024-08-13T23:00:00+0000,Money Movement,Fully Paid Stock Lending Income,,,,FULLYPAID LENDING REBATE,0.20,0,,0,0.00,,,,,,,123456,USD"
    )
    t.moneyMovement(lending_income_transaction)
    lending_income = t.year(2024).securitiesLendingIncome
    assert (
        0.18
        <= float(clean_numpy_str(str(lending_income)).split(":")[1].split(",")[0])
        <= 0.19
    )
    assert "'usd': 0.2" in clean_numpy_str(str(lending_income))
