import pytest
import pandas as pd
from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.money import Money

class TestArchitectureIntegration:
    @pytest.fixture
    def tasty_instance(self):
        return Tasty()
    
    def test_equity_etf_profits_with_new_architecture(self, tasty_instance):
        trades = pd.DataFrame([
            {
                'Symbol': 'SCHG',
                'callPutStock': PositionType.stock,
                'AmountEuro': 100.0,
                'Amount': 120.0
            },
            {
                'Symbol': 'TECL',
                'callPutStock': PositionType.stock,
                'AmountEuro': 200.0,
                'Amount': 240.0
            },
            {
                'Symbol': 'AAPL',
                'callPutStock': PositionType.stock,
                'AmountEuro': 50.0,
                'Amount': 60.0
            }
        ])
        
        result = tasty_instance.getEquityEtfProfits(trades)
        
        expected_eur = (100.0 + 200.0) * 0.70
        expected_usd = (120.0 + 240.0) * 0.70
        
        assert abs(result.eur - expected_eur) < 0.01
        assert abs(result.usd - expected_usd) < 0.01
    
    def test_other_stock_and_bond_profits_excludes_equity_etfs(self, tasty_instance):
        trades = pd.DataFrame([
            {
                'Symbol': 'SCHG',
                'callPutStock': PositionType.stock,
                'AmountEuro': 100.0,
                'Amount': 120.0
            },
            {
                'Symbol': 'AAPL',
                'callPutStock': PositionType.stock,
                'AmountEuro': 50.0,
                'Amount': 60.0
            },
            {
                'Symbol': 'PULS',
                'callPutStock': PositionType.stock,
                'AmountEuro': 75.0,
                'Amount': 90.0
            }
        ])
        
        result = tasty_instance.getOtherStockAndBondProfits(trades)
        
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
        trades = pd.DataFrame([
            {
                'Symbol': 'AOM',
                'callPutStock': PositionType.stock,
                'AmountEuro': 100.0,
                'Amount': 120.0
            },
            {
                'Symbol': 'VNQ',
                'callPutStock': PositionType.stock,
                'AmountEuro': 200.0,
                'Amount': 240.0
            }
        ])
        
        aom_classification = tasty_instance.classifier.classify('AOM', PositionType.stock)
        vnq_classification = tasty_instance.classifier.classify('VNQ', PositionType.stock)
        
        assert aom_classification == 'MIXED_FUND_ETF'
        assert vnq_classification == 'REAL_ESTATE_ETF'
        
        assert tasty_instance.classifier.get_exemption_percentage(aom_classification) == 15
        assert tasty_instance.classifier.get_exemption_percentage(vnq_classification) == 60