import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from tastyworksTaxes.money import convert_usd_to_eur


class History(pd.DataFrame):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def fromFile(cls, path):
        """ initializes a History object / pd df from a filesystem path
        """

        df = History(pd.read_csv(path))
        df['Date/Time'] = pd.to_datetime(df['Date/Time'],
                                         format='%m/%d/%Y %I:%M %p')
        df['Expiration Date'] = pd.to_datetime(
            df['Expiration Date'], format='%m/%d/%Y')
        df.addEuroConversion()
        df._selfTest()
        df.drop(columns="Account Reference", inplace=True)
        return df


    def addEuroConversion(self):
        """ adds a new column called "AmountEuro" and "FeesEuro" to the dataframe
        """
        self['Date/Time'] = pd.to_datetime(self['Date/Time'])
        self['Expiration Date'] = pd.to_datetime(self['Expiration Date'])
        self['AmountEuro'] = self.apply(lambda x: convert_usd_to_eur(
            x['Amount'], x['Date/Time']), axis=1)
        self['FeesEuro'] = self.apply(lambda x: convert_usd_to_eur(
            x['Fees'], x['Date/Time']), axis=1)

    def _selfTest(self):
        if "Date/Time" not in self.columns:
            raise ValueError(
                "Couldn't find the first column labeled Date/Time in the csv file")


    # _merge method removed - was problematic due to non-unique timestamps
    # Use manual CSV concatenation: ls -r 20*.csv | tr '\n' '\0' |xargs -0 cat > merged.csv
