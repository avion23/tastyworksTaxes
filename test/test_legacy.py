import pytest
import pandas as pd
from tastyworksTaxes.legacy import convert_to_legacy_format

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

def test_convert_to_legacy_format(sample_new_tastytrade_df):
    result = convert_to_legacy_format(sample_new_tastytrade_df)

    expected_columns = ['Date/Time', 'Transaction Code', 'Transaction Subcode', 'Symbol', 'Buy/Sell', 'Open/Close',
                        'Quantity', 'Expiration Date', 'Strike', 'Call/Put', 'Price', 'Fees', 'Amount', 'Description', 'Account Reference']
    assert all(col in result.columns for col in expected_columns)

    assert result['Date/Time'].iloc[0] == '08/05/2024 11:00 PM'
    assert result['Symbol'].iloc[0] == 'SCHG'
    assert result['Buy/Sell'].iloc[0] == 'Sell'
    assert result['Open/Close'].iloc[0] == ''
    assert result['Call/Put'].iloc[0] == 'P'
    assert result['Account Reference'].iloc[0] == 'Individual...39'

    assert result['Quantity'].iloc[1] == 159
    assert result['Amount'].iloc[1] == '7,893.28'
    assert result['Price'].iloc[1] == '49.64'
    assert result['Fees'].iloc[1] == '0.370'

    assert result['Open/Close'].iloc[1] == 'Close'
