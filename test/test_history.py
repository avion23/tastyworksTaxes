import pytest
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


