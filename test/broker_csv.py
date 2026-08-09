from pathlib import Path

import pandas as pd


BROKER_COLUMNS = [
    'Date', 'Type', 'Sub Type', 'Action', 'Symbol', 'Instrument Type',
    'Description', 'Value', 'Quantity', 'Average Price', 'Commissions',
    'Fees', 'Multiplier', 'Root Symbol', 'Underlying Symbol',
    'Expiration Date', 'Strike Price', 'Call or Put', 'Order #', 'Currency',
]


def _reject_unknown_columns(updates):
    unknown = sorted(set(updates) - set(BROKER_COLUMNS))
    if unknown:
        raise KeyError(f"Unknown broker columns: {unknown}")


def broker_row(**updates):
    _reject_unknown_columns(updates)
    row = {
        'Date': '2024-01-02T12:00:00+00:00',
        'Type': 'Money Movement',
        'Sub Type': 'Deposit',
        'Action': '',
        'Symbol': '',
        'Instrument Type': '',
        'Description': 'SYNTHETIC TRANSACTION',
        'Value': '100.00',
        'Quantity': '0',
        'Average Price': '',
        'Commissions': '',
        'Fees': '0.00',
        'Multiplier': '',
        'Root Symbol': '',
        'Underlying Symbol': '',
        'Expiration Date': '',
        'Strike Price': '',
        'Call or Put': '',
        'Order #': '',
        'Currency': 'USD',
    }
    row.update(updates)
    return row


def stock_trade(**updates):
    row = broker_row(**{
        'Type': 'Trade',
        'Sub Type': 'Buy to Open',
        'Action': 'BUY_TO_OPEN',
        'Symbol': 'SYN',
        'Instrument Type': 'Equity',
        'Description': 'SYNTHETIC STOCK FILL',
        'Value': '-100.00',
        'Quantity': '10',
        'Average Price': '10.00',
        'Commissions': '-1.00',
        'Fees': '-0.10',
        'Root Symbol': 'SYN',
        'Underlying Symbol': 'SYN',
        'Order #': 'ORDER-1',
    })
    _reject_unknown_columns(updates)
    row.update(updates)
    return row


def write_broker_csv(path: Path, rows):
    pd.DataFrame(rows, columns=BROKER_COLUMNS).to_csv(path, index=False)
