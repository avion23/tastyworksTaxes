from tastyworksTaxes.money import Money
from tastyworksTaxes.printer import Printer
from tastyworksTaxes.values import Values


def test_german_report_labels_distinguish_stock_and_fund_results():
    values = Values(
        stockProfits=Money(eur=80),
        stockLosses=Money(eur=-16),
        fundProfits=Money(eur=70),
        fundLosses=Money(eur=-7),
        fundDistributions=Money(eur=10),
        fundDistributionExempt=Money(eur=3),
        fundDistributionTaxable=Money(eur=7),
    )

    report = str(Printer(values, []).generateGermanTaxReport())

    for label in (
        "Aktiengewinne Z20",
        "Aktienverluste Z23",
        "Investmentfondsgewinne",
        "Investmentfondsverluste",
        "Fondsausschüttungen brutto",
        "Fondsausschüttungen steuerfrei",
        "Fondsausschüttungen steuerpflichtig",
    ):
        assert label in report
