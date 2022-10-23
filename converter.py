import logging
import pprint


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


class Converter(object):
    def __init__(self, path: str) -> None:
        self.path = path

    def toGerman(self, input: dict) -> dict:
        return input.replace(".", ",")


if __name__ == "__main__":
    import doctest
    # doctest.testmod(extraglobs={"t": Tasty("test/merged.csv")})
    doctest.testmod()
