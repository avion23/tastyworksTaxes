import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tastyworksTaxes.money import Money
import json

from dataclasses_json import dataclass_json
from dataclasses import dataclass, field


@dataclass_json
@dataclass
class Values(object):
    """store all data here"""
    withdrawal: Money = field(default_factory=Money)
    transfer: Money = field(default_factory=Money)
    balanceAdjustment: Money = field(default_factory=Money)
    fee: Money = field(default_factory=Money)
    deposit: Money = field(default_factory=Money)
    creditInterest: Money = field(default_factory=Money)
    securitiesLendingIncome: Money = field(default_factory=Money)
    debitInterest: Money = field(default_factory=Money)
    dividend: Money = field(default_factory=Money)
    stockAndOptionsSum: Money = field(default_factory=Money)
    equityEtfGrossProfits: Money = field(default_factory=Money)
    equityEtfProfits: Money = field(default_factory=Money)
    otherStockAndBondProfits: Money = field(default_factory=Money)
    totalTaxableStockAndEtfProfits: Money = field(default_factory=Money)
    stockAndEtfLosses: Money = field(default_factory=Money)
    optionSum: Money = field(default_factory=Money)
    longOptionProfits: Money = field(default_factory=Money)
    longOptionLosses: Money = field(default_factory=Money)
    longOptionTotalLosses: Money = field(default_factory=Money)
    shortOptionProfits: Money = field(default_factory=Money)
    shortOptionLosses: Money = field(default_factory=Money)
    grossOptionDifferential: Money = field(default_factory=Money)
    stockFees: Money = field(default_factory=Money)
    otherFees: Money = field(default_factory=Money)

    def __str__(self):
        """pretty prints all the contained Values
        """
        j = self.to_json()
        return str(json.dumps(j, indent=4, sort_keys=True))
