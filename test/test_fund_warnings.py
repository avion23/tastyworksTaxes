import pytest
import logging
from datetime import date, datetime

from tastyworksTaxes.asset_classifier import AssetClassifier
from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.position_lot import PositionLot
from tastyworksTaxes.transaction import Transaction
from tastyworksTaxes.fifo_processor import TradeResult
from tastyworksTaxes.history import History
from test.test_pipeline_safety_scenarios import history, row

class TestTastyWithAssetClassifier:
    @pytest.fixture
    def tasty_instance(self):
        return Tasty()
    
    def test_asset_classification_warnings_in_equity_etf_profits(self, tasty_instance, caplog):
        trades = [
            TradeResult(
                symbol='UNKNOWN_FUND',
                position_type=PositionType.stock,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=120.0,
                profit_eur=100.0,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
            )
        ]
        
        with caplog.at_level(logging.WARNING):
            tasty_instance._checkAssetClassifications(trades)
        
        assert "Asset classification requires manual review" in caplog.text
        assert "UNKNOWN_FUND" not in caplog.text
        assert tasty_instance.unverified_asset_symbols_by_year == {
            2020: {"UNKNOWN_FUND"}
        }
    
    def test_no_warnings_for_empty_trades(self, tasty_instance, caplog):
        empty_trades = []
        
        with caplog.at_level(logging.WARNING):
            tasty_instance._checkAssetClassifications(empty_trades)
        
        assert len(caplog.records) == 0
    
    def test_no_warnings_for_option_trades(self, tasty_instance, caplog):
        option_trades = [
            TradeResult(
                symbol='UNKNOWN_OPTION',
                position_type=PositionType.call,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=50.0,
                profit_eur=50.0,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
            )
        ]
        
        with caplog.at_level(logging.WARNING):
            tasty_instance._checkAssetClassifications(option_trades)
        
        assert len(caplog.records) == 0


def test_bundled_unverified_symbols_fall_back_to_stock_totals_and_warn(caplog):
    symbols = {"AOR", "AOA", "BTC", "ETH", "DOGE"}
    rows = []
    for index, symbol in enumerate(sorted(symbols), 1):
        rows.extend([
            row(f"2025-01-27T10:{index:02d}:00+00:00", "Trade", "Buy to Open",
                action="BUY_TO_OPEN", symbol=symbol, instrument="Equity",
                value="-100", quantity="1", price="100", root=symbol,
                underlying=symbol, order=str(index * 2 - 1)),
            row(f"2025-01-28T10:{index:02d}:00+00:00", "Trade", "Sell to Close",
                action="SELL_TO_CLOSE", symbol=symbol, instrument="Equity",
                value="200", quantity="1", price="200", root=symbol,
                underlying=symbol, order=str(index * 2)),
        ])
    tasty = Tasty()
    tasty.history = history(*rows)

    with caplog.at_level(logging.WARNING):
        result = tasty.run()

    assert tasty.unverified_asset_symbols_by_year == {2025: symbols}
    assert result[2025].stockProfits.usd == 500
    assert result[2025].fundProfits.usd == 0
    warnings = [
        record.getMessage()
        for record in caplog.records
        if record.getMessage() == "Asset classification requires manual review"
    ]
    assert len(warnings) == 5
    assert all(symbol not in warning for symbol in symbols for warning in warnings)


def test_unverified_symbols_are_recorded_by_closing_year_and_effective_period(tmp_path):
    registry = tmp_path / "assets.csv"
    registry.write_text(
        "symbol,classification,tax_category,teilfreistellung_pct,verified,effective_from,effective_to,evidence\n"
        "TEST,EQUITY_ETF,KAP-INV,30,true,2020-01-01,2020-12-31,Prospectus\n",
        encoding="utf-8",
    )
    tasty = Tasty()
    tasty.classifier = AssetClassifier(registry)
    trades = [
        TradeResult(
            symbol="TEST", position_type=PositionType.stock,
            opening_date="2019-12-01", closing_date=closing_date, quantity=1,
            profit_usd=100, profit_eur=100, fees_usd=0, fees_eur=0,
            worthless_expiry=False,
        )
        for closing_date in ("2020-06-01", "2021-06-01")
    ]

    tasty._checkAssetClassifications(trades)

    assert tasty.unverified_asset_symbols_by_year == {2021: {"TEST"}}
    assert tasty.classifier.is_verified("TEST", PositionType.stock, date(2020, 6, 1))
    assert not tasty.classifier.is_verified("TEST", PositionType.stock, date(2021, 6, 1))


def test_run_resets_unverified_symbols_from_previous_run():
    tasty = Tasty()
    tasty.history = history(
        row("2020-01-02T10:00:00+00:00", "Trade", "Buy to Open",
            action="BUY_TO_OPEN", symbol="UNKNOWN", instrument="Equity",
            value="-100", quantity="1", price="100", root="UNKNOWN",
            underlying="UNKNOWN", order="1"),
        row("2020-02-03T10:00:00+00:00", "Trade", "Sell to Close",
            action="SELL_TO_CLOSE", symbol="UNKNOWN", instrument="Equity",
            value="200", quantity="1", price="200", root="UNKNOWN",
            underlying="UNKNOWN", order="2"),
    )
    tasty.run()
    assert tasty.unverified_asset_symbols_by_year == {2020: {"UNKNOWN"}}

    tasty.history = History()
    tasty.run()

    assert tasty.unverified_asset_symbols_by_year == {}
    assert tasty.yearValues == {}
    assert tasty.position_manager.closed_trades == []


def test_dividend_only_exposure_uses_payment_year_and_effective_date(tmp_path):
    registry = tmp_path / "assets.csv"
    registry.write_text(
        "symbol,classification,tax_category,teilfreistellung_pct,verified,effective_from,effective_to,evidence\n"
        "FUND,EQUITY_ETF,KAP-INV,30,true,2020-01-01,2020-12-31,Prospectus\n",
        encoding="utf-8",
    )
    tasty = Tasty()
    tasty.classifier = AssetClassifier(registry)

    for year in (2020, 2021):
        tasty.moneyMovement(Transaction.fromString(
            f"{year}-06-15T12:00:00+0000,Money Movement,Dividend,,FUND,Equity,"
            "Fund distribution,100,0,,0,0.00,,FUND,FUND,,,,123456,USD"
        ))

    assert tasty.unverified_asset_symbols_by_year == {2021: {"FUND"}}


def test_open_position_only_exposure_creates_year_scoped_readiness():
    tasty = Tasty()
    tasty.history = history(row(
        "2021-07-01T10:00:00+00:00", "Trade", "Buy to Open",
        action="BUY_TO_OPEN", symbol="UNKNOWN_FUND", instrument="Equity",
        value="-1000", quantity="10", price="100", root="UNKNOWN_FUND",
        underlying="UNKNOWN_FUND", order="1",
    ))

    result = tasty.run()

    assert list(result) == [2021]
    assert tasty.unverified_asset_symbols_by_year == {2021: {"UNKNOWN_FUND"}}


def test_holding_readiness_is_limited_to_acquisition_through_disposal():
    tasty = Tasty()
    tasty.history = history(
        row("2021-06-01T10:00:00+00:00", "Trade", "Buy to Open",
            action="BUY_TO_OPEN", symbol="UNKNOWN_FUND", instrument="Equity",
            value="-100", quantity="1", price="100", root="UNKNOWN_FUND",
            underlying="UNKNOWN_FUND", order="1"),
        row("2022-03-01T10:00:00+00:00", "Trade", "Sell to Close",
            action="SELL_TO_CLOSE", symbol="UNKNOWN_FUND", instrument="Equity",
            value="110", quantity="1", price="110", root="UNKNOWN_FUND",
            underlying="UNKNOWN_FUND", order="2"),
    )

    tasty.run()

    assert tasty.unverified_asset_symbols_by_year == {
        2021: {"UNKNOWN_FUND"},
        2022: {"UNKNOWN_FUND"},
    }
    assert set(tasty.yearValues) == {2021, 2022}


@pytest.mark.parametrize(
    ("middle_registry_row", "warning_text"),
    [
        ("", "Unknown fund/stock type"),
        (
            "TEST,EQUITY_ETF,KAP-INV,30,false,2021-04-01,2021-09-30,Pending verification\n",
            "UNVERIFIED ASSET CLASSIFICATION",
        ),
    ],
    ids=["mid_year_gap", "mid_year_unverified"],
)
def test_holding_readiness_checks_mid_year_registry_states_once_per_year(
    tmp_path, caplog, middle_registry_row, warning_text
):
    registry = tmp_path / "assets.csv"
    registry.write_text(
        "symbol,classification,tax_category,teilfreistellung_pct,verified,effective_from,effective_to,evidence\n"
        "TEST,EQUITY_ETF,KAP-INV,30,true,2021-01-01,2021-03-31,Prospectus\n"
        f"{middle_registry_row}"
        "TEST,EQUITY_ETF,KAP-INV,30,true,2021-10-01,2021-12-31,Prospectus\n",
        encoding="utf-8",
    )
    tasty = Tasty()
    tasty.classifier = AssetClassifier(registry)
    tasty.history = history(
        row("2021-01-04T10:00:00+00:00", "Trade", "Buy to Open",
            action="BUY_TO_OPEN", symbol="TEST", instrument="Equity",
            value="-100", quantity="1", price="100", root="TEST",
            underlying="TEST", order="1"),
        row("2021-12-30T10:00:00+00:00", "Trade", "Sell to Close",
            action="SELL_TO_CLOSE", symbol="TEST", instrument="Equity",
            value="110", quantity="1", price="110", root="TEST",
            underlying="TEST", order="2"),
    )

    with caplog.at_level(logging.WARNING):
        tasty.run()

    assert tasty.unverified_asset_symbols_by_year == {2021: {"TEST"}}
    relevant_warnings = [
        record for record in caplog.records
        if record.levelno == logging.WARNING
        and record.getMessage() == "Asset classification requires manual review"
    ]
    assert len(relevant_warnings) == 1
    assert "TEST" not in relevant_warnings[0].getMessage()
