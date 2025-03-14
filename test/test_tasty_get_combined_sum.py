import pytest
import pandas as pd

from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.money import Money

class TestTastyGetCombinedSum:
    @pytest.fixture
    def sample_df(self):
        data = [
            {
                'Amount': 1420.0,
                'AmountEuro': 1154.28,
                'Symbol': 'LFIN',
                'callPutStock': 'PositionType.call',
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
                'callPutStock': 'PositionType.call',
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
                'callPutStock': 'PositionType.stock',
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
                'callPutStock': 'PositionType.stock',
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

    def test_getCombinedSum_returns_correct_sums(self, sample_df):
        t = Tasty()
        result = t.getCombinedSum(sample_df)
        
        assert isinstance(result, Money)
        assert result.usd == -2518.0
        assert round(result.eur, 2) == -2059.88
        
    def test_getCombinedSum_minimal_data(self):
        t = Tasty()
        data = [
            {'Amount': 1458.0, 'AmountEuro': 1186.95},
            {'Amount': -2676.0, 'AmountEuro': -2182.65}
        ]
        
        result = t.getCombinedSum(pd.DataFrame(data))
        assert result.usd == -1218.0
        assert result.eur == -995.7
