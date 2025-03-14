import pytest
import pandas as pd
from pathlib import Path
from glob import glob
from tastyworksTaxes.history import History

def test_fromFile():
    t = History.fromFile("test/merged.csv")
    assert isinstance(t, History)
    assert 'Date/Time' in t.columns
    assert 'Expiration Date' in t.columns
    assert 'AmountEuro' in t.columns
    assert 'FeesEuro' in t.columns

def test_addEuroConversion():
    t = History.fromFile("test/merged.csv")
    assert "AmountEuro" in t.columns
    assert "FeesEuro" in t.columns

def test_merge():
    try:
        paths = [Path(p) for p in glob(str(Path('test/20*.csv').expanduser()))]
        merged = History._merge(paths)
        assert isinstance(merged, pd.DataFrame)
        merged.to_csv("test/temp.csv", index=None, date_format='%m/%d/%Y %I:%M %p')
        assert Path("test/temp.csv").exists()
    finally:
        # Clean up temp file
        temp_path = Path("test/temp.csv")
        if temp_path.exists():
            temp_path.unlink()
