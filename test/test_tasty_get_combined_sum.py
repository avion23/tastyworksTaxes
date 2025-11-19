import pytest
import pandas as pd

from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.money import Money
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.fifo_processor import TradeResult
from tastyworksTaxes.trade_calculator import (
    calculate_combined_sum, calculate_option_sum, calculate_long_option_profits,
    calculate_long_option_losses, calculate_long_option_total_losses,
    calculate_short_option_profits, calculate_short_option_losses,
    calculate_option_differential, calculate_stock_loss, calculate_stock_fees,
    calculate_other_fees, calculate_fees_sum, calculate_gross_equity_etf_profits,
    calculate_equity_etf_profits, calculate_other_stock_and_bond_profits
)

class TestTastyFinancialCalculations:
    @pytest.fixture
    def sample_trades(self):
        return [
            TradeResult(
                symbol='LFIN',
                position_type=PositionType.call,
                opening_date='2018-03-12 17:08:00',
                closing_date='2018-03-19 22:00:00',
                quantity=-2,
                profit_usd=1420.0,
                profit_eur=1154.28,
                fees_usd=2.324,
                fees_eur=1.89,
                worthless_expiry=False,
                strike=30.0,
                expiry='2018-06-15'
            ),
            TradeResult(
                symbol='LFIN',
                position_type=PositionType.call,
                opening_date='2018-03-12 17:08:00',
                closing_date='2018-03-21 18:42:00',
                quantity=1,
                profit_usd=1458.0,
                profit_eur=1186.95,
                fees_usd=1.32,
                fees_eur=1.07,
                worthless_expiry=False,
                strike=40.0,
                expiry='2018-06-15'
            ),
            TradeResult(
                symbol='LFIN',
                position_type=PositionType.stock,
                opening_date='2018-03-19 22:00:00',
                closing_date='2018-03-21 18:42:00',
                quantity=-100,
                profit_usd=-2676.0,
                profit_eur=-2182.65,
                fees_usd=2.662,
                fees_eur=2.16,
                worthless_expiry=False,
                strike=None,
                expiry=None
            ),
            TradeResult(
                symbol='LFIN',
                position_type=PositionType.stock,
                opening_date='2018-03-19 22:00:00',
                closing_date='2018-03-21 19:59:00',
                quantity=-100,
                profit_usd=-2720.0,
                profit_eur=-2218.46,
                fees_usd=2.662,
                fees_eur=2.16,
                worthless_expiry=False,
                strike=None,
                expiry=None
            )
        ]

    @pytest.mark.parametrize("method_name,expected_usd,expected_eur", [
        ("calculate_combined_sum", -2518.0, -2059.88),
        ("calculate_option_sum", 2878.0, 2341.23)
    ])
    def test_money_calculations_with_sample_df(self, method_name, expected_usd, expected_eur, sample_trades):
        function_map = {
            "calculate_combined_sum": calculate_combined_sum,
            "calculate_option_sum": calculate_option_sum
        }
        method = function_map[method_name]
        result = method(sample_trades)
        
        assert isinstance(result, Money)
        assert result.usd == expected_usd
        assert round(result.eur, 2) == expected_eur
        
    def test_stock_calculations_with_sample_df(self, sample_trades):
        t = Tasty()
        equity_etf_profits = calculate_equity_etf_profits(sample_trades, t.classifier)
        other_profits = calculate_other_stock_and_bond_profits(sample_trades, t.classifier) 
        losses = calculate_stock_loss(sample_trades)
        
        total_stock = Money(
            usd=equity_etf_profits.usd + other_profits.usd + losses.usd,
            eur=equity_etf_profits.eur + other_profits.eur + losses.eur
        )
        
        assert total_stock.usd == -5401.324
        assert round(total_stock.eur, 2) == -4405.43
        
    def test_getCombinedSum_minimal_data(self):
        trades = [
            TradeResult(
                symbol='TEST',
                position_type=PositionType.stock,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=1458.0,
                profit_eur=1186.95,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            ),
            TradeResult(
                symbol='TEST',
                position_type=PositionType.stock,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=-2676.0,
                profit_eur=-2182.65,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            )
        ]
        
        result = calculate_combined_sum(trades)
        assert result.usd == -1218.0
        assert result.eur == -995.7
        
    def test_getLongOptionsProfits(self):
        trades = [
            TradeResult(
                symbol='TEST',
                position_type=PositionType.call,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=1457.0,
                profit_eur=1186.14,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            ),
            TradeResult(
                symbol='TEST',
                position_type=PositionType.put,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=2,
                profit_usd=1520.0,
                profit_eur=1236.45,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            )
        ]
        
        result = calculate_long_option_profits(trades)
        assert result.usd == 2977.0
        assert round(result.eur, 2) == 2422.59
        
    def test_getLongOptionLosses(self):
        trades = [
            TradeResult(
                symbol='TEST',
                position_type=PositionType.put,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=2,
                profit_usd=-193.0,
                profit_eur=-157.05,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            ),
            TradeResult(
                symbol='TEST',
                position_type=PositionType.call,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=245.0,
                profit_eur=199.35,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            ),
            TradeResult(
                symbol='TEST',
                position_type=PositionType.call,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=2,
                profit_usd=-702.0,
                profit_eur=-571.20,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=True,
                strike=None,
                expiry=None
            )
        ]
        
        result = calculate_long_option_losses(trades)
        assert result.usd == -193.0
        assert round(result.eur, 2) == -157.05
        
    def test_getLongOptionTotalLosses(self):
        trades = [
            TradeResult(
                symbol='TEST',
                position_type=PositionType.put,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=2,
                profit_usd=-193.0,
                profit_eur=-157.05,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            ),
            TradeResult(
                symbol='TEST',
                position_type=PositionType.call,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=2,
                profit_usd=-702.0,
                profit_eur=-571.20,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=True,
                strike=None,
                expiry=None
            )
        ]
        
        result = calculate_long_option_total_losses(trades)
        assert result.usd == -702.0
        assert round(result.eur, 2) == -571.20
        
    def test_getShortOptionProfits(self):
        trades = [
            TradeResult(
                symbol='TEST',
                position_type=PositionType.call,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=-1,
                profit_usd=145.0,
                profit_eur=118.05,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            ),
            TradeResult(
                symbol='TEST',
                position_type=PositionType.put,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=-2,
                profit_usd=-55.0,
                profit_eur=-44.75,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            )
        ]
        
        result = calculate_short_option_profits(trades)
        assert result.usd == 145.0
        assert round(result.eur, 2) == 118.05
        
    def test_getShortOptionLosses(self):
        trades = [
            TradeResult(
                symbol='TEST',
                position_type=PositionType.call,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=-1,
                profit_usd=145.0,
                profit_eur=118.05,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            ),
            TradeResult(
                symbol='TEST',
                position_type=PositionType.put,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=-2,
                profit_usd=-55.0,
                profit_eur=-44.75,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            )
        ]
        
        result = calculate_short_option_losses(trades)
        assert result.usd == -55.0
        assert round(result.eur, 2) == -44.75
        
    def test_getOptionDifferential(self):
        trades = [
            TradeResult(
                symbol='TEST',
                position_type=PositionType.call,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=-1,
                profit_usd=145.0,
                profit_eur=118.05,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            ),
            TradeResult(
                symbol='TEST',
                position_type=PositionType.put,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=2,
                profit_usd=-100.0,
                profit_eur=-81.45,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            )
        ]
        
        result = calculate_option_differential(trades)
        assert result.usd == 100.0
        assert round(result.eur, 2) == 81.45
        
    def test_getStockLoss(self):
        trades = [
            TradeResult(
                symbol='TEST',
                position_type=PositionType.stock,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=350.0,
                profit_eur=284.90,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            ),
            TradeResult(
                symbol='TEST',
                position_type=PositionType.stock,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=-200.0,
                profit_eur=-162.85,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            )
        ]
        
        result = calculate_stock_loss(trades)
        assert result.usd == -200.0
        assert round(result.eur, 2) == -162.85
        
    @pytest.mark.parametrize("fee_method,expected_usd,expected_eur", [
        ("getStockFees", 2.60, 2.12),
        ("getOtherFees", 4.0, 3.25)
    ])
    def test_fee_calculations(self, fee_method, expected_usd, expected_eur):
        trades = [
            TradeResult(
                symbol='TEST',
                position_type=PositionType.stock,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=350.0,
                profit_eur=284.90,
                fees_usd=1.25,
                fees_eur=1.02,
                worthless_expiry=False,
                strike=None,
                expiry=None
            ),
            TradeResult(
                symbol='TEST',
                position_type=PositionType.call,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=145.0,
                profit_eur=118.05,
                fees_usd=2.25,
                fees_eur=1.83,
                worthless_expiry=False,
                strike=None,
                expiry=None
            ),
            TradeResult(
                symbol='TEST',
                position_type=PositionType.stock,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=-200.0,
                profit_eur=-162.85,
                fees_usd=1.35,
                fees_eur=1.10,
                worthless_expiry=False,
                strike=None,
                expiry=None
            ),
            TradeResult(
                symbol='TEST',
                position_type=PositionType.put,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=-100.0,
                profit_eur=-81.45,
                fees_usd=1.75,
                fees_eur=1.42,
                worthless_expiry=False,
                strike=None,
                expiry=None
            )
        ]
        
        function_map = {
            "getStockFees": calculate_stock_fees,
            "getOtherFees": calculate_other_fees
        }
        method = function_map[fee_method]
        result = method(trades)
        assert result.usd == expected_usd
        assert round(result.eur, 2) == expected_eur
        
    def test_stock_profits_calculation(self):
        t = Tasty()
        trades = [
            TradeResult(
                symbol='AAPL',
                position_type=PositionType.stock,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=350.0,
                profit_eur=284.90,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            ),
            TradeResult(
                symbol='MSFT',
                position_type=PositionType.stock,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=-200.0,
                profit_eur=-162.85,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            )
        ]
        
        t = Tasty()
        equity_etf_profits = calculate_equity_etf_profits(trades, t.classifier)
        other_profits = calculate_other_stock_and_bond_profits(trades, t.classifier)
        
        total_profits = Money(
            usd=equity_etf_profits.usd + other_profits.usd,
            eur=equity_etf_profits.eur + other_profits.eur
        )
        
        assert total_profits.usd == 350.0
        assert round(total_profits.eur, 2) == 284.90
        
    def test_getFeesSum(self):
        trades = [
            TradeResult(
                symbol='TEST',
                position_type=PositionType.stock,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=0,
                profit_eur=0,
                fees_usd=1.25,
                fees_eur=1.02,
                worthless_expiry=False,
                strike=None,
                expiry=None
            ),
            TradeResult(
                symbol='TEST',
                position_type=PositionType.stock,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=0,
                profit_eur=0,
                fees_usd=2.25,
                fees_eur=1.83,
                worthless_expiry=False,
                strike=None,
                expiry=None
            ),
            TradeResult(
                symbol='TEST',
                position_type=PositionType.stock,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=0,
                profit_eur=0,
                fees_usd=1.75,
                fees_eur=1.42,
                worthless_expiry=False,
                strike=None,
                expiry=None
            )
        ]
        
        result = calculate_fees_sum(trades)
        assert result.usd == 5.25
        assert round(result.eur, 2) == 4.27