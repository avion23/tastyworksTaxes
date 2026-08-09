from unittest.mock import MagicMock

import pandas as pd

from tastyworksTaxes.asset_classifier import AssetClassifier
from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.history import History
from tastyworksTaxes.money import Money
from tastyworksTaxes.values import Values
from tastyworksTaxes.fifo_processor import TradeResult
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.printer import Printer
from tastyworksTaxes.transaction import Transaction
from test.test_pipeline_safety_scenarios import history, row


class TestTastyRun:
    def test_run_includes_trade_only_year_without_money_movements(self):
        t = Tasty()
        t.history = history(
            row(
                "2022-01-03T10:00:00+00:00", "Trade", "Buy to Open",
                action="BUY_TO_OPEN", symbol="XYZ", instrument="Equity",
                value="-100", quantity="1", price="100", root="XYZ",
                underlying="XYZ", order="1",
            ),
            row(
                "2022-02-04T10:00:00+00:00", "Trade", "Sell to Close",
                action="SELL_TO_CLOSE", symbol="XYZ", instrument="Equity",
                value="110", quantity="1", price="110", root="XYZ",
                underlying="XYZ", order="2",
            ),
        )

        result = t.run()

        assert set(result) == {2022}
        assert isinstance(result[2022], Values)
        assert result[2022].stockProfits.usd == 10

    def test_run_collects_only_closed_short_stocks_by_year_and_resets(self):
        t = Tasty()
        t.history = history(
            row("2020-01-02T10:00:00+00:00", "Trade", "Sell to Open",
                action="SELL_TO_OPEN", symbol="SHORT20", instrument="Equity",
                value="100", quantity="1", price="100", root="SHORT20",
                underlying="SHORT20", order="1"),
            row("2020-02-03T10:00:00+00:00", "Trade", "Buy to Close",
                action="BUY_TO_CLOSE", symbol="SHORT20", instrument="Equity",
                value="-90", quantity="1", price="90", root="SHORT20",
                underlying="SHORT20", order="2"),
            row("2021-01-04T10:00:00+00:00", "Trade", "Sell to Open",
                action="SELL_TO_OPEN", symbol="SHORT21", instrument="Equity",
                value="100", quantity="1", price="100", root="SHORT21",
                underlying="SHORT21", order="3"),
            row("2021-02-01T10:00:00+00:00", "Trade", "Buy to Close",
                action="BUY_TO_CLOSE", symbol="SHORT21", instrument="Equity",
                value="-90", quantity="1", price="90", root="SHORT21",
                underlying="SHORT21", order="4"),
            row("2021-03-01T10:00:00+00:00", "Trade", "Buy to Open",
                action="BUY_TO_OPEN", symbol="LONG", instrument="Equity",
                value="-100", quantity="1", price="100", root="LONG",
                underlying="LONG", order="5"),
            row("2021-04-01T10:00:00+00:00", "Trade", "Sell to Close",
                action="SELL_TO_CLOSE", symbol="LONG", instrument="Equity",
                value="110", quantity="1", price="110", root="LONG",
                underlying="LONG", order="6"),
        )

        t.run()

        assert {
            year: [trade.symbol for trade in trades]
            for year, trades in t.short_stock_trades_by_year.items()
        } == {2020: ["SHORT20"], 2021: ["SHORT21"]}

        t.history = History()
        t.run()
        assert t.short_stock_trades_by_year == {}

    def test_short_option_is_split_between_opening_and_closing_years(self):
        from tastyworksTaxes.transaction import Transaction

        tasty = Tasty()
        tasty.position_manager.add_position(
            Transaction.fromString(
                "2022-12-30T15:00:00+0000,Trade,Sell to Open,SELL_TO_OPEN,"
                "ANON  230120P00010000,Equity Option,Synthetic open,100,1,100,"
                "0,0,100,ANON,ANON,01/20/23,10,PUT,1,USD"
            )
        )
        tasty.position_manager.add_position(
            Transaction.fromString(
                "2023-01-03T15:00:00+0000,Trade,Buy to Close,BUY_TO_CLOSE,"
                "ANON  230120P00010000,Equity Option,Synthetic close,-40,1,40,"
                "0,0,100,ANON,ANON,01/20/23,10,PUT,2,USD"
            )
        )

        trades_by_year = tasty.getYearlyTrades()

        assert set(trades_by_year) == {2022, 2023}
        opening_leg = trades_by_year[2022]
        closing_leg = trades_by_year[2023]
        assert len(opening_leg) == 1
        assert len(closing_leg) == 1
        assert opening_leg[0].symbol == "ANON"
        assert opening_leg[0].opening_date == opening_leg[0].closing_date
        assert opening_leg[0].profit_usd == 100
        assert closing_leg[0].symbol == "ANON"
        assert closing_leg[0].opening_date == closing_leg[0].closing_date
        assert closing_leg[0].profit_usd == -40
        assert opening_leg[0].profit_usd + closing_leg[0].profit_usd == 60


    def test_fund_holding_years_require_manual_review_and_include_gross_losses(self):
        t = Tasty()
        t.history = history(
            row("2024-06-03T10:00:00+00:00", "Trade", "Buy to Open",
                action="BUY_TO_OPEN", symbol="QQQ", instrument="Equity",
                value="-100", quantity="1", price="100", root="QQQ",
                underlying="QQQ", order="1"),
            row("2025-02-03T10:00:00+00:00", "Trade", "Sell to Close",
                action="SELL_TO_CLOSE", symbol="QQQ", instrument="Equity",
                value="200", quantity="1", price="200", root="QQQ",
                underlying="QQQ", order="2"),
            row("2025-03-03T10:00:00+00:00", "Trade", "Buy to Open",
                action="BUY_TO_OPEN", symbol="QQQ", instrument="Equity",
                value="-100", quantity="1", price="100", root="QQQ",
                underlying="QQQ", order="3"),
            row("2025-04-01T10:00:00+00:00", "Trade", "Sell to Close",
                action="SELL_TO_CLOSE", symbol="QQQ", instrument="Equity",
                value="50", quantity="1", price="50", root="QQQ",
                underlying="QQQ", order="4"),
        )

        result = t.run()

        assert result[2024].fundTaxReviewRequired is True
        assert result[2024].fundGrossProfits.usd == 0
        assert result[2024].fundGrossLosses.usd == 0
        rendered_2024 = str(
            Printer(result[2024], [], assessment_year=2024).generateGermanTaxReport()
        )
        assert "KAP-INV NOT FILING-READY" in rendered_2024
        assert "Vorabpauschale" in rendered_2024
        assert result[2025].fundTaxReviewRequired is True
        assert result[2025].fundGrossProfits.usd == 100
        assert result[2025].fundGrossLosses.usd == -50
        assert result[2025].fundProfits.usd == 70
        assert result[2025].fundLosses.usd == -35


    def test_negative_only_verified_fund_dividend_marks_pipeline_not_ready(
        self, tmp_path
    ):
        registry = tmp_path / "assets.csv"
        registry.write_text(
            "symbol,classification,tax_category,teilfreistellung_pct,verified,"
            "effective_from,effective_to,evidence\n"
            "ANONFUND,EQUITY_ETF,KAP-INV,30,true,2020-01-01,,Official factsheet\n",
            encoding="utf-8",
        )
        t = Tasty()
        t.classifier = AssetClassifier(registry)
        t.history = history(row(
            "2025-06-02T12:00:00+00:00", "Money Movement", "Dividend",
            symbol="ANONFUND", description="fund distribution adjustment",
            value="-10", order="1",
        ))

        result = t.run()
        values = result[2025]
        rendered = str(
            Printer(values, [], assessment_year=2025).generateGermanTaxReport()
        )

        assert values.fundTaxReviewRequired is True
        assert values.fundDistributions.usd == 0
        assert values.fundDistributionTaxable.usd == 0
        assert values.paidDividend.usd == -10
        assert t.ambiguous_withholding_years == set()
        assert "KAP-INV NOT FILING-READY" in rendered
        assert "Vorabpauschale" in rendered
