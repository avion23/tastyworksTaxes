

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tastyworksTaxes.money import Money
from tastyworksTaxes.printer import Printer
from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.values import Values

def test_uso():
    """Tests with the uso file"""


    t = Tasty("test/uso.csv")
    t.run()


def test_tax_reports_use_existing_long_option_fields():
    values = Values()
    values.longOptionProfits = Money(eur=20.0, usd=22.0)
    values.longOptionLosses = Money(eur=-5.0, usd=-5.5)
    values.longOptionTotalLosses = Money(eur=-12.34, usd=-13.0)
    printer = Printer(values, [])

    english_report = printer.generateEnglishTaxReport()
    german_report = printer.generateGermanTaxReport()

    assert english_report.other_losses == 0
    assert english_report.long_option_gains == 20.0
    assert english_report.long_option_losses == -5.0
    assert english_report.long_option_total == 2.66
    assert german_report.sonstige_verluste == 0
    assert german_report.long_optionen_gewinne == 20.0
    assert german_report.long_optionen_verluste == -5.0
    assert german_report.long_optionen_gesamt == 2.66


def test_tax_reports_keep_gross_dividends_and_withholding_separate():
    values = Values()
    values.dividend = Money(eur=100.0, usd=110.0)
    values.paidDividend = Money(eur=-5.0, usd=-5.5)
    values.withholdingTax = Money(eur=15.0, usd=16.5)

    printer = Printer(values, [])
    english = printer.generateEnglishTaxReport()
    german = printer.generateGermanTaxReport()

    assert (english.dividends, english.paid_dividends, english.withholding_tax_z41) == (100.0, -5.0, 15.0)
    assert (german.dividenden, german.bezahlte_dividenden, german.quellensteuer_z41) == (100.0, -5.0, 15.0)
