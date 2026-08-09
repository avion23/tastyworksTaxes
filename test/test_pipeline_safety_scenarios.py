import copy
import io
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from tastyworksTaxes.asset_classifier import AssetClassifier
from tastyworksTaxes.history import History
from tastyworksTaxes.main import main
from tastyworksTaxes.position_manager import PositionManager
from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.transaction import Transaction


HEADER = (
    "Date,Type,Sub Type,Action,Symbol,Instrument Type,Description,Value,"
    "Quantity,Average Price,Commissions,Fees,Multiplier,Root Symbol,"
    "Underlying Symbol,Expiration Date,Strike Price,Call or Put,Order #,Currency"
)


def row(date, code, subcode, *, action="", symbol="", instrument="",
        description="pipeline marker", value="0", quantity="0", price="",
        commissions="0", fees="0", multiplier="", root="", underlying="",
        expiration="", strike="", call_put="", order="1"):
    return ",".join([
        date, code, subcode, action, symbol, instrument, description, str(value),
        str(quantity), str(price), str(commissions), str(fees), str(multiplier),
        root, underlying, expiration, str(strike), call_put, str(order), "USD",
    ])


def history(*rows):
    return History.fromFile(io.StringIO(HEADER + "\n" + "\n".join(rows)))


def stock_rows(symbol="PIPE"):
    return (
        row("2024-01-02T09:00:00+00:00", "Trade", "Buy to Open",
            action="BUY_TO_OPEN", symbol=symbol, instrument="Equity",
            description="opening marker", value="-100", quantity="1",
            price="100", root=symbol, underlying=symbol, order="1"),
        row("2024-01-03T09:00:00+00:00", "Trade", "Sell to Close",
            action="SELL_TO_CLOSE", symbol=symbol, instrument="Equity",
            description="closing marker", value="110", quantity="1",
            price="110", root=symbol, underlying=symbol, order="2"),
    )


def test_run_is_fresh_repeatable_and_recovers_from_failure():
    tasty = Tasty()
    tasty.history = history(*stock_rows())
    original_history = tasty.history
    classifier = tasty.classifier
    config = tasty.position_manager._corporate_actions_config

    first = tasty.run()
    second = tasty.run()
    assert first[2024].stockProfits.usd == second[2024].stockProfits.usd == 10
    assert len(tasty.position_manager.closed_trades) == 1
    assert tasty.history is original_history
    assert tasty.classifier is classifier
    assert tasty.position_manager._corporate_actions_config is config

    tasty.history = history(row(
        "2024-01-02T09:00:00+00:00", "SENTINEL_CODE", "SENTINEL_SUBCODE",
        description="SENTINEL_DESCRIPTION", value="987654"))
    with pytest.raises(ValueError, match="Unsupported transaction code"):
        tasty.run()
    assert tasty.yearValues == {}
    assert tasty.position_manager.closed_trades == []
    assert tasty.position_manager.get_all_open_lots() == []

    tasty.history = original_history
    assert tasty.run()[2024].stockProfits.usd == 10
    assert len(tasty.position_manager.closed_trades) == 1
    assert tasty.classifier is classifier
    assert tasty.position_manager._corporate_actions_config is config

    tasty.history = History()
    assert tasty.run() == {}
    assert tasty.yearValues == {}
    assert tasty.position_manager.closed_trades == []
    assert tasty.position_manager.get_all_open_lots() == []


def test_first_empty_run_discards_preseeded_derived_state():
    tasty = Tasty()
    tasty.year(2023).deposit.usd = 12
    tasty.position_manager.add_position(
        Transaction(history(stock_rows()[0]).iloc[0])
    )
    tasty.unverified_asset_symbols_by_year = {2023: {"STALE"}}
    tasty.ambiguous_withholding_years = {2023}
    tasty.history = History()

    assert tasty.run() == {}
    assert tasty.yearValues == {}
    assert tasty.position_manager.closed_trades == []
    assert tasty.position_manager.get_all_open_lots() == []
    assert tasty.unverified_asset_symbols_by_year == {}
    assert tasty.ambiguous_withholding_years == set()


@pytest.mark.parametrize(("code", "subcode", "expected"), [
    ("SENTINEL_CODE", "Deposit", "Unsupported transaction code"),
    ("Money Movement", "SENTINEL_SUBCODE", "Unsupported transaction subcode"),
])
def test_prevalidation_is_transactional_and_sanitized(code, subcode, expected):
    tasty = Tasty()
    tasty.year(2023).deposit.usd = 12
    manager_state = copy.deepcopy(tasty.position_manager.__dict__)
    tasty.history = history(
        *stock_rows(),
        row("2024-01-03T10:00:00+00:00", code, subcode,
            description="SENTINEL_DESCRIPTION", value="987654", order="3"),
    )
    with pytest.raises(ValueError) as exc_info:
        tasty.processTransactionHistory()
    message = str(exc_info.value)
    assert expected in message
    assert "SENTINEL" not in message
    assert "987654" not in message
    assert "Description" not in message
    assert "row" not in message.lower()
    assert tasty.year(2023).deposit.usd == 12
    assert tasty.position_manager.__dict__ == manager_state


def test_absolute_time_controls_cross_timezone_order_and_is_required():
    crossed = history(
        row("2024-01-03T00:30:00+14:00", "Trade", "Buy to Open",
            action="BUY_TO_OPEN", symbol="ZONE", instrument="Equity",
            value="-100", quantity="1", price="100", root="ZONE",
            underlying="ZONE", order="1"),
        row("2024-01-02T23:00:00-12:00", "Trade", "Sell to Close",
            action="SELL_TO_CLOSE", symbol="ZONE", instrument="Equity",
            value="110", quantity="1", price="110", root="ZONE",
            underlying="ZONE", order="2"),
    )
    assert crossed.iloc[0]["Date/Time"] > crossed.iloc[1]["Date/Time"]
    assert crossed.iloc[0]["_Absolute Date/Time"] < crossed.iloc[1]["_Absolute Date/Time"]
    tasty = Tasty()
    tasty.history = crossed
    assert tasty.run()[2024].stockProfits.usd == 10

    tasty.history = crossed.drop(columns=["_Absolute Date/Time"])
    with pytest.raises(ValueError, match="Absolute transaction timestamp is required"):
        tasty.run()


@pytest.mark.parametrize(("open_offset", "close_offset", "succeeds"), [
    ("+02:00", "-02:00", True),
    ("-02:00", "+02:00", False),
])
def test_absolute_time_breaks_same_local_wall_time_ties(
    open_offset, close_offset, succeeds
):
    tasty = Tasty()
    tasty.history = history(
        row(f"2024-01-03T10:00:00{open_offset}", "Trade", "Buy to Open",
            action="BUY_TO_OPEN", symbol="WALL", instrument="Equity",
            value="-100", quantity="1", price="100", root="WALL",
            underlying="WALL", order="1"),
        row(f"2024-01-03T10:00:00{close_offset}", "Trade", "Sell to Close",
            action="SELL_TO_CLOSE", symbol="WALL", instrument="Equity",
            value="110", quantity="1", price="110", root="WALL",
            underlying="WALL", order="2"),
    )

    if succeeds:
        assert tasty.run()[2024].stockProfits.usd == 10
        return
    with pytest.raises(ValueError, match="Position close found no open position"):
        tasty.run()
    assert tasty.yearValues == {}
    assert tasty.position_manager.closed_trades == []
    assert tasty.position_manager.get_all_open_lots() == []


def test_late_run_failure_is_atomic_and_corrected_rerun_succeeds():
    tasty = Tasty()
    tasty.history = history(stock_rows()[0])
    original_history = tasty.history
    classifier = tasty.classifier
    config = tasty.position_manager._corporate_actions_config

    with patch.object(
        classifier, "effective_checkpoints", side_effect=RuntimeError("late failure")
    ):
        with pytest.raises(RuntimeError, match="late failure"):
            tasty.run()

    assert tasty.yearValues == {}
    assert tasty.position_manager.closed_trades == []
    assert tasty.position_manager.get_all_open_lots() == []
    assert tasty.unverified_asset_symbols_by_year == {}
    assert tasty.short_stock_trades_by_year == {}
    assert tasty.fund_tax_review_years == set()
    assert tasty.ambiguous_withholding_years == set()
    assert tasty.unsupported_tax_category_symbols_by_year == {}
    assert tasty._withholding_remaining == {}
    assert tasty._asset_classification_checks == set()
    assert tasty.history is original_history
    assert tasty.classifier is classifier
    assert tasty.position_manager._corporate_actions_config is config

    assert 2024 in tasty.run()
    assert len(tasty.position_manager.get_all_open_lots()) == 1


def dividend(value, order):
    return row("2025-01-27T12:00:00+00:00", "Money Movement", "Dividend",
               symbol="AMAT", description="dividend marker", value=value,
               order=order)


def test_withholding_ambiguity_state_and_main_warning(tmp_path, monkeypatch, capsys):
    positive, negative = dividend("100", "1"), dividend("-15", "2")
    tasty = Tasty()
    tasty.history = history(positive, negative)
    values = tasty.run()[2025]
    assert values.dividend.usd == 100
    assert values.withholdingTax.usd == 15
    assert values.paidDividend.usd == 0
    assert tasty.ambiguous_withholding_years == {2025}

    positive_only = Tasty()
    positive_only.history = history(positive)
    assert positive_only.run()[2025].dividend.usd == 100
    assert positive_only.ambiguous_withholding_years == set()

    negative_only = Tasty()
    negative_only.history = history(dividend("-15", "3"))
    negative_values = negative_only.run()[2025]
    assert negative_values.withholdingTax.usd == 0
    assert negative_values.paidDividend.usd == -15
    assert negative_only.ambiguous_withholding_years == set()

    csv_path = tmp_path / "dividend.csv"
    csv_path.write_text(HEADER + "\n" + positive + "\n" + negative + "\n")
    monkeypatch.setattr(sys, "argv", ["tastyworks-taxes", str(csv_path)])
    main()
    output = capsys.readouterr().out
    assert "AMBIGUOUS DIVIDEND WITHHOLDING - NOT FILING-READY" in output


def test_unsupported_category_state_generic_log_and_main_warning(
    tmp_path, monkeypatch, capsys, caplog
):
    rows = stock_rows("BTC/USD")
    tasty = Tasty()
    tasty.history = history(*rows)
    with caplog.at_level(logging.WARNING):
        result = tasty.run()
    assert result[2024].stockProfits.usd == 0
    assert tasty.position_manager.closed_trades[0].profit_usd == 10
    assert tasty.unsupported_tax_category_symbols_by_year == {2024: {"BTC/USD"}}
    dividend_tasty = Tasty()
    dividend_tasty.history = history(row(
        "2024-01-03T12:00:00+00:00", "Money Movement", "Dividend",
        symbol="BTC/USD", description="unsupported income", value="25", order="3",
    ))
    dividend_values = dividend_tasty.run()[2024]
    assert dividend_values.dividend.usd == 0
    assert dividend_values.paidDividend.usd == 0
    assert dividend_values.fundDistributions.usd == 0
    assert dividend_values.fundDistributionTaxable.usd == 0
    assert dividend_tasty.unsupported_tax_category_symbols_by_year == {
        2024: {"BTC/USD"}
    }
    assert any(r.getMessage() == "Unsupported tax category requires manual review"
               for r in caplog.records)
    assert all("BTC/USD" not in r.getMessage() for r in caplog.records)

    csv_path = tmp_path / "unsupported.csv"
    csv_path.write_text(HEADER + "\n" + "\n".join(rows) + "\n")
    monkeypatch.setattr(sys, "argv", ["tastyworks-taxes", str(csv_path)])
    main()
    output = capsys.readouterr().out
    assert "UNSUPPORTED TAX CATEGORY - NOT FILING-READY" in output
    assert "BTC/USD" in output
    assert "Calculate these entries manually" in output


class ConfigResource:
    def __init__(self, content=None, error=None):
        self.content, self.error = content, error

    def joinpath(self, name):
        assert name == "corporate_actions.csv"
        return self

    def open(self, *args, **kwargs):
        if self.error:
            raise self.error
        return io.StringIO(self.content)


@pytest.mark.parametrize("resource", [
    ConfigResource(error=FileNotFoundError()),
    ConfigResource(""),
    ConfigResource('date,symbol,ratio,source\n"unterminated'),
    ConfigResource("date,symbol,ratio\n2024-01-02,PIPE,0.5\n"),
    ConfigResource("date,symbol,ratio,source,extra\n2024-01-02,PIPE,0.5,evidence,x\n"),
    ConfigResource("date,symbol,ratio,source\n2024-01-02,PIPE,0.5,evidence,x\n"),
    ConfigResource("symbol,date,ratio,source\nPIPE,2024-01-02,0.5,evidence\n"),
    ConfigResource("date,symbol,ratio,source\n2024-01-02,PIPE,nan,evidence\n"),
    ConfigResource("date,symbol,ratio,source\n2024-01-02,PIPE,inf,evidence\n"),
    ConfigResource("date,symbol,ratio,source\n2024-01-02,PIPE,0,evidence\n"),
    ConfigResource("date,symbol,ratio,source\n2024-01-02,PIPE,-0.5,evidence\n"),
    ConfigResource("date,symbol,ratio,source\n2024-02-30,PIPE,0.5,evidence\n"),
    ConfigResource("date,symbol,ratio,source\n2024-1-02,PIPE,0.5,evidence\n"),
    ConfigResource("date,symbol,ratio,source\n2024-01-02,PIPE,0.5,evidence\n2024-01-02,PIPE,0.25,other\n"),
    ConfigResource("date,symbol,ratio,source\n2024-01-02,,0.5,evidence\n"),
    ConfigResource("date,symbol,ratio,source\n2024-01-02,PIPE,0.5,\n"),
])
def test_corporate_action_config_fails_closed_and_sanitized(resource):
    with patch("tastyworksTaxes.position_manager.files", return_value=resource):
        with pytest.raises(ValueError) as exc_info:
            PositionManager()
    assert str(exc_info.value) in {
        "Corporate actions configuration is unavailable",
        "Corporate actions configuration is invalid",
    }
    assert "PIPE" not in str(exc_info.value)


def test_packaged_corporate_action_config_is_valid():
    config = PositionManager()._corporate_actions_config
    assert config["reverse_splits"][0]["ratio"] == 0.125


def test_imports_preserve_paths_and_logger_levels_from_arbitrary_cwd(tmp_path):
    package_root = str(Path(__file__).resolve().parents[1])
    script = r'''import json
import logging
import sys
path = list(sys.path)
root = logging.getLogger().level
named = logging.getLogger("tastyworksTaxes.tasty").level
import tastyworksTaxes.position
import tastyworksTaxes.tasty
print(json.dumps({"path": path == sys.path, "root": root == logging.getLogger().level,
                  "named": named == logging.getLogger("tastyworksTaxes.tasty").level}))'''
    env = os.environ.copy()
    env["PYTHONPATH"] = package_root
    completed = subprocess.run([sys.executable, "-c", script], cwd=tmp_path,
                               env=env, text=True, capture_output=True, check=True)
    assert json.loads(completed.stdout) == {"path": True, "root": True, "named": True}


def test_direct_asset_classifier_logs_are_generic(caplog):
    classifier = AssetClassifier()
    symbols = ["PRIVATE_UNKNOWN", "AOR", "BTC/USD"]
    assert [
        classifier.unsupported_asset_state(symbol)[0] for symbol in symbols
    ] == ["unknown", "unverified", "unsupported_tax_category"]

    with caplog.at_level(logging.WARNING):
        classifier.check_unsupported_assets(symbols)

    assert [record.getMessage() for record in caplog.records] == [
        "Asset classification requires manual review",
        "Asset classification requires manual review",
        "Unsupported tax category requires manual review",
    ]
    messages = "\n".join(record.getMessage() for record in caplog.records)
    for identifier in [*symbols, "INDIVIDUAL_STOCK", "CRYPTO", "SO"]:
        assert identifier not in messages


def test_position_logs_are_generic(caplog):
    transaction = Transaction(history(stock_rows("SECRET")[0]).iloc[0])
    manager = PositionManager()
    with caplog.at_level(logging.DEBUG):
        manager.add_position(transaction)
    messages = "\n".join(record.getMessage() for record in caplog.records)
    assert "Opened position" in messages
    for secret in ["SECRET", "opening marker", "-100", "100.0", "2024-01-02"]:
        assert secret not in messages



def test_position_manager_exceptions_are_generic_and_sanitized():
    manager = PositionManager()
    manager.add_position(Transaction(history(row(
        "2024-01-03T09:00:00+00:00", "Trade", "Buy to Open",
        action="BUY_TO_OPEN", symbol="PRIVATE_ID", instrument="Equity",
        description="PRIVATE_DESCRIPTION", value="-987654", quantity="1",
        price="987654", root="PRIVATE_ID", underlying="PRIVATE_ID",
    )).iloc[0]))
    close = Transaction(history(row(
        "2024-01-04T09:00:00+00:00", "Trade", "Sell to Close",
        action="SELL_TO_CLOSE", symbol="PRIVATE_ID", instrument="Equity",
        description="PRIVATE_DESCRIPTION", value="1975308", quantity="2",
        price="987654", root="PRIVATE_ID", underlying="PRIVATE_ID",
    )).iloc[0])
    with pytest.raises(ValueError) as exc_info:
        manager.add_position(close)
    assert str(exc_info.value) == "Position close exceeds available position"
    assert exc_info.value.__cause__ is None

    reverse_split = Transaction(history(row(
        "2024-01-05T09:00:00+00:00", "Receive Deliver", "Reverse Split",
        symbol="PRIVATE_ID", instrument="Equity",
        description="PRIVATE_DESCRIPTION", value="0", quantity="0",
        root="PRIVATE_ID", underlying="PRIVATE_ID",
    )).iloc[0])
    with pytest.raises(ValueError) as exc_info:
        manager.add_position(reverse_split)
    assert str(exc_info.value) == (
        "REVERSE SPLIT RATIO UNKNOWN: add a validated event to "
        "corporate_actions.csv and re-run"
    )
    assert exc_info.value.__cause__ is None

    messages = "\n".join([
        "Position close exceeds available position",
        str(exc_info.value),
    ])
    for secret in [
        "PRIVATE_ID", "PRIVATE_DESCRIPTION", "987654", "1975308", "2024-01-05"
    ]:
        assert secret not in messages


def test_closed_trades_sink_log_is_generic(tmp_path, monkeypatch, caplog):
    input_path = tmp_path / "input.csv"
    input_path.write_text(HEADER + "\n" + "\n".join(stock_rows()) + "\n")
    sink_path = tmp_path / "PRIVATE_SINK.csv"
    monkeypatch.setattr(sys, "argv", [
        "tastyworks-taxes", str(input_path), "--write-closed-trades", str(sink_path),
    ])

    with caplog.at_level(logging.INFO):
        main()

    assert sink_path.is_file()
    messages = [record.getMessage() for record in caplog.records]
    assert "Writing closed trades" in messages
    assert all("PRIVATE_SINK" not in message for message in messages)
    assert all(str(sink_path) not in message for message in messages)
