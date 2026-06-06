import pytest
import pandas as pd
import pathlib
from pathlib import Path
from unittest.mock import patch, MagicMock
import pprint

from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.money import Money
from tastyworksTaxes.values import Values
from tastyworksTaxes.fifo_processor import TradeResult
from tastyworksTaxes.position import PositionType

# Skip tests that require the full dataset if it's not available (CI environment)
FULL_DATASET = Path("test/transactions_2018_to_2025.csv")


class TestTastyRun:
    def test_tasty_run_with_merged_data(self):
        t = Tasty()
        t.processTransactionHistory = MagicMock()

        sample_trades = [
            TradeResult(
                symbol="LFIN",
                position_type=PositionType.call,
                opening_date="2018-03-12 17:08:00",
                closing_date="2018-03-19 22:00:00",
                quantity=-2,
                profit_usd=1420.0,
                profit_eur=1154.28,
                fees_usd=2.324,
                fees_eur=1.89,
                worthless_expiry=False,
                strike=30.0,
                expiry="2018-06-15",
            ),
            TradeResult(
                symbol="LFIN",
                position_type=PositionType.stock,
                opening_date="2018-03-19 22:00:00",
                closing_date="2018-03-21 18:42:00",
                quantity=-100,
                profit_usd=-2676.0,
                profit_eur=-2182.65,
                fees_usd=2.662,
                fees_eur=2.16,
                worthless_expiry=False,
            ),
        ]
        t.position_manager.closed_trades = sample_trades

        result = t.run()

        t.processTransactionHistory.assert_called_once()
        assert isinstance(result, dict)
        assert 2018 in result

        year_keys = list(result.keys())
        assert all(isinstance(key, int) for key in year_keys)

        year_data = result[2018]
        assert isinstance(year_data, Values)
        assert isinstance(year_data.stockAndOptionsSum, Money)
        assert isinstance(year_data.optionSum, Money)
        assert isinstance(year_data.longOptionProfits, Money)
        assert isinstance(year_data.longOptionLosses, Money)

    def test_run_includes_trade_only_year_without_money_movements(self):
        t = Tasty()
        t.processTransactionHistory = MagicMock()
        t.position_manager.closed_trades = [
            TradeResult(
                symbol="XYZ",
                position_type=PositionType.stock,
                opening_date="2022-01-03 10:00:00",
                closing_date="2022-02-04 10:00:00",
                quantity=1,
                profit_usd=10.0,
                profit_eur=9.0,
                fees_usd=1.0,
                fees_eur=0.9,
                worthless_expiry=False,
            )
        ]

        result = t.run()

        assert set(result.keys()) == {2022}
        assert isinstance(result[2022], Values)
        assert result[2022].stockAndOptionsSum.eur == 9.0
        assert result[2022].fee.eur == -0.9

    @pytest.mark.skipif(
        not FULL_DATASET.exists(), reason="Full dataset not available (CI environment)"
    )
    def test_run_with_real_csv_data(self):
        t = Tasty(FULL_DATASET)

        result = t.run()

        assert len(result) > 0
        assert any(
            hasattr(year_value, "equityEtfProfits") for year_value in result.values()
        )

        for year, value in result.items():
            assert isinstance(year, int)
            assert isinstance(value.stockAndOptionsSum, Money)
            assert isinstance(value.equityEtfProfits, Money)
            assert isinstance(value.otherStockAndBondProfits, Money)
            assert isinstance(value.stockAndEtfLosses, Money)
            assert isinstance(value.optionSum, Money)
