"""Tests for corporate actions (reverse splits, symbol changes, stock mergers)"""

import pytest
from datetime import datetime
from tastyworksTaxes.position_manager import PositionManager
from tastyworksTaxes.position_lot import PositionLot
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.transaction import Transaction
import pandas as pd


class TestCorporateActions:
    
    @pytest.fixture
    def position_manager(self):
        return PositionManager()
    
    @pytest.fixture 
    def sample_stock_lot(self):
        return PositionLot(
            symbol='USO',
            position_type=PositionType.stock,
            quantity=100,
            amount_usd=-1000.0,
            amount_eur=-850.0,
            fees_usd=1.0,
            fees_eur=0.85,
            date=datetime(2020, 4, 1)
        )
    
    @pytest.fixture
    def sample_option_lot(self):
        return PositionLot(
            symbol='USO',
            position_type=PositionType.put,
            quantity=-6,
            amount_usd=648.0,
            amount_eur=551.0,
            fees_usd=6.86,
            fees_eur=5.83,
            date=datetime(2020, 4, 23),
            strike=3.5,
            expiry=datetime(2020, 7, 17),
            call_put='P'
        )
    
    def test_reverse_split_adjusts_stock_quantity(self, position_manager, sample_stock_lot):
        """Test that reverse split correctly adjusts stock quantity"""
        position_manager.open_lots.append(sample_stock_lot)
        
        reverse_split_data = {
            'Date/Time': '2020-04-29 12:34:00',
            'Transaction Code': 'Receive Deliver',
            'Transaction Subcode': 'Reverse Split',
            'Symbol': 'USO',
            'Buy/Sell': 'Sell',
            'Open/Close': 'Open',
            'Quantity': 6,
            'Expiration Date': '',
            'Strike': '',
            'Call/Put': '',
            'Price': '',
            'Amount': 0.0,
            'Description': 'Reverse split',
            'Fees': 0.0,
            'AmountEuro': 0.0,
            'FeesEuro': 0.0
        }
        transaction = Transaction(pd.Series(reverse_split_data))
        
        position_manager._handle_reverse_split(transaction)
        
        assert sample_stock_lot.quantity == 12
        assert sample_stock_lot.strike is None
        
    def test_reverse_split_adjusts_option_quantity_and_strike(self, position_manager, sample_option_lot):
        """Test that reverse split correctly adjusts option quantity and strike"""
        position_manager.open_lots.append(sample_option_lot)
        
        reverse_split_data = {
            'Date/Time': '2020-04-29 12:34:00',
            'Transaction Code': 'Receive Deliver', 
            'Transaction Subcode': 'Reverse Split',
            'Symbol': 'USO',
            'Buy/Sell': 'Sell',
            'Open/Close': 'Open',
            'Quantity': 6,
            'Expiration Date': '2020-07-17',
            'Strike': 3.5,
            'Call/Put': 'P',
            'Price': '',
            'Amount': 0.0,
            'Description': 'Reverse split',
            'Fees': 0.0,
            'AmountEuro': 0.0,
            'FeesEuro': 0.0
        }
        transaction = Transaction(pd.Series(reverse_split_data))
        
        position_manager._handle_reverse_split(transaction)
        
        assert sample_option_lot.quantity == 0
        assert sample_option_lot.strike == 28.0
        
    def test_reverse_split_no_effect_on_other_symbols(self, position_manager, sample_stock_lot):
        """Test that reverse split only affects the target symbol"""
        position_manager.open_lots.append(sample_stock_lot)
        
        other_lot = PositionLot(
            symbol='AAPL',
            position_type=PositionType.stock,
            quantity=50,
            amount_usd=-500.0,
            amount_eur=-425.0,
            fees_usd=1.0,
            fees_eur=0.85,
            date=datetime(2020, 4, 1)
        )
        position_manager.open_lots.append(other_lot)
        
        reverse_split_data = {
            'Date/Time': '2020-04-29 12:34:00',
            'Transaction Code': 'Receive Deliver',
            'Transaction Subcode': 'Reverse Split',
            'Symbol': 'USO',
            'Buy/Sell': 'Sell',
            'Open/Close': 'Open',
            'Quantity': 6,
            'Expiration Date': '',
            'Strike': '',
            'Call/Put': '',
            'Price': '',
            'Amount': 0.0,
            'Description': 'Reverse split',
            'Fees': 0.0,
            'AmountEuro': 0.0,
            'FeesEuro': 0.0
        }
        transaction = Transaction(pd.Series(reverse_split_data))
        
        position_manager._handle_reverse_split(transaction)
        
        assert sample_stock_lot.quantity == 12
        assert other_lot.quantity == 50
        
    def test_reverse_split_regex_parsing(self, position_manager, sample_stock_lot):
        """Test reverse split with various ratio formats in description"""
        test_cases = [
            ('Reverse split: Open 1 ABC1 with ratio 1:8', 1/8, 'ABC'),
            ('1-for-8 reverse split', 1/8, 'TEST'),
            ('8 for 1 reverse split', 1/8, 'XYZ'),
            ('Regular split: 2:1', 2/1, 'SPLIT'),
            ('Stock split 3 for 1', 3/1, 'GROW'),
        ]
        
        for description, expected_ratio, symbol in test_cases:
            sample_stock_lot.symbol = symbol
            sample_stock_lot.quantity = 100
            position_manager.open_lots = [sample_stock_lot]
            
            reverse_split_data = {
                'Date/Time': '2020-04-29 12:34:00',
                'Transaction Code': 'Receive Deliver',
                'Transaction Subcode': 'Reverse Split',
                'Symbol': symbol,
                'Description': description,
                'Amount': 0.0,
                'Fees': 0.0,
                'AmountEuro': 0.0,
                'FeesEuro': 0.0
            }
            transaction = Transaction(pd.Series(reverse_split_data))
            
            result = position_manager._handle_reverse_split(transaction)
            assert result is True, f"Failed to handle reverse split for: {description}"
            
            expected_quantity = int(100 * expected_ratio)
            assert sample_stock_lot.quantity == expected_quantity, f"Failed for description: {description}. Expected {expected_quantity}, got {sample_stock_lot.quantity}"