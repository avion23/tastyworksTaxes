import pytest
import pandas as pd
from pathlib import Path

from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.transaction import Transaction
from tastyworksTaxes.position import PositionType

class TestTastyGetYearlyTrades:
    def test_yearly_trades_count(self):
        """Tests that getYearlyTrades returns correct number of dataframes"""
        t = Tasty()
        t.closedTrades = pd.read_csv("test/closed-trades.csv")
        
        yearly_trades = t.getYearlyTrades()
        
        # Verify that we have 6 years of trades as per doctest
        assert len(yearly_trades) == 6
    
    def test_position_type_conversion(self):
        """Tests that position types are properly converted"""
        t = Tasty()
        t.closedTrades = pd.read_csv("test/closed-trades.csv")
        
        yearly_trades = t.getYearlyTrades()
        
        # Check that all callPutStock values are PositionType enums
        for trades_df in yearly_trades:
            for value in trades_df['callPutStock']:
                assert isinstance(value, PositionType)
    
    def test_date_conversion(self):
        """Tests that dates are converted to datetime objects"""
        t = Tasty()
        t.closedTrades = pd.read_csv("test/closed-trades.csv")
        
        yearly_trades = t.getYearlyTrades()
        
        # Check that the Closing Date is converted to datetime
        for trades_df in yearly_trades:
            assert pd.api.types.is_datetime64_dtype(trades_df['Closing Date'])
    
    def test_year_grouping(self):
        """Tests that trades are correctly grouped by year"""
        t = Tasty()
        t.closedTrades = pd.read_csv("test/closed-trades.csv")
        
        yearly_trades = t.getYearlyTrades()
        
        # Check that each DataFrame contains trades from exactly one year
        for trades_df in yearly_trades:
            unique_years = trades_df['Closing Date'].dt.year.unique()
            assert len(unique_years) == 1
    
    def test_with_static_data(self):
        """Tests with static data specifically for testing getYearlyTrades"""
        t = Tasty()
        
        # Create a dataframe with trades from different years (2018, 2019, 2020)
        data = [
            # 2018 trades (LFIN)
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
            # 2019 trade (TSLA)
            {
                'Symbol': 'TSLA', 
                'callPutStock': 'PositionType.put',
                'Opening Date': '2019-05-02 16:08:00',
                'Closing Date': '2019-05-03 16:34:00',
                'Quantity': -1,
                'Amount': 806.0
            },
            # 2021 trade (BB) - Note: Trades are grouped by closing date year, not opening date
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
        
        # Get yearly trades
        yearly_trades = t.getYearlyTrades()
        
        # Check that we have 3 years of trades (2018, 2019, 2021)
        assert len(yearly_trades) == 3
        
        # Check the number of trades in each year
        year_2018_trades = next((trades for trades in yearly_trades if trades['year'].iloc[0] == 2018), None)
        year_2019_trades = next((trades for trades in yearly_trades if trades['year'].iloc[0] == 2019), None)
        year_2021_trades = next((trades for trades in yearly_trades if trades['year'].iloc[0] == 2021), None)
        
        assert year_2018_trades is not None
        assert year_2019_trades is not None
        assert year_2021_trades is not None
        
        assert len(year_2018_trades) == 2
        assert len(year_2019_trades) == 1
        assert len(year_2021_trades) == 1
        
        # Check that the data was grouped correctly
        assert year_2018_trades.iloc[0]['Symbol'] == 'LFIN'
        assert year_2019_trades.iloc[0]['Symbol'] == 'TSLA'
        assert year_2021_trades.iloc[0]['Symbol'] == 'BB'
