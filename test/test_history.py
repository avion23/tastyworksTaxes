import pytest
import pandas as pd
from tastyworksTaxes.history import History

from test.broker_csv import broker_row, stock_trade, write_broker_csv


def test_internal_format_csv_loads_and_normalizes(tmp_path):
    csv_path = tmp_path / "internal.csv"
    pd.DataFrame({
        "Date/Time": ["2020-05-08 17:24:00", "2020-05-07 14:00:00"],
        "Transaction Code": ["Money Movement", "Trade"],
        "Transaction Subcode": ["Fee", "Sell to Open"],
        "Symbol": ["", "SVXY"],
        "Buy/Sell": ["", "Sell"],
        "Open/Close": ["", "Open"],
        "Quantity": ["", "3"],
        "Expiration Date": ["", "2020-06-19"],
        "Strike": ["", "30"],
        "Call/Put": ["", "P"],
        "Price": ["", "0.80"],
        "Fees": ["", "1.15"],
        "Amount": ["-1.0", "240.0"],
        "Description": [
            "Regulatory fee",
            "Sold 3 SVXY 06/19/20 Put 30.00 @ 0.80",
        ],
        "Account Reference": ["acct", "acct"],
    }).to_csv(csv_path, index=False)

    hist = History.fromFile(csv_path)

    assert hist["Date/Time"].is_monotonic_increasing
    assert "AmountEuro" in hist.columns
    assert "FeesEuro" in hist.columns
    assert hist.loc[1, "Quantity"] == 0
    assert hist.loc[1, "Fees"] == 0
    assert pd.isna(hist.loc[1, "Expiration Date"])
    assert hist.loc[0, "Strike"] == 30
    assert hist.loc[0, "Price"] == 0.80


def test_internal_format_invalid_numeric_raises(tmp_path):
    csv_path = tmp_path / "internal_bad_numeric.csv"
    pd.DataFrame({
        "Date/Time": ["2020-05-07 14:00:00"],
        "Transaction Code": ["Trade"],
        "Transaction Subcode": ["Sell to Open"],
        "Symbol": ["SVXY"],
        "Buy/Sell": ["Sell"],
        "Open/Close": ["Open"],
        "Quantity": ["not-a-number"],
        "Expiration Date": ["2020-06-19"],
        "Strike": ["30"],
        "Call/Put": ["P"],
        "Price": ["0.80"],
        "Fees": ["1.15"],
        "Amount": ["240.0"],
        "Description": ["Sold 3 SVXY 06/19/20 Put 30.00 @ 0.80"],
    }).to_csv(csv_path, index=False)

    with pytest.raises(ValueError, match="Failed to parse numeric values"):
        History.fromFile(csv_path)


def test_internal_format_invalid_option_expiration_raises(tmp_path):
    csv_path = tmp_path / "internal_bad_expiration.csv"
    pd.DataFrame({
        "Date/Time": ["2020-05-07 14:00:00"],
        "Transaction Code": ["Trade"],
        "Transaction Subcode": ["Sell to Open"],
        "Symbol": ["SVXY"],
        "Buy/Sell": ["Sell"],
        "Open/Close": ["Open"],
        "Quantity": ["3"],
        "Expiration Date": ["bad-date"],
        "Strike": ["30"],
        "Call/Put": ["P"],
        "Price": ["0.80"],
        "Fees": ["1.15"],
        "Amount": ["240.0"],
        "Description": ["Sold 3 SVXY 06/19/20 Put 30.00 @ 0.80"],
    }).to_csv(csv_path, index=False)

    with pytest.raises(ValueError, match="Failed to parse Expiration Date"):
        History.fromFile(csv_path)


def test_unsupported_csv_schema_raises_clear_error(tmp_path):
    csv_path = tmp_path / "unsupported.csv"
    pd.DataFrame({"Not Date": ["2020-05-08"], "Value": [1]}).to_csv(csv_path, index=False)

    with pytest.raises(ValueError, match="Unsupported CSV schema"):
        History.fromFile(csv_path)


@pytest.mark.parametrize("contents", ["", "Date,Type,Sub Type,Value,Description\n"])
def test_empty_csv_raises_clear_error(tmp_path, contents):
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text(contents)

    with pytest.raises(ValueError, match="empty|no transactions"):
        History.fromFile(csv_path)


def test_new_format_blank_optional_values_use_safe_defaults(tmp_path):
    csv_path = tmp_path / "minimal_tastytrade.csv"
    write_broker_csv(csv_path, [broker_row(**{
        'Date': '2020-05-08T17:24:00-04:00',
        'Type': 'Money Movement',
        'Sub Type': 'Fee',
        'Value': '-1.0',
        'Description': 'Regulatory fee',
    })])

    history = History.fromFile(csv_path)

    assert history.loc[0, "Symbol"] == ""
    assert history.loc[0, "Quantity"] == 0
    assert history.loc[0, "Fees"] == 0
    assert pd.isna(history.loc[0, "Expiration Date"])


def test_new_format_invalid_optional_value_has_clear_error(tmp_path):
    csv_path = tmp_path / "bad_quantity.csv"
    write_broker_csv(csv_path, [stock_trade(**{
        'Date': '2020-05-08T17:24:00-04:00',
        'Description': 'Bought stock',
        'Quantity': 'not-a-number',
    })])

    with pytest.raises(ValueError, match="numeric values.*Quantity"):
        History.fromFile(csv_path)


def test_new_format_option_with_invalid_expiration_has_clear_error(tmp_path):
    csv_path = tmp_path / "bad_option_expiration.csv"
    write_broker_csv(csv_path, [stock_trade(**{
        'Date': '2020-05-08T17:24:00-04:00',
        'Description': 'Bought option',
        'Symbol': 'SYN  200619C00050000',
        'Instrument Type': 'Equity Option',
        'Expiration Date': 'not-a-date',
        'Strike Price': '50',
        'Call or Put': 'CALL',
        'Multiplier': '100',
    })])

    with pytest.raises(ValueError, match="Failed to parse Expiration Date"):
        History.fromFile(csv_path)


def test_new_format_csv_sorting(tmp_path):
    csv_path = tmp_path / "sorting.csv"
    write_broker_csv(csv_path, [
        stock_trade(**{
            'Date': '2020-05-08T17:24:00-04:00',
            'Sub Type': 'Sell to Close',
            'Action': 'SELL_TO_CLOSE',
            'Symbol': 'SVXY  200619P00030000',
            'Instrument Type': 'Equity Option',
            'Description': 'Sold 3 SVXY 06/19/20 Put 30.00 @ 0.81',
            'Value': '243.0',
            'Quantity': '3',
            'Average Price': '81',
            'Commissions': '0.00',
            'Fees': '-0.44',
            'Multiplier': '100',
            'Root Symbol': 'SVXY',
            'Underlying Symbol': 'SVXY',
            'Expiration Date': '06/19/20',
            'Strike Price': '30',
            'Call or Put': 'PUT',
            'Order #': 'ORDER-1',
        }),
        stock_trade(**{
            'Date': '2020-05-07T14:00:00-04:00',
            'Sub Type': 'Sell to Open',
            'Action': 'SELL_TO_OPEN',
            'Symbol': 'SVXY  200619P00030000',
            'Instrument Type': 'Equity Option',
            'Description': 'Sold 3 SVXY 06/19/20 Put 30.00 @ 0.80',
            'Value': '240.0',
            'Quantity': '3',
            'Average Price': '80',
            'Commissions': '0.00',
            'Fees': '-1.15',
            'Multiplier': '100',
            'Root Symbol': 'SVXY',
            'Underlying Symbol': 'SVXY',
            'Expiration Date': '06/19/20',
            'Strike Price': '30',
            'Call or Put': 'PUT',
            'Order #': 'ORDER-2',
        }),
    ])

    hist = History.fromFile(csv_path)

    assert hist["Date/Time"].is_monotonic_increasing
    assert hist["Transaction Subcode"].iloc[0] == "Sell to Open"
    assert hist["Transaction Subcode"].iloc[1] == "Sell to Close"


def test_new_format_accepts_fractional_iso_date_and_normalizes_option(tmp_path):
    csv_path = tmp_path / "fractional_date.csv"
    write_broker_csv(csv_path, [stock_trade(**{
        'Date': '2024-01-02T03:04:05.123456Z',
        'Description': 'Bought option',
        'Symbol': 'SYN  240119C01000000',
        'Instrument Type': 'Equity Option',
        'Expiration Date': '01/19/24',
        'Strike Price': '1,000',
        'Average Price': '125',
        'Call or Put': 'call',
        'Multiplier': '100',
    })])

    history = History.fromFile(csv_path)

    assert history.loc[0, "Date/Time"] == pd.Timestamp("2024-01-02 03:04:05.123456")
    assert history.loc[0, "Call/Put"] == "C"
    assert history.loc[0, "Strike"] == 1000
    assert history.loc[0, "Price"] == 1.25
