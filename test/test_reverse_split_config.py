"""Test reverse split handling with config file"""

import pytest
from datetime import datetime
from pathlib import Path
from tastyworksTaxes.position_manager import PositionManager
from tastyworksTaxes.position_lot import PositionLot
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.transaction import Transaction
import pandas as pd


class TestReverseSplitConfig:
    @pytest.fixture
    def position_manager(self):
        return PositionManager()

    def test_config_file_loads(self, position_manager):
        """Verify that corporate_actions.yaml is loaded"""
        assert position_manager._corporate_actions_config is not None
        reverse_splits = position_manager._corporate_actions_config.get(
            "reverse_splits", []
        )

        # Should contain USO entry
        uso_split = next((s for s in reverse_splits if s.get("symbol") == "USO"), None)
        assert uso_split is not None
        assert uso_split["date"] == "2020-04-29"
        assert uso_split["ratio"] == 0.125

    def test_config_lookup_finds_uso(self, position_manager):
        """Test that USO ratio can be found via config lookup"""
        date = datetime(2020, 4, 29)
        ratio = position_manager._get_reverse_split_ratio_from_config("USO", date)
        assert ratio == 0.125

    def test_config_lookup_returns_none_for_unknown(self, position_manager):
        """Test that unknown symbols return None"""
        date = datetime(2020, 4, 29)
        ratio = position_manager._get_reverse_split_ratio_from_config("UNKNOWN", date)
        assert ratio is None

    def test_stock_reverse_split_with_config(self, position_manager):
        """Test that stock reverse split uses config when description lacks ratio"""
        # Add USO stock position (not option - options are handled as trades)
        uso_stock_lot = PositionLot(
            symbol="USO",
            position_type=PositionType.stock,
            quantity=100,
            amount_usd=-1000.0,
            amount_eur=-850.0,
            fees_usd=1.0,
            fees_eur=0.85,
            date=datetime(2020, 4, 23),
        )
        position_manager.add_lot_directly(uso_stock_lot)

        # Create reverse split transaction (description has NO ratio, must use config)
        reverse_split_data = {
            "Date/Time": "2020-04-29 12:34:53",
            "Transaction Code": "Receive Deliver",
            "Transaction Subcode": "Reverse Split",
            "Symbol": "USO",
            "Description": "Reverse split",  # NO ratio pattern!
            "Amount": 0.0,
            "Fees": 0.0,
            "AmountEuro": 0.0,
            "FeesEuro": 0.0,
        }
        transaction = Transaction(pd.Series(reverse_split_data))

        # Should use config ratio (0.125 = 1:8) and succeed
        result = position_manager._handle_reverse_split(transaction)

        assert result is True
        # After 1:8 split, 100 shares should become 12.5 -> 12 shares (floor for long positions)
        assert uso_stock_lot.quantity == 12

    def test_unknown_symbol_raises_helpful_error(self, position_manager):
        """Test that unknown reverse split raises error with YAML template"""
        xyz_lot = PositionLot(
            symbol="XYZ",
            position_type=PositionType.stock,
            quantity=100,
            amount_usd=-1000.0,
            amount_eur=-850.0,
            fees_usd=1.0,
            fees_eur=0.85,
            date=datetime(2023, 1, 1),
        )
        position_manager.add_lot_directly(xyz_lot)

        reverse_split_data = {
            "Date/Time": "2023-06-15 12:00:00",
            "Transaction Code": "Receive Deliver",
            "Transaction Subcode": "Reverse Split",
            "Symbol": "XYZ",
            "Description": "Reverse split",  # No ratio
            "Amount": 0.0,
            "Fees": 0.0,
            "AmountEuro": 0.0,
            "FeesEuro": 0.0,
        }
        transaction = Transaction(pd.Series(reverse_split_data))

        with pytest.raises(ValueError) as exc_info:
            position_manager._handle_reverse_split(transaction)

        error_msg = str(exc_info.value)
        assert "REVERSE SPLIT RATIO UNKNOWN" in error_msg
        assert "XYZ" in error_msg
        assert "2023-06-15" in error_msg
        assert "corporate_actions.yaml" in error_msg
        assert "ratio: ???" in error_msg
