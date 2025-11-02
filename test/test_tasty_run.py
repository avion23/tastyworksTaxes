import pytest
import pandas as pd
import pathlib
from unittest.mock import patch, MagicMock
import pprint

from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.money import Money
from tastyworksTaxes.values import Values
from tastyworksTaxes.fifo_processor import TradeResult
from tastyworksTaxes.position import PositionType

class TestTastyRun:
    def test_tasty_run_with_merged_data(self):
        t = Tasty()
        t.processTransactionHistory = MagicMock()
        
        sample_trades = [
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
                position_type=PositionType.stock,
                opening_date='2018-03-19 22:00:00',
                closing_date='2018-03-21 18:42:00',
                quantity=-100,
                profit_usd=-2676.0,
                profit_eur=-2182.65,
                fees_usd=2.662,
                fees_eur=2.16,
                worthless_expiry=False
            )
        ]
        t.position_manager.closed_trades = sample_trades
        
        result = t.run()
        
        t.processTransactionHistory.assert_called_once()
        assert isinstance(result, dict)
        
        year_keys = list(result.keys())
        assert all(isinstance(key, int) for key in year_keys)
        
        if year_keys:
            sample_year = year_keys[0]
            year_data = result[sample_year]
            
            assert isinstance(year_data, Values)
            assert isinstance(year_data.stockAndOptionsSum, Money)
            assert isinstance(year_data.stockSum, Money)
            assert isinstance(year_data.optionSum, Money)
            assert isinstance(year_data.longOptionProfits, Money)
            assert isinstance(year_data.longOptionLosses, Money)
    
    def test_run_with_real_csv_data(self):
        t = Tasty(pathlib.Path("test/transactions_2018_to_2025.csv"))
        
        result = t.run()
        
        assert len(result) > 0
        assert any(hasattr(year_value, 'equityEtfProfits') for year_value in result.values())
        
        for year, value in result.items():
            assert isinstance(year, int)
            assert isinstance(value.stockAndOptionsSum, Money)
            assert isinstance(value.equityEtfProfits, Money)
            assert isinstance(value.otherStockAndBondProfits, Money)
            assert isinstance(value.stockAndEtfLosses, Money)
            assert isinstance(value.optionSum, Money)
