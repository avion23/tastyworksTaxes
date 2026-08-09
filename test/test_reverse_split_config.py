"""Test reverse split handling with config file"""

import pytest
from datetime import datetime
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
            quantity=96,
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
        # Exact 1:8 entitlement is applied without discarding basis.
        assert uso_stock_lot.quantity == 12
        assert uso_stock_lot.amount_usd == -1000.0

    def test_unknown_stock_fails_before_trade_or_lot_mutation(self, position_manager):
        """An unrecognized stock split cannot fall through to taxable FIFO handling."""
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

        description = "Reverse split: Close 100 XYZ"
        transaction = Transaction.fromString(
            "2023-06-15T12:00:00+0000,Receive Deliver,Reverse Split,"
            "SELL_TO_CLOSE,XYZ,Equity,"
            f"{description},1000,100,10,0,0,,XYZ,XYZ,,,,123456,USD"
        )

        with pytest.raises(ValueError) as exc_info:
            position_manager.add_position(transaction)

        error_msg = str(exc_info.value)
        assert "REVERSE SPLIT RATIO UNKNOWN" in error_msg
        assert "XYZ" in error_msg
        assert "2023-06-15" in error_msg
        assert description in error_msg
        assert "corporate_actions.csv" in error_msg
        assert "???" in error_msg
        assert position_manager.closed_trades == []
        assert position_manager.get_all_open_lots() == [xyz_lot]
        assert xyz_lot.quantity == 100
        assert xyz_lot.amount_usd == -1000.0

    def test_configured_stock_split_mutates_instead_of_trading(self, position_manager):
        lot = PositionLot(
            symbol="XYZ",
            position_type=PositionType.stock,
            quantity=100,
            amount_usd=-1000.0,
            amount_eur=-850.0,
            fees_usd=1.0,
            fees_eur=0.85,
            date=datetime(2023, 1, 1),
        )
        position_manager.add_lot_directly(lot)
        position_manager._corporate_actions_config = {
            "reverse_splits": [
                {
                    "date": "2023-06-15",
                    "symbol": "XYZ",
                    "ratio": 0.25,
                    "source": "verified filing",
                }
            ]
        }
        transaction = Transaction.fromString(
            "2023-06-15T12:00:00+0000,Receive Deliver,Reverse Split,"
            "SELL_TO_CLOSE,XYZ,Equity,Reverse split,0,100,,0,0,,"
            "XYZ,XYZ,,,,123456,USD"
        )

        position_manager.add_position(transaction)

        assert lot.quantity == 25
        assert position_manager.get_all_open_lots() == [lot]
        assert position_manager.closed_trades == []

    def test_confirmed_option_close_and_open_keep_fifo_processing(self, position_manager):
        position_manager.add_position(Transaction.fromString(
            "2020-04-23T19:30:00+0000,Trade,Buy to Open,BUY_TO_OPEN,"
            "USO  200717P00002000,Equity Option,Bought 6 USO 07/17/20 Put 2.00 @ 0.29,"
            "-174,6,29,-1,5.83,100,USO,USO,7/17/20,2,PUT,123456,USD"
        ))

        position_manager.add_position(Transaction.fromString(
            "2020-04-29T12:35:00+0000,Receive Deliver,Reverse Split,"
            "SELL_TO_CLOSE,USO  200717P00002000,Equity Option,"
            "OCC adjustment after reverse split; retiring 6 USO   200717P00002000,174,6,,0,0,100,"
            "USO,USO,7/17/20,2,PUT,123456,USD"
        ))
        position_manager.add_position(Transaction.fromString(
            "2020-04-29T12:35:00+0000,Receive Deliver,Reverse Split,"
            "BUY_TO_OPEN,USO1  200717P00002000,Equity Option,"
            "Replacement contract from reverse split 6 USO1  200717P00002000,-174,6,,0,0,100,"
            "USO,USO,7/17/20,2,PUT,123456,USD"
        ))

        assert len(position_manager.closed_trades) == 1
        assert position_manager.closed_trades[0].quantity == 6
        open_lots = position_manager.get_all_open_lots()
        assert len(open_lots) == 1
        assert open_lots[0].quantity == 6
        assert open_lots[0].position_type == PositionType.put

    def test_ambiguous_option_split_fails_without_mutating_stock_lots(self, position_manager):
        stock_lot = PositionLot(
            symbol="USO",
            position_type=PositionType.stock,
            quantity=100,
            amount_usd=-1000,
            amount_eur=-900,
            fees_usd=1,
            fees_eur=0.9,
            date=datetime(2020, 1, 1),
        )
        position_manager.add_lot_directly(stock_lot)
        transaction = Transaction(pd.Series({
            "Date/Time": datetime(2020, 4, 29),
            "Transaction Code": "Receive Deliver",
            "Transaction Subcode": "Reverse Split",
            "Symbol": "USO  200717P00002000",
            "Buy/Sell": "Sell",
            "Open/Close": "",
            "Quantity": 6,
            "Expiration Date": datetime(2020, 7, 17),
            "Strike": 2.0,
            "Call/Put": "P",
            "Description": "Reverse split adjustment USO 200717P00002000",
            "Amount": 0,
            "AmountEuro": 0,
            "Fees": 0,
            "FeesEuro": 0,
        }))

        with pytest.raises(ValueError, match="AMBIGUOUS OPTION REVERSE SPLIT"):
            position_manager.add_position(transaction)

        assert position_manager.get_all_open_lots() == [stock_lot]
        assert stock_lot.quantity == 100
        assert position_manager.closed_trades == []

    def test_stock_shaped_occ_row_with_stale_option_metadata_fails_closed(
        self, position_manager
    ):
        stock_lot = PositionLot(
            symbol="XYZ", position_type=PositionType.stock, quantity=100,
            amount_usd=-1000, amount_eur=-900, fees_usd=1, fees_eur=0.9,
            date=datetime(2023, 1, 1),
        )
        position_manager.add_lot_directly(stock_lot)
        transaction = Transaction(pd.Series({
            "Date/Time": datetime(2023, 6, 15),
            "Transaction Code": "Receive Deliver",
            "Transaction Subcode": "Reverse Split",
            "Symbol": "XYZ",
            "Buy/Sell": "Buy",
            "Open/Close": "Open",
            "Quantity": 1,
            "Expiration Date": datetime(2023, 7, 21),
            "Strike": 0.0,
            "Call/Put": "P",
            "Description": "Stale metadata XYZ 230721P00002000",
            "Amount": 0,
            "AmountEuro": 0,
            "Fees": 0,
            "FeesEuro": 0,
        }))

        with pytest.raises(ValueError, match="resolved type was not an option"):
            position_manager.add_position(transaction)

        assert position_manager.get_all_open_lots() == [stock_lot]
        assert stock_lot.quantity == 100
        assert position_manager.closed_trades == []

    def test_resolved_option_with_missing_expiry_fails_closed(self, position_manager):
        transaction = Transaction(pd.Series({
            "Date/Time": datetime(2023, 6, 15),
            "Transaction Code": "Receive Deliver",
            "Transaction Subcode": "Reverse Split",
            "Symbol": "XYZ  230721P00002000",
            "Buy/Sell": "Buy",
            "Open/Close": "Open",
            "Quantity": 1,
            "Expiration Date": None,
            "Strike": 2.0,
            "Call/Put": "P",
            "Description": "Replacement XYZ 230721P00002000",
            "Amount": 0,
            "AmountEuro": 0,
            "Fees": 0,
            "FeesEuro": 0,
        }))

        with pytest.raises(ValueError, match="valid option fields"):
            position_manager.add_position(transaction)

        assert position_manager.get_all_open_lots() == []
        assert position_manager.closed_trades == []

    def _seed_atomicity_state(self, position_manager):
        lots = [
            PositionLot(
                symbol="XYZ", position_type=PositionType.stock, quantity=100,
                amount_usd=-1000, amount_eur=-900, fees_usd=1, fees_eur=0.9,
                date=datetime(2023, 1, 1),
            ),
            PositionLot(
                symbol="XYZ", position_type=PositionType.put, quantity=3,
                amount_usd=-150, amount_eur=-135, fees_usd=2, fees_eur=1.8,
                date=datetime(2023, 2, 1), strike=20,
                expiry=datetime(2023, 9, 15), call_put="P",
            ),
        ]
        for lot in lots:
            position_manager.add_lot_directly(lot)
        closed_trade = object()
        position_manager.closed_trades.append(closed_trade)
        return lots, tuple(position_manager.open_lots), closed_trade

    def _assert_atomicity_state(
        self, position_manager, lots, original_keys, closed_trade
    ):
        assert tuple(position_manager.open_lots) == original_keys
        assert position_manager.get_all_open_lots() == lots
        assert [
            (lot.quantity, lot.amount_usd, lot.amount_eur, lot.strike)
            for lot in lots
        ] == [
            (100, -1000, -900, None),
            (3, -150, -135, 20),
        ]
        assert position_manager.closed_trades == [closed_trade]

    @pytest.mark.parametrize("ratio", [0, -0.5, float("nan"), float("inf")])
    def test_invalid_configured_ratio_is_atomic(self, position_manager, ratio):
        lots, original_keys, closed_trade = self._seed_atomicity_state(position_manager)
        position_manager._corporate_actions_config = {
            "reverse_splits": [{
                "date": "2023-06-15",
                "symbol": "XYZ",
                "ratio": ratio,
                "source": "test",
            }]
        }
        transaction = Transaction(pd.Series({
            "Date/Time": datetime(2023, 6, 15),
            "Transaction Code": "Receive Deliver",
            "Transaction Subcode": "Reverse Split",
            "Symbol": "XYZ",
            "Description": "Reverse split",
            "Amount": 0,
            "AmountEuro": 0,
            "Fees": 0,
            "FeesEuro": 0,
        }))

        with pytest.raises(ValueError, match="finite and greater than zero"):
            position_manager._handle_reverse_split(transaction)

        self._assert_atomicity_state(
            position_manager, lots, original_keys, closed_trade
        )

    def test_invalid_inferred_ratio_is_atomic(self, position_manager):
        lots, original_keys, closed_trade = self._seed_atomicity_state(position_manager)
        transaction = Transaction(pd.Series({
            "Date/Time": datetime(2023, 6, 15),
            "Transaction Code": "Receive Deliver",
            "Transaction Subcode": "Reverse Split",
            "Symbol": "XYZ",
            "Description": "0:8 reverse split",
            "Amount": 0,
            "AmountEuro": 0,
            "Fees": 0,
            "FeesEuro": 0,
        }))

        with pytest.raises(ValueError, match="finite and greater than zero"):
            position_manager._handle_reverse_split(transaction)

        self._assert_atomicity_state(
            position_manager, lots, original_keys, closed_trade
        )
