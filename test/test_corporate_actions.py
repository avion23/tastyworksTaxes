"""Tests for corporate actions (reverse splits, symbol changes, stock mergers)"""

import pytest
from datetime import datetime
from tastyworksTaxes.position_manager import PositionManager
from tastyworksTaxes.position_lot import PositionLot
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.transaction import Transaction
from tastyworksTaxes.tasty import Tasty
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
            quantity=96,
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
        
        assert not result
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
            ('Regular split: 2:1', 2/1, 'SPLIT'),
            ('Stock split 3 for 1', 3/1, 'GROW'),
        ]
        
        for description, expected_ratio, symbol in test_cases:
            sample_stock_lot.symbol = symbol
            sample_stock_lot.quantity = 96
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
            
            expected_quantity = 96 * expected_ratio
            assert sample_stock_lot.quantity == expected_quantity, f"Failed for description: {description}. Expected {expected_quantity}, got {sample_stock_lot.quantity}"

    def test_ambiguous_reverse_split_ratio_is_not_inferred(self, position_manager, sample_stock_lot):
        sample_stock_lot.symbol = 'XYZ'
        position_manager.add_lot_directly(sample_stock_lot)
        transaction = Transaction(pd.Series({
            'Date/Time': '2020-04-29 12:34:00',
            'Transaction Code': 'Receive Deliver',
            'Transaction Subcode': 'Reverse Split',
            'Symbol': 'XYZ',
            'Description': '8 for 1 reverse split',
            'Amount': 0.0,
            'Fees': 0.0,
            'AmountEuro': 0.0,
            'FeesEuro': 0.0,
        }))

        with pytest.raises(ValueError, match='REVERSE SPLIT RATIO UNKNOWN'):
            position_manager._handle_reverse_split(transaction)

        assert sample_stock_lot.quantity == 96

    def test_short_position_reverse_split_preserves_basis(self, position_manager):
        short_lot = PositionLot(
            symbol='XYZ',
            position_type=PositionType.stock,
            quantity=-96,
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
        assert short_lot.amount_usd == 1000.0
        assert short_lot.fees_usd == 1.0

    def test_fractional_residual_fails_atomically(self, position_manager):
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

        with pytest.raises(ValueError, match="FRACTIONAL RESIDUAL UNKNOWN"):
            position_manager._handle_reverse_split(transaction)

        assert position_manager.get_all_open_lots() == [small_lot]
        assert small_lot.quantity == 5
        assert small_lot.amount_usd == -500.0
        assert small_lot.fees_usd == 5.0

    def test_multi_lot_split_preserves_aggregate_entitlement_and_basis(
        self, position_manager
    ):
        lots = [
            PositionLot(
                symbol="XYZ", position_type=PositionType.stock, quantity=4,
                amount_usd=-400, amount_eur=-360, fees_usd=1, fees_eur=0.9,
                date=datetime(2024, 1, day),
            )
            for day in (1, 2)
        ]
        for lot in lots:
            position_manager.add_lot_directly(lot)
        transaction = Transaction(pd.Series({
            "Date/Time": datetime(2024, 2, 1),
            "Transaction Code": "Receive Deliver",
            "Transaction Subcode": "Reverse Split",
            "Symbol": "XYZ",
            "Description": "1-for-8 reverse split",
            "Amount": 0,
            "AmountEuro": 0,
            "Fees": 0,
            "FeesEuro": 0,
        }))

        position_manager.add_position(transaction)

        adjusted = position_manager.get_all_open_lots()
        assert sum(lot.quantity for lot in adjusted) == 1
        assert sum(lot.amount_usd for lot in adjusted) == -800
        assert [lot.quantity for lot in adjusted] == [0.5, 0.5]

    def test_stock_reverse_split_does_not_mutate_same_symbol_option(self):
        stock_open = Transaction.fromString(
            "2024-01-01T09:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,XYZ,Equity,open,-800,80,10,0,0,,XYZ,XYZ,,,,1,USD"
        )
        option_open = Transaction.fromString(
            "2024-01-02T09:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,XYZ  240621C00010000,Equity Option,open,-100,2,50,0,0,100,XYZ,XYZ,6/21/24,10,CALL,2,USD"
        )
        stock_split = Transaction.fromString(
            "2024-02-01T09:00:00+0000,Receive Deliver,Reverse Split,SELL_TO_CLOSE,XYZ,Equity,1-for-8 reverse split,0,80,0,0,0,,XYZ,XYZ,,,,3,USD"
        )
        tasty = Tasty()
        tasty.history = pd.DataFrame([stock_open, option_open, stock_split])

        tasty.processTransactionHistory()

        lots = tasty.position_manager.get_all_open_lots()
        stock_lot = next(lot for lot in lots if lot.position_type == PositionType.stock)
        option_lot = next(lot for lot in lots if lot.position_type == PositionType.call)
        assert (stock_lot.quantity, stock_lot.amount_usd) == (10, -800)
        assert (option_lot.quantity, option_lot.strike, option_lot.amount_usd) == (
            2, 10, -100
        )

    def test_large_split_fraction_is_not_hidden_by_relative_tolerance(
        self, position_manager
    ):
        lot = PositionLot(
            symbol="BIG", position_type=PositionType.stock,
            quantity=1_000_000_000_000.5,
            amount_usd=-1000, amount_eur=-900, fees_usd=1, fees_eur=0.9,
            date=datetime(2024, 1, 1),
        )
        position_manager.add_lot_directly(lot)
        transaction = Transaction(pd.Series({
            "Date/Time": datetime(2024, 2, 1),
            "Transaction Code": "Receive Deliver",
            "Transaction Subcode": "Reverse Split",
            "Symbol": "BIG",
            "Description": "1-for-2 reverse split",
            "Amount": 0,
            "AmountEuro": 0,
            "Fees": 0,
            "FeesEuro": 0,
        }))

        with pytest.raises(ValueError, match="FRACTIONAL RESIDUAL UNKNOWN"):
            position_manager.add_position(transaction)

        assert lot.quantity == 1_000_000_000_000.5
        assert lot.amount_usd == -1000
