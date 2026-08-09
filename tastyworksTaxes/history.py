import math
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

import pandas as pd

from tastyworksTaxes.money import convert_usd_to_eur


class History(pd.DataFrame):

    _NEW_FORMAT_COLUMNS = (
        'Date', 'Type', 'Sub Type', 'Action', 'Symbol', 'Instrument Type',
        'Description', 'Value', 'Quantity', 'Average Price', 'Commissions',
        'Fees', 'Multiplier', 'Root Symbol', 'Underlying Symbol',
        'Expiration Date', 'Strike Price', 'Call or Put', 'Order #', 'Currency',
    )
    _NEW_FORMAT_REQUIRED_COLUMNS = set(_NEW_FORMAT_COLUMNS)
    _INTERNAL_FORMAT_REQUIRED_COLUMNS = {
        'Date/Time', 'Transaction Code', 'Transaction Subcode', 'Symbol',
        'Buy/Sell', 'Open/Close', 'Quantity', 'Expiration Date', 'Strike',
        'Call/Put', 'Price', 'Fees', 'Amount', 'Description',
    }
    _US_NUMBER = re.compile(
        r'^[+-]?(?:(?:\d{1,3}(?:,\d{3})+)|\d+)(?:\.\d+)?$'
    )
    _BLANK_NUMBERS = {'', '--'}
    _SOURCE_ROW = '_Source Row'
    _ABSOLUTE_DATE_TIME = '_Absolute Date/Time'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def fromFile(cls, path):
        try:
            df_raw = pd.read_csv(
                path,
                encoding='utf-8-sig',
                dtype=object,
                keep_default_na=False,
            )
        except UnicodeDecodeError as exc:
            raise ValueError(
                f"Input CSV must be UTF-8 encoded (UTF-8 BOM is accepted): {path}"
            ) from exc
        except pd.errors.EmptyDataError as exc:
            raise ValueError(f"Input CSV is empty: {path}") from exc
        except pd.errors.ParserError as exc:
            raise ValueError(f"Input CSV is malformed: {path}: {exc}") from exc

        if df_raw.empty:
            raise ValueError(f"Input CSV contains no transactions: {path}")

        identical_rows = df_raw.duplicated(keep=False)
        if identical_rows.any():
            rows = [int(index) + 2 for index in df_raw.index[identical_rows]]
            raise ValueError(
                "Input CSV contains ambiguous identical rows at CSV lines "
                f"{rows}. Without a distinct broker fill identity, the loader cannot "
                "distinguish a duplicate export row from two legitimate identical fills; review "
                "these rows and remove only confirmed duplicates before accounting"
            )

        df = History(cls._load_supported_schema(df_raw))
        order_key = df['Order #'].fillna('').astype(str)
        df['_Broker Order Sort'] = order_key
        df.sort_values(
            [cls._ABSOLUTE_DATE_TIME, '_Broker Order Sort', cls._SOURCE_ROW],
            kind='stable',
            inplace=True,
        )
        df.drop(columns=['_Broker Order Sort'], inplace=True)
        df.reset_index(drop=True, inplace=True)
        df.addEuroConversion()
        df._selfTest()
        return df

    @staticmethod
    def _load_supported_schema(df: pd.DataFrame) -> pd.DataFrame:
        if History._is_new_format(df):
            return History._transform(df, validate_broker=True)
        if History._is_internal_format(df):
            return History._normalize_internal(df)

        missing_new = sorted(History._NEW_FORMAT_REQUIRED_COLUMNS - set(df.columns))
        missing_internal = sorted(
            History._INTERNAL_FORMAT_REQUIRED_COLUMNS - set(df.columns)
        )
        raise ValueError(
            "Unsupported CSV schema. Expected either the complete 20-column "
            "TastyTrade transaction export or the normalized internal schema. "
            f"Missing new-format columns: {missing_new}; "
            f"missing internal-format columns: {missing_internal}; "
            f"found columns: {list(df.columns)}"
        )

    @staticmethod
    def _is_new_format(df: pd.DataFrame) -> bool:
        return list(df.columns) == list(History._NEW_FORMAT_COLUMNS)

    @staticmethod
    def _is_internal_format(df: pd.DataFrame) -> bool:
        return History._INTERNAL_FORMAT_REQUIRED_COLUMNS.issubset(df.columns)

    @staticmethod
    def _parse_numeric_value(
        value,
        column_name: str,
        *,
        allow_blank: bool = False,
        blank_value: float = 0.0,
    ) -> float:
        text = '' if pd.isna(value) else str(value).strip()
        if text in History._BLANK_NUMBERS:
            if allow_blank:
                return blank_value
            raise ValueError(
                f"Required numeric value is blank in CSV column '{column_name}'"
            )
        if not History._US_NUMBER.fullmatch(text):
            raise ValueError(
                f"Failed to parse numeric values in CSV column '{column_name}': "
                f"invalid US-format value {value!r}"
            )
        try:
            parsed = Decimal(text.replace(',', ''))
        except InvalidOperation as exc:
            raise ValueError(
                f"Invalid numeric value in CSV column '{column_name}': {value!r}"
            ) from exc
        if not parsed.is_finite():
            raise ValueError(
                f"Non-finite numeric value in CSV column '{column_name}': {value!r}"
            )
        converted = float(parsed)
        if not math.isfinite(converted):
            raise ValueError(
                f"Numeric value overflows finite float range in CSV column "
                f"'{column_name}': {value!r}"
            )
        return converted

    @staticmethod
    def _numeric_column(
        series: pd.Series,
        column_name: str,
        *,
        allow_blank: bool = False,
        blank_value: float = 0.0,
    ) -> pd.Series:
        return series.apply(
            lambda value: History._parse_numeric_value(
                value,
                column_name,
                allow_blank=allow_blank,
                blank_value=blank_value,
            )
        )

    @staticmethod
    def _parse_datetime(value, column_name: str, *, require_offset: bool):
        text = str(value).strip()
        if not text:
            raise ValueError(f"Required date value is blank in CSV column '{column_name}'")
        try:
            parsed = datetime.fromisoformat(text.replace('Z', '+00:00'))
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Failed to parse date in CSV column '{column_name}': {value!r}"
            ) from exc
        if require_offset and parsed.tzinfo is None:
            raise ValueError(
                f"Failed to parse date in CSV column '{column_name}': "
                "timezone offset is missing"
            )
        wall_time = parsed.replace(tzinfo=None)
        if parsed.tzinfo is None:
            absolute_time = parsed.replace(tzinfo=timezone.utc)
        else:
            absolute_time = parsed.astimezone(timezone.utc)
        return wall_time, absolute_time

    @staticmethod
    def _validate_usd_currency(series: pd.Series) -> pd.Series:
        normalized = series.astype(str).str.strip().str.upper()
        invalid = normalized != 'USD'
        if invalid.any():
            rows = [int(index) + 2 for index in series.index[invalid]]
            values = sorted(set(normalized.loc[invalid]))
            raise ValueError(
                "Only USD TastyTrade transactions are supported; invalid Currency "
                f"values {values} at CSV lines {rows}"
            )
        return normalized

    @staticmethod
    def _require_nonblank(df: pd.DataFrame, column: str, mask, context: str):
        blank = df[column].astype(str).str.strip().isin(['', '--'])
        invalid = mask & blank
        if invalid.any():
            rows = [int(index) + 2 for index in df.index[invalid]]
            raise ValueError(
                f"Required {context} field '{column}' is blank at CSV lines {rows}"
            )

    @staticmethod
    def _normalize_internal(df: pd.DataFrame) -> pd.DataFrame:
        internal_df = df.copy()
        internal_df[History._SOURCE_ROW] = range(len(internal_df))

        if 'Underlying Symbol' not in internal_df:
            internal_df['Underlying Symbol'] = internal_df['Symbol']
        else:
            missing_underlying = (
                internal_df['Underlying Symbol'].astype(str).str.strip() == ''
            )
            internal_df.loc[missing_underlying, 'Underlying Symbol'] = internal_df.loc[
                missing_underlying, 'Symbol'
            ]
        if 'Multiplier' not in internal_df:
            internal_df['Multiplier'] = '100'
        if 'Order #' not in internal_df:
            internal_df['Order #'] = ''
        else:
            internal_df['Order #'] = internal_df['Order #'].astype(str).str.strip()
        if 'Currency' not in internal_df:
            internal_df['Currency'] = 'USD'
        internal_df['Currency'] = History._validate_usd_currency(
            internal_df['Currency']
        )

        parsed_dates = internal_df['Date/Time'].apply(
            lambda value: History._parse_datetime(
                value, 'Date/Time', require_offset=False
            )
        )
        internal_df['Date/Time'] = parsed_dates.apply(lambda value: value[0])
        internal_df[History._ABSOLUTE_DATE_TIME] = pd.to_datetime(
            parsed_dates.apply(lambda value: value[1]), utc=True
        )

        raw_expiration = internal_df['Expiration Date'].copy()
        internal_df['Expiration Date'] = pd.to_datetime(
            raw_expiration.where(
                ~raw_expiration.astype(str).str.strip().isin(['', '--']), None
            ),
            errors='coerce',
        )

        internal_df['Call/Put'] = (
            internal_df['Call/Put'].astype(str).str.strip().str.upper()
        )
        invalid_call_put = ~internal_df['Call/Put'].isin(['', 'C', 'P'])
        if invalid_call_put.any():
            values = sorted(set(internal_df.loc[invalid_call_put, 'Call/Put']))
            raise ValueError(f"Invalid normalized Call/Put values: {values}")
        has_option_type = internal_df['Call/Put'].isin(['C', 'P'])
        expiration_provided = ~raw_expiration.astype(str).str.strip().isin(['', '--'])

        internal_df['Amount'] = History._numeric_column(
            internal_df['Amount'], 'Amount'
        )
        internal_trade = (
            internal_df['Transaction Code'].astype(str).str.strip() == 'Trade'
        )
        History._require_nonblank(
            internal_df, 'Fees', internal_trade, 'normalized trade'
        )
        internal_df['Fees'] = History._numeric_column(
            internal_df['Fees'], 'Fees', allow_blank=True
        )
        negative_fees = internal_df['Fees'] < 0
        if negative_fees.any():
            rows = [int(index) + 2 for index in internal_df.index[negative_fees]]
            raise ValueError(
                "Normalized internal Fees must be nonnegative costs at CSV lines "
                f"{rows}"
            )
        for column in ['Quantity', 'Strike', 'Price']:
            internal_df[column] = History._numeric_column(
                internal_df[column], column, allow_blank=True
            )
        internal_df['Multiplier'] = History._numeric_column(
            internal_df['Multiplier'], 'Multiplier', allow_blank=True, blank_value=100
        )
        option_metadata = (
            has_option_type | expiration_provided | (internal_df['Strike'] != 0)
        )
        invalid_option_fields = option_metadata & (
            ~has_option_type
            | internal_df['Expiration Date'].isna()
            | (internal_df['Strike'] <= 0)
            | (internal_df['Multiplier'] <= 0)
        )
        if invalid_option_fields.any():
            rows = [
                int(index) + 2
                for index in internal_df.index[invalid_option_fields]
            ]
            raise ValueError(
                "Failed to parse Expiration Date or option fields. Normalized "
                "option rows require C/P, a valid Expiration Date, positive Strike, "
                "and positive Multiplier at CSV lines "
                f"{rows}"
            )
        return internal_df

    @staticmethod
    def _transform(
        df: pd.DataFrame, *, validate_broker: bool = False
    ) -> pd.DataFrame:
        if list(df.columns) != list(History._NEW_FORMAT_COLUMNS):
            raise ValueError(
                "TastyTrade export header must exactly match the ordered 20-column "
                f"schema; expected {list(History._NEW_FORMAT_COLUMNS)}, "
                f"found {list(df.columns)}"
            )

        source_df = df.copy().where(pd.notna(df), '')
        source_df['Currency'] = History._validate_usd_currency(source_df['Currency'])
        source_df[History._SOURCE_ROW] = range(len(source_df))

        recognized_position = source_df['Type'].astype(str).str.strip().isin(
            ['Trade', 'Receive Deliver']
        )
        trade = source_df['Type'].astype(str).str.strip() == 'Trade'
        for column in ['Value', 'Quantity', 'Fees']:
            History._require_nonblank(
                source_df, column, pd.Series(True, index=source_df.index), 'transaction'
            )
        for column in ['Symbol', 'Instrument Type']:
            History._require_nonblank(
                source_df, column, recognized_position, 'position transaction'
            )
        if validate_broker:
            for column in ['Action', 'Average Price', 'Commissions', 'Order #']:
                History._require_nonblank(source_df, column, trade, 'trade')

        instrument = source_df['Instrument Type'].astype(str).str.strip()
        invalid_instrument = recognized_position & ~instrument.isin(
            ['Equity', 'Equity Option']
        )
        if invalid_instrument.any():
            values = sorted(set(instrument.loc[invalid_instrument]))
            raise ValueError(f"Unsupported Instrument Type values: {values}")

        parsed_dates = source_df['Date'].apply(
            lambda value: History._parse_datetime(value, 'Date', require_offset=True)
        )
        internal_df = pd.DataFrame(index=source_df.index)
        internal_df['Date/Time'] = parsed_dates.apply(lambda value: value[0])
        internal_df[History._ABSOLUTE_DATE_TIME] = pd.to_datetime(
            parsed_dates.apply(lambda value: value[1]), utc=True
        )
        internal_df[History._SOURCE_ROW] = source_df[History._SOURCE_ROW]
        internal_df['Order #'] = source_df['Order #'].astype(str).str.strip()
        internal_df['Currency'] = source_df['Currency']
        internal_df['Transaction Code'] = source_df['Type'].astype(str).str.strip()
        internal_df['Transaction Subcode'] = source_df['Sub Type'].astype(str).str.strip()

        def parse_symbol(symbol):
            parts = str(symbol).strip().split()
            return parts[0] if parts else ''

        internal_df['Symbol'] = source_df['Symbol'].apply(parse_symbol)
        underlying = source_df['Underlying Symbol'].where(
            source_df['Underlying Symbol'].astype(str).str.strip() != '',
            source_df['Symbol'],
        )
        internal_df['Underlying Symbol'] = underlying.apply(parse_symbol)
        internal_df['Multiplier'] = History._numeric_column(
            source_df['Multiplier'], 'Multiplier', allow_blank=True, blank_value=0
        )

        def extract_buy_sell(row):
            sub_type = str(row['Sub Type'])
            action = str(row['Action'])
            if 'Buy' in sub_type:
                return 'Buy'
            if 'Sell' in sub_type:
                return 'Sell'
            if 'BUY' in action:
                return 'Buy'
            if 'SELL' in action:
                return 'Sell'
            return ''

        internal_df['Buy/Sell'] = source_df.apply(extract_buy_sell, axis=1)
        internal_df['Open/Close'] = source_df['Action'].apply(
            lambda value: str(value).split('_TO_')[-1].capitalize()
            if '_TO_' in str(value) else ''
        )
        internal_df['Quantity'] = History._numeric_column(
            source_df['Quantity'], 'Quantity'
        )

        raw_expiration = source_df['Expiration Date']
        internal_df['Expiration Date'] = pd.to_datetime(
            raw_expiration.where(
                ~raw_expiration.astype(str).str.strip().isin(['', '--']), None
            ),
            format='%m/%d/%y',
            errors='coerce',
        )
        internal_df['Strike'] = History._numeric_column(
            source_df['Strike Price'], 'Strike Price', allow_blank=True
        )

        call_put = source_df['Call or Put'].astype(str).str.strip().str.upper()
        call_put = call_put.replace({'CALL': 'C', 'PUT': 'P'})
        invalid_call_put = ~call_put.isin(['', '--', 'C', 'P'])
        if invalid_call_put.any():
            values = sorted(set(call_put.loc[invalid_call_put]))
            raise ValueError(f"Invalid Call or Put values: {values}")
        internal_df['Call/Put'] = call_put.replace({'--': ''})

        option = recognized_position & (instrument == 'Equity Option')
        invalid_option_expiry = option & internal_df['Expiration Date'].isna()
        if invalid_option_expiry.any():
            rows = [int(index) + 2 for index in source_df.index[invalid_option_expiry]]
            raise ValueError(
                "Failed to parse Expiration Date for option rows at CSV lines "
                f"{rows}"
            )
        invalid_option_fields = option & (
            ~internal_df['Call/Put'].isin(['C', 'P'])
            | (internal_df['Strike'] <= 0)
            | (internal_df['Multiplier'] <= 0)
        )
        if invalid_option_fields.any():
            rows = [int(index) + 2 for index in source_df.index[invalid_option_fields]]
            raise ValueError(
                "Option rows require Call or Put, positive Strike Price, and positive "
                f"Multiplier at CSV lines {rows}"
            )

        average_price = History._numeric_column(
            source_df['Average Price'], 'Average Price', allow_blank=True
        )
        internal_df['Price'] = average_price.where(~option, average_price / 100)

        commissions = History._numeric_column(
            source_df['Commissions'], 'Commissions', allow_blank=True
        )
        broker_fees = History._numeric_column(source_df['Fees'], 'Fees')
        internal_df['Fees'] = commissions.abs() + broker_fees.abs()
        internal_df['Amount'] = History._numeric_column(source_df['Value'], 'Value')
        internal_df['Description'] = source_df['Description']
        return internal_df

    def addEuroConversion(self):
        """Add EUR amount and fee columns using the local broker wall date."""
        self['Date/Time'] = pd.to_datetime(self['Date/Time'])
        self['Expiration Date'] = pd.to_datetime(self['Expiration Date'])
        self['AmountEuro'] = self.apply(
            lambda row: convert_usd_to_eur(row['Amount'], row['Date/Time']), axis=1
        )
        self['FeesEuro'] = self.apply(
            lambda row: convert_usd_to_eur(row['Fees'], row['Date/Time']), axis=1
        )

    def _selfTest(self):
        if 'Date/Time' not in self.columns:
            raise ValueError("Couldn't find the Date/Time column in the CSV file")
