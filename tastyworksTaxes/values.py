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
    # Diagnostic components named after the former form lines. The VZ 2025
    # Anlage KAP has no lines 21/24. Its line 19 includes both components and
    # its line 22 repeats the applicable loss as a positive amount.
    z21_termingeschaefsgewinne: Money = field(default_factory=Money)
    z24_termingeschaefte_verluste: Money = field(default_factory=Money)
    # Appended fields preserve the positional constructor order above.
    fundGrossLosses: Money = field(default_factory=Money)
    fundTaxReviewRequired: bool = False

    def __str__(self):
        """Pretty-print every annual value without double-encoding JSON."""
        values = {
            name: {"eur": value.eur, "usd": value.usd}
            if isinstance(value, Money) else value
            for name, value in vars(self).items()
        }
        return json.dumps(values, indent=4, sort_keys=True)
