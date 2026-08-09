from unittest.mock import MagicMock

from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.money import Money
from tastyworksTaxes.values import Values
from tastyworksTaxes.fifo_processor import TradeResult
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.printer import Printer


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

    def test_run_collects_only_closed_short_stocks_by_year_and_resets(self):
        t = Tasty()
        t.processTransactionHistory = MagicMock()

        def trade(symbol, position_type, quantity, closing_date):
            return TradeResult(
                symbol=symbol,
                position_type=position_type,
                opening_date="2020-01-01 00:00:00",
                closing_date=closing_date,
                quantity=quantity,
                profit_usd=10.0,
                profit_eur=9.0,
                fees_usd=0.0,
                fees_eur=0.0,
                worthless_expiry=False,
            )

        short_stock_2020 = trade(
            "SHORT20", PositionType.stock, -10, "2020-02-01 00:00:00"
        )
        short_stock_2021 = trade(
            "SHORT21", PositionType.stock, -5, "2021-02-01 00:00:00"
        )
        long_stock = trade("LONG", PositionType.stock, 10, "2021-03-01 00:00:00")
        short_option = trade("OPTION", PositionType.call, -1, "2021-04-01 00:00:00")
        t.position_manager.closed_trades = [
            short_stock_2020,
            short_stock_2021,
            long_stock,
            short_option,
        ]

        t.run()

        assert t.short_stock_trades_by_year == {
            2020: [short_stock_2020],
            2021: [short_stock_2021],
        }

        t.position_manager.closed_trades = [long_stock, short_option]
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
        t.processTransactionHistory = MagicMock()
        t.position_manager.closed_trades = [
            TradeResult(
                symbol="QQQ", position_type=PositionType.stock,
                opening_date="2024-06-01 00:00:00",
                closing_date="2025-02-01 00:00:00", quantity=1,
                profit_usd=100, profit_eur=100, fees_usd=0, fees_eur=0,
                worthless_expiry=False,
            ),
            TradeResult(
                symbol="QQQ", position_type=PositionType.stock,
                opening_date="2025-03-01 00:00:00",
                closing_date="2025-04-01 00:00:00", quantity=1,
                profit_usd=-50, profit_eur=-50, fees_usd=0, fees_eur=0,
                worthless_expiry=False,
            ),
        ]

        result = t.run()

        assert result[2024].fundTaxReviewRequired is True
        assert result[2024].fundGrossProfits.eur == 0
        assert result[2024].fundGrossLosses.eur == 0
        rendered_2024 = str(
            Printer(result[2024], [], assessment_year=2024).generateGermanTaxReport()
        )
        assert "KAP-INV NOT FILING-READY" in rendered_2024
        assert "Vorabpauschale" in rendered_2024
        assert result[2025].fundTaxReviewRequired is True
        assert result[2025].fundGrossProfits.eur == 100
        assert result[2025].fundGrossLosses.eur == -50
        assert result[2025].fundProfits.eur == 70
        assert result[2025].fundLosses.eur == -35
