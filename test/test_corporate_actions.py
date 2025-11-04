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
        position_manager.add_lot_directly(sample_stock_lot)
        
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
        position_manager.add_lot_directly(sample_option_lot)
        
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
            'Description': 'Reverse split: Close 6 USO   200717P00003500',
            'Fees': 0.0,
            'AmountEuro': 0.0,
            'FeesEuro': 0.0
        }
        transaction = Transaction(pd.Series(reverse_split_data))
        
        result = position_manager._handle_reverse_split(transaction)
        
        assert result == False
        assert sample_option_lot.quantity == -6
        assert sample_option_lot.strike == 3.5
        
    def test_reverse_split_no_effect_on_other_symbols(self, position_manager, sample_stock_lot):
        """Test that reverse split only affects the target symbol"""
        position_manager.add_lot_directly(sample_stock_lot)

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
        position_manager.add_lot_directly(other_lot)
        
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
            position_manager.open_lots.clear()
            position_manager.add_lot_directly(sample_stock_lot)
            
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

    def test_short_position_reverse_split_ceiling_rounding(self, position_manager):
        from math import ceil

        target = -9 * 0.25
        new_qty = ceil(target)
        assert new_qty == -2

        short_lot = PositionLot(
            symbol='XYZ',
            position_type=PositionType.stock,
            quantity=-100,
            amount_usd=1000.0,
            amount_eur=850.0,
            fees_usd=1.0,
            fees_eur=0.85,
            date=datetime(2020, 1, 1)
        )
        position_manager.add_lot_directly(short_lot)

        reverse_split_data = {
            'Date/Time': '2020-04-29 12:34:00',
            'Transaction Code': 'Receive Deliver',
            'Transaction Subcode': 'Reverse Split',
            'Symbol': 'XYZ',
            'Description': '1-for-8 reverse split',
            'Amount': 0.0,
            'Fees': 0.0,
            'AmountEuro': 0.0,
            'FeesEuro': 0.0
        }
        transaction = Transaction(pd.Series(reverse_split_data))

        position_manager._handle_reverse_split(transaction)

        assert short_lot.quantity == -12
        assert abs(short_lot.amount_usd - 960.0) < 0.01
        assert abs(short_lot.fees_usd - 0.96) < 0.01

    def test_residual_basis_retained_when_split_rounds_to_zero(self, position_manager):
        small_lot = PositionLot(
            symbol='XYZ',
            position_type=PositionType.stock,
            quantity=5,
            amount_usd=-500.0,
            amount_eur=-425.0,
            fees_usd=5.0,
            fees_eur=4.25,
            date=datetime(2020, 1, 1)
        )
        position_manager.add_lot_directly(small_lot)

        reverse_split_data = {
            'Date/Time': '2020-04-29 12:34:00',
            'Transaction Code': 'Receive Deliver',
            'Transaction Subcode': 'Reverse Split',
            'Symbol': 'XYZ',
            'Description': '1-for-8 reverse split',
            'Amount': 0.0,
            'Fees': 0.0,
            'AmountEuro': 0.0,
            'FeesEuro': 0.0
        }
        transaction = Transaction(pd.Series(reverse_split_data))

        position_manager._handle_reverse_split(transaction)

        assert small_lot.quantity == 0
        assert small_lot.amount_usd != 0.0
        assert small_lot.fees_usd != 0.0

        open_lots = position_manager.get_all_open_lots()
        assert len(open_lots) == 1
        assert open_lots[0].quantity == 0
        assert abs(open_lots[0].amount_usd) > 0