import argparse
import logging
import pathlib
from dataclasses import asdict, fields

import pandas as pd

from tastyworksTaxes.fifo_processor import TradeResult
from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.printer import Printer


logger = logging.getLogger(__name__)


def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input", help="Input file path to the tastyworks csv export", type=pathlib.Path)
    parser.add_argument("-w", "--write-closed-trades", help="optional output path for the closed trades csv",
                        type=pathlib.Path, required=False)
    return parser


def main() -> None:
    logging.basicConfig(format="%(message)s", level=logging.INFO)
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
    for year in sorted(t.yearValues):
        values = t.yearValues[year]
        print(f"Values for year {year} in Euro:")
        unverified_symbols = t.unverified_asset_symbols_by_year.get(year, set())
        if unverified_symbols:
            symbols = ", ".join(sorted(unverified_symbols))
            print("*** INCOMPLETE ASSET CLASSIFICATION - NOT FILING-READY ***")
            print(
                "The following symbols lack a verified classification in the asset registry. "
                "No partial exemption was applied; unknown symbols were treated as individual stocks and may be funds requiring "
                "different German tax treatment:"
            )
            print(symbols)
            print("Verify each symbol's stock/fund status before using this report for a tax filing.\n")
        short_stock_trades = t.short_stock_trades_by_year.get(year, [])
        if short_stock_trades:
            symbols = ", ".join(sorted({trade.symbol for trade in short_stock_trades}))
            print("*** CLOSED SHORT-STOCK TRADES - NOT FILING-READY ***")
            print(
                "Closed short-stock trades were detected for the following symbols: "
                f"{symbols}. A potential 30% substitute assessment may require separate "
                "tax treatment; this rule is not calculated by this report."
            )
            print("Review these trades manually before using this annual report for a tax filing.\n")
        if year in getattr(t, "ambiguous_withholding_years", set()):
            print("*** AMBIGUOUS DIVIDEND WITHHOLDING - NOT FILING-READY ***")
            print(
                "A negative dividend cash movement was allocated by the withholding "
                "heuristic. Review the broker statement before using this annual "
                "report for a tax filing.\n"
            )
        unsupported_symbols = getattr(
            t, "unsupported_tax_category_symbols_by_year", {}
        ).get(year, set())
        if unsupported_symbols:
            symbols = ", ".join(sorted(unsupported_symbols))
            print("*** UNSUPPORTED TAX CATEGORY - NOT FILING-READY ***")
            print(
                "The following symbols require a tax category that this report does "
                f"not calculate: {symbols}"
            )
            print(
                "Calculate these entries manually before using this annual report "
                "for a tax filing.\n"
            )
        p = Printer(
            values=values,
            closed_trades=t.position_manager.closed_trades,
            assessment_year=year,
        )
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
