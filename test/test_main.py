from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from tastyworksTaxes.main import main


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
    assert "Verify every classification" in output
