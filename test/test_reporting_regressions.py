import json
from importlib.resources import files

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
