import argparse
import logging
import pathlib
import re

from tasty import Tasty


def function_proper(param1, param2) -> None:
    # CODE...
    pass


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
    if not args.input.exists():
        raise FileNotFoundError(f"File {args.input} does not exist")
    else:
        t = Tasty(path=args.input)
        t.run()
        if args.write_closed_trades:
            logging.info(
                f"Writing closed trades to: '{args.write_closed_trades}'")
            closedTrades = t.closedTrades
            if not closedTrades.empty:
                closedTrades.to_csv(args.write_closed_trades, index=False)
            else:
                logging.error(
                    "The closed trades dataframe is empty. Not saving to file.")
    logging.info("Done")


if __name__ == "__main__":
    main()
