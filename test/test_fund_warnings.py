import pytest
import pandas as pd
import logging
from unittest.mock import patch

from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.position import PositionType

class TestFundWarnings:
    @pytest.fixture
    def tasty_instance(self):
        return Tasty()
    
    @pytest.fixture 
    def sample_stock_trades(self):
        return pd.DataFrame([
            {
                'Symbol': 'UNKNOWN_FUND',
                'callPutStock': PositionType.stock,
                'AmountEuro': 100.0
            },
            {
                'Symbol': 'SCHG', 
                'callPutStock': PositionType.stock,
                'AmountEuro': 200.0
            }
        ])
    
    def test_unknown_fund_warning(self, tasty_instance, sample_stock_trades, caplog):
        with caplog.at_level(logging.WARNING):
            tasty_instance._checkUnknownFundTypes(sample_stock_trades)
        
        assert "Unknown fund/stock type for symbol 'UNKNOWN_FUND'" in caplog.text
        assert "Mischfonds or Immobilienfonds" in caplog.text
    
    def test_no_warning_for_known_funds(self, tasty_instance, caplog):
        known_trades = pd.DataFrame([
            {
                'Symbol': 'SCHG',
                'callPutStock': PositionType.stock,
                'AmountEuro': 200.0
            }
        ])
        
        with caplog.at_level(logging.WARNING):
            tasty_instance._checkUnknownFundTypes(known_trades)
        
        assert len(caplog.records) == 0
    
    def test_immobilienfonds_warning(self, tasty_instance, caplog):
        tasty_instance.IMMOBILIENFONDS_SYMBOLS.add('REIT_FUND')
        
        immobilien_trades = pd.DataFrame([
            {
                'Symbol': 'REIT_FUND',
                'callPutStock': PositionType.stock,
                'AmountEuro': 300.0
            }
        ])
        
        with caplog.at_level(logging.WARNING):
            tasty_instance._checkSpecialFundTypes(immobilien_trades)
        
        assert "Immobilienfonds detected: REIT_FUND" in caplog.text
        assert "60%/80%" in caplog.text
    
    def test_mischfonds_warning(self, tasty_instance, caplog):
        tasty_instance.MISCHFONDS_SYMBOLS.add('MIXED_FUND')
        
        misch_trades = pd.DataFrame([
            {
                'Symbol': 'MIXED_FUND',
                'callPutStock': PositionType.stock,
                'AmountEuro': 150.0
            }
        ])
        
        with caplog.at_level(logging.WARNING):
            tasty_instance._checkSpecialFundTypes(misch_trades)
        
        assert "Mischfonds detected: MIXED_FUND" in caplog.text
        assert "15%" in caplog.text
    
    def test_no_warnings_for_option_trades(self, tasty_instance, caplog):
        option_trades = pd.DataFrame([
            {
                'Symbol': 'UNKNOWN_OPTION',
                'callPutStock': PositionType.call,
                'AmountEuro': 50.0
            }
        ])
        
        with caplog.at_level(logging.WARNING):
            tasty_instance._checkUnknownFundTypes(option_trades)
            tasty_instance._checkSpecialFundTypes(option_trades)
        
        assert len(caplog.records) == 0
    
    def test_warnings_called_in_equity_etf_profits(self, tasty_instance):
        trades = pd.DataFrame([
            {
                'Symbol': 'UNKNOWN_FUND',
                'callPutStock': PositionType.stock,
                'AmountEuro': 100.0,
                'Amount': 120.0
            }
        ])
        
        with patch.object(tasty_instance, '_checkUnknownFundTypes') as mock_unknown:
            with patch.object(tasty_instance, '_checkSpecialFundTypes') as mock_special:
                tasty_instance.getEquityEtfProfits(trades)
                
                mock_unknown.assert_called_once_with(trades)
                mock_special.assert_called_once_with(trades)