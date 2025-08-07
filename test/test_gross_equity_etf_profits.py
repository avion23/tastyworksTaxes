import pytest
import pandas as pd
from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.money import Money
from tastyworksTaxes.fifo_processor import TradeResult
from tastyworksTaxes.trade_calculator import (
    calculate_gross_equity_etf_profits, calculate_equity_etf_profits
)

class TestGrossEquityEtfProfits:
    @pytest.fixture
    def tasty_instance(self):
        return Tasty()
    
    def test_gross_equity_etf_profits_basic(self, tasty_instance):
        trades = [
            TradeResult(
                symbol='SCHG',
                position_type=PositionType.stock,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=120.0,
                profit_eur=100.0,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            ),
            TradeResult(
                symbol='TECL',
                position_type=PositionType.stock,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=240.0,
                profit_eur=200.0,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            )
        ]
        
        result = calculate_gross_equity_etf_profits(trades, tasty_instance.classifier)
        
        assert abs(result.eur - 300.0) < 0.01
        assert abs(result.usd - 360.0) < 0.01
    
    def test_gross_equity_etf_profits_excludes_non_equity_etfs(self, tasty_instance):
        trades = [
            TradeResult(
                symbol='SCHG',
                position_type=PositionType.stock,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=120.0,
                profit_eur=100.0,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            ),
            TradeResult(
                symbol='AAPL',
                position_type=PositionType.stock,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=60.0,
                profit_eur=50.0,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            ),
            TradeResult(
                symbol='PULS',
                position_type=PositionType.stock,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=90.0,
                profit_eur=75.0,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            )
        ]
        
        result = calculate_gross_equity_etf_profits(trades, tasty_instance.classifier)
        
        assert abs(result.eur - 100.0) < 0.01
        assert abs(result.usd - 120.0) < 0.01
    
    def test_gross_equity_etf_profits_excludes_losses(self, tasty_instance):
        trades = [
            TradeResult(
                symbol='SCHG',
                position_type=PositionType.stock,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=120.0,
                profit_eur=100.0,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            ),
            TradeResult(
                symbol='TECL',
                position_type=PositionType.stock,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=-60.0,
                profit_eur=-50.0,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            )
        ]
        
        result = calculate_gross_equity_etf_profits(trades, tasty_instance.classifier)
        
        assert abs(result.eur - 100.0) < 0.01
        assert abs(result.usd - 120.0) < 0.01
    
    def test_gross_equity_etf_profits_excludes_options(self, tasty_instance):
        trades = [
            TradeResult(
                symbol='SCHG',
                position_type=PositionType.stock,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=120.0,
                profit_eur=100.0,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            ),
            TradeResult(
                symbol='SCHG',
                position_type=PositionType.call,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=60.0,
                profit_eur=50.0,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            )
        ]
        
        result = calculate_gross_equity_etf_profits(trades, tasty_instance.classifier)
        
        assert abs(result.eur - 100.0) < 0.01
        assert abs(result.usd - 120.0) < 0.01
    
    def test_gross_equity_etf_profits_empty_trades(self, tasty_instance):
        trades = []
        
        result = calculate_gross_equity_etf_profits(trades, tasty_instance.classifier)
        
        assert result.eur == 0.0
        assert result.usd == 0.0
    
    def test_gross_vs_taxable_equity_etf_profits_relationship(self, tasty_instance):
        trades = [
            TradeResult(
                symbol='SCHG',
                position_type=PositionType.stock,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=120.0,
                profit_eur=100.0,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            ),
            TradeResult(
                symbol='TECL',
                position_type=PositionType.stock,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=240.0,
                profit_eur=200.0,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            )
        ]
        
        gross_result = calculate_gross_equity_etf_profits(trades, tasty_instance.classifier)
        taxable_result = calculate_equity_etf_profits(trades, tasty_instance.classifier)
        
        expected_taxable_eur = gross_result.eur * 0.70
        expected_taxable_usd = gross_result.usd * 0.70
        
        assert abs(taxable_result.eur - expected_taxable_eur) < 0.01
        assert abs(taxable_result.usd - expected_taxable_usd) < 0.01