import pytest
import pandas as pd
from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.money import Money

class TestGrossEquityEtfProfits:
    @pytest.fixture
    def tasty_instance(self):
        return Tasty()
    
    def test_gross_equity_etf_profits_basic(self, tasty_instance):
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
            }
        ])
        
        result = tasty_instance.getGrossEquityEtfProfits(trades)
        
        assert abs(result.eur - 300.0) < 0.01
        assert abs(result.usd - 360.0) < 0.01
    
    def test_gross_equity_etf_profits_excludes_non_equity_etfs(self, tasty_instance):
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
        
        result = tasty_instance.getGrossEquityEtfProfits(trades)
        
        assert abs(result.eur - 100.0) < 0.01
        assert abs(result.usd - 120.0) < 0.01
    
    def test_gross_equity_etf_profits_excludes_losses(self, tasty_instance):
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
                'AmountEuro': -50.0,
                'Amount': -60.0
            }
        ])
        
        result = tasty_instance.getGrossEquityEtfProfits(trades)
        
        assert abs(result.eur - 100.0) < 0.01
        assert abs(result.usd - 120.0) < 0.01
    
    def test_gross_equity_etf_profits_excludes_options(self, tasty_instance):
        trades = pd.DataFrame([
            {
                'Symbol': 'SCHG',
                'callPutStock': PositionType.stock,
                'AmountEuro': 100.0,
                'Amount': 120.0
            },
            {
                'Symbol': 'SCHG',
                'callPutStock': PositionType.call,
                'AmountEuro': 50.0,
                'Amount': 60.0
            }
        ])
        
        result = tasty_instance.getGrossEquityEtfProfits(trades)
        
        assert abs(result.eur - 100.0) < 0.01
        assert abs(result.usd - 120.0) < 0.01
    
    def test_gross_equity_etf_profits_empty_trades(self, tasty_instance):
        trades = pd.DataFrame(columns=['Symbol', 'callPutStock', 'AmountEuro', 'Amount'])
        
        result = tasty_instance.getGrossEquityEtfProfits(trades)
        
        assert result.eur == 0.0
        assert result.usd == 0.0
    
    def test_gross_vs_taxable_equity_etf_profits_relationship(self, tasty_instance):
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
            }
        ])
        
        gross_result = tasty_instance.getGrossEquityEtfProfits(trades)
        taxable_result = tasty_instance.getEquityEtfProfits(trades)
        
        expected_taxable_eur = gross_result.eur * 0.70
        expected_taxable_usd = gross_result.usd * 0.70
        
        assert abs(taxable_result.eur - expected_taxable_eur) < 0.01
        assert abs(taxable_result.usd - expected_taxable_usd) < 0.01