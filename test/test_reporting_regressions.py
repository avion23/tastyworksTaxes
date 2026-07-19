from importlib.resources import files

import pytest

from tastyworksTaxes.asset_classifier import AssetClassifier
from tastyworksTaxes.fifo_processor import TradeResult
from tastyworksTaxes.money import Money
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.printer import EnglishTaxReport, Printer
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


def test_german_and_english_reports_map_split_fields():
    values = Values(
        stockProfits=Money(eur=10), stockLosses=Money(eur=-3),
        fundProfits=Money(eur=20), fundLosses=Money(eur=-4),
        fundDistributions=Money(eur=8), fundDistributionExempt=Money(eur=2.4),
        fundDistributionTaxable=Money(eur=5.6), dividend=Money(eur=7),
        creditInterest=Money(eur=1), securitiesLendingIncome=Money(eur=2),
        withholdingTax=Money(eur=3),
    )
    printer = Printer(values, [])
    german = printer.generateGermanTaxReport()
    english = printer.generateEnglishTaxReport()

    assert (german.aktiengewinne_z20, german.aktienverluste_z23, german.aktien_gesamt) == (10, -3, 7)
    assert (german.investmentfondsgewinne, german.investmentfondsverluste, german.anlage_kap_inv) == (20, -4, 21.6)
    assert german.z19_auslaendische_kapitalertraege == pytest.approx(15.6)
    assert german.kap_kap_inv_kerst_soli == 0
    assert english.investment_kap_inv == pytest.approx(21.6)
    assert "Soli/KESt are not computed" in str(german)


def test_corporate_actions_resource_is_packaged_with_the_module():
    resource = files("tastyworksTaxes").joinpath("corporate_actions.csv")
    assert resource.is_file()
    assert "USO" in resource.read_text(encoding="utf-8")


def test_english_report_renders_fund_distribution_fields():
    rendered = str(EnglishTaxReport(
        fund_distributions_gross=10,
        fund_distributions_exempt=3,
        fund_distributions_taxable=7,
    ))
    assert "fund distributions gross" in rendered
    assert "fund distributions exempt" in rendered
    assert "fund distributions taxable" in rendered
