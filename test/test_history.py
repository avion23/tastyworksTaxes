import pytest
import pandas as pd
import tempfile
import os
from pathlib import Path
from tastyworksTaxes.history import History

# Skip tests that require the full dataset if it's not available (CI environment)
FULL_DATASET = Path("test/transactions_2018_to_2025.csv")


@pytest.mark.skipif(
    not FULL_DATASET.exists(), reason="Full dataset not available (CI environment)"
)
def test_fromFile():
    t = History.fromFile(FULL_DATASET)
    assert isinstance(t, History)
    assert "Date/Time" in t.columns
    assert "Expiration Date" in t.columns
    assert "AmountEuro" in t.columns
    assert "FeesEuro" in t.columns


@pytest.mark.skipif(
    not FULL_DATASET.exists(), reason="Full dataset not available (CI environment)"
)
def test_addEuroConversion():
    t = History.fromFile(FULL_DATASET)
    assert "AmountEuro" in t.columns
    assert "FeesEuro" in t.columns


def test_new_format_csv_sorting():
    test_data = {
        "Date": ["2020-05-08T17:24:00-04:00", "2020-05-07T14:00:00-04:00"],
        "Type": ["Trade", "Trade"],
        "Sub Type": ["Sell to Close", "Sell to Open"],
        "Symbol": ["SVXY  200619P00030000", "SVXY  200619P00030000"],
        "Quantity": [3, 3],
        "Value": ["243.0", "240.0"],
        "Average Price": [81, 80],
        "Fees": [-0.44, -1.15],
        "Expiration Date": ["06/19/20", "06/19/20"],
        "Strike Price": [30, 30],
        "Call or Put": ["PUT", "PUT"],
        "Description": [
            "Sold 3 SVXY 06/19/20 Put 30.00 @ 0.81",
            "Sold 3 SVXY 06/19/20 Put 30.00 @ 0.80",
        ],
        "Action": ["SELL_TO_CLOSE", "SELL_TO_OPEN"],
    }

    temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
    df = pd.DataFrame(test_data)
    df.to_csv(temp_file.name, index=False)
    temp_file.close()

    try:
        hist = History.fromFile(temp_file.name)
        assert hist["Date/Time"].is_monotonic_increasing
        assert hist["Transaction Subcode"].iloc[0] == "Sell to Open"
        assert hist["Transaction Subcode"].iloc[1] == "Sell to Close"
    finally:
        os.unlink(temp_file.name)
