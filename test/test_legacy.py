import pytest
import pandas as pd
from tastyworksTaxes.legacy import convert_to_legacy_format, convert_to_new_format, NEW_TO_LEGACY_MAPPING, LEGACY_TO_NEW_MAPPING, ADDITIONAL_LEGACY_FIELDS, ADDITIONAL_NEW_FIELDS


@pytest.fixture
def sample_new_tastytrade_df():
    return pd.DataFrame({
        'Date': ['2024-08-05T23:00:00+0200'],
        'Type': ['Receive Deliver'],
        'Sub Type': ['Assignment'],
        'Action': ['BUY_TO_OPEN'],
        'Symbol': ['SCHG  240816P00103000'],
        'Instrument Type': ['Equity Option'],
        'Quantity': [1],
        'Value': [-10300.00],
        'Expiration Date': ['8/16/24'],
        'Strike Price': [103],
        'Call or Put': ['PUT'],
        'Multiplier': [100],
        'Root Symbol': ['SCHG'],
        'Underlying Symbol': ['SCHG'],
        'Currency': ['USD'],
        'Average Price': [103.00],
        'Fees': [0.00],
        'Description': ['Removal of option due to assignment']
    })


@pytest.fixture
def sample_legacy_df():
    return pd.DataFrame({
        'Date/Time': ['08/05/2024 11:00 PM'],
        'Transaction Code': ['Receive Deliver'],
        'Transaction Subcode': ['Assignment'],
        'Symbol': ['SCHG  240816P00103000'],
        'Buy/Sell': ['Buy'],
        'Open/Close': ['Open'],
        'Quantity': [1],
        'Amount': [-10300.00],
        'Expiration Date': ['8/16/24'],
        'Strike': [103],
        'Call/Put': ['PUT'],
        'Account Reference': ['Individual...39'],
        'Price': [103.00],
        'Fees': [0.00],
        'Description': ['Removal of option due to assignment']
    })


def test_convert_to_legacy_format(sample_new_tastytrade_df):
    result = convert_to_legacy_format(sample_new_tastytrade_df)
    assert set(NEW_TO_LEGACY_MAPPING.values()).issubset(result.columns)
    assert set(ADDITIONAL_LEGACY_FIELDS).issubset(result.columns)
    assert result['Buy/Sell'].iloc[0] == 'Buy'
    assert result['Open/Close'].iloc[0] == 'Open'
    assert result['Date/Time'].iloc[0].startswith('08/05/2024')


def test_convert_to_new_format(sample_legacy_df):
    result = convert_to_new_format(sample_legacy_df)
    assert set(LEGACY_TO_NEW_MAPPING.values()).issubset(result.columns)
    assert set(ADDITIONAL_NEW_FIELDS).issubset(result.columns)
    assert result['Action'].iloc[0] == 'BUY_TO_OPEN'
    assert result['Instrument Type'].iloc[0] == 'Equity Option'
    assert result['Date'].iloc[0].startswith('2024-08-05T')
