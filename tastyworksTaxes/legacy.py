from datetime import datetime
import argparse
import logging
from typing import Dict, List
import pandas as pd

# tastyworks only exports 1000 rows at a time.

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


def parse_date(date_str):
    if isinstance(date_str, pd.Series):
        return date_str.apply(lambda x: datetime.strptime(x, '%Y-%m-%dT%H:%M:%S%z').strftime('%m/%d/%Y %I:%M %p'))
    return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S%z').strftime('%m/%d/%Y %I:%M %p')


def extract_symbol(symbol) -> str:
    if pd.isna(symbol) or symbol == '':
        return ''
    parts = str(symbol).split()
    return parts[0] if parts else ''


def determine_buy_sell(sub_type: str) -> str:
    if 'Buy' in sub_type:
        return 'Buy'
    elif 'Sell' in sub_type:
        return 'Sell'
    return ''


def determine_open_close(action: str) -> str:
    return action.split('_TO_')[-1].capitalize() if pd.notna(action) else ''


def format_strike_price(strike) -> str:
    if pd.isna(strike) or strike == '':
        return ''
    try:
        return f"{float(strike):.0f}"
    except ValueError:
        return str(strike)


def is_option(symbol: str) -> bool:
    return len(str(symbol).split()) > 1


def format_price(price, is_option: bool) -> str:
    if pd.isna(price) or price == '--' or price == 0:
        return ''
    price_str = str(price).replace(',', '')
    if is_option:
        option_price = float(price_str) / 100
        return f"{option_price:.5f}".rstrip('0').rstrip('.')
    return price_str.rstrip('0').rstrip('.')


def format_fees(fees: float) -> str:
    if pd.isna(fees) or fees == '--' or fees == 0:
        return '0.00'
    fee_float = abs(float(str(fees).replace(',', '')))
    return f"{fee_float:.3f}"


def format_amount(amount) -> str:
    if pd.isna(amount):
        return ''
    amount_float = float(str(amount).replace(',', ''))
    return f"{amount_float:.0f}" if amount_float.is_integer() else f"{amount_float:.2f}"


def convert_to_legacy_format(df: pd.DataFrame) -> pd.DataFrame:
    legacy_df = pd.DataFrame()

    legacy_df['Date/Time'] = df['Date'].apply(parse_date)
    legacy_df['Transaction Code'] = df['Type']
    legacy_df['Transaction Subcode'] = df['Sub Type']
    legacy_df['Symbol'] = df['Symbol'].apply(
        extract_symbol) if 'Symbol' in df else ''
    legacy_df['Buy/Sell'] = df['Sub Type'].apply(determine_buy_sell)
    legacy_df['Open/Close'] = df['Action'].apply(
        determine_open_close) if 'Action' in df else ''
    legacy_df['Quantity'] = df['Quantity'] if 'Quantity' in df else 0
    legacy_df['Expiration Date'] = pd.to_datetime(
        df['Expiration Date'], format='%m/%d/%y', errors='coerce').dt.strftime('%m/%d/%Y') if 'Expiration Date' in df else ''
    legacy_df['Strike'] = df['Strike Price'].apply(
        format_strike_price) if 'Strike Price' in df else ''
    legacy_df['Call/Put'] = df['Call or Put'].str[0] if 'Call or Put' in df else ''

    # Handle 'Price' calculation more gracefully
    if 'Average Price' in df.columns:
        legacy_df['Price'] = df.apply(
            lambda row: format_price(
                row['Average Price'], is_option(row.get('Symbol', '')))
            if row['Type'] != 'Receive Deliver' else '',
            axis=1
        )
    else:
        legacy_df['Price'] = ''

    legacy_df['Fees'] = df['Fees'].apply(format_fees)
    legacy_df['Amount'] = df['Value'].apply(format_amount)
    legacy_df['Description'] = df['Description']
    legacy_df['Account Reference'] = 'Individual...39'

    # Handle special case for "Receive Deliver, Sell to Open" transactions
    mask = (legacy_df['Transaction Code'] == 'Receive Deliver') & (
        legacy_df['Transaction Subcode'] == 'Sell to Open')
    if 'Average Price' in df.columns:
        legacy_df.loc[mask, 'Price'] = df.loc[mask, 'Average Price'].apply(
            lambda x: format_price(x, False) if pd.notnull(x) else '')

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
    logger.warning(
        "There is an factor of 8 in the fees. The newly exported data from Tastyworks has this offset compared to my old legacy format data.")
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
