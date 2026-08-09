from datetime import date
from io import StringIO
import logging

import pandas as pd
import pytest

from tastyworksTaxes import money
from tastyworksTaxes.history import History
from tastyworksTaxes.printer import Printer
from tastyworksTaxes.tasty import Tasty

from test.broker_csv import BROKER_COLUMNS, broker_row, stock_trade


def _interest_history(transaction_date: str, amount: str) -> History:
    buf = StringIO()
    pd.DataFrame([broker_row(**{
        'Date': transaction_date,
        'Sub Type': 'Credit Interest',
        'Value': amount,
        'Description': 'Interest',
    })], columns=BROKER_COLUMNS).to_csv(buf, index=False)
    buf.seek(0)
    return History.fromFile(buf)


def _trade_history(transaction_date: str, amount: str) -> History:
    buf = StringIO()
    pd.DataFrame([stock_trade(**{
        'Date': transaction_date,
        'Sub Type': 'Buy to Open',
        'Value': amount,
        'Description': 'SYNTHETIC STOCK FILL',
    })], columns=BROKER_COLUMNS).to_csv(buf, index=False)
    buf.seek(0)
    return History.fromFile(buf)


def test_available_weekday_rate_flows_into_the_annual_tax_report():
    tasty = Tasty()
    tasty.history = _interest_history("2021-07-06T12:00:00Z", "100")

    tasty.run()
    report = Printer(tasty.yearValues[2021], []).generateGermanTaxReport()

    assert report.zinseinnahmen == pytest.approx(84.47372867038351)
    assert report.z19_auslaendische_kapitalertraege == pytest.approx(
        84.47372867038351
    )


def test_unavailable_rates_fail_closed_without_logging_financial_data(caplog):
    with caplog.at_level(logging.WARNING):
        with pytest.raises(ValueError) as exc_info:
            _trade_history("2100-01-01T12:00:00Z", "123.45")

    message = str(exc_info.value)
    assert "no ECB reference rate is available" in message
    assert "bundled rate range" in message
    assert "2021" not in message
    assert "2100" not in message
    assert "123.45" not in message
    assert "rate=" not in message
    assert not caplog.records


def test_trades_on_ecb_holidays_use_nearest_prior_rate():
    history = _trade_history("2020-04-13T12:00:00Z", "123.45")

    nearest_prior_date = max(
        rate_date
        for rate_date, rate in money._converter._rates['USD'].items()
        if rate is not None and rate_date <= date(2020, 4, 13)
    )
    expected = money.convert_usd_to_eur(123.45, nearest_prior_date)

    assert history.loc[0, "AmountEuro"] == pytest.approx(expected)
    assert history.loc[0, "AmountEuro"] > 0


@pytest.mark.parametrize(
    "transaction_date",
    [date(2021, 7, 4), date(2100, 1, 1)],
)
def test_money_movements_on_unavailable_dates_use_nearest_prior_rate(
    transaction_date,
):
    if transaction_date == date(2100, 1, 1):
        with pytest.raises(ValueError, match="no ECB reference rate is available"):
            _interest_history(
                f"{transaction_date.isoformat()}T12:00:00Z", "123.45"
            )
        return

    history = _interest_history(
        f"{transaction_date.isoformat()}T12:00:00Z", "123.45"
    )

    nearest_prior_date = max(
        rate_date
        for rate_date, rate in money._converter._rates['USD'].items()
        if rate is not None and rate_date <= transaction_date
    )
    assert nearest_prior_date == date(2021, 7, 2)
    expected = money.convert_usd_to_eur(123.45, nearest_prior_date)

    assert history.loc[0, "AmountEuro"] == pytest.approx(expected)
    assert history.loc[0, "AmountEuro"] > 0


def test_zero_value_rows_do_not_access_the_converter(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("converter must not be called for zero")

    monkeypatch.setattr(money._converter, "convert", fail_if_called)

    history = _interest_history("2100-01-01T12:00:00Z", "0")

    assert history.loc[0, "AmountEuro"] == 0.0
    assert history.loc[0, "FeesEuro"] == 0.0


@pytest.mark.parametrize("amount", [True, False, "100", None, 1 + 2j])
def test_non_real_usd_amounts_fail_before_converter_access(monkeypatch, amount):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("converter must not be called for an invalid amount")

    monkeypatch.setattr(money._converter, "convert", fail_if_called)

    with pytest.raises(TypeError) as exc_info:
        money.convert_usd_to_eur(amount, "2021-07-06")

    assert str(exc_info.value) == "USD amount must be a finite real number."


@pytest.mark.parametrize("amount", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_usd_amounts_fail_before_converter_access(monkeypatch, amount):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("converter must not be called for an invalid amount")

    monkeypatch.setattr(money._converter, "convert", fail_if_called)

    with pytest.raises(ValueError) as exc_info:
        money.convert_usd_to_eur(amount, "2021-07-06")

    assert str(exc_info.value) == "USD amount must be finite."


class _DateLike:
    def __init__(self, result):
        self.result = result

    def date(self):
        return self.result


@pytest.mark.parametrize(
    "conversion_date",
    [None, "", "2021-07-06", True, False, object(), _DateLike(None)],
)
def test_invalid_dates_fail_before_converter_access(monkeypatch, conversion_date):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("converter must not be called for an invalid date")

    monkeypatch.setattr(money._converter, "convert", fail_if_called)

    for operation in (
        lambda: money.convert_usd_to_eur(0.0, conversion_date),
        lambda: money.get_used_rate(conversion_date),
    ):
        with pytest.raises(TypeError) as exc_info:
            operation()
        assert str(exc_info.value) == (
            "Conversion date must be an explicit calendar date."
        )


def test_date_like_values_are_normalised_to_explicit_calendar_dates():
    amount = money.convert_usd_to_eur(100, _DateLike(date(2021, 7, 6)))

    assert amount == pytest.approx(84.47372867038351)


def test_internal_converter_failures_propagate(monkeypatch):
    def corrupted_converter(*args, **kwargs):
        raise RuntimeError("converter corruption")

    monkeypatch.setattr(money._converter, "convert", corrupted_converter)

    with pytest.raises(RuntimeError, match="converter corruption"):
        _interest_history("2021-07-06T12:00:00Z", "100")


def test_nearest_prior_rate_fallback_is_reported_once_per_load(caplog):
    with caplog.at_level(logging.WARNING, logger='tastyworksTaxes.history'):
        _interest_history("2021-07-04T12:00:00Z", "123.45")

    assert "1 row(s) converted at the nearest earlier ECB reference rate" in caplog.text
    assert caplog.text.count("nearest earlier ECB reference rate") == 1

    caplog.clear()
    with caplog.at_level(logging.WARNING, logger='tastyworksTaxes.history'):
        _interest_history("2021-07-06T12:00:00Z", "100")

    assert "row(s) converted at the nearest earlier ECB reference rate" not in caplog.text
