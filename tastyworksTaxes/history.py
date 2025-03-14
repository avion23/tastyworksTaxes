import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from currency_converter import CurrencyConverter
from pathlib import Path
from glob import glob


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
        c = CurrencyConverter(fallback_on_missing_rate=True,
                              fallback_on_wrong_date=True)
        self['Date/Time'] = pd.to_datetime(self['Date/Time'])
        self['Expiration Date'] = pd.to_datetime(self['Expiration Date'])
        self['AmountEuro'] = self.apply(lambda x: c.convert(
            x['Amount'], 'USD', 'EUR', date=x['Date/Time']), axis=1)
        self['FeesEuro'] = self.apply(lambda x: c.convert(
            x['Fees'], 'USD', 'EUR', date=x['Date/Time']), axis=1)

    def _selfTest(self):
        if "Date/Time" not in self.columns:
            raise ValueError(
                "Couldn't find the first column labeled Date/Time in the csv file")

        if not self["Date/Time"].is_monotonic_decreasing:
            raise ValueError(
                "The 'Date/Time' column is not monotonically decreasing. We can't sort the file because the timestamps are not unique. Please do it manually.")

    @classmethod
    def _merge(cls, pathIn):
        """ 
        some test code to assemble test data. Merges multiple tastyworks csv files into one and keeps order. Doesn't remove duplicates

        ### Warning ### I think I messed up here and this doesn't work. In the end, I merged the files manually
        - the csv files have duplicate entries because the time only has minute resolution
        - you can't sort it because, again, only minute resolution. That leads to close before open
        I've used
            ls -r 20*.csv | tr '\n' '\0' |xargs -0 cat > merged2.csv
        in a shell and removed the duplicated headers manually
        """
        h = []
        for csvfile in pathIn:
            temp = pd.read_csv(csvfile, index_col=False)
            temp["Date/Time"] = pd.to_datetime(temp['Date/Time'],
                                               format='%m/%d/%Y %I:%M %p')
            h.append(temp)
        result = pd.concat(h, ignore_index=True)
        result = result.sort_values("Date/Time", ascending=True)
        return result[::-1]
