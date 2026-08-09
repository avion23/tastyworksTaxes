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
    fundDistributions: Money = field(default_factory=Money)
    fundDistributionExempt: Money = field(default_factory=Money)
    fundDistributionTaxable: Money = field(default_factory=Money)
    paidDividend: Money = field(default_factory=Money)
    withholdingTax: Money = field(default_factory=Money)
    stockProfits: Money = field(default_factory=Money)
    stockLosses: Money = field(default_factory=Money)
    fundGrossProfits: Money = field(default_factory=Money)
    fundProfits: Money = field(default_factory=Money)
    fundLosses: Money = field(default_factory=Money)
    optionSum: Money = field(default_factory=Money)
    longOptionProfits: Money = field(default_factory=Money)
    longOptionLosses: Money = field(default_factory=Money)
    longOptionTotalLosses: Money = field(default_factory=Money)
    shortOptionProfits: Money = field(default_factory=Money)
    shortOptionLosses: Money = field(default_factory=Money)
    optionDifferential: Money = field(default_factory=Money)
    stockFees: Money = field(default_factory=Money)
    otherFees: Money = field(default_factory=Money)
    # NOTE: field NAMES keep the legacy Z21/Z24 Anlage-KAP line numbers, but since
    # the JStG 2024 (BGBl. 2024 I Nr. 387, applies to all open cases) abolished the
    # separate Termingeschäfte loss pot, Anlage KAP dropped Zeile 21 and 24 from
    # VZ 2025 onward. The values are still computed the same way; for VZ 2025+
    # gains and losses together form the Zeile 19 net saldo, with the losses
    # additionally broken out in Zeile 22.
    z21_termingeschaefsgewinne: Money = field(default_factory=Money)
    z24_termingeschaefte_verluste: Money = field(default_factory=Money)

    def __str__(self):
        """Pretty-print every annual value without double-encoding JSON."""
        values = {
            name: {"eur": money.eur, "usd": money.usd}
            for name, money in vars(self).items()
        }
        return json.dumps(values, indent=4, sort_keys=True)
