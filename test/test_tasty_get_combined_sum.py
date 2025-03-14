import pytest
import pandas as pd

from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.money import Money
from tastyworksTaxes.position import PositionType

class TestTastyFinancialCalculations:
    @pytest.fixture
    def sample_df(self):
        data = [
            {
                'Amount': 1420.0,
                'AmountEuro': 1154.28,
                'Symbol': 'LFIN',
                'callPutStock': PositionType.call,
                'Closing Date': '2018-03-19 22:00:00',
                'worthlessExpiry': False,
                'Expiry': '2018-06-15',
                'Strike': 30.0,
                'Fees': 2.324,
                'FeesEuro': 1.89,
                'Opening Date': '2018-03-12 17:08:00',
                'Quantity': -2
            },
            {
                'Amount': 1458.0,
                'AmountEuro': 1186.95,
                'Symbol': 'LFIN',
                'callPutStock': PositionType.call,
                'Closing Date': '2018-03-21 18:42:00',
                'worthlessExpiry': False,
                'Expiry': '2018-06-15',
                'Strike': 40.0,
                'Fees': 1.32,
                'FeesEuro': 1.07,
                'Opening Date': '2018-03-12 17:08:00',
                'Quantity': 1
            },
            {
                'Amount': -2676.0,
                'AmountEuro': -2182.65,
                'Symbol': 'LFIN',
                'callPutStock': PositionType.stock,
                'Closing Date': '2018-03-21 18:42:00',
                'worthlessExpiry': False,
                'Expiry': '',
                'Strike': '',
                'Fees': 2.662,
                'FeesEuro': 2.16,
                'Opening Date': '2018-03-19 22:00:00',
                'Quantity': -100
            },
            {
                'Amount': -2720.0,
                'AmountEuro': -2218.46,
                'Symbol': 'LFIN',
                'callPutStock': PositionType.stock,
                'Closing Date': '2018-03-21 19:59:00',
                'worthlessExpiry': False,
                'Expiry': '',
                'Strike': '',
                'Fees': 2.662,
                'FeesEuro': 2.16,
                'Opening Date': '2018-03-19 22:00:00',
                'Quantity': -100
            }
        ]
        return pd.DataFrame(data)

    @pytest.mark.parametrize("method_name,expected_usd,expected_eur", [
        ("getCombinedSum", -2518.0, -2059.88),
        ("getStockSum", -5396.0, -4401.11),
        ("getOptionSum", 2878.0, 2341.23)
    ])
    def test_money_calculations_with_sample_df(self, method_name, expected_usd, expected_eur, sample_df):
        t = Tasty()
        method = getattr(t, method_name)
        result = method(sample_df)
        
        assert isinstance(result, Money)
        assert result.usd == expected_usd
        assert round(result.eur, 2) == expected_eur
        
    def test_getCombinedSum_minimal_data(self):
        t = Tasty()
        data = [
            {'Amount': 1458.0, 'AmountEuro': 1186.95},
            {'Amount': -2676.0, 'AmountEuro': -2182.65}
        ]
        
        result = t.getCombinedSum(pd.DataFrame(data))
        assert result.usd == -1218.0
        assert result.eur == -995.7
        
    def test_getLongOptionsProfits(self):
        t = Tasty()
        data = [
            {
                'Amount': 1457.0,
                'AmountEuro': 1186.14,
                'callPutStock': PositionType.call,
                'Quantity': 1,
                'worthlessExpiry': False
            },
            {
                'Amount': 1520.0,
                'AmountEuro': 1236.45,
                'callPutStock': PositionType.put,
                'Quantity': 2,
                'worthlessExpiry': False
            }
        ]
        
        result = t.getLongOptionsProfits(pd.DataFrame(data))
        assert result.usd == 2977.0
        assert round(result.eur, 2) == 2422.59
        
    def test_getLongOptionLosses(self):
        t = Tasty()
        data = [
            {
                'Amount': -193.0,
                'AmountEuro': -157.05,
                'callPutStock': PositionType.put,
                'Quantity': 2,
                'worthlessExpiry': False
            },
            {
                'Amount': 245.0,
                'AmountEuro': 199.35,
                'callPutStock': PositionType.call,
                'Quantity': 1,
                'worthlessExpiry': False
            },
            {
                'Amount': -702.0,
                'AmountEuro': -571.20,
                'callPutStock': PositionType.call,
                'Quantity': 2,
                'worthlessExpiry': True
            }
        ]
        
        result = t.getLongOptionLosses(pd.DataFrame(data))
        assert result.usd == -193.0
        assert round(result.eur, 2) == -157.05
        
    def test_getLongOptionTotalLosses(self):
        t = Tasty()
        data = [
            {
                'Amount': -193.0,
                'AmountEuro': -157.05,
                'callPutStock': PositionType.put,
                'Quantity': 2,
                'worthlessExpiry': False
            },
            {
                'Amount': -702.0,
                'AmountEuro': -571.20,
                'callPutStock': PositionType.call,
                'Quantity': 2,
                'worthlessExpiry': True
            }
        ]
        
        result = t.getLongOptionTotalLosses(pd.DataFrame(data))
        assert result.usd == -702.0
        assert round(result.eur, 2) == -571.20
        
    def test_getShortOptionProfits(self):
        t = Tasty()
        data = [
            {
                'Amount': 145.0,
                'AmountEuro': 118.05,
                'callPutStock': PositionType.call,
                'Quantity': -1,
                'worthlessExpiry': False
            },
            {
                'Amount': -55.0,
                'AmountEuro': -44.75,
                'callPutStock': PositionType.put,
                'Quantity': -2,
                'worthlessExpiry': False
            }
        ]
        
        result = t.getShortOptionProfits(pd.DataFrame(data))
        assert result.usd == 145.0
        assert round(result.eur, 2) == 118.05
        
    def test_getShortOptionLosses(self):
        t = Tasty()
        data = [
            {
                'Amount': 145.0,
                'AmountEuro': 118.05,
                'callPutStock': PositionType.call,
                'Quantity': -1,
                'worthlessExpiry': False
            },
            {
                'Amount': -55.0,
                'AmountEuro': -44.75,
                'callPutStock': PositionType.put,
                'Quantity': -2,
                'worthlessExpiry': False
            }
        ]
        
        result = t.getShortOptionLosses(pd.DataFrame(data))
        assert result.usd == -55.0
        assert round(result.eur, 2) == -44.75
        
    def test_getOptionDifferential(self):
        t = Tasty()
        data = [
            {
                'Amount': 145.0,
                'AmountEuro': 118.05,
                'callPutStock': PositionType.call,
                'Quantity': -1
            },
            {
                'Amount': -100.0,
                'AmountEuro': -81.45,
                'callPutStock': PositionType.put,
                'Quantity': 2
            }
        ]
        
        result = t.getOptionDifferential(pd.DataFrame(data))
        assert result.usd == 100.0
        assert round(result.eur, 2) == 81.45
        
    def test_getStockLoss(self):
        t = Tasty()
        data = [
            {
                'Amount': 350.0,
                'AmountEuro': 284.90,
                'callPutStock': PositionType.stock
            },
            {
                'Amount': -200.0,
                'AmountEuro': -162.85,
                'callPutStock': PositionType.stock
            }
        ]
        
        result = t.getStockLoss(pd.DataFrame(data))
        assert result.usd == -200.0
        assert round(result.eur, 2) == -162.85
        
    @pytest.mark.parametrize("fee_method,expected_usd,expected_eur", [
        ("getStockFees", 2.60, 2.12),
        ("getOtherFees", 4.0, 3.25)
    ])
    def test_fee_calculations(self, fee_method, expected_usd, expected_eur):
        t = Tasty()
        data = [
            {
                'Amount': 350.0,
                'AmountEuro': 284.90,
                'callPutStock': PositionType.stock,
                'Fees': 1.25,
                'FeesEuro': 1.02
            },
            {
                'Amount': 145.0,
                'AmountEuro': 118.05,
                'callPutStock': PositionType.call,
                'Fees': 2.25,
                'FeesEuro': 1.83
            },
            {
                'Amount': -200.0,
                'AmountEuro': -162.85,
                'callPutStock': PositionType.stock,
                'Fees': 1.35,
                'FeesEuro': 1.10
            },
            {
                'Amount': -100.0,
                'AmountEuro': -81.45,
                'callPutStock': PositionType.put,
                'Fees': 1.75,
                'FeesEuro': 1.42
            }
        ]
        
        method = getattr(t, fee_method)
        result = method(pd.DataFrame(data))
        assert result.usd == expected_usd
        assert round(result.eur, 2) == expected_eur
        
    def test_getStockProfits(self):
        t = Tasty()
        data = [
            {
                'Amount': 350.0,
                'AmountEuro': 284.90,
                'callPutStock': PositionType.stock
            },
            {
                'Amount': -200.0,
                'AmountEuro': -162.85,
                'callPutStock': PositionType.stock
            }
        ]
        
        result = t.getStockProfits(pd.DataFrame(data))
        assert result.usd == 350.0
        assert round(result.eur, 2) == 284.90
        
    def test_getFeesSum(self):
        t = Tasty()
        data = [
            {
                'Fees': 1.25,
                'FeesEuro': 1.02
            },
            {
                'Fees': 2.25,
                'FeesEuro': 1.83
            },
            {
                'Fees': 1.75,
                'FeesEuro': 1.42
            }
        ]
        
        result = t.getFeesSum(pd.DataFrame(data))
        assert result.usd == 5.25
        assert round(result.eur, 2) == 4.27
