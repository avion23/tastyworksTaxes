import pytest
import pandas as pd
from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.money import Money
from tastyworksTaxes.fifo_processor import TradeResult
from tastyworksTaxes.trade_calculator import (
    calculate_gross_equity_etf_profits, calculate_equity_etf_profits,
    calculate_other_stock_and_bond_profits
)

class TestArchitectureIntegration:
    @pytest.fixture
    def tasty_instance(self):
        return Tasty()
    
    def test_equity_etf_profits_with_new_architecture(self, tasty_instance):
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
            )
        ]
        
        result = calculate_equity_etf_profits(trades, tasty_instance.classifier)
        
        expected_eur = (100.0 + 200.0) * 0.70
        expected_usd = (120.0 + 240.0) * 0.70
        
        assert abs(result.eur - expected_eur) < 0.01
        assert abs(result.usd - expected_usd) < 0.01
    
    def test_gross_equity_etf_profits_calculation(self, tasty_instance):
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
            )
        ]
        
        gross_result = calculate_gross_equity_etf_profits(trades, tasty_instance.classifier)
        taxable_result = calculate_equity_etf_profits(trades, tasty_instance.classifier)
        
        expected_gross_eur = 100.0 + 200.0
        expected_gross_usd = 120.0 + 240.0
        
        assert abs(gross_result.eur - expected_gross_eur) < 0.01
        assert abs(gross_result.usd - expected_gross_usd) < 0.01
        
        assert abs(taxable_result.eur - (expected_gross_eur * 0.70)) < 0.01
        assert abs(taxable_result.usd - (expected_gross_usd * 0.70)) < 0.01
    
    def test_other_stock_and_bond_profits_excludes_equity_etfs(self, tasty_instance):
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
        
        result = calculate_other_stock_and_bond_profits(trades, tasty_instance.classifier)
        
        expected_eur = 50.0 + 75.0
        expected_usd = 60.0 + 90.0
        
        assert abs(result.eur - expected_eur) < 0.01
        assert abs(result.usd - expected_usd) < 0.01
    
    def test_classifier_integration_with_tasty(self, tasty_instance):
        assert tasty_instance.classifier is not None
        
        assert tasty_instance.classifier.classify('SCHG', PositionType.stock) == 'EQUITY_ETF'
        assert tasty_instance.classifier.classify('PULS', PositionType.stock) == 'BOND_ETF'
        assert tasty_instance.classifier.classify('AAPL', PositionType.stock) == 'INDIVIDUAL_STOCK'
        
        assert tasty_instance.classifier.get_exemption_percentage('EQUITY_ETF') == 30
        assert tasty_instance.classifier.get_exemption_percentage('MIXED_FUND_ETF') == 15
        assert tasty_instance.classifier.get_exemption_percentage('REAL_ESTATE_ETF') == 60
    
    def test_mixed_and_real_estate_funds_work_with_classification(self, tasty_instance):
        trades = [
            TradeResult(
                symbol='AOM',
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
                symbol='VNQ',
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
        
        aom_classification = tasty_instance.classifier.classify('AOM', PositionType.stock)
        vnq_classification = tasty_instance.classifier.classify('VNQ', PositionType.stock)
        
        assert aom_classification == 'MIXED_FUND_ETF'
        assert vnq_classification == 'REAL_ESTATE_ETF'
        
        assert tasty_instance.classifier.get_exemption_percentage(aom_classification) == 15
        assert tasty_instance.classifier.get_exemption_percentage(vnq_classification) == 60