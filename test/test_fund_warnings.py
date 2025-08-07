import pytest
import pandas as pd
import logging
from unittest.mock import patch

from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.fifo_processor import TradeResult

class TestTastyWithAssetClassifier:
    @pytest.fixture
    def tasty_instance(self):
        return Tasty()
    
    def test_asset_classification_warnings_in_equity_etf_profits(self, tasty_instance, caplog):
        trades = [
            TradeResult(
                symbol='UNKNOWN_FUND',
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
            )
        ]
        
        with caplog.at_level(logging.WARNING):
            tasty_instance._checkAssetClassifications(trades)
        
        assert "Unknown fund/stock type" in caplog.text
        assert "UNKNOWN_FUND" in caplog.text
    
    def test_warnings_called_via_check_asset_classifications(self, tasty_instance):
        trades = [
            TradeResult(
                symbol='UNKNOWN_FUND',
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
            )
        ]
        
        with patch.object(tasty_instance.classifier, 'check_unsupported_assets') as mock_check:
            tasty_instance._checkAssetClassifications(trades)
            mock_check.assert_called_once()
    
    def test_no_warnings_for_empty_trades(self, tasty_instance, caplog):
        empty_trades = []
        
        with caplog.at_level(logging.WARNING):
            tasty_instance._checkAssetClassifications(empty_trades)
        
        assert len(caplog.records) == 0
    
    def test_no_warnings_for_option_trades(self, tasty_instance, caplog):
        option_trades = [
            TradeResult(
                symbol='UNKNOWN_OPTION',
                position_type=PositionType.call,
                opening_date='2020-01-01 00:00:00',
                closing_date='2020-01-02 00:00:00',
                quantity=1,
                profit_usd=50.0,
                profit_eur=50.0,
                fees_usd=0,
                fees_eur=0,
                worthless_expiry=False,
                strike=None,
                expiry=None
            )
        ]
        
        with caplog.at_level(logging.WARNING):
            tasty_instance._checkAssetClassifications(option_trades)
        
        assert len(caplog.records) == 0