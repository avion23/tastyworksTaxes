import pytest
from pathlib import Path
from unittest.mock import MagicMock

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
        assert isinstance(year_data.stockProfits, Money)
        assert isinstance(year_data.stockLosses, Money)
        assert isinstance(year_data.fundProfits, Money)
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
        assert result[2022].stockProfits.eur == 8.1
        assert result[2022].fee.eur == -0.9

    @pytest.mark.skipif(
        not FULL_DATASET.exists(), reason="Full dataset not available (CI environment)"
    )
    def test_run_with_real_csv_data(self):
        t = Tasty(FULL_DATASET)

        result = t.run()

        assert len(result) > 0
        assert any(
            hasattr(year_value, "fundProfits") for year_value in result.values()
        )

        for year, value in result.items():
            assert isinstance(year, int)
            assert isinstance(value.stockProfits, Money)
            assert isinstance(value.stockLosses, Money)
            assert isinstance(value.fundGrossProfits, Money)
            assert isinstance(value.fundProfits, Money)
            assert isinstance(value.fundLosses, Money)
            assert isinstance(value.optionSum, Money)

    @pytest.mark.skipif(
        not FULL_DATASET.exists(), reason="Full dataset not available (CI environment)"
    )
    def test_short_options_grouped_by_opening_year(self):
        from datetime import datetime
        from tastyworksTaxes.position import PositionType

        t = Tasty(FULL_DATASET)
        t.processTransactionHistory()
        trades_by_year = t.getYearlyTrades()

        for trade in t.position_manager.closed_trades:
            is_short_option = (
                trade.quantity < 0
                and trade.position_type in (PositionType.call, PositionType.put)
            )
            if not is_short_option:
                continue
            open_year = datetime.strptime(trade.opening_date, "%Y-%m-%d %H:%M:%S").year
            close_year = datetime.strptime(trade.closing_date, "%Y-%m-%d %H:%M:%S").year
            if open_year == close_year:
                continue
            open_year_trades = trades_by_year[open_year]
            close_year_trades = trades_by_year[close_year]
            opening_legs = [t for t in open_year_trades if t.symbol == trade.symbol and t.closing_date == trade.opening_date]
            closing_legs = [t for t in close_year_trades if t.symbol == trade.symbol and t.opening_date == trade.closing_date]
            assert len(opening_legs) >= 1, f"Expected opening leg(s) for {trade.symbol} in {open_year}"
            assert len(closing_legs) >= 1, f"Expected closing leg(s) for {trade.symbol} in {close_year}"
            assert opening_legs[0].profit_usd == pytest.approx(trade.opening_profit_usd)
            assert closing_legs[0].profit_usd == pytest.approx(trade.closing_profit_usd)
