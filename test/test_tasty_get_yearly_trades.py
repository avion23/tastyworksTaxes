import pytest
import pandas as pd
from pathlib import Path

from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.transaction import Transaction
from tastyworksTaxes.position import PositionType

class TestTastyGetYearlyTrades:
    def test_yearly_trades_count(self):
        t = Tasty()
        t.closedTrades = pd.read_csv("test/closed-trades.csv")
        
        yearly_trades = t.getYearlyTrades()
        
        assert len(yearly_trades) == 6
    
    def test_position_type_conversion(self):
        t = Tasty()
        t.closedTrades = pd.read_csv("test/closed-trades.csv")
        
        yearly_trades = t.getYearlyTrades()
        
        for trades_df in yearly_trades:
            for value in trades_df['callPutStock']:
                assert isinstance(value, PositionType)
    
    def test_date_conversion(self):
        t = Tasty()
        t.closedTrades = pd.read_csv("test/closed-trades.csv")
        
        yearly_trades = t.getYearlyTrades()
        
        for trades_df in yearly_trades:
            assert pd.api.types.is_datetime64_dtype(trades_df['Closing Date'])
    
    def test_year_grouping(self):
        t = Tasty()
        t.closedTrades = pd.read_csv("test/closed-trades.csv")
        
        yearly_trades = t.getYearlyTrades()
        
        for trades_df in yearly_trades:
            unique_years = trades_df['Closing Date'].dt.year.unique()
            assert len(unique_years) == 1
    
    def test_with_real_data(self):
        t = Tasty()
        
        data = [
            {
                'Symbol': 'LFIN', 
                'callPutStock': 'PositionType.call',
                'Opening Date': '2018-03-12 17:08:00',
                'Closing Date': '2018-03-21 18:42:00',
                'Quantity': 1,
                'Amount': 1458.0
            },
            {
                'Symbol': 'LFIN', 
                'callPutStock': 'PositionType.stock',
                'Opening Date': '2018-03-19 22:00:00',
                'Closing Date': '2018-03-21 18:42:00',
                'Quantity': -100,
                'Amount': -2676.0
            },
            {
                'Symbol': 'TSLA', 
                'callPutStock': 'PositionType.put',
                'Opening Date': '2019-05-02 16:08:00',
                'Closing Date': '2019-05-03 16:34:00',
                'Quantity': -1,
                'Amount': 806.0
            },
            {
                'Symbol': 'BB', 
                'callPutStock': 'PositionType.call',
                'Opening Date': '2020-12-23 15:45:00',
                'Closing Date': '2021-01-11 17:51:00',
                'Quantity': 5,
                'Amount': 45.0
            }
        ]
        
        t.closedTrades = pd.DataFrame(data)
        
        yearly_trades = t.getYearlyTrades()
        
        assert len(yearly_trades) == 3
        
        year_2018_trades = next((trades for trades in yearly_trades if trades['year'].iloc[0] == 2018), None)
        year_2019_trades = next((trades for trades in yearly_trades if trades['year'].iloc[0] == 2019), None)
        year_2021_trades = next((trades for trades in yearly_trades if trades['year'].iloc[0] == 2021), None)
        
        assert year_2018_trades is not None
        assert year_2019_trades is not None
        assert year_2021_trades is not None
        
        assert len(year_2018_trades) == 2
        assert len(year_2019_trades) == 1
        assert len(year_2021_trades) == 1
        
        assert year_2018_trades.iloc[0]['Symbol'] == 'LFIN'
        assert year_2019_trades.iloc[0]['Symbol'] == 'TSLA'
        assert year_2021_trades.iloc[0]['Symbol'] == 'BB'
