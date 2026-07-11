import pandas as pd
from datetime import datetime
from tastyworksTaxes.money import convert_usd_to_eur


class History(pd.DataFrame):

    _NEW_FORMAT_REQUIRED_COLUMNS = {
        'Date', 'Type', 'Sub Type', 'Value', 'Description',
    }
    _NEW_FORMAT_DEFAULTS = {
        'Symbol': '',
        'Action': '',
        'Quantity': 0,
        'Expiration Date': '',
        'Strike Price': 0,
        'Call or Put': '',
        'Average Price': 0,
        'Commissions': 0,
        'Fees': 0,
    }
    _INTERNAL_FORMAT_REQUIRED_COLUMNS = {
        'Date/Time', 'Transaction Code', 'Transaction Subcode', 'Symbol',
        'Buy/Sell', 'Open/Close', 'Quantity', 'Expiration Date', 'Strike',
        'Call/Put', 'Price', 'Fees', 'Amount', 'Description',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def fromFile(cls, path):
        df_raw = pd.read_csv(path)
        df = cls._load_supported_schema(df_raw)

        df = History(df)
        df.sort_values('Date/Time', inplace=True)
        df.reset_index(drop=True, inplace=True)
        df.addEuroConversion()
        df._selfTest()
        return df

    @staticmethod
    def _load_supported_schema(df: pd.DataFrame) -> pd.DataFrame:
        if History._is_new_format(df):
            return History._transform(df)
        if History._is_internal_format(df):
            return History._normalize_internal(df)

        raise ValueError(
            "Unsupported CSV schema. Expected either new TastyTrade export columns "
            "('Date', 'Type', 'Sub Type', 'Value', ...) or normalized internal columns "
            "('Date/Time', 'Transaction Code', 'Transaction Subcode', 'Amount', ...). "
            f"Found columns: {list(df.columns)}"
        )

    @staticmethod
    def _is_new_format(df: pd.DataFrame) -> bool:
        return History._NEW_FORMAT_REQUIRED_COLUMNS.issubset(df.columns)

    @staticmethod
    def _is_internal_format(df: pd.DataFrame) -> bool:
        return History._INTERNAL_FORMAT_REQUIRED_COLUMNS.issubset(df.columns)

    @staticmethod
    def _numeric_column(series: pd.Series, column_name: str) -> pd.Series:
        raw = series.copy()
        text = raw.astype(str).str.strip()
        blank = raw.isna() | text.isin(['', '--', 'nan'])
        cleaned = text.str.replace(',', '', regex=False)
        parsed = pd.to_numeric(cleaned.where(~blank, '0'), errors='coerce')

        invalid = parsed.isna() & ~blank
        if invalid.any():
            bad_values = raw.loc[invalid].tolist()
            raise ValueError(
                f"Failed to parse numeric values in normalized CSV column "
                f"'{column_name}': {bad_values}"
            )

        return parsed

    @staticmethod
    def _normalize_internal(df: pd.DataFrame) -> pd.DataFrame:
        internal_df = df.copy()

        internal_df['Date/Time'] = pd.to_datetime(internal_df['Date/Time'], errors='coerce')
        if internal_df['Date/Time'].isna().any():
            bad_values = df.loc[internal_df['Date/Time'].isna(), 'Date/Time'].tolist()
            raise ValueError(f"Failed to parse Date/Time values in normalized CSV: {bad_values}")

        raw_expiration = internal_df['Expiration Date'].copy()
        internal_df['Expiration Date'] = pd.to_datetime(raw_expiration, errors='coerce')

        has_option_type = internal_df['Call/Put'].astype(str).str.strip().isin(['C', 'P'])
        invalid_option_expiry = has_option_type & internal_df['Expiration Date'].isna()
        if invalid_option_expiry.any():
            bad_values = raw_expiration.loc[invalid_option_expiry].tolist()
            raise ValueError(
                "Failed to parse Expiration Date values for option rows in "
                f"normalized CSV: {bad_values}"
            )

        for column in ['Amount', 'Fees', 'Quantity', 'Strike', 'Price']:
            internal_df[column] = History._numeric_column(internal_df[column], column)

        return internal_df

    @staticmethod
    def _transform(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for column, default in History._NEW_FORMAT_DEFAULTS.items():
            if column not in df:
                df[column] = default

        internal_df = pd.DataFrame()

        def parse_date(date_str):
            if pd.isna(date_str):
                raise ValueError("Failed to parse date: value is missing")
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S%z')
                return dt.replace(tzinfo=None)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Failed to parse date '{date_str}': {e}")

        internal_df['Date/Time'] = df['Date'].apply(parse_date)
        internal_df['Transaction Code'] = df['Type']
        internal_df['Transaction Subcode'] = df['Sub Type']
        def parse_symbol(symbol):
            if pd.isna(symbol):
                return ''
            parts = str(symbol).strip().split()
            return parts[0] if parts else ''

        internal_df['Symbol'] = df['Symbol'].apply(parse_symbol)

        def extract_buy_sell(row):
            sub_type = str(row.get('Sub Type', ''))
            action = str(row.get('Action', ''))
            if 'Buy' in sub_type:
                return 'Buy'
            elif 'Sell' in sub_type:
                return 'Sell'
            elif 'BUY' in action:
                return 'Buy'
            elif 'SELL' in action:
                return 'Sell'
            return ''

        internal_df['Buy/Sell'] = df.apply(extract_buy_sell, axis=1)
        internal_df['Open/Close'] = df['Action'].apply(
            lambda x: str(x).split('_TO_')[-1].capitalize() if pd.notna(x) and '_TO_' in str(x) else '')
        internal_df['Quantity'] = History._numeric_column(df['Quantity'], 'Quantity')
        raw_expiration = df['Expiration Date']
        internal_df['Expiration Date'] = pd.to_datetime(
            raw_expiration, format='%m/%d/%y', errors='coerce')

        def parse_strike(strike):
            if pd.isna(strike) or strike == '':
                return 0.0
            try:
                return float(strike)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Failed to parse strike '{strike}': {e}")

        internal_df['Strike'] = df['Strike Price'].apply(parse_strike) if 'Strike Price' in df else 0.0

        def format_call_put(cp):
            if pd.notna(cp) and cp not in ('', '--'):
                return str(cp)[0]
            return ''

        internal_df['Call/Put'] = df['Call or Put'].apply(format_call_put) if 'Call or Put' in df else ''
        has_option_type = internal_df['Call/Put'].isin(['C', 'P'])
        invalid_option_expiry = has_option_type & internal_df['Expiration Date'].isna()
        if invalid_option_expiry.any():
            bad_values = raw_expiration.loc[invalid_option_expiry].tolist()
            raise ValueError(
                "Failed to parse Expiration Date values for option rows in "
                f"TastyTrade CSV: {bad_values}"
            )

        def parse_price(row):
            price = row.get('Average Price', None)
            if pd.isna(price) or price == '--' or price == 0 or price == '':
                return 0.0
            try:
                price_float = float(str(price).replace(',', ''))
                symbol = row.get('Symbol', '')
                is_option = len(str(symbol).split()) > 1
                if is_option:
                    return price_float / 100
                else:
                    return price_float
            except (ValueError, TypeError) as e:
                raise ValueError(f"Failed to parse price '{price}' for symbol '{row.get('Symbol', '')}': {e}")

        internal_df['Price'] = df.apply(parse_price, axis=1)

        def calc_fees(row):
            commissions = row.get('Commissions', 0)
            fees = row.get('Fees', 0)
            try:
                comm_val = abs(float(str(commissions).replace(',', ''))) if commissions != '--' and pd.notna(commissions) else 0
                fees_val = abs(float(str(fees).replace(',', ''))) if fees != '--' and pd.notna(fees) else 0
                return comm_val + fees_val
            except (ValueError, TypeError) as e:
                raise ValueError(f"Failed to parse fees - commissions: '{commissions}', fees: '{fees}': {e}")

        internal_df['Fees'] = df.apply(calc_fees, axis=1)

        def parse_amount(amount):
            if pd.isna(amount):
                return 0.0
            try:
                return float(str(amount).replace(',', ''))
            except (ValueError, TypeError) as e:
                raise ValueError(f"Failed to parse amount '{amount}': {e}")

        internal_df['Amount'] = df['Value'].apply(parse_amount)
        internal_df['Description'] = df['Description']

        return internal_df

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
