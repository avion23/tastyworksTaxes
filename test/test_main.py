from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from tastyworksTaxes.fifo_processor import TradeResult
from tastyworksTaxes.main import main, vorabpauschale_warning_lines
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.tasty import Tasty


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
    ]


def test_cli_marks_unverified_asset_classifications(tmp_path, monkeypatch, capsys):
    source = tmp_path / "transactions.csv"
    source.write_text("data")
    monkeypatch.setattr("sys.argv", ["tastyworks-taxes", str(source)])
    tasty = MagicMock()
    tasty.yearValues = {}
    tasty.position_manager.closed_trades = []
    tasty.unverified_asset_symbols = {"SQQQ", "AAPL"}

    with patch("tastyworksTaxes.main.Tasty", return_value=tasty):
        main()

    output = capsys.readouterr().out
    assert "INCOMPLETE ASSET CLASSIFICATION - NOT FILING-READY" in output
    assert "AAPL, SQQQ" in output
    assert "lack a verified classification in the asset registry" in output
    assert "Verify each symbol's stock/fund status" in output


def fund_trade(opening_date, closing_date):
    return TradeResult(
        symbol="SCHG", position_type=PositionType.stock,
        opening_date=opening_date, closing_date=closing_date, quantity=1,
        profit_usd=10, profit_eur=9, fees_usd=0, fees_eur=0,
        worthless_expiry=False, strike=None, expiry=None,
    )


def test_vorabpauschale_warning_for_fund_held_over_year_boundary():
    tasty = Tasty()
    tasty.position_manager.closed_trades = [
        fund_trade("2023-06-01", "2025-04-01")
    ]
    tasty.year(2025)

    lines = vorabpauschale_warning_lines(tasty)

    assert len(lines) == 1
    assert "fund SCHG held at start of 2024" in lines[0]
    assert "months_before_acquisition=0" in lines[0]
    assert "Basiszins 2.29%" in lines[0]
    assert "deemed received in 2025" in lines[0]


def test_vorabpauschale_warning_for_fund_bought_and_sold_during_calendar_year():
    tasty = Tasty()
    tasty.position_manager.closed_trades = [
        fund_trade("2024-02-01", "2024-10-01")
    ]
    tasty.year(2025)

    lines = vorabpauschale_warning_lines(tasty)

    assert len(lines) == 1
    assert "first acquired in 2024-02" in lines[0]
    assert "months_before_acquisition=1" in lines[0]


def test_vorabpauschale_acquisition_year_warning_for_fund_sold_next_year():
    tasty = Tasty()
    tasty.position_manager.closed_trades = [
        fund_trade("2024-07-15", "2025-03-01")
    ]
    tasty.year(2025)

    lines = vorabpauschale_warning_lines(tasty)

    assert len(lines) == 1
    assert "first acquired in 2024-07" in lines[0]
    assert "months_before_acquisition=6" in lines[0]


def test_vorabpauschale_warning_is_assigned_to_following_assessment_year():
    tasty = Tasty()
    tasty.position_manager.closed_trades = [
        fund_trade("2025-03-01", "2025-09-01")
    ]
    tasty.year(2025)
    tasty.year(2026)

    lines = vorabpauschale_warning_lines(tasty)

    assert len(lines) == 1
    assert "calendar year 2025" in lines[0]
    assert "deemed received in 2026" in lines[0]
    assert "months_before_acquisition=2" in lines[0]
