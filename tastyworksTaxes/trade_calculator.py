from typing import List
import logging
from tastyworksTaxes.money import Money
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.fifo_processor import TradeResult
from datetime import date, datetime

logger = logging.getLogger(__name__)

def sum_money_from_trades(trades: List[TradeResult]) -> Money:
    if not trades:
        return Money()
    return Money(
        usd=sum(t.profit_usd - t.fees_usd for t in trades),
        eur=sum(t.profit_eur - t.fees_eur for t in trades)
    )

def sum_fees_from_trades(trades: List[TradeResult]) -> Money:
    if not trades:
        return Money()
    return Money(
        usd=sum(t.fees_usd for t in trades),
        eur=sum(t.fees_eur for t in trades)
    )

def get_option_trades(trades: List[TradeResult]) -> List[TradeResult]:
    return [t for t in trades if t.position_type in [PositionType.call, PositionType.put]]

def get_stock_trades(trades: List[TradeResult]) -> List[TradeResult]:
    return [t for t in trades if t.position_type == PositionType.stock]

def get_profitable_trades(trades: List[TradeResult]) -> List[TradeResult]:
    return [t for t in trades if _net_profit_eur(t) > 0]

def get_loss_trades(trades: List[TradeResult]) -> List[TradeResult]:
    return [t for t in trades if _net_profit_eur(t) <= 0]

def _net_profit_eur(trade: TradeResult) -> float:
    return trade.profit_eur - trade.fees_eur

def _trade_date(trade: TradeResult) -> date:
    value = trade.closing_date
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _is_taxable_capital_asset(trade: TradeResult, classifier) -> bool:
    return classifier.get_tax_category(
        classifier.classify_for_tax(trade.symbol, trade.position_type, _trade_date(trade))
    ) != "SO"

def get_long_trades(trades: List[TradeResult]) -> List[TradeResult]:
    return [t for t in trades if t.quantity > 0]

def get_short_trades(trades: List[TradeResult]) -> List[TradeResult]:
    return [t for t in trades if t.quantity < 0]

def get_worthless_expiry_trades(trades: List[TradeResult]) -> List[TradeResult]:
    return [t for t in trades if t.worthless_expiry]

def get_non_worthless_expiry_trades(trades: List[TradeResult]) -> List[TradeResult]:
    return [t for t in trades if not t.worthless_expiry]

def calculate_combined_sum(trades: List[TradeResult]) -> Money:
    return sum_money_from_trades(trades)

def calculate_option_sum(trades: List[TradeResult]) -> Money:
    option_trades = get_option_trades(trades)
    return sum_money_from_trades(option_trades)

def calculate_long_option_profits(trades: List[TradeResult]) -> Money:
    filtered_trades = get_long_trades(
        get_profitable_trades(
            get_non_worthless_expiry_trades(
                get_option_trades(trades)
            )
        )
    )
    return sum_money_from_trades(filtered_trades)

def calculate_long_option_losses(trades: List[TradeResult]) -> Money:
    filtered_trades = get_long_trades(
        get_loss_trades(
            get_non_worthless_expiry_trades(
                get_option_trades(trades)
            )
        )
    )
    return sum_money_from_trades(filtered_trades)

def calculate_long_option_total_losses(trades: List[TradeResult]) -> Money:
    filtered_trades = get_long_trades(
        get_loss_trades(
            get_worthless_expiry_trades(
                get_option_trades(trades)
            )
        )
    )
    return sum_money_from_trades(filtered_trades)

def calculate_short_option_profits(trades: List[TradeResult]) -> Money:
    filtered_trades = get_short_trades(
        get_profitable_trades(
            get_option_trades(trades)
        )
    )
    return sum_money_from_trades(filtered_trades)

def calculate_short_option_losses(trades: List[TradeResult]) -> Money:
    filtered_trades = get_short_trades(
        get_loss_trades(
            get_option_trades(trades)
        )
    )
    return sum_money_from_trades(filtered_trades)

def calculate_option_differential(trades: List[TradeResult]) -> Money:
    option_trades = get_option_trades(trades)
    
    if not option_trades:
        return Money()
    
    negative_sum = sum_money_from_trades(get_loss_trades(option_trades))
    positive_sum = sum_money_from_trades(get_profitable_trades(option_trades))
    
    return Money(
        usd=min(abs(negative_sum.usd), abs(positive_sum.usd)),
        eur=min(abs(negative_sum.eur), abs(positive_sum.eur))
    )

def calculate_stock_loss(trades: List[TradeResult], classifier=None) -> Money:
    filtered_trades = [
        trade for trade in get_stock_trades(trades)
        if _net_profit_eur(trade) <= 0
        and (classifier is None or _is_taxable_capital_asset(trade, classifier))
    ]
    if not filtered_trades:
        return Money()

    if classifier is not None:
        total_usd = 0.0
        total_eur = 0.0
        for trade in filtered_trades:
            taxable_portion = 1.0 - (
                classifier.get_exemption_percentage_for(
                    trade.symbol, trade.position_type, _trade_date(trade)
                ) / 100.0
            )
            total_usd += (trade.profit_usd - trade.fees_usd) * taxable_portion
            total_eur += (trade.profit_eur - trade.fees_eur) * taxable_portion
        return Money(usd=total_usd, eur=total_eur)

    return Money(
        usd=sum(t.profit_usd - t.fees_usd for t in filtered_trades),
        eur=sum(t.profit_eur - t.fees_eur for t in filtered_trades)
    )

def calculate_stock_fees(trades: List[TradeResult]) -> Money:
    stock_trades = get_stock_trades(trades)
    return sum_fees_from_trades(stock_trades)

def calculate_other_fees(trades: List[TradeResult]) -> Money:
    option_trades = get_option_trades(trades)
    return sum_fees_from_trades(option_trades)

def calculate_fees_sum(trades: List[TradeResult]) -> Money:
    return sum_fees_from_trades(trades)

def calculate_gross_equity_etf_profits(trades: List[TradeResult], classifier) -> Money:
    profitable_stock_trades = [
        trade for trade in get_stock_trades(trades) if _net_profit_eur(trade) > 0
    ]
    if not profitable_stock_trades:
        return Money()
    
    total_eur = 0.0
    total_usd = 0.0
    
    for trade in profitable_stock_trades:
        classification = classifier.classify_for_tax(
            trade.symbol, trade.position_type, _trade_date(trade)
        )
        
        if classification == 'EQUITY_ETF':
            total_eur += trade.profit_eur
            total_usd += trade.profit_usd
    
    return Money(usd=total_usd, eur=total_eur)

def calculate_equity_etf_profits(trades: List[TradeResult], classifier) -> Money:
    profitable_stock_trades = [
        trade for trade in get_stock_trades(trades) if _net_profit_eur(trade) > 0
    ]
    if not profitable_stock_trades:
        return Money()

    total_taxable_eur = 0.0
    total_taxable_usd = 0.0

    for trade in profitable_stock_trades:
        classification = classifier.classify_for_tax(
            trade.symbol, trade.position_type, _trade_date(trade)
        )

        if classification == 'EQUITY_ETF':
            exemption_pct = classifier.get_exemption_percentage_for(
                trade.symbol, trade.position_type, _trade_date(trade)
            )
            taxable_portion = 1.0 - (exemption_pct / 100.0)

            net_profit_eur = trade.profit_eur - trade.fees_eur
            net_profit_usd = trade.profit_usd - trade.fees_usd

            total_taxable_eur += net_profit_eur * taxable_portion
            total_taxable_usd += net_profit_usd * taxable_portion

            logger.debug(f"Applied {exemption_pct}% Teilfreistellung to {trade.symbol}")

    return Money(usd=total_taxable_usd, eur=total_taxable_eur)

def calculate_other_stock_and_bond_profits(trades: List[TradeResult], classifier) -> Money:
    profitable_stock_trades = [
        trade for trade in get_stock_trades(trades) if _net_profit_eur(trade) > 0
    ]
    if not profitable_stock_trades:
        return Money()

    total_eur = 0.0
    total_usd = 0.0

    for trade in profitable_stock_trades:
        classification = classifier.classify_for_tax(
            trade.symbol, trade.position_type, _trade_date(trade)
        )

        if classification == "EQUITY_ETF" or classifier.get_tax_category(classification) == "SO":
            continue

        exemption_pct = classifier.get_exemption_percentage_for(
            trade.symbol, trade.position_type, _trade_date(trade)
        )
        taxable_portion = 1.0 - (exemption_pct / 100.0)
        total_eur += (trade.profit_eur - trade.fees_eur) * taxable_portion
        total_usd += (trade.profit_usd - trade.fees_usd) * taxable_portion

    return Money(usd=total_usd, eur=total_eur)
