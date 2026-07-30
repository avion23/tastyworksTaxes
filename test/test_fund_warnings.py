import pytest
import logging
from datetime import date, datetime
from unittest.mock import patch

from tastyworksTaxes.asset_classifier import AssetClassifier
from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.position_lot import PositionLot
from tastyworksTaxes.transaction import Transaction
from tastyworksTaxes.fifo_processor import TradeResult

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
        
        assert "Unknown fund/stock type" in caplog.text
        assert "UNKNOWN_FUND" in caplog.text
    
    def test_warnings_called_via_check_asset_classifications(self, tasty_instance):
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
        
        with patch.object(tasty_instance.classifier, 'check_unsupported_assets') as mock_check:
            tasty_instance._checkAssetClassifications(trades)
            mock_check.assert_called_once()
    
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
    tasty.processTransactionHistory = lambda: None
    tasty.position_manager.closed_trades = [
        TradeResult(
            symbol="UNKNOWN", position_type=PositionType.stock,
            opening_date="2020-01-01 00:00:00",
            closing_date="2020-02-01 00:00:00", quantity=1,
            profit_usd=100, profit_eur=100, fees_usd=0, fees_eur=0,
            worthless_expiry=False,
        )
    ]
    tasty.run()
    assert tasty.unverified_asset_symbols_by_year == {2020: {"UNKNOWN"}}

    tasty.position_manager.closed_trades = []
    tasty.run()

    assert tasty.unverified_asset_symbols_by_year == {}


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
    tasty.processTransactionHistory = lambda: None
    lot = PositionLot(
        symbol="UNKNOWN_FUND",
        position_type=PositionType.stock,
        quantity=10,
        amount_usd=-1000,
        amount_eur=-900,
        fees_usd=1,
        fees_eur=0.9,
        date=datetime(2021, 7, 1),
    )
    tasty.position_manager.add_lot_directly(lot)

    result = tasty.run()

    assert list(result) == [2021]
    assert tasty.unverified_asset_symbols_by_year == {2021: {"UNKNOWN_FUND"}}


def test_holding_readiness_is_limited_to_acquisition_through_disposal():
    tasty = Tasty()
    tasty.processTransactionHistory = lambda: None
    tasty.position_manager.closed_trades = [
        TradeResult(
            symbol="UNKNOWN_FUND",
            position_type=PositionType.stock,
            opening_date="2021-06-01 00:00:00",
            closing_date="2022-03-01 00:00:00",
            quantity=1,
            profit_usd=10,
            profit_eur=9,
            fees_usd=0,
            fees_eur=0,
            worthless_expiry=False,
        )
    ]
    tasty.year(2020)
    tasty.year(2023)

    tasty.run()

    assert tasty.unverified_asset_symbols_by_year == {
        2021: {"UNKNOWN_FUND"},
        2022: {"UNKNOWN_FUND"},
    }
