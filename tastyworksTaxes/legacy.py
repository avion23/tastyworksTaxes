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

LEGACY_TO_NEW_MAPPING: Dict[str, str] = {
    v: k for k, v in NEW_TO_LEGACY_MAPPING.items()}

ADDITIONAL_LEGACY_FIELDS: List[str] = [
    'Buy/Sell', 'Open/Close', 'Account Reference']
ADDITIONAL_NEW_FIELDS: List[str] = [
    'Action', 'Instrument Type', 'Multiplier', 'Root Symbol', 'Underlying Symbol', 'Order #', 'Currency'
]


def safe_map(x: Union[str, float], mapping: Dict[str, str]) -> str:
    """Safely map a value to a new value using the provided mapping."""
    if isinstance(x, str):
        return mapping.get(x.upper(), 'Unknown')
    return 'Unknown'


def convert_to_legacy_format(df: pd.DataFrame) -> pd.DataFrame:
    """Convert the new TastyTrade format to the legacy format."""
    legacy_df = pd.DataFrame()

    # Correct column order
    legacy_columns = [
        'Date/Time', 'Transaction Code', 'Transaction Subcode', 'Symbol',
        'Buy/Sell', 'Open/Close', 'Quantity', 'Expiration Date', 'Strike',
        'Call/Put', 'Price', 'Fees', 'Amount', 'Description', 'Account Reference'
    ]

    # Mapping and conversion
    legacy_df['Date/Time'] = pd.to_datetime(df['Date'],
                                            utc=True).dt.strftime('%m/%d/%Y %I:%M %p')
    legacy_df['Transaction Code'] = df['Type']
    legacy_df['Transaction Subcode'] = df['Sub Type']
    legacy_df['Symbol'] = df['Underlying Symbol'].fillna(
        df['Symbol'].str.split().str[0])
    legacy_df['Quantity'] = df['Quantity'].fillna(0).astype(int)
    legacy_df['Expiration Date'] = df['Expiration Date'].fillna('')
    legacy_df['Strike'] = df['Strike Price'].fillna('')
    legacy_df['Call/Put'] = df['Call or Put'].apply(
        lambda x: x[0] if pd.notna(x) else '')
    legacy_df['Price'] = df['Average Price'].abs().fillna('')
    legacy_df['Fees'] = df['Fees'].fillna(0)
    legacy_df['Amount'] = df['Value'].fillna(0)
    legacy_df['Description'] = df['Description'].fillna('')
    legacy_df['Account Reference'] = 'Individual...39'

    # Handle Buy/Sell and Open/Close
    is_trade = df['Type'].isin(['Trade', 'Receive Deliver'])
    legacy_df['Buy/Sell'] = ''
    legacy_df.loc[is_trade, 'Buy/Sell'] = df.loc[is_trade,
                                                 'Action'].apply(lambda x: 'Buy' if 'BUY' in str(x).upper() else 'Sell')
    legacy_df['Open/Close'] = ''
    legacy_df.loc[is_trade, 'Open/Close'] = df.loc[is_trade,
                                                   'Action'].apply(lambda x: 'Open' if 'OPEN' in str(x).upper() else 'Close')

    # Set Quantity to 0 for non-trade transactions
    legacy_df.loc[~is_trade, 'Quantity'] = 0

    # Reorder columns
    legacy_df = legacy_df.reindex(columns=legacy_columns)

    return legacy_df


def convert_to_new_format(df: pd.DataFrame) -> pd.DataFrame:
    """Convert the legacy format to the new TastyTrade format."""
    new_df = df.rename(columns=LEGACY_TO_NEW_MAPPING)
    new_df = new_df.reindex(columns=list(
        LEGACY_TO_NEW_MAPPING.values()) + ADDITIONAL_NEW_FIELDS, fill_value='')

    new_df['Action'] = df.apply(
        lambda row: f"{'BUY' if row['Buy/Sell'] == 'Buy' else 'SELL'}_TO_{'OPEN' if row['Open/Close'] == 'Open' else 'CLOSE'}",
        axis=1
    )
    new_df['Instrument Type'] = df.apply(
        lambda row: 'Equity Option' if pd.notna(
            row['Expiration Date']) and pd.notna(row['Strike']) else 'Equity',
        axis=1
    )
    new_df['Root Symbol'] = df['Symbol'].str.split().str[0]
    new_df['Underlying Symbol'] = new_df['Root Symbol']
    new_df['Multiplier'] = new_df['Instrument Type'].map(
        {'Equity Option': 100, 'Equity': 1})
    new_df['Currency'] = 'USD'
    new_df['Order #'] = ''

    new_df['Date'] = pd.to_datetime(
        new_df['Date'], utc=True).dt.strftime('%Y-%m-%dT%H:%M:%S%z')

    if 'Average Price' not in new_df.columns:
        new_df['Average Price'] = pd.to_numeric(
            df['Amount'], errors='coerce') / pd.to_numeric(df['Quantity'], errors='coerce')

    return new_df


def convert_csv(input_file: str, output_file: str, conversion_direction: str) -> None:
    """Convert CSV file between new TastyTrade and legacy formats."""
    try:
        df = pd.read_csv(input_file)
        logger.info(f"Successfully read input file: {input_file}")
    except Exception as e:
        logger.error(f"Error reading input file: {e}")
        raise

    if conversion_direction == 'to_legacy':
        converted_df = convert_to_legacy_format(df)
    elif conversion_direction == 'to_new':
        converted_df = convert_to_new_format(df)
    else:
        raise ValueError(
            "Invalid conversion direction. Use 'to_legacy' or 'to_new'.")

    try:
        converted_df.to_csv(output_file, index=False)
        logger.info(f"Successfully wrote output file: {output_file}")
    except Exception as e:
        logger.error(f"Error writing output file: {e}")
        raise


def main() -> None:
    """Main function to handle command-line interface and initiate conversion."""
    parser = argparse.ArgumentParser(
        description="Convert CSV between new TastyTrade and legacy formats.")
    parser.add_argument('input_file', help="Path to the input CSV file")
    parser.add_argument('output_file', help="Path to the output CSV file")
    parser.add_argument('direction', choices=[
                        'to_legacy', 'to_new'], help="Conversion direction")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    logger.debug("Starting CSV conversion process")
    convert_csv(args.input_file, args.output_file, args.direction)
    logger.debug("CSV conversion process completed")


if __name__ == "__main__":
    main()
