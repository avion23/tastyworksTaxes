import pytest
import pandas as pd
import logging
from unittest.mock import patch

from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.position import PositionType

class TestTastyWithAssetClassifier:
    @pytest.fixture
    def tasty_instance(self):
        return Tasty()
    
    def test_asset_classification_warnings_in_equity_etf_profits(self, tasty_instance, caplog):
        trades = pd.DataFrame([
            {
                'Symbol': 'UNKNOWN_FUND',
                'callPutStock': PositionType.stock,
                'AmountEuro': 100.0,
                'Amount': 120.0
            }
        ])
        
        with caplog.at_level(logging.WARNING):
            tasty_instance.getEquityEtfProfits(trades)
        
        assert "Unknown fund/stock type" in caplog.text
        assert "UNKNOWN_FUND" in caplog.text
    
    def test_warnings_called_via_check_asset_classifications(self, tasty_instance):
        trades = pd.DataFrame([
            {
                'Symbol': 'UNKNOWN_FUND',
                'callPutStock': PositionType.stock,
                'AmountEuro': 100.0,
                'Amount': 120.0
            }
        ])
        
        with patch.object(tasty_instance.classifier, 'check_unsupported_assets') as mock_check:
            tasty_instance._checkAssetClassifications(trades)
            mock_check.assert_called_once()
    
    def test_no_warnings_for_empty_trades(self, tasty_instance, caplog):
        empty_trades = pd.DataFrame(columns=['Symbol', 'callPutStock', 'AmountEuro'])
        
        with caplog.at_level(logging.WARNING):
            tasty_instance._checkAssetClassifications(empty_trades)
        
        assert len(caplog.records) == 0
    
    def test_no_warnings_for_option_trades(self, tasty_instance, caplog):
        option_trades = pd.DataFrame([
            {
                'Symbol': 'UNKNOWN_OPTION',
                'callPutStock': PositionType.call,
                'AmountEuro': 50.0
            }
        ])
        
        with caplog.at_level(logging.WARNING):
            tasty_instance._checkAssetClassifications(option_trades)
        
        assert len(caplog.records) == 0