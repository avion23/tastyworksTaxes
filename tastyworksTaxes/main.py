import argparse
import logging
import pathlib
from dataclasses import asdict, fields
from datetime import date, datetime

import pandas as pd

from tastyworksTaxes.fifo_processor import TradeResult
from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.printer import Printer
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.vorabpauschale import BASISZINS


logging.basicConfig(
    format='%(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)


def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input", help="Input file path to the tastyworks csv export", type=pathlib.Path)
    parser.add_argument("-w", "--write-closed-trades", help="optional output path for the closed trades csv",
                        type=pathlib.Path, required=False)
    return parser


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def vorabpauschale_warning_lines(tasty: Tasty) -> list[str]:
    lines = []
    closed_trades = tasty.position_manager.closed_trades
    open_lots = tasty.position_manager.get_all_open_lots()
    for assessment_year in sorted(tasty.yearValues):
        calendar_year = assessment_year - 1
        if calendar_year not in BASISZINS:
            continue
        boundary = date(calendar_year, 1, 1)
        symbols = {
            trade.symbol
            for trade in closed_trades
            if trade.position_type == PositionType.stock
            and trade.quantity > 0
            and _as_date(trade.opening_date) < boundary
            and _as_date(trade.closing_date) >= boundary
        }
        symbols.update(
            lot.symbol
            for lot in open_lots
            if lot.position_type == PositionType.stock
            and lot.quantity > 0
            and _as_date(lot.date) < boundary
        )
        for symbol in sorted(symbols):
            classification = tasty.classifier.classify_for_tax(
                symbol, PositionType.stock, boundary
            )
            if tasty.classifier.get_tax_category(classification) != "KAP-INV":
                continue
            basiszins_pct = BASISZINS[calendar_year] * 100
            lines.append(
                f"WARNING: VORABPAUSCHALE: fund {symbol} held at start of {calendar_year}; "
                f"compute Vorabpauschale for calendar year {calendar_year} "
                f"(Basiszins {basiszins_pct:g}%), deemed received in {assessment_year}. "
                "Use tastyworksTaxes.vorabpauschale.calculate_vorabpauschale("
                "start_of_year_value_eur, basiszins, teilfreistellung_pct, "
                "distributions_eur, value_increase_eur)."
            )
    return lines


def main() -> None:
    parser = init_argparse()
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error(f"input file does not exist or is not a file: {args.input}")
    if args.write_closed_trades:
        output = args.write_closed_trades
        if output.resolve() == args.input.resolve():
            parser.error("closed-trades output must not overwrite the input CSV")
        if not output.parent.is_dir():
            parser.error(f"output directory does not exist or is not a directory: {output.parent}")
    t = Tasty(path=args.input)
    t.run()
    for warning in vorabpauschale_warning_lines(t):
        print(warning)
    if getattr(t, "unverified_asset_symbols", None):
        symbols = ", ".join(sorted(t.unverified_asset_symbols))
        print("*** INCOMPLETE ASSET CLASSIFICATION - NOT FILING-READY ***")
        print(
            "The following symbols lack a verified classification in the asset registry. "
            "No partial exemption was applied; unknown symbols were treated as individual stocks and may be funds requiring "
            "different German tax treatment:"
        )
        print(symbols)
        print("Verify each symbol's stock/fund status before using this report for a tax filing.\n")
    for year, values in t.yearValues.items():
        print(f"Values for year {year} in Euro:")
        p = Printer(values=values, closed_trades=t.position_manager.closed_trades)
        print(p.generateGermanTaxReport())
    if args.write_closed_trades:
        logging.info(
            f"Writing closed trades to: '{args.write_closed_trades}'")
        closed_trades = t.position_manager.closed_trades
        trades_data = [asdict(trade) for trade in closed_trades]
        columns = [field.name for field in fields(TradeResult)]
        pd.DataFrame(trades_data, columns=columns).to_csv(
            args.write_closed_trades, index=False)
    logging.info("Done")


if __name__ == "__main__":
    main()
