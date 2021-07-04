
import pandas as pd
from currency_converter import CurrencyConverter


class History(pd.DataFrame):

    def __init__(self, *args, **kwargs):
        """ reads in a tastyworks transaction history file
        
        """
        super().__init__(*args, **kwargs)
        self._selfTest()

    @classmethod
    def fromFile(cls, path):
        """ initializes a History object / pd df from a filesystem path

        >>> t = History.fromFile("test/merged.csv")
        """ 
        df = History(pd.read_csv(path))
        df['Date/Time']=pd.to_datetime(df['Date/Time'], format='%m/%d/%Y %I:%M %p')
        df['Expiration Date']=pd.to_datetime(df['Expiration Date'], format='%m/%d/%Y')
        df.addEuroConversion()
        return df


    def addEuroConversion(self):
        """ adds a new column called "AmountEuro" and "FeesEuro" to the dataframe


        >>> t = History.fromFile("test/merged.csv")
        >>> t.addEuroConversion()
        >>> "AmountEuro" in t.columns
        True
        >>> "FeesEuro" in t.columns
        True
        """
        c = CurrencyConverter(fallback_on_missing_rate=True)
        self['AmountEuro'] = self.apply(lambda x: c.convert(x['Amount'], 'USD', 'EUR', date=x['Date/Time']), axis=1)
        self['FeesEuro'] = self.apply(lambda x: c.convert(x['Fees'], 'USD', 'EUR', date=x['Date/Time']), axis=1)


    def _selfTest(self):
        if "Date/Time" not in self.columns: 
            raise ValueError("Couldn't find the first column labeled Date/Time in the csv file")


if __name__ == "__main__":
    import doctest
    doctest.testmod()