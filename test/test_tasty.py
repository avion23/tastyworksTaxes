import pytest
import pandas as pd

from tastyworksTaxes.tasty import Tasty
from tastyworksTaxes.transaction import Transaction

class TestTasty:
    def test_money_movement_debit_interest(self):
        t = Tasty()
        debit_interest_transaction = Transaction.fromString("2019-08-16T23:00:00+0000,Money Movement,Withdrawal,,,,FROM 07/16 THRU 08/15 @ 8    %,-9.81,0,,0,0.00,,,,,,,123456,USD")
        t.moneyMovement(debit_interest_transaction)
        assert t.year(2019).debitInterest.eur == -8.856988082340196
        assert t.year(2019).debitInterest.usd == -9.81

    def test_money_movement_deposit_transfer(self):
        t = Tasty()
        deposit_transfer_transaction = Transaction.fromString("2018-03-08T23:00:00+0000,Money Movement,Transfer,,,,Wire Funds Received,1200,0,,0,0.00,,,,,,,123456,USD")
        t.moneyMovement(deposit_transfer_transaction)
        assert t.year(2018).transfer.eur == 966.10578858385
        assert t.year(2018).transfer.usd == 1200.0

    def test_money_movement_balance_adjustment(self):
        t = Tasty()
        balance_adjustment_transaction = Transaction.fromString("2018-03-26T15:09:00+0000,Money Movement,Balance Adjustment,,,,Regulatory fee adjustment,-0.01,0,,0,0.00,,,,,,,123456,USD")
        t.moneyMovement(balance_adjustment_transaction)
        assert t.year(2018).balanceAdjustment.eur == -0.008057368463459834
        assert t.year(2018).balanceAdjustment.usd == -0.01

    def test_money_movement_fee(self):
        t = Tasty()
        fee_transaction = Transaction.fromString("2018-03-23T22:00:00+0000,Money Movement,Fee,,LFIN,Equity,LONGFIN CORP,-43.24,0,,0,0.00,,LFIN,LFIN,,,,123456,USD")
        t.moneyMovement(fee_transaction)
        assert t.year(2018).fee.eur == -35.02348938927588
        assert t.year(2018).fee.usd == -43.24

    def test_money_movement_credit_interest(self):
        t = Tasty()
        credit_interest_transaction = Transaction.fromString("2020-12-16T23:00:00+0000,Money Movement,Credit Interest,,,,INTEREST ON CREDIT BALANCE,0.030,0,,0,0.000,,,,,,,123456,USD")
        t.moneyMovement(credit_interest_transaction)
        assert t.year(2020).creditInterest.eur == pytest.approx(0.02461235540241201)
        assert t.year(2020).creditInterest.usd == 0.03

    def test_money_movement_credit_interest_via_deposit(self):
        t = Tasty()
        deposit_transaction = Transaction.fromString("2019-10-16T23:00:00+0000,Money Movement,Deposit,,,,INTEREST ON CREDIT BALANCE,0.010,0,,0,0.000,,,,,,,123456,USD")
        t.moneyMovement(deposit_transaction)
        assert t.year(2019).creditInterest.eur == pytest.approx(0.009070294784580499)
        assert t.year(2019).creditInterest.usd == 0.01

    def test_money_movement_general_deposit(self):
        t = Tasty()
        deposit_transaction = Transaction.fromString("2024-03-07T20:03:00+0000,Money Movement,Deposit,,,,DEPOSIT,1000.00,0,,0,0.00,,,,,,,123456,USD")
        t.moneyMovement(deposit_transaction)
        assert t.year(2024).deposit.eur == pytest.approx(917.8522257916476)
        assert t.year(2024).deposit.usd == 1000.0

    def test_money_movement_debit_interest_merged2(self):
        t = Tasty()
        debit_interest_transaction = Transaction.fromString("2021-06-16T23:00:00+0000,Money Movement,Debit Interest,,,,FROM 05/16 THRU 06/15 @ 8    %,-0.87,0,,0,0.00,,,,,,,123456,USD")
        t.moneyMovement(debit_interest_transaction)
        assert t.year(2021).debitInterest.eur == pytest.approx(-0.7175849554602441)
        assert t.year(2021).debitInterest.usd == -0.87

    def test_money_movement_dividend(self):
        t = Tasty()
        dividend_transaction = Transaction.fromString("2021-07-06T23:00:00+0000,Money Movement,Dividend,,UWMC,Equity,UWM HOLDINGS CORPORATION,-3,0,,0,0.00,,UWMC,UWMC,,,,123456,USD")
        t.moneyMovement(dividend_transaction)
        assert t.year(2021).paidDividend.eur == pytest.approx(-2.5342118601115056)
        assert t.year(2021).paidDividend.usd == -3.0
        assert t.year(2021).dividend.usd == 0

    def test_dividend_withholding_is_not_netted_from_income(self):
        income = Transaction.fromString(
            "2025-10-10T23:00:00+0000,Money Movement,Dividend,,NVDY,Equity,"
            "TIDAL TRUST II,397.70,0,,0,0.00,,NVDY,NVDY,,,,123456,USD"
        )
        withholding = Transaction.fromString(
            "2025-10-10T23:17:42+0000,Money Movement,Dividend,,NVDY,Equity,"
            "TIDAL TRUST II,-59.66,0,,0,0.00,,NVDY,NVDY,,,,123456,USD"
        )
        t = Tasty()
        t.history = pd.DataFrame([income, withholding])

        t.processTransactionHistory()

        assert t.year(2025).fundDistributions.usd == 397.70
        assert t.year(2025).fundDistributionExempt.usd == 0
        assert t.year(2025).fundDistributionTaxable.usd == 397.70
        assert t.year(2025).dividend.usd == 0
        assert t.year(2025).withholdingTax.usd == 59.66
        assert t.year(2025).paidDividend.usd == 0

    def test_fund_and_stock_dividends_are_separated(self):
        fund = Transaction.fromString(
            "2025-10-10T23:00:00+0000,Money Movement,Dividend,,SCHG,Equity,"
            "SCHWAB ETF,100,0,,0,0.00,,SCHG,SCHG,,,,123456,USD"
        )
        stock = Transaction.fromString(
            "2025-10-10T23:00:00+0000,Money Movement,Dividend,,AAPL,Equity,"
            "APPLE INC,50,0,,0,0.00,,AAPL,AAPL,,,,123456,USD"
        )
        t = Tasty()

        t.moneyMovement(fund)
        t.moneyMovement(stock)

        values = t.year(2025)
        assert values.fundDistributions.usd == 100
        assert values.fundDistributionExempt.usd == 30
        assert values.fundDistributionTaxable.usd == 70
        assert values.dividend.usd == 50

    @pytest.mark.parametrize(
        "negative, expected_withholding, expected_paid",
        [(-15, 15, 0), (-150, 100, -50)],
    )
    def test_dividend_withholding_is_capped_by_positive_dividend(
        self, negative, expected_withholding, expected_paid
    ):
        income = Transaction.fromString(
            "2025-10-10T20:00:00+0000,Money Movement,Dividend,,AAPL,Equity,"
            "APPLE INC,100,0,,0,0.00,,AAPL,AAPL,,,,123456,USD"
        )
        negative_leg = Transaction.fromString(
            f"2025-10-10T23:17:42+0000,Money Movement,Dividend,,AAPL,Equity,"
            f"OTHER PAYMENT,{negative},0,,0,0.00,,AAPL,AAPL,,,,123456,USD"
        )
        t = Tasty()
        t.history = pd.DataFrame([income, negative_leg])

        t.processTransactionHistory()

        values = t.year(2025)
        assert values.dividend.usd == 100
        assert values.withholdingTax.usd == expected_withholding
        assert values.paidDividend.usd == expected_paid

    def test_money_movement_special_dividend_uses_fund_classification(self):
        t = Tasty()
        transaction = Transaction.fromString(
            "2025-12-17T19:00:00+0000,Money Movement,Special Dividend,,SCHG,Equity,"
            "Cash special dividend,100,0,,0,0.00,,SCHG,SCHG,,,,123456,USD"
        )

        t.moneyMovement(transaction)

        values = t.year(2025)
        assert values.dividend.usd == 0
        assert values.fundDistributions.usd == 100
        assert values.fundDistributionExempt.usd == 30
        assert values.fundDistributionTaxable.usd == 70

    def test_paired_special_dividend_bookkeeping_is_not_withholding(self):
        opening = Transaction.fromString(
            "2025-12-10T08:47:06-0300,Money Movement,Special Dividend,,"
            "TECL  251219C00131960,Equity Option,Special dividend: Open 1.0,"
            "275,0,,0,0.00,,TECL,TECL,12/19/25,131.96,C,123456,USD"
        )
        closing = Transaction.fromString(
            "2025-12-10T08:47:06-0300,Money Movement,Special Dividend,,"
            "TECL  251219C00140000,Equity Option,Special dividend: Close 1.0,"
            "-275,0,,0,0.00,,TECL,TECL,12/19/25,140,C,123456,USD"
        )
        t = Tasty()
        t.history = pd.DataFrame([opening, closing])

        t.processTransactionHistory()

        assert t.year(2025).dividend.usd == 0
        assert t.year(2025).withholdingTax.usd == 0
        assert t.year(2025).paidDividend.usd == 0

    def test_money_movement_deposit_via_withdrawal(self):
        t = Tasty()
        deposit_withdrawal_transaction = Transaction.fromString("2021-03-01T23:00:00+0000,Money Movement,Withdrawal,,,,Wire Funds Received,4770.4,0,,0,0.00,,,,,,,123456,USD")
        t.moneyMovement(deposit_withdrawal_transaction)
        assert t.year(2021).deposit.eur == pytest.approx(3957.8528167261256)
        assert t.year(2021).deposit.usd == 4770.4

    def test_money_movement_securities_lending_income(self):
        t = Tasty()
        lending_income_transaction = Transaction.fromString("2024-08-13T23:00:00+0000,Money Movement,Fully Paid Stock Lending Income,,,,FULLYPAID LENDING REBATE,0.20,0,,0,0.00,,,,,,,123456,USD")
        t.moneyMovement(lending_income_transaction)
        assert t.year(2024).securitiesLendingIncome.eur == pytest.approx(0.1829658768639649, abs=1e-5)
        assert t.year(2024).securitiesLendingIncome.usd == 0.2

    def test_symbol_change_close_is_processed_before_same_time_open(self):
        old_open = Transaction.fromString(
            "2024-01-02T09:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,OLD,Equity,Bought stock,-100,10,10,0,0,,OLD,OLD,,,,123456,USD"
        )
        new_open = Transaction.fromString(
            "2024-01-03T09:00:00+0000,Receive Deliver,Symbol Change,BUY_TO_OPEN,NEW,Equity,Symbol change open,-999,20,0,0,0,,NEW,NEW,,,,123456,USD"
        )
        old_close = Transaction.fromString(
            "2024-01-03T09:00:00+0000,Receive Deliver,Symbol Change,SELL_TO_CLOSE,OLD,Equity,Symbol change close,250,10,0,0,0,,OLD,OLD,,,,123456,USD"
        )
        t = Tasty()
        t.history = pd.DataFrame([old_open, new_open, old_close])

        t.processTransactionHistory()

        lots = t.position_manager.get_all_open_lots()
        assert [(lot.symbol, lot.quantity, lot.amount_usd) for lot in lots] == [
            ("NEW", 20, -100),
        ]
        assert t.position_manager._pending_symbol_change_lots == {}

    def test_multiple_same_time_symbol_changes_reject_distinct_amounts(self):
        def transaction(line):
            return Transaction.fromString(line)

        rows = [
            transaction("2024-01-02T09:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,OLD1,Equity,open,-100,10,10,0,0,,OLD1,OLD1,,,,1,USD"),
            transaction("2024-01-02T09:01:00+0000,Trade,Buy to Open,BUY_TO_OPEN,OLD2,Equity,open,-200,10,20,0,0,,OLD2,OLD2,,,,2,USD"),
            transaction("2024-02-01T09:00:00+0000,Receive Deliver,Symbol Change,SELL_TO_CLOSE,OLD1,Equity,close,100,10,0,0,0,,OLD1,OLD1,,,,3,USD"),
            transaction("2024-02-01T09:00:00+0000,Receive Deliver,Symbol Change,SELL_TO_CLOSE,OLD2,Equity,close,200,10,0,0,0,,OLD2,OLD2,,,,4,USD"),
            transaction("2024-02-01T09:00:00+0000,Receive Deliver,Symbol Change,BUY_TO_OPEN,NEW1,Equity,open,-100,10,0,0,0,,NEW1,NEW1,,,,5,USD"),
            transaction("2024-02-01T09:00:00+0000,Receive Deliver,Symbol Change,BUY_TO_OPEN,NEW2,Equity,open,-200,10,0,0,0,,NEW2,NEW2,,,,6,USD"),
        ]
        t = Tasty()
        t.history = pd.DataFrame(rows)

        with pytest.raises(ValueError, match="AMBIGUOUS OR UNMATCHED"):
            t.processTransactionHistory()

        assert t.position_manager.get_all_open_lots() == []

    def test_crossed_amounts_do_not_correlate_simultaneous_symbol_changes(self):
        rows = [
            Transaction.fromString("2024-01-02T09:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,OLD1,Equity,open,-100,10,10,0,0,,OLD1,OLD1,,,,1,USD"),
            Transaction.fromString("2024-02-01T09:00:00+0000,Receive Deliver,Symbol Change,SELL_TO_CLOSE,OLD1,Equity,close,100,10,0,0,0,,OLD1,OLD1,,,,2,USD"),
            Transaction.fromString("2024-02-01T09:00:00+0000,Receive Deliver,Symbol Change,SELL_TO_CLOSE,OLD2,Equity,close,200,10,0,0,0,,OLD2,OLD2,,,,3,USD"),
            Transaction.fromString("2024-02-01T09:00:00+0000,Receive Deliver,Symbol Change,BUY_TO_OPEN,NEW1,Equity,open,-200,10,0,0,0,,NEW1,NEW1,,,,4,USD"),
            Transaction.fromString("2024-02-01T09:00:00+0000,Receive Deliver,Symbol Change,BUY_TO_OPEN,NEW2,Equity,open,-100,10,0,0,0,,NEW2,NEW2,,,,5,USD"),
        ]
        t = Tasty()
        t.history = pd.DataFrame(rows)

        with pytest.raises(ValueError, match="AMBIGUOUS OR UNMATCHED"):
            t.processTransactionHistory()

        assert t.position_manager.get_all_open_lots() == []

    def test_unmatched_conversion_fails_before_processing(self):
        rows = [
            Transaction.fromString("2024-01-02T09:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,OLD,Equity,open,-100,10,10,0,0,,OLD,OLD,,,,1,USD"),
            Transaction.fromString("2024-02-01T09:00:00+0000,Receive Deliver,Symbol Change,SELL_TO_CLOSE,OLD,Equity,close,100,10,0,0,0,,OLD,OLD,,,,2,USD"),
        ]
        t = Tasty()
        t.history = pd.DataFrame(rows)

        with pytest.raises(ValueError, match="AMBIGUOUS OR UNMATCHED"):
            t.processTransactionHistory()

        assert t.position_manager.get_all_open_lots() == []

    def test_zero_quantity_conversion_with_basis_fails_without_ghost_lot(self):
        rows = [
            Transaction.fromString("2024-01-02T09:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,OLD,Equity,open,-100,10,10,0,0,,OLD,OLD,,,,1,USD"),
            Transaction.fromString("2024-02-01T09:00:00+0000,Receive Deliver,Symbol Change,SELL_TO_CLOSE,OLD,Equity,close,50,0,0,0,0,,OLD,OLD,,,,2,USD"),
            Transaction.fromString("2024-02-01T09:00:00+0000,Receive Deliver,Symbol Change,BUY_TO_OPEN,NEW,Equity,open,-50,0,0,0,0,,NEW,NEW,,,,3,USD"),
        ]
        t = Tasty()
        t.history = pd.DataFrame(rows)

        with pytest.raises(ValueError, match="finite nonzero quantity"):
            t.processTransactionHistory()

        assert t.position_manager.get_all_open_lots() == []

    def test_later_conversion_failure_rolls_back_all_processing_state(self):
        t = Tasty()
        t.position_manager.add_position(Transaction.fromString(
            "2023-12-01T09:00:00+0000,Trade,Buy to Open,BUY_TO_OPEN,KEEP,Equity,keep,-50,5,10,0,0,,KEEP,KEEP,,,,1,USD"
        ))
        manager = t.position_manager
        t.moneyMovement(Transaction.fromString(
            "2023-12-04T09:00:00+0000,Money Movement,Deposit,,,,seed,25,0,,0,0.00,,,,,,,2,USD"
        ))
        t.unverified_asset_symbols_by_year = {2023: {"KEEP"}}
        t.short_stock_trades_by_year = {2023: []}
        t._withholding_remaining = {("seed", "KEEP"): 7}
        t._asset_classification_checks = {("seed",)}
        original_state_objects = {
            "yearValues": t.yearValues,
            "unverified_asset_symbols_by_year": t.unverified_asset_symbols_by_year,
            "short_stock_trades_by_year": t.short_stock_trades_by_year,
            "_withholding_remaining": t._withholding_remaining,
            "_asset_classification_checks": t._asset_classification_checks,
        }
        rows = [
            Transaction.fromString("2024-01-02T09:00:00+0000,Money Movement,Dividend,,UNKNOWN,Equity,cash,100,0,,0,0,,UNKNOWN,UNKNOWN,,,,3,USD"),
            Transaction.fromString("2024-01-03T09:00:00+0000,Receive Deliver,Symbol Change,SELL_TO_CLOSE,MISSING,Equity,close,999,10,0,0,0,,MISSING,MISSING,,,,4,USD"),
            Transaction.fromString("2024-01-03T09:00:00+0000,Receive Deliver,Symbol Change,BUY_TO_OPEN,NEW,Equity,open,-1,10,0,0,0,,NEW,NEW,,,,5,USD"),
        ]
        t.history = pd.DataFrame(rows)

        with pytest.raises(ValueError, match="found no open position"):
            t.processTransactionHistory()

        assert t.position_manager is manager
        assert [
            (lot.symbol, lot.quantity, lot.amount_usd)
            for lot in manager.get_all_open_lots()
        ] == [("KEEP", 5, -50)]
        assert manager.closed_trades == []
        assert sorted(t.yearValues) == [2023]
        assert t.year(2023).deposit.usd == 25
        assert t.unverified_asset_symbols_by_year == {2023: {"KEEP"}}
        assert t.short_stock_trades_by_year == {2023: []}
        assert t._withholding_remaining == {("seed", "KEEP"): 7}
        assert t._asset_classification_checks == {("seed",)}
        for name, value in original_state_objects.items():
            assert getattr(t, name) is value
