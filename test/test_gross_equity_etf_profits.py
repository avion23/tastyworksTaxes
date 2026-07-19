import pytest

from tastyworksTaxes.asset_classifier import AssetClassifier
from tastyworksTaxes.fifo_processor import TradeResult
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.trade_calculator import (
    calculate_fund_gross_profits,
    calculate_fund_gross_losses,
    calculate_fund_losses,
    calculate_fund_profits,
    calculate_stock_losses,
    calculate_stock_profits,
)


def trade(symbol, profit_eur, profit_usd=None, fees=0):
    return TradeResult(
        symbol=symbol,
        position_type=PositionType.stock,
        opening_date="2020-01-01 00:00:00",
        closing_date="2020-01-02 00:00:00",
        quantity=1,
        profit_usd=profit_eur if profit_usd is None else profit_usd,
        profit_eur=profit_eur,
        fees_usd=fees,
        fees_eur=fees,
        worthless_expiry=False,
        strike=None,
        expiry=None,
    )


@pytest.fixture
def classifier():
    return AssetClassifier()


def test_verified_equity_etf_gain_routes_only_to_funds(classifier):
    trades = [trade("SCHG", 100, 120)]

    assert calculate_fund_gross_profits(trades, classifier).eur == 100
    assert calculate_fund_profits(trades, classifier).eur == 70
    assert calculate_fund_profits(trades, classifier).usd == 84
    assert calculate_stock_profits(trades, classifier).eur == 0


def test_verified_equity_etf_loss_routes_only_to_funds(classifier):
    trades = [trade("SCHG", -100, -120)]

    assert calculate_fund_losses(trades, classifier).eur == -70
    assert calculate_fund_losses(trades, classifier).usd == -84
    assert calculate_stock_losses(trades, classifier).eur == 0


@pytest.mark.parametrize("symbol", ["PULS", "AOM"])
def test_zero_exemption_funds_route_full_result_to_kap_inv(classifier, symbol):
    gains = [trade(symbol, 100)]
    losses = [trade(symbol, -100)]

    assert calculate_fund_profits(gains, classifier).eur == 100
    assert calculate_fund_losses(losses, classifier).eur == -100
    assert calculate_stock_profits(gains, classifier).eur == 0
    assert calculate_stock_losses(losses, classifier).eur == 0


def test_individual_stock_never_routes_to_funds(classifier):
    trades = [trade("AAPL", 100), trade("MSFT", -50)]

    assert calculate_stock_profits(trades, classifier).eur == 100
    assert calculate_stock_losses(trades, classifier).eur == -50
    assert calculate_fund_gross_profits(trades, classifier).eur == 0
    assert calculate_fund_profits(trades, classifier).eur == 0
    assert calculate_fund_losses(trades, classifier).eur == 0


def test_fees_determine_result_sign_and_are_exempted(classifier):
    trades = [trade("SCHG", 1, fees=2)]

    assert calculate_fund_profits(trades, classifier).eur == 0
    assert calculate_fund_losses(trades, classifier).eur == pytest.approx(-0.7)


def test_mixed_fund_gain_and_loss_use_fifteen_percent_exemption(classifier):
    gains = [trade("AOR", 100, 120)]
    losses = [trade("AOR", -100, -120)]

    assert calculate_fund_profits(gains, classifier).eur == 85
    assert calculate_fund_profits(gains, classifier).usd == 102
    assert calculate_fund_losses(losses, classifier).eur == -85
    assert calculate_fund_losses(losses, classifier).usd == -102


def test_raw_stock_and_fund_results_reconcile_without_gaps_or_double_counting(classifier):
    trades = [
        trade("AAPL", 100),
        trade("SCHG", 80),
        trade("AOR", 60),
        trade("MSFT", -40),
        trade("PULS", -30),
        trade("SCHG", -20),
    ]

    raw_profits = sum(t.profit_eur - t.fees_eur for t in trades if t.profit_eur - t.fees_eur > 0)
    raw_losses = sum(t.profit_eur - t.fees_eur for t in trades if t.profit_eur - t.fees_eur < 0)

    assert (
        calculate_stock_profits(trades, classifier).eur
        + calculate_fund_gross_profits(trades, classifier).eur
    ) == raw_profits
    assert (
        calculate_stock_losses(trades, classifier).eur
        + calculate_fund_gross_losses(trades, classifier).eur
    ) == raw_losses
