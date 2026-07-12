from importlib.resources import files

from tastyworksTaxes.asset_classifier import AssetClassifier
from tastyworksTaxes.fifo_processor import TradeResult
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.printer import EnglishTaxReport
from tastyworksTaxes.trade_calculator import (
    calculate_equity_etf_profits,
    calculate_gross_equity_etf_profits,
    calculate_other_stock_and_bond_profits,
    calculate_stock_loss,
)


def stock_trade(symbol, profit_eur, fees_eur=0):
    return TradeResult(
        symbol=symbol,
        position_type=PositionType.stock,
        opening_date="2024-01-01",
        closing_date="2024-01-02",
        quantity=1,
        profit_usd=profit_eur,
        profit_eur=profit_eur,
        fees_usd=fees_eur,
        fees_eur=fees_eur,
        worthless_expiry=False,
        strike=None,
        expiry=None,
    )


def test_stock_results_are_classified_after_fees_and_crypto_is_excluded():
    classifier = AssetClassifier()
    trades = [
        stock_trade("AAPL", 1, 2),
        stock_trade("BTC", 100),
    ]

    assert calculate_other_stock_and_bond_profits(trades, classifier).eur == 0
    assert calculate_stock_loss(trades, classifier).eur == -1


def test_unverified_mixed_and_real_estate_funds_get_no_exemption():
    classifier = AssetClassifier()
    trades = [stock_trade("AOM", 100), stock_trade("VNQ", 100)]

    result = calculate_other_stock_and_bond_profits(trades, classifier)

    assert result.eur == 200
    assert result.usd == 200


def test_unverified_equity_fund_does_not_enter_fund_tax_bucket():
    classifier = AssetClassifier()
    trades = [stock_trade("TECL", 100)]

    assert calculate_gross_equity_etf_profits(trades, classifier).eur == 0
    assert calculate_equity_etf_profits(trades, classifier).eur == 0
    assert calculate_other_stock_and_bond_profits(trades, classifier).eur == 100


def test_trade_date_controls_effective_fund_exemption(tmp_path):
    registry = tmp_path / "assets.csv"
    registry.write_text(
        "symbol,classification,tax_category,teilfreistellung_pct,verified,effective_from,effective_to,evidence\n"
        "TEST,EQUITY_ETF,KAP-INV,30,true,2020-01-01,2020-12-31,Prospectus section 2\n",
        encoding="utf-8",
    )
    classifier = AssetClassifier(registry)
    effective_trade = stock_trade("TEST", 100)
    effective_trade.closing_date = "2020-06-01 12:00:00"
    expired_trade = stock_trade("TEST", 100)
    expired_trade.closing_date = "2021-06-01 12:00:00"

    assert calculate_equity_etf_profits([effective_trade, expired_trade], classifier).eur == 70
    assert calculate_other_stock_and_bond_profits([effective_trade, expired_trade], classifier).eur == 100


def test_unverified_fund_losses_get_no_exemption():
    classifier = AssetClassifier()
    trades = [
        stock_trade("TECL", -100),
        stock_trade("AOM", -100),
        stock_trade("VNQ", -100),
        stock_trade("PULS", -100),
        stock_trade("AAPL", -100),
    ]

    result = calculate_stock_loss(trades, classifier)

    assert result.eur == -500
    assert result.usd == -500


def test_unverified_fund_loss_includes_fees_without_exemption():
    classifier = AssetClassifier()

    result = calculate_stock_loss([stock_trade("TECL", 1, 2)], classifier)

    assert result.eur == -1
    assert result.usd == -1


def test_corporate_actions_resource_is_packaged_with_the_module():
    resource = files("tastyworksTaxes").joinpath("corporate_actions.csv")

    assert resource.is_file()
    assert "USO" in resource.read_text(encoding="utf-8")


def test_english_report_renders_all_populated_fields():
    report = EnglishTaxReport(
        additional_order_fees=1,
        dividends=2,
        paid_dividends=3,
        withholding_tax_z41=4,
        interest_income=5,
        interest_expenses=6,
        interest_total=7,
        z19_foreign_capital_gains=8,
    )
    rendered = str(report)

    for label in (
        "additional order fees",
        "dividends",
        "paid dividends",
        "withholding tax z41",
        "interest income",
        "interest expenses",
        "interest total",
        "z19 foreign capital gains",
    ):
        assert label in rendered
