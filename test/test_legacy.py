import pytest
import pandas as pd
from tastyworksTaxes.legacy import convert_to_legacy_format

@pytest.fixture
def create_input_df():
    def _create_input_df(data):
        return pd.DataFrame([data])
    return _create_input_df


def test_option_assignment(create_input_df):
    input_data = {
        'Date': '2018-03-19T22:00:00+0100',
        'Type': 'Receive Deliver',
        'Sub Type': 'Assignment',
        'Action': '',
        'Symbol': 'LFIN  180615C00030000',
        'Quantity': 2,
        'Value': '0.00',
        'Average Price': 0.00,
        'Fees': 0.00,
        'Expiration Date': '6/15/18',
        'Strike Price': 30,
        'Call or Put': 'CALL',
        'Description': 'Removal of option due to assignment'
    }
    input_df = create_input_df(input_data)
    result = convert_to_legacy_format(input_df)

    assert result['Transaction Code'].iloc[0] == 'Receive Deliver'
    assert result['Transaction Subcode'].iloc[0] == 'Assignment'
    assert result['Symbol'].iloc[0] == 'LFIN'
    assert result['Buy/Sell'].iloc[0] == ''
    assert result['Open/Close'].iloc[0] == ''
    assert result['Quantity'].iloc[0] == 2
    assert result['Expiration Date'].iloc[0] == '06/15/2018'
    assert result['Strike'].iloc[0] == '30'
    assert result['Call/Put'].iloc[0] == 'C'
    assert result['Price'].iloc[0] == ''
    assert float(result['Fees'].iloc[0]) == 0.00
    assert float(result['Amount'].iloc[0]) == 0.00


def test_equity_sell_to_open(create_input_df):
    input_data = {
        'Date': '2018-03-19T22:00:00+0100',
        'Type': 'Receive Deliver',
        'Sub Type': 'Sell to Open',
        'Action': 'SELL_TO_OPEN',
        'Symbol': 'LFIN',
        'Quantity': 200,
        'Value': '6,000.00',
        'Average Price': 30.00,
        'Fees': -5.16,
        'Description': 'Sell to Open 200 LFIN @ 30.00'
    }
    input_df = create_input_df(input_data)
    result = convert_to_legacy_format(input_df)

    assert result['Transaction Code'].iloc[0] == 'Receive Deliver'
    assert result['Transaction Subcode'].iloc[0] == 'Sell to Open'
    assert result['Symbol'].iloc[0] == 'LFIN'
    assert result['Buy/Sell'].iloc[0] == 'Sell'
    assert result['Open/Close'].iloc[0] == 'Open'
    assert result['Quantity'].iloc[0] == 200
    assert result['Price'].iloc[0] == '30'
    assert float(result['Fees'].iloc[0]) == 5.16
    assert float(result['Amount'].iloc[0]) == 6000.00
    # Expect empty string for equity
    assert result['Expiration Date'].iloc[0] == ''
    assert result['Strike'].iloc[0] == ''  # Expect empty string for equity
    assert result['Call/Put'].iloc[0] == ''  # Expect empty string for equity


def test_money_movement(create_input_df):
    input_data = {
        'Date': '2018-05-18T23:00:00+0200',
        'Type': 'Money Movement',
        'Sub Type': 'Transfer',
        'Value': '1,149.50',
        'Fees': 0.00,
        'Description': 'Wire Funds Received'
    }
    input_df = create_input_df(input_data)
    result = convert_to_legacy_format(input_df)

    assert result['Transaction Code'].iloc[0] == 'Money Movement'
    assert result['Transaction Subcode'].iloc[0] == 'Transfer'
    assert result['Symbol'].iloc[0] == ''
    assert result['Buy/Sell'].iloc[0] == ''
    assert result['Open/Close'].iloc[0] == ''
    assert result['Quantity'].iloc[0] == 0
    assert result['Price'].iloc[0] == ''
    assert float(result['Fees'].iloc[0]) == 0.00
    assert float(result['Amount'].iloc[0]) == 1149.50
    assert result['Expiration Date'].iloc[0] == ''
    assert result['Strike'].iloc[0] == ''
    assert result['Call/Put'].iloc[0] == ''


def test_option_sell_to_open(create_input_df):
    input_data = {
        'Date': '2024-03-07T18:03:58+0100',
        'Type': 'Trade',
        'Sub Type': 'Sell to Open',
        'Action': 'SELL_TO_OPEN',
        'Symbol': './ZBM4 OZBK4 240426P113',
        'Quantity': 2,
        'Value': '343.75',
        'Average Price': 171.875,
        'Fees': -2.34,
        'Expiration Date': '4/26/24',
        'Strike Price': 113,
        'Call or Put': 'PUT',
        'Description': 'Sold 2 /ZBM4 OZBK4 04/26/24 Put 113\'00 @ 0.171875'
    }
    input_df = create_input_df(input_data)
    result = convert_to_legacy_format(input_df)

    assert result['Price'].iloc[0] == '1.71875'
