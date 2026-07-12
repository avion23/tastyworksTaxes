import argparse
import logging
import pathlib
from dataclasses import asdict, fields

import pandas as pd

from tastyworksTaxes.fifo_processor import TradeResult
from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.printer import Printer


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
    if getattr(t, "unverified_asset_symbols", None):
        symbols = ", ".join(sorted(t.unverified_asset_symbols))
        print("*** INCOMPLETE ASSET CLASSIFICATION - NOT FILING-READY ***")
        print(
            "The following symbols are not in the program's explicit asset registry. "
            "They were treated as individual stocks but may be funds requiring "
            "different German tax treatment:"
        )
        print(symbols)
        print("Verify each symbol's stock/fund status before using this report for a tax filing.\n")
    for year, values in t.yearValues.items():
        print(f"Values for year {year} in Euro:")
        p = Printer(values=values, closed_trades=t.position_manager.closed_trades)
        print(p.generateDummyReport())
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
