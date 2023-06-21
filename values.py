import logging
import pprint
from dataclasses import dataclass
from dataclasses_json import dataclass_json
from unittest.mock import Mock, patch
from history import History
from money import Money
import json


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
    grossOptionsDifferential: Money = Money()
    stockProfits: Money = Money()
    stockLoss: Money = Money()
    otherLoss: Money = Money()
    stockFees: Money = Money()
    otherFees: Money = Money()

    def __str__(self):
        """pretty prints all the contained Values
        >>> values = Values()

        """
        j = self.to_json()
        return str(json.dumps(j, indent=4, sort_keys=True))
