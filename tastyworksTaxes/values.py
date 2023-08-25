import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tastyworksTaxes.money import Money
import json
from unittest.mock import Mock, patch
from dataclasses_json import dataclass_json
from dataclasses import dataclass


@dataclass_json
@dataclass
class Values(object):
    """store all data here"""
    withdrawal: Money = Money()
    transfer: Money = Money()
    balanceAdjustment: Money = Money()
    fee: Money = Money()
    deposit: Money = Money()
    creditInterest: Money = Money()
    debitInterest: Money = Money()
    dividend: Money = Money()
    stockAndOptionsSum: Money = Money()
    stockSum: Money = Money()
    optionSum: Money = Money()
    longOptionProfits: Money = Money()
    longOptionLosses: Money = Money()
    longOptionTotalLosses: Money = Money()
    grossOptionDifferential: Money = Money()
    stockProfits: Money = Money()
    stockLoss: Money = Money()
    stockFees: Money = Money()
    otherFees: Money = Money()

    def __str__(self):
        """pretty prints all the contained Values
        >>> values = Values()

        """
        j = self.to_json()
        return str(json.dumps(j, indent=4, sort_keys=True))


if __name__ == "__main__":
    import doctest
    doctest.testmod()
