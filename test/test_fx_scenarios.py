from io import StringIO
import logging

import pytest

from tastyworksTaxes import money
from tastyworksTaxes.history import History
from tastyworksTaxes.printer import Printer
from tastyworksTaxes.tasty import Tasty


def _interest_history(transaction_date: str, amount: str) -> History:
    csv = (
        "Date,Type,Sub Type,Value,Description,Currency\n"
        f"{transaction_date},Money Movement,Credit Interest,{amount},Interest,USD\n"
    )
    return History.fromFile(StringIO(csv))


def test_available_weekday_rate_flows_into_the_annual_tax_report():
    tasty = Tasty()
    tasty.history = _interest_history("2021-07-06T12:00:00Z", "100")

    tasty.run()
    report = Printer(tasty.yearValues[2021], []).generateGermanTaxReport()

    assert report.zinseinnahmen == pytest.approx(84.47372867038351)
    assert report.z19_auslaendische_kapitalertraege == pytest.approx(
        84.47372867038351
    )


@pytest.mark.parametrize(
    "transaction_date",
    ["2021-07-04T12:00:00Z", "2100-01-01T12:00:00Z"],
)
def test_unavailable_rates_fail_closed_without_logging_financial_data(
    transaction_date, caplog
):
    with caplog.at_level(logging.WARNING):
        with pytest.raises(ValueError) as exc_info:
            _interest_history(transaction_date, "123.45")

    message = str(exc_info.value)
    assert "no ECB reference rate is available" in message
    assert "bundled rate range" in message
    assert "2021" not in message
    assert "2100" not in message
    assert "123.45" not in message
    assert "rate=" not in message
    assert not caplog.records


def test_zero_value_rows_do_not_access_the_converter(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("converter must not be called for zero")

    monkeypatch.setattr(money._converter, "convert", fail_if_called)

    history = _interest_history("2100-01-01T12:00:00Z", "0")

    assert history.loc[0, "AmountEuro"] == 0.0
    assert history.loc[0, "FeesEuro"] == 0.0


def test_internal_converter_failures_propagate(monkeypatch):
    def corrupted_converter(*args, **kwargs):
        raise RuntimeError("converter corruption")

    monkeypatch.setattr(money._converter, "convert", corrupted_converter)

    with pytest.raises(RuntimeError, match="converter corruption"):
        _interest_history("2021-07-06T12:00:00Z", "100")
