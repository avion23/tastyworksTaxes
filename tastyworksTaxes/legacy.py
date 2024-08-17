from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo
from datetime import datetime
import argparse
import logging
from typing import Dict, List, Union
import pandas as pd

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

NEW_TO_LEGACY_MAPPING: Dict[str, str] = {
    'Date': 'Date/Time',
    'Type': 'Transaction Code',
    'Sub Type': 'Transaction Subcode',
    'Symbol': 'Symbol',
    'Expiration Date': 'Expiration Date',
    'Strike Price': 'Strike',
    'Call or Put': 'Call/Put',
    'Average Price': 'Price',
    'Fees': 'Fees',
    'Value': 'Amount',
    'Description': 'Description',
    'Quantity': 'Quantity'
}

ADDITIONAL_LEGACY_FIELDS: List[str] = [
    'Buy/Sell', 'Open/Close', 'Account Reference']

def format_number(value, decimals: int = 2, include_commas: bool = False) -> str:
    if pd.isna(value) or value == '':
        return ''
    try:
        num = Decimal(str(value)).quantize(
            Decimal(f'0.{"0" * decimals}'), rounding=ROUND_HALF_UP)
        formatted = f'{abs(num):,}' if include_commas else f'{abs(num)}'
        return f'-{formatted}' if num < 0 else formatted
    except:
        return str(value)

def parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S%z')

def format_date(dt: datetime) -> str:
    return dt.strftime('%m/%d/%Y %-I:%M %p')

def convert_to_legacy_format(df: pd.DataFrame) -> pd.DataFrame:
    legacy_df = pd.DataFrame()

    legacy_df['Date/Time'] = df['Date'].apply(parse_date).apply(format_date)
    legacy_df['Transaction Code'] = df['Type']
    legacy_df['Transaction Subcode'] = df['Sub Type']
    legacy_df['Symbol'] = df['Symbol'].str.split().str[0]
    legacy_df['Buy/Sell'] = df['Action'].str.split(
        '_TO_').str[0].str.capitalize()
    legacy_df['Open/Close'] = df['Action'].str.split(
        '_TO_').str[1].str.capitalize()
    legacy_df['Quantity'] = df['Quantity'].fillna(0).astype(int)
    legacy_df['Expiration Date'] = pd.to_datetime(
        df['Expiration Date'], format='%m/%d/%y', errors='coerce').dt.strftime('%m/%d/%Y')
    legacy_df['Strike'] = df['Strike Price'].apply(lambda x: format_number(x, decimals=0) if pd.notna(
        x) and x != '' and float(x).is_integer() else format_number(x, decimals=1))
    legacy_df['Call/Put'] = df['Call or Put'].str[0]
    legacy_df['Price'] = df.apply(lambda row: format_number(row['Average Price'], decimals=2, include_commas=True)
                                  if row['Type'] == 'Trade' else format_number(row['Average Price'], decimals=2), axis=1)
    legacy_df['Fees'] = df['Fees'].apply(
        lambda x: format_number(-float(x), decimals=3) if pd.notna(x) and x != '' else '0.000')
    legacy_df['Amount'] = df['Value'].apply(
        lambda x: format_number(x, decimals=2, include_commas=True))
    legacy_df['Description'] = df['Description']
    legacy_df['Account Reference'] = 'Individual...39'

    column_order = ['Date/Time', 'Transaction Code', 'Transaction Subcode', 'Symbol', 'Buy/Sell', 'Open/Close',
                    'Quantity', 'Expiration Date', 'Strike', 'Call/Put', 'Price', 'Fees', 'Amount', 'Description', 'Account Reference']

    return legacy_df.reindex(columns=column_order)


def convert_csv(input_file: str, output_file: str) -> None:
    logger.info(f"Reading input file: {input_file}")
    df = pd.read_csv(input_file)

    logger.info("Converting to legacy format")
    converted_df = convert_to_legacy_format(df)

    logger.info(f"Writing output file: {output_file}")
    converted_df.to_csv(output_file, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert new TastyTrade CSV to legacy format.")
    parser.add_argument('input_file', help="Path to the input CSV file")
    parser.add_argument('output_file', help="Path to the output CSV file")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    logger.debug("Starting CSV conversion process")
    convert_csv(args.input_file, args.output_file)
    logger.debug("CSV conversion process completed")

if __name__ == "__main__":
    main()
