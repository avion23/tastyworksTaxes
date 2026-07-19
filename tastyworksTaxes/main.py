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


def _as_optional_date(value) -> date | None:
    if value is None or pd.isna(value):
        return None
    if str(value).strip().lower() in {"", "none", "nan", "nat"}:
        return None
    return _as_date(value)


def vorabpauschale_warning_lines(tasty: Tasty) -> list[str]:
    lines = []
    closed_trades = tasty.position_manager.closed_trades
    open_lots = tasty.position_manager.get_all_open_lots()
    for assessment_year in sorted(tasty.yearValues):
        calendar_year = assessment_year - 1
        if calendar_year not in BASISZINS:
            continue
        year_start = date(calendar_year, 1, 1)
        year_end = date(calendar_year, 12, 31)
        holdings = [
            (
                trade.symbol,
                trade.position_type,
                trade.quantity,
                _as_date(trade.opening_date),
                _as_optional_date(trade.closing_date),
            )
            for trade in closed_trades
        ]
        holdings.extend(
            (lot.symbol, lot.position_type, lot.quantity, _as_date(lot.date), None)
            for lot in open_lots
        )
        fund_acquisitions = {}
        for symbol, position_type, quantity, opening_date, closing_date in holdings:
            if position_type != PositionType.stock or quantity <= 0:
                continue
            if opening_date > year_end or (
                closing_date is not None and closing_date < year_start
            ):
                continue
            classification_date = max(opening_date, year_start)
            classification = tasty.classifier.classify_for_tax(
                symbol, PositionType.stock, classification_date
            )
            if tasty.classifier.get_tax_category(classification) != "KAP-INV":
                continue
            previous = fund_acquisitions.get(symbol)
            if previous is None or opening_date < previous:
                fund_acquisitions[symbol] = opening_date

        for symbol in sorted(fund_acquisitions):
            opening_date = fund_acquisitions[symbol]
            months_before_acquisition = (
                opening_date.month - 1 if opening_date >= year_start else 0
            )
            timeline = (
                f"first acquired in {calendar_year}-{opening_date.month:02d}"
                if opening_date >= year_start
                else f"held at start of {calendar_year}"
            )
            basiszins_pct = BASISZINS[calendar_year] * 100
            lines.append(
                f"WARNING: VORABPAUSCHALE: fund {symbol} {timeline}; "
                f"months_before_acquisition={months_before_acquisition}. "
                f"compute Vorabpauschale for calendar year {calendar_year} "
                f"(Basiszins {basiszins_pct:g}%), deemed received in {assessment_year}. "
                "Use tastyworksTaxes.vorabpauschale.calculate_vorabpauschale("
                "start_of_year_value_eur, basiszins, teilfreistellung_pct, "
                "distributions_eur, value_increase_eur, "
                f"months_before_acquisition={months_before_acquisition})."
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
