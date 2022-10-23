import argparse
import logging
import pathlib
import re

from tasty import Tasty


logger = logging.getLogger(__name__)
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.WARNING,
    datefmt='%Y-%m-%d %H:%M:%S')
for key in logging.Logger.manager.loggerDict:  # disable logging for imported modules
    temp = logging.getLogger(key)
    temp.propagate = True
    temp.setLevel(logging.INFO)
    if temp.name == "trade":
        temp.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.StreamHandler()
    logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


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
