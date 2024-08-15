import pytest
import pandas as pd
from tastyworksTaxes.legacy import convert_to_legacy_format, convert_to_new_format

@pytest.fixture
def sample_new_tastytrade_df():
    return pd.DataFrame({
        'Date': ['2024-08-05T23:00:00+0200', '2024-07-19T20:22:12+0200', '2024-07-16T23:00:00+0200'],
        'Type': ['Receive Deliver', 'Trade', 'Money Movement'],
        'Sub Type': ['Assignment', 'Sell to Close', 'Credit Interest'],
        'Action': ['', 'SELL_TO_CLOSE', ''],
        'Symbol': ['SCHG  240816P00103000', 'PULS', ''],
        'Instrument Type': ['Equity Option', 'Equity', ''],
        'Quantity': [1, 159, 0],
        'Value': [0.00, 7893.28, 0.02],
        'Expiration Date': ['8/16/24', '', ''],
        'Strike Price': [103, '', ''],
        'Call or Put': ['PUT', '', ''],
        'Root Symbol': ['SCHG', 'PULS', ''],
        'Underlying Symbol': ['SCHG', 'PULS', ''],
        'Currency': ['USD', 'USD', 'USD'],
        'Average Price': [0.00, 49.64, ''],
        'Fees': [0.00, -0.37, 0.00],
        'Description': ['Removal of option due to assignment', 'Sold 159 PULS @ 49.64', 'INTEREST ON CREDIT BALANCE']
    })

@pytest.fixture
def sample_legacy_df():
    return pd.DataFrame({
        'Date/Time': ['08/05/2024 09:00 PM', '07/19/2024 06:22 PM', '07/16/2024 09:00 PM'],
        'Transaction Code': ['Receive Deliver', 'Trade', 'Money Movement'],
        'Transaction Subcode': ['Assignment', 'Sell to Close', 'Credit Interest'],
        'Symbol': ['SCHG', 'PULS', ''],
        'Buy/Sell': ['Sell', 'Sell', ''],
        'Open/Close': ['Close', 'Close', ''],
        'Quantity': [1, 159, 0],
        'Amount': [0.00, 7893.28, 0.02],
        'Expiration Date': ['8/16/24', '', ''],
        'Strike': [103, '', ''],
        'Call/Put': ['P', '', ''],
        'Account Reference': ['Individual...39', 'Individual...39', 'Individual...39'],
        'Price': [0.00, 49.64, ''],
        'Fees': [0.00, -0.37, 0.00],
        'Description': ['Removal of option due to assignment', 'Sold 159 PULS @ 49.64', 'INTEREST ON CREDIT BALANCE']
    })

def test_convert_to_legacy_format(sample_new_tastytrade_df):
    result = convert_to_legacy_format(sample_new_tastytrade_df)

    assert 'Date/Time' in result.columns
    assert 'Transaction Code' in result.columns
    assert 'Transaction Subcode' in result.columns
    assert 'Symbol' in result.columns
    assert 'Buy/Sell' in result.columns
    assert 'Open/Close' in result.columns
    assert 'Quantity' in result.columns
    assert 'Amount' in result.columns
    assert 'Expiration Date' in result.columns
    assert 'Strike' in result.columns
    assert 'Call/Put' in result.columns
    assert 'Account Reference' in result.columns
    assert 'Price' in result.columns
    assert 'Fees' in result.columns
    assert 'Description' in result.columns

    assert result['Date/Time'].iloc[0] == '08/05/2024 09:00 PM'
    assert result['Symbol'].iloc[0] == 'SCHG'
    assert result['Buy/Sell'].iloc[0] == 'Sell'
    assert result['Open/Close'].iloc[0] == 'Close'
    assert result['Call/Put'].iloc[0] == 'P'

def test_convert_to_new_format(sample_legacy_df):
    result = convert_to_new_format(sample_legacy_df)

    assert 'Date' in result.columns
    assert 'Type' in result.columns
    assert 'Sub Type' in result.columns
    assert 'Action' in result.columns
    assert 'Symbol' in result.columns
    assert 'Instrument Type' in result.columns
    assert 'Quantity' in result.columns
    assert 'Value' in result.columns
    assert 'Expiration Date' in result.columns
    assert 'Strike Price' in result.columns
    assert 'Call or Put' in result.columns
    assert 'Root Symbol' in result.columns
    assert 'Underlying Symbol' in result.columns
    assert 'Currency' in result.columns
    assert 'Average Price' in result.columns
    assert 'Fees' in result.columns
    assert 'Description' in result.columns

    assert result['Date'].iloc[0] == '2024-08-05T21:00:00+0000'

    # Check components of the Symbol separately
    symbol_parts = result['Symbol'].iloc[0].split()
    assert symbol_parts[0] == 'SCHG'  # Ticker
    assert len(symbol_parts[1]) == 14  # 81624P00000103 format
    assert symbol_parts[1][5] == 'P'  # Put option
    assert int(symbol_parts[1][6:]) == 103  # Strike price

    assert result['Action'].iloc[0] == 'SELL_TO_CLOSE'
    assert result['Instrument Type'].iloc[0] == 'Equity Option'
    assert result['Call or Put'].iloc[0] == 'PUT'


def test_roundtrip_conversion(sample_new_tastytrade_df, sample_legacy_df):
    # Test converting from new to legacy and back to new
    legacy_df = convert_to_legacy_format(sample_new_tastytrade_df)
    roundtrip_df = convert_to_new_format(legacy_df)

    # Check that key information is preserved
    assert all(
        sample_new_tastytrade_df['Quantity'] == roundtrip_df['Quantity'])
    assert all(sample_new_tastytrade_df['Value'] == roundtrip_df['Value'])
    assert all(
        sample_new_tastytrade_df['Description'] == roundtrip_df['Description'])

    # Test converting from legacy to new and back to legacy
    new_df = convert_to_new_format(sample_legacy_df)
    roundtrip_df = convert_to_legacy_format(new_df)

    # Check that key information is preserved
    assert all(sample_legacy_df['Quantity'] == roundtrip_df['Quantity'])
    assert all(sample_legacy_df['Amount'] == roundtrip_df['Amount'])
    assert all(sample_legacy_df['Description'] == roundtrip_df['Description'])
