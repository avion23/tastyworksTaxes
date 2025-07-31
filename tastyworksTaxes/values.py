import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tastyworksTaxes.money import Money
import json

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
    securitiesLendingIncome: Money = Money()
    debitInterest: Money = Money()
    dividend: Money = Money()
    stockAndOptionsSum: Money = Money()
    equityEtfProfits: Money = Money()
    otherStockAndBondProfits: Money = Money()
    totalTaxableStockAndEtfProfits: Money = Money()
    stockAndEtfLosses: Money = Money()
    optionSum: Money = Money()
    longOptionProfits: Money = Money()
    longOptionLosses: Money = Money()
    longOptionTotalLosses: Money = Money()
    shortOptionProfits: Money = Money()
    shortOptionLosses: Money = Money()
    grossOptionDifferential: Money = Money()
    stockFees: Money = Money()
    otherFees: Money = Money()

    def __str__(self):
        """pretty prints all the contained Values
        """
        j = self.to_json()
        return str(json.dumps(j, indent=4, sort_keys=True))
