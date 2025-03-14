import pytest
import pandas as pd
import pathlib
from unittest.mock import patch, MagicMock
import pprint

from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.money import Money
from tastyworksTaxes.values import Values

class TestTastyRun:
    def test_tasty_run_with_merged_data(self):
        t = Tasty()
        t.processTransactionHistory = MagicMock()
        t.closedTrades = pd.read_csv("test/closed-trades.csv")
        
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
        t = Tasty(pathlib.Path("test/merged3.csv"))
        t.closedTrades = pd.read_csv("test/closed-trades.csv")
        
        result = t.run()
        
        assert len(result) > 0
        assert any(hasattr(year_value, 'stockSum') for year_value in result.values())
        
        for year, value in result.items():
            assert isinstance(year, int)
            assert isinstance(value.stockAndOptionsSum, Money)
            assert isinstance(value.stockSum, Money)
            assert isinstance(value.optionSum, Money)
