import json
import os
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

import pytest

from tastyworksTaxes.asset_classifier import AssetClassifier
from tastyworksTaxes.fifo_processor import TradeResult
from tastyworksTaxes.money import Money
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.printer import EnglishTaxReport, GermanTaxReport, Printer
from tastyworksTaxes.trade_calculator import calculate_fund_profits, calculate_stock_profits
from tastyworksTaxes.values import Values


def stock_trade(symbol, profit_eur, closing_date="2024-01-02"):
    return TradeResult(
        symbol=symbol, position_type=PositionType.stock,
        opening_date="2024-01-01", closing_date=closing_date, quantity=1,
        profit_usd=profit_eur, profit_eur=profit_eur, fees_usd=0, fees_eur=0,
        worthless_expiry=False, strike=None, expiry=None,
    )


def test_trade_date_controls_effective_fund_routing(tmp_path):
    registry = tmp_path / "assets.csv"
    registry.write_text(
        "symbol,classification,tax_category,teilfreistellung_pct,verified,effective_from,effective_to,evidence\n"
        "TEST,EQUITY_ETF,KAP-INV,30,true,2020-01-01,2020-12-31,Prospectus\n",
        encoding="utf-8",
    )
    classifier = AssetClassifier(registry)
    active = stock_trade("TEST", 100, "2020-06-01")
    expired = stock_trade("TEST", 100, "2021-06-01")

    assert calculate_fund_profits([active, expired], classifier).eur == 70
    assert calculate_stock_profits([active, expired], classifier).eur == 100


def test_annual_reports_reconcile_all_calculated_categories():
    values = Values(
        deposit=Money(eur=200), withdrawal=Money(eur=-50),
        fee=Money(usd=-5, eur=-4), stockFees=Money(eur=-1),
        otherFees=Money(eur=-3),
        stockProfits=Money(eur=10), stockLosses=Money(eur=-3),
        fundProfits=Money(eur=20), fundLosses=Money(eur=-4),
        fundDistributions=Money(eur=8), fundDistributionExempt=Money(eur=2.4),
        fundDistributionTaxable=Money(eur=5.6), dividend=Money(eur=7),
        paidDividend=Money(eur=-1), withholdingTax=Money(eur=3),
        creditInterest=Money(eur=1), debitInterest=Money(eur=-0.5),
        securitiesLendingIncome=Money(eur=2),
        shortOptionProfits=Money(eur=9), shortOptionLosses=Money(eur=-2),
        longOptionProfits=Money(eur=6), longOptionLosses=Money(eur=-1),
        longOptionTotalLosses=Money(eur=-2),
        z21_termingeschaefsgewinne=Money(eur=15),
        z24_termingeschaefte_verluste=Money(eur=-5),
    )

    printer = Printer(values, [])
    german = printer.generateGermanTaxReport()
    english = printer.generateEnglishTaxReport()

    assert german.aktien_gesamt == german.aktiengewinne_z20 + german.aktienverluste_z23 == 7
    assert german.anlage_kap_inv == (
        german.investmentfondsgewinne
        + german.investmentfondsverluste
        + german.fondsausschuettungen_steuerpflichtig
    ) == pytest.approx(21.6)
    assert german.stillhalter_gesamt == german.stillhalter_gewinne + german.stillhalter_verluste == 7
    assert german.long_optionen_gesamt == (
        german.long_optionen_gewinne
        + german.long_optionen_verluste
        + german.long_optionen_verfallverluste
    ) == 3
    assert german.zinsen_gesamt == german.zinseinnahmen + german.zinsausgaben == 0.5
    assert german.z19_auslaendische_kapitalertraege == pytest.approx(15.6)
    assert (
        german.brokergebuehren,
        german.alle_gebuehren_in_usd,
        german.alle_gebuehren_in_euro,
        german.zusatzliche_ordergebuehren,
    ) == (-1, -5, -4, -3)
    assert (
        english.stock_total,
        english.investment_kap_inv,
        english.option_holder_total,
        english.long_option_total,
        english.interest_total,
        english.z19_foreign_capital_gains,
    ) == pytest.approx((7, 21.6, 7, 3, 0.5, 15.6))
    assert (
        english.stock_gains_z20,
        english.stock_losses_z23,
        english.z21_term_gains,
        english.z24_term_losses,
    ) == (
        german.aktiengewinne_z20,
        german.aktienverluste_z23,
        german.z21_termingeschaefsgewinne,
        german.z24_termingeschaefte_verluste,
    )
    assert "Soli/KESt are not computed" in str(german)


def test_corporate_actions_resource_is_packaged_with_the_module():
    resource = files("tastyworksTaxes").joinpath("corporate_actions.csv")
    assert resource.is_file()
    assert "USO" in resource.read_text(encoding="utf-8")


def test_values_string_is_structured_json_with_every_annual_value():
    values = Values(
        dividend=Money(usd=11, eur=10),
        longOptionTotalLosses=Money(usd=-13, eur=-12.34),
    )

    rendered = str(values)
    decoded = json.loads(rendered)

    assert not rendered.startswith('"')
    assert set(decoded) == set(values.__dataclass_fields__)
    assert decoded["dividend"] == {"eur": 10, "usd": 11}
    assert decoded["longOptionTotalLosses"] == {"eur": -12.34, "usd": -13}


def test_german_legacy_positional_constructor_order_is_preserved():
    report = GermanTaxReport(*range(1, 63))

    assert report.long_optionen_gesamt == 43
    assert report.future_gewinne == 44
    assert report.zusatzliche_ordergebuehren == 47
    assert report.wertpapierleihe_einkommen == 62
    assert report.long_optionen_verfallverluste == 0


def test_english_legacy_positional_constructor_order_is_preserved():
    report = EnglishTaxReport(*range(1, 63))

    assert report.long_option_total == 43
    assert report.future_gains == 44
    assert report.additional_order_fees == 47
    assert report.securities_lending_income == 62
    assert report.long_option_worthless_expiry_losses == 0


def test_reports_do_not_render_uncalculated_tax_totals_as_zero():
    printer = Printer(Values(), [])
    german = str(printer.generateGermanTaxReport())
    english = str(printer.generateEnglishTaxReport())

    assert "KAP+KAP-INV" not in german
    assert "KErSt+Soli" not in german
    assert "kap kap inv" not in english
    assert "kerst soli" not in english
    assert "Soli/KESt are not computed" in german


def test_vz_2025_uses_official_kap_lines_and_excludes_kap_inv():
    values = Values(
        dividend=Money(eur=100),
        creditInterest=Money(eur=20),
        securitiesLendingIncome=Money(eur=15),
        stockProfits=Money(eur=40),
        stockLosses=Money(eur=-30),
        fundGrossProfits=Money(eur=100),
        fundGrossLosses=Money(eur=-20),
        fundProfits=Money(eur=70),
        fundLosses=Money(eur=-15),
        fundDistributions=Money(eur=80),
        fundDistributionExempt=Money(eur=30),
        fundDistributionTaxable=Money(eur=50),
        z21_termingeschaefsgewinne=Money(eur=50),
        z24_termingeschaefte_verluste=Money(eur=-60),
        fundTaxReviewRequired=True,
    )

    report = Printer(values, [], assessment_year=2025).generateGermanTaxReport()
    rendered = str(report)

    # 100 + 20 + 15 + (40 - 30) + (50 - 60); no KAP-INV amount.
    assert report.z19_auslaendische_kapitalertraege == 135
    assert report.z22_verluste_ohne_aktienveraeusserungen == 60
    assert report.aktienverluste_z23 == 30
    assert report.fondveraeusserungsgewinne_brutto == 100
    assert report.fondveraeusserungsverluste_brutto == -20
    assert report.anlage_kap_inv == 105  # diagnostic post-exemption subtotal
    assert "Z21 Termingeschäfte" not in rendered
    assert "Z24 Termingeschäftsverluste" not in rendered
    assert "Diagnose: ehemalige Zeile 21" in rendered
    assert "Diagnose: ehemalige Zeile 24" in rendered
    assert "KAP-INV NOT FILING-READY" in rendered
    assert "Vorabpauschale" in rendered


def test_non_2025_mapping_preserves_values_but_is_not_filing_ready():
    values = Values(
        dividend=Money(eur=135),
        fundDistributionTaxable=Money(eur=50),
        stockLosses=Money(eur=-30),
    )

    report = Printer(values, []).generateGermanTaxReport()
    rendered = str(report)

    assert report.z19_auslaendische_kapitalertraege == 185
    assert report.aktienverluste_z23 == -30
    assert "ASSESSMENT YEAR UNSPECIFIED" in rendered
    assert "NOT FILING-READY" in rendered


def test_package_import_from_arbitrary_cwd_does_not_mutate_sys_path(tmp_path):
    package_root = Path(__file__).resolve().parents[1]
    code = """
import sys
before = list(sys.path)
import tastyworksTaxes.printer
import tastyworksTaxes.values
assert sys.path == before, (before, sys.path)
"""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(package_root)

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("assessment_year", [None, 2024])
def test_non_2025_german_render_preserves_legacy_labels_and_order(assessment_year):
    expected_labels = [
        'Einzahlungen', 'Auszahlungen',
        'Aktiengebühren (Info; bereits im Nettoergebnis)',
        'Alle Gebühren in USD (Info; Handelsgebühren bereits im Nettoergebnis)',
        'Alle Gebühren in EUR (Info; Handelsgebühren bereits im Nettoergebnis)',
        'Währungsgewinne USD', 'Währungsgewinne USD steuerfrei',
        'Währungsgewinne USD Gesamt', 'Krypto Gewinne', 'Krypto Verluste',
        'Anlage SO', 'Anlage SO Steuerbetrag', 'Anlage SO Verlustvortrag',
        'Investmentfondsgewinne', 'Investmentfondsverluste', 'Anlage KAP-INV',
        'Fondsausschüttungen brutto', 'Fondsausschüttungen steuerfrei',
        'Fondsausschüttungen steuerpflichtig', 'Aktiengewinne Z20',
        'Aktienverluste Z23', 'Aktien Gesamt', 'Aktien Steuerbetrag',
        'Aktien Verlustvortrag', 'Sonstige Gewinne', 'Sonstige Verluste',
        'Sonstige Gesamt', 'Stillhalter Gewinne', 'Stillhalter Verluste',
        'Stillhalter Gesamt', 'Durchschnitt behaltene Prämien pro Tag',
        'Stillhalter Gewinne Calls (FIFO)', 'Stillhalter Verluste Calls (FIFO)',
        'Stillhalter Calls Gesamt (FIFO)', 'Stillhalter Gewinne Puts (FIFO)',
        'Stillhalter Verluste Puts (FIFO)', 'Stillhalter Puts Gesamt (FIFO)',
        'Stillhalter-Gewinne (FIFO)', 'Stillhalter-Verluste (FIFO)',
        'Stillhalter-Gesamt (FIFO)', 'Long-Optionen-Gewinne',
        'Long-Optionen-Verluste', 'Long-Optionen-Verluste aus wertlosem Verfall',
        'Long-Optionen-Gesamt', 'Future-Gewinne', 'Future-Verluste',
        'Future-Gesamt', 'Optionsgebühren (Info; bereits im Nettoergebnis)',
        'Dividenden', 'bezahlte Dividenden', 'Quellensteuer Z41',
        'Zinseinnahmen', 'Zinsausgaben', 'Zinsen insgesamt',
        'Z19 Ausländische Kapitalerträge', 'Z21 Termingeschäfte+Stillhalter',
        'Z24 Termingeschäftsverluste', 'Cash Balance USD',
        'Net Liquidating Value', 'Wertpapierleihe Einkommen',
    ]
    expected_lines = [f"{label:<40} 0,00" for label in expected_labels]

    rendered = str(
        Printer(Values(), [], assessment_year=assessment_year).generateGermanTaxReport()
    )

    assert rendered.splitlines()[:len(expected_lines)] == expected_lines


@pytest.mark.parametrize("assessment_year", [None, 2024])
def test_non_2025_english_render_preserves_legacy_labels_and_order(assessment_year):
    expected_labels = [
        'deposits', 'withdrawals', 'stock fees (info; already included in net P&L)',
        'all fees in USD (info; trade fees already included in net P&L)',
        'all fees in EUR (info; trade fees already included in net P&L)',
        'currency gains usd', 'currency gains usd tax free',
        'currency gains usd total', 'crypto gains', 'crypto losses',
        'investment so', 'investment so tax amount',
        'investment so loss carryforward', 'investment fund gains',
        'investment fund losses', 'investment kap inv', 'fund distributions gross',
        'fund distributions exempt', 'fund distributions taxable',
        'stock gains z20', 'stock losses z23', 'stock total', 'stock tax amount',
        'stock loss carryforward', 'other gains', 'other losses', 'other total',
        'short option writer gains', 'short option writer losses',
        'short option writer total', 'average held premium per day',
        'short call writer gains fifo', 'short call writer losses fifo',
        'short call writer total fifo', 'short put writer gains fifo',
        'short put writer losses fifo', 'short put writer total fifo',
        'short option writer gains fifo', 'short option writer losses fifo',
        'short option writer total fifo', 'long option gains', 'long option losses',
        'long option worthless-expiry losses', 'long option total', 'future gains',
        'future losses', 'future total',
        'option fees (info; already included in net P&L)', 'dividends',
        'paid dividends', 'withholding tax z41', 'interest income',
        'interest expenses', 'interest total', 'z19 foreign capital gains',
        'z21 term gains', 'z24 term losses', 'cash balance usd',
        'net liquidating value', 'securities lending income',
    ]
    expected_lines = [f"{label:<40} 0.00" for label in expected_labels]

    rendered = str(
        Printer(Values(), [], assessment_year=assessment_year).generateEnglishTaxReport()
    )

    assert rendered.splitlines()[:len(expected_lines)] == expected_lines
