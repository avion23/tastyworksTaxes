from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from tastyworksTaxes.main import main
from tastyworksTaxes.values import Values


def test_cli_refuses_to_overwrite_input(tmp_path, monkeypatch):
    source = tmp_path / "transactions.csv"
    source.write_text("data")
    monkeypatch.setattr(
        "sys.argv", ["tastyworks-taxes", str(source), "-w", str(source)]
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 2
    assert source.read_text() == "data"


def test_cli_replaces_stale_output_with_header_only_csv(tmp_path, monkeypatch):
    source = tmp_path / "transactions.csv"
    source.write_text("data")
    output = tmp_path / "closed.csv"
    output.write_text("stale,data\n1,2\n")
    monkeypatch.setattr(
        "sys.argv", ["tastyworks-taxes", str(source), "-w", str(output)]
    )
    tasty = MagicMock()
    tasty.yearValues = {}
    tasty.position_manager.closed_trades = []

    with patch("tastyworksTaxes.main.Tasty", return_value=tasty):
        main()

    result = pd.read_csv(output)
    assert result.empty
    assert list(result.columns) == [
        "symbol", "position_type", "opening_date", "closing_date", "quantity",
        "profit_usd", "profit_eur", "fees_usd", "fees_eur",
        "worthless_expiry", "strike", "expiry",
        "opening_profit_usd", "opening_profit_eur",
        "closing_profit_usd", "closing_profit_eur",
        "opening_fees_usd", "opening_fees_eur",
        "closing_fees_usd", "closing_fees_eur",
        "settled_by_exercise",
    ]


def test_cli_marks_unverified_asset_classifications_in_each_annual_report(
    tmp_path, monkeypatch, capsys
):
    source = tmp_path / "transactions.csv"
    source.write_text("data")
    monkeypatch.setattr("sys.argv", ["tastyworks-taxes", str(source)])
    tasty = MagicMock()
    tasty.yearValues = {2020: Values(), 2021: Values(), 2022: Values()}
    tasty.position_manager.closed_trades = []
    tasty.unverified_asset_symbols_by_year = {
        2020: {"SQQQ", "AAPL"},
        2022: {"XYZ"},
    }
    tasty.short_stock_trades_by_year = {}

    with (
        patch("tastyworksTaxes.main.Tasty", return_value=tasty),
        patch("tastyworksTaxes.main.Printer") as printer,
    ):
        printer.return_value.generateGermanTaxReport.return_value = "REPORT"
        main()

    output = capsys.readouterr().out
    reports = {
        year: output.split(f"Values for year {year} in Euro:", 1)[1].split(
            "Values for year", 1
        )[0]
        for year in (2020, 2021, 2022)
    }
    assert "AAPL, SQQQ" in reports[2020]
    assert "INCOMPLETE ASSET CLASSIFICATION" not in reports[2021]
    assert "XYZ" in reports[2022]
    assert output.count("INCOMPLETE ASSET CLASSIFICATION - NOT FILING-READY") == 2
    assert output.index("INCOMPLETE ASSET CLASSIFICATION") > output.index(
        "Values for year 2020"
    )
    assert "lack a verified classification in the asset registry" in output
    assert "Verify each symbol's stock/fund status" in output


def test_cli_marks_closed_short_stock_trades_only_in_their_annual_report(
    tmp_path, monkeypatch, capsys
):
    source = tmp_path / "transactions.csv"
    source.write_text("data")
    monkeypatch.setattr("sys.argv", ["tastyworks-taxes", str(source)])
    tasty = MagicMock()
    tasty.yearValues = {2020: Values(), 2021: Values(), 2022: Values()}
    tasty.position_manager.closed_trades = []
    tasty.unverified_asset_symbols_by_year = {}
    tasty.short_stock_trades_by_year = {
        2021: [MagicMock(symbol="GME"), MagicMock(symbol="AMC")]
    }

    with (
        patch("tastyworksTaxes.main.Tasty", return_value=tasty),
        patch("tastyworksTaxes.main.Printer") as printer,
    ):
        printer.return_value.generateGermanTaxReport.return_value = "REPORT"
        main()

    output = capsys.readouterr().out
    reports = {
        year: output.split(f"Values for year {year} in Euro:", 1)[1].split(
            "Values for year", 1
        )[0]
        for year in (2020, 2021, 2022)
    }
    assert "CLOSED SHORT-STOCK TRADES" not in reports[2020]
    assert "AMC, GME" in reports[2021]
    assert "CLOSED SHORT-STOCK TRADES" not in reports[2022]
    assert output.count("CLOSED SHORT-STOCK TRADES - NOT FILING-READY") == 1
    assert "potential 30% substitute assessment" in reports[2021]
    assert "this rule is not calculated" in reports[2021]
    assert "Review these trades manually" in reports[2021]
