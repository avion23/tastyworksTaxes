from typing import List
from tastyworksTaxes.money import Money
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.fifo_processor import TradeResult
from datetime import date, datetime

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
    return [
        t for t in trades
        if t.position_type in [PositionType.call, PositionType.put]
        and not t.settled_by_exercise
    ]

def get_stock_trades(trades: List[TradeResult]) -> List[TradeResult]:
    return [t for t in trades if t.position_type == PositionType.stock]

def get_profitable_trades(trades: List[TradeResult]) -> List[TradeResult]:
    return [t for t in trades if _net_profit_eur(t) > 0]

def get_loss_trades(trades: List[TradeResult]) -> List[TradeResult]:
    return [t for t in trades if _net_profit_eur(t) < 0]

def _net_profit_eur(trade: TradeResult) -> float:
    return trade.profit_eur - trade.fees_eur

def _trade_date(trade: TradeResult) -> date:
    value = trade.closing_date
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


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

def _classification(trade: TradeResult, classifier) -> str:
    return classifier.classify_for_tax(
        trade.symbol, trade.position_type, _trade_date(trade)
    )


def _is_fund(trade: TradeResult, classifier) -> bool:
    return classifier.get_tax_category(_classification(trade, classifier)) == "KAP-INV"


def _calculate_stock_result(trades, classifier, profitable: bool) -> Money:
    filtered = [
        trade for trade in get_stock_trades(trades)
        if (_net_profit_eur(trade) > 0) == profitable
        and _net_profit_eur(trade) != 0
        and _classification(trade, classifier) == "INDIVIDUAL_STOCK"
    ]
    return sum_money_from_trades(filtered)


def calculate_stock_profits(trades: List[TradeResult], classifier) -> Money:
    return _calculate_stock_result(trades, classifier, True)


def calculate_stock_losses(trades: List[TradeResult], classifier) -> Money:
    return _calculate_stock_result(trades, classifier, False)


def _calculate_fund_result(trades, classifier, profitable: bool, taxable: bool) -> Money:
    total_usd = 0.0
    total_eur = 0.0
    for trade in get_stock_trades(trades):
        if (_net_profit_eur(trade) > 0) != profitable or _net_profit_eur(trade) == 0:
            continue
        if not _is_fund(trade, classifier):
            continue
        taxable_portion = 1.0
        if taxable:
            taxable_portion -= classifier.get_exemption_percentage_for(
                trade.symbol, trade.position_type, _trade_date(trade)
            ) / 100.0
        total_usd += (trade.profit_usd - trade.fees_usd) * taxable_portion
        total_eur += (trade.profit_eur - trade.fees_eur) * taxable_portion
    return Money(usd=total_usd, eur=total_eur)


def calculate_fund_profits(trades: List[TradeResult], classifier) -> Money:
    return _calculate_fund_result(trades, classifier, True, True)


def calculate_fund_losses(trades: List[TradeResult], classifier) -> Money:
    return _calculate_fund_result(trades, classifier, False, True)


def calculate_fund_gross_profits(trades: List[TradeResult], classifier) -> Money:
    return _calculate_fund_result(trades, classifier, True, False)


def calculate_fund_gross_losses(trades: List[TradeResult], classifier) -> Money:
    return _calculate_fund_result(trades, classifier, False, False)

def calculate_stock_fees(trades: List[TradeResult]) -> Money:
    stock_trades = get_stock_trades(trades)
    return sum_fees_from_trades(stock_trades)

def calculate_other_fees(trades: List[TradeResult]) -> Money:
    option_trades = get_option_trades(trades)
    return sum_fees_from_trades(option_trades)

def calculate_fees_sum(trades: List[TradeResult]) -> Money:
    return sum_fees_from_trades(trades)
