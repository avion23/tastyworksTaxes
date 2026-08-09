import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tastyworksTaxes.values import Values
from dataclasses_json import dataclass_json
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


def _round_for_presentation(value: float) -> float:
    """Round only rendered values and normalize rounded negative zero."""
    rounded = round(value, 2)
    return 0.0 if rounded == 0 else rounded


def _format_german_number(value: float) -> str:
    """Format a number deterministically without changing process-wide locale."""
    value = _round_for_presentation(value)
    return f"{value:,.2f}".translate(str.maketrans({",": ".", ".": ","}))


def _format_report_line(label: str, value: float, width: int = 40) -> str:
    """Helper to format tax report lines consistently"""
    value = _round_for_presentation(value)
    return f"{label:<{width}}{value: .2f}\n"


def _format_german_report_line(label: str, value: float, width: int = 40) -> str:
    value = _round_for_presentation(value)
    formatted = _format_german_number(abs(value))
    sign = "-" if value < 0 else " "
    return f"{label:<{width}}{sign}{formatted}\n"


@dataclass_json
@dataclass
class GermanTaxReport(object):
    """ represents the german tax report

    Sorry for the german variable names. There is also an english version and I've created translation functions

    Example output:
    Einzahlungen
    Auszahlungen
    Brokergebühren
    Alle Gebühren in USD
    Alle Gebühren in Euro
    Währungsgewinne USD
    Währungsgewinne USD (steuerfrei)
    Währungsgewinne USD Gesamt
    Krypto-Gewinne
    Krypto-Verluste
    Anlage SO
    Anlage SO Steuerbetrag
    Anlage SO Verlustvortrag
    Investmentfondsgewinne
    Investmentfondsverluste
    Anlage KAP-INV
    Aktiengewinne (Z20)
    Aktienverluste (Z23)
    Aktien Gesamt
    Aktien Steuerbetrag
    Aktien Verlustvortrag
    Sonstige Gewinne
    Sonstige Verluste
    Sonstige Gesamt
    Stillhalter-Gewinne
    Stillhalter-Verluste
    Stillhalter Gesamt
    Durchschnitt behaltene Prämien pro Tag
    Stillhalter-Gewinne Calls (FIFO)
    Stillhalter-Verluste Calls (FIFO)
    Stillhalter Calls Gesamt (FIFO)
    Stillhalter-Gewinne Puts (FIFO)
    Stillhalter-Verluste Puts (FIFO)
    Stillhalter Puts Gesamt (FIFO)
    Stillhalter-Gewinne (FIFO)
    Stillhalter-Verluste (FIFO)
    Stillhalter Gesamt (FIFO)
    Long-Optionen-Gewinne
    Long-Optionen-Verluste
    Long-Optionen Gesamt
    Future-Gewinne
    Future-Verluste
    Future Gesamt
    zusätzliche Ordergebühren
    Dividenden
    bezahlte Dividenden
    Quellensteuer (Z41)
    Zinseinnahmen
    Zinsausgaben
    Zinsen Gesamt
    Z19 Ausländische Kapitalerträge
    Z21 Termingeschäftsgewinne+Stillhalter
    Z24 Termingeschäftsverluste
    Cash Balance USD
    Net Liquidating Value

    Z21/Z24 form mapping (Anlage KAP):
      Until VZ 2024 the gains below were reported in Zeile 21 and the losses in
      Zeile 24. The JStG 2024 (BGBl. 2024 I Nr. 387, § 52 Abs. 28 Sätze 25 und 26
      EStG -> applies to all open cases incl. VZ 2024 and 2025) removed the
      separate Termingeschäfte loss pot, so Anlage KAP dropped Zeile 21 and 24
      from VZ 2025 onward. The values are still computed here for traceability.
      For VZ 2025+: gains AND losses together form the Zeile 19 net saldo
      (Nettoertrag); the Termingeschäftsverluste are ADDITIONALLY broken out in
      Zeile 22 (Verluste ohne Aktienveräußerungen). Stock losses stay in Zeile 23
      and remain restricted to stock gains (§ 20 Abs. 6 Satz 4 EStG).
    """
    einzahlungen: float = 0
    auszahlungen: float = 0
    brokergebuehren: float = 0
    alle_gebuehren_in_usd: float = 0
    alle_gebuehren_in_euro: float = 0
    waehrungsgewinne_usd: float = 0
    waehrungsgewinne_usd_steuerfrei: float = 0
    waehrungsgewinne_usd_gesamt: float = 0
    krypto_gewinne: float = 0
    krypto_verluste: float = 0
    anlage_so: float = 0
    anlage_so_steuerbetrag: float = 0
    anlage_so_verlustvortrag: float = 0
    investmentfondsgewinne: float = 0
    investmentfondsverluste: float = 0
    anlage_kap_inv: float = 0
    fondsausschuettungen_brutto: float = 0
    fondsausschuettungen_steuerfrei: float = 0
    fondsausschuettungen_steuerpflichtig: float = 0
    aktiengewinne_z20: float = 0
    aktienverluste_z23: float = 0
    aktien_gesamt: float = 0
    aktien_steuerbetrag: float = 0
    aktien_verlustvortrag: float = 0
    sonstige_gewinne: float = 0
    sonstige_verluste: float = 0
    sonstige_gesamt: float = 0
    stillhalter_gewinne: float = 0
    stillhalter_verluste: float = 0
    stillhalter_gesamt: float = 0
    durchschnitt_behaltene_praemien_pro_tag: float = 0
    stillhalter_gewinne_calls_fifo: float = 0
    stillhalter_verluste_calls_fifo: float = 0
    stillhalter_calls_gesamt_fifo: float = 0
    stillhalter_gewinne_puts_fifo: float = 0
    stillhalter_verluste_puts_fifo: float = 0
    stillhalter_puts_gesamt_fifo: float = 0
    stillhalter_gewinne_fifo: float = 0
    stillhalter_verluste_fifo: float = 0
    stillhalter_gesamt_fifo: float = 0
    long_optionen_gewinne: float = 0
    long_optionen_verluste: float = 0
    long_optionen_verfallverluste: float = 0
    long_optionen_gesamt: float = 0
    future_gewinne: float = 0
    future_verluste: float = 0
    future_gesamt: float = 0
    zusatzliche_ordergebuehren: float = 0
    dividenden: float = 0
    bezahlte_dividenden: float = 0
    quellensteuer_z41: float = 0
    zinseinnahmen: float = 0
    zinsausgaben: float = 0
    zinsen_gesamt: float = 0
    z19_auslaendische_kapitalertraege: float = 0
    # legacy Z21/Z24 names kept; Anlage KAP removed these lines from VZ 2025
    # (JStG 2024). See class docstring for the current form mapping.
    z21_termingeschaefsgewinne: float = 0
    z24_termingeschaefte_verluste: float = 0
    kap_kap_inv: float = 0
    kap_kap_inv_kerst_soli: float = 0
    kap_kap_inv_verlustvortrag: float = 0
    cash_balance_usd: float = 0
    net_liquidating_value: float = 0
    wertpapierleihe_einkommen: float = 0

    def __str__(self) -> str:
        fields = [
            ('Einzahlungen', self.einzahlungen),
            ('Auszahlungen', self.auszahlungen),
            ('Aktiengebühren (Info; bereits im Nettoergebnis)', self.brokergebuehren),
            ('Alle Gebühren in USD (Info; Handelsgebühren bereits im Nettoergebnis)', self.alle_gebuehren_in_usd),
            ('Alle Gebühren in EUR (Info; Handelsgebühren bereits im Nettoergebnis)', self.alle_gebuehren_in_euro),
            ('Währungsgewinne USD', self.waehrungsgewinne_usd),
            ('Währungsgewinne USD steuerfrei', self.waehrungsgewinne_usd_steuerfrei),
            ('Währungsgewinne USD Gesamt', self.waehrungsgewinne_usd_gesamt),
            ('Krypto Gewinne', self.krypto_gewinne),
            ('Krypto Verluste', self.krypto_verluste),
            ('Anlage SO', self.anlage_so),
            ('Anlage SO Steuerbetrag', self.anlage_so_steuerbetrag),
            ('Anlage SO Verlustvortrag', self.anlage_so_verlustvortrag),
            ('Investmentfondsgewinne', self.investmentfondsgewinne),
            ('Investmentfondsverluste', self.investmentfondsverluste),
            ('Anlage KAP-INV', self.anlage_kap_inv),
            ('Fondsausschüttungen brutto', self.fondsausschuettungen_brutto),
            ('Fondsausschüttungen steuerfrei', self.fondsausschuettungen_steuerfrei),
            ('Fondsausschüttungen steuerpflichtig', self.fondsausschuettungen_steuerpflichtig),
            ('Aktiengewinne Z20', self.aktiengewinne_z20),
            ('Aktienverluste Z23', self.aktienverluste_z23),
            ('Aktien Gesamt', self.aktien_gesamt),
            ('Aktien Steuerbetrag', self.aktien_steuerbetrag),
            ('Aktien Verlustvortrag', self.aktien_verlustvortrag),
            ('Sonstige Gewinne', self.sonstige_gewinne),
            ('Sonstige Verluste', self.sonstige_verluste),
            ('Sonstige Gesamt', self.sonstige_gesamt),
            ('Stillhalter Gewinne', self.stillhalter_gewinne),
            ('Stillhalter Verluste', self.stillhalter_verluste),
            ('Stillhalter Gesamt', self.stillhalter_gesamt),
            ('Durchschnitt behaltene Prämien pro Tag', self.durchschnitt_behaltene_praemien_pro_tag),
            ('Stillhalter Gewinne Calls (FIFO)', self.stillhalter_gewinne_calls_fifo),
            ('Stillhalter Verluste Calls (FIFO)', self.stillhalter_verluste_calls_fifo),
            ('Stillhalter Calls Gesamt (FIFO)', self.stillhalter_calls_gesamt_fifo),
            ('Stillhalter Gewinne Puts (FIFO)', self.stillhalter_gewinne_puts_fifo),
            ('Stillhalter Verluste Puts (FIFO)', self.stillhalter_verluste_puts_fifo),
            ('Stillhalter Puts Gesamt (FIFO)', self.stillhalter_puts_gesamt_fifo),
            ('Stillhalter-Gewinne (FIFO)', self.stillhalter_gewinne_fifo),
            ('Stillhalter-Verluste (FIFO)', self.stillhalter_verluste_fifo),
            ('Stillhalter-Gesamt (FIFO)', self.stillhalter_gesamt_fifo),
            ('Long-Optionen-Gewinne', self.long_optionen_gewinne),
            ('Long-Optionen-Verluste', self.long_optionen_verluste),
            ('Long-Optionen-Verluste aus wertlosem Verfall', self.long_optionen_verfallverluste),
            ('Long-Optionen-Gesamt', self.long_optionen_gesamt),
            ('Future-Gewinne', self.future_gewinne),
            ('Future-Verluste', self.future_verluste),
            ('Future-Gesamt', self.future_gesamt),
            ('Optionsgebühren (Info; bereits im Nettoergebnis)', self.zusatzliche_ordergebuehren),
            ('Dividenden', self.dividenden),
            ('bezahlte Dividenden', self.bezahlte_dividenden),
            ('Quellensteuer Z41', self.quellensteuer_z41),
            ('Zinseinnahmen', self.zinseinnahmen),
            ('Zinsausgaben', self.zinsausgaben),
            ('Zinsen insgesamt', self.zinsen_gesamt),
            ('Z19 Ausländische Kapitalerträge', self.z19_auslaendische_kapitalertraege),
            ('Z21 Termingeschäfte+Stillhalter', self.z21_termingeschaefsgewinne),
            ('Z24 Termingeschäftsverluste', self.z24_termingeschaefte_verluste),
            ('Cash Balance USD', self.cash_balance_usd),
            ('Net Liquidating Value', self.net_liquidating_value),
            ('Wertpapierleihe Einkommen', self.wertpapierleihe_einkommen),
        ]
        return (
            ''.join(_format_german_report_line(label, value) for label, value in fields)
            + 'NOTE: Soli/KESt are not computed; the Finanzamt computes German tax.\n'
            + 'NOTE: Since VZ 2025 (JStG 2024) Anlage KAP has no Zeile 21/24. '
            'Gains and losses together form the Zeile 19 net saldo; report the '
            'Termingeschäftsverluste additionally in Zeile 22. Stock losses (Z23) '
            'stay restricted to stock gains (§ 20 Abs. 6 S. 4 EStG).\n'
        )


@dataclass_json
@dataclass
class EnglishTaxReport(object):
    deposits: float = 0
    withdrawals: float = 0
    broker_fees: float = 0
    all_fees_in_usd: float = 0
    all_fees_in_euro: float = 0
    currency_gains_usd: float = 0
    currency_gains_usd_tax_free: float = 0
    currency_gains_usd_total: float = 0
    crypto_gains: float = 0
    crypto_losses: float = 0
    investment_so: float = 0
    investment_so_tax_amount: float = 0
    investment_so_loss_carryforward: float = 0
    investment_fund_gains: float = 0
    investment_fund_losses: float = 0
    investment_kap_inv: float = 0
    fund_distributions_gross: float = 0
    fund_distributions_exempt: float = 0
    fund_distributions_taxable: float = 0
    stock_gains_z20: float = 0
    stock_losses_z23: float = 0
    stock_total: float = 0
    stock_tax_amount: float = 0
    stock_loss_carryforward: float = 0
    other_gains: float = 0
    other_losses: float = 0
    other_total: float = 0
    option_holder_gains: float = 0
    option_holder_losses: float = 0
    option_holder_total: float = 0
    average_held_premium_per_day: float = 0
    option_holder_gains_calls_fifo: float = 0
    option_holder_losses_calls_fifo: float = 0
    option_holder_calls_total_fifo: float = 0
    option_holder_gains_puts_fifo: float = 0
    option_holder_losses_puts_fifo: float = 0
    option_holder_puts_total_fifo: float = 0
    option_holder_gains_fifo: float = 0
    option_holder_losses_fifo: float = 0
    option_holder_total_fifo: float = 0
    long_option_gains: float = 0
    long_option_losses: float = 0
    long_option_worthless_expiry_losses: float = 0
    long_option_total: float = 0
    future_gains: float = 0
    future_losses: float = 0
    future_total: float = 0
    additional_order_fees: float = 0
    dividends: float = 0
    paid_dividends: float = 0
    withholding_tax_z41: float = 0
    interest_income: float = 0
    interest_expenses: float = 0
    interest_total: float = 0
    z19_foreign_capital_gains: float = 0
    z21_term_gains: float = 0
    z24_term_losses: float = 0
    kap_kap_inv: float = 0
    kap_kap_inv_kerst_soli: float = 0
    kap_kap_inv_loss_carryforward: float = 0
    cash_balance_usd: float = 0
    net_liquidating_value: float = 0
    securities_lending_income: float = 0

    def __str__(self) -> str:
        fields = [
            ('deposits', self.deposits),
            ('withdrawals', self.withdrawals),
            ('stock fees (info; already included in net P&L)', self.broker_fees),
            ('all fees in USD (info; trade fees already included in net P&L)', self.all_fees_in_usd),
            ('all fees in EUR (info; trade fees already included in net P&L)', self.all_fees_in_euro),
            ('currency gains usd', self.currency_gains_usd),
            ('currency gains usd tax free', self.currency_gains_usd_tax_free),
            ('currency gains usd total', self.currency_gains_usd_total),
            ('crypto gains', self.crypto_gains),
            ('crypto losses', self.crypto_losses),
            ('investment so', self.investment_so),
            ('investment so tax amount', self.investment_so_tax_amount),
            ('investment so loss carryforward', self.investment_so_loss_carryforward),
            ('investment fund gains', self.investment_fund_gains),
            ('investment fund losses', self.investment_fund_losses),
            ('investment kap inv', self.investment_kap_inv),
            ('fund distributions gross', self.fund_distributions_gross),
            ('fund distributions exempt', self.fund_distributions_exempt),
            ('fund distributions taxable', self.fund_distributions_taxable),
            ('stock gains z20', self.stock_gains_z20),
            ('stock losses z23', self.stock_losses_z23),
            ('stock total', self.stock_total),
            ('stock tax amount', self.stock_tax_amount),
            ('stock loss carryforward', self.stock_loss_carryforward),
            ('other gains', self.other_gains),
            ('other losses', self.other_losses),
            ('other total', self.other_total),
            ('short option writer gains', self.option_holder_gains),
            ('short option writer losses', self.option_holder_losses),
            ('short option writer total', self.option_holder_total),
            ('average held premium per day', self.average_held_premium_per_day),
            ('short call writer gains fifo', self.option_holder_gains_calls_fifo),
            ('short call writer losses fifo', self.option_holder_losses_calls_fifo),
            ('short call writer total fifo', self.option_holder_calls_total_fifo),
            ('short put writer gains fifo', self.option_holder_gains_puts_fifo),
            ('short put writer losses fifo', self.option_holder_losses_puts_fifo),
            ('short put writer total fifo', self.option_holder_puts_total_fifo),
            ('short option writer gains fifo', self.option_holder_gains_fifo),
            ('short option writer losses fifo', self.option_holder_losses_fifo),
            ('short option writer total fifo', self.option_holder_total_fifo),
            ('long option gains', self.long_option_gains),
            ('long option losses', self.long_option_losses),
            ('long option worthless-expiry losses', self.long_option_worthless_expiry_losses),
            ('long option total', self.long_option_total),
            ('future gains', self.future_gains),
            ('future losses', self.future_losses),
            ('future total', self.future_total),
            ('option fees (info; already included in net P&L)', self.additional_order_fees),
            ('dividends', self.dividends),
            ('paid dividends', self.paid_dividends),
            ('withholding tax z41', self.withholding_tax_z41),
            ('interest income', self.interest_income),
            ('interest expenses', self.interest_expenses),
            ('interest total', self.interest_total),
            ('z19 foreign capital gains', self.z19_foreign_capital_gains),
            ('z21 term gains', self.z21_term_gains),
            ('z24 term losses', self.z24_term_losses),
            ('cash balance usd', self.cash_balance_usd),
            ('net liquidating value', self.net_liquidating_value),
            ('securities lending income', self.securities_lending_income),
        ]
        return ''.join(_format_report_line(label, value) for label, value in fields)


class Printer(object):
    def __init__(self, values: Values, closed_trades: list) -> None:
        self.values = values
        self.closed_trades = closed_trades

    def generateEnglishTaxReport(self) -> EnglishTaxReport:
        report = EnglishTaxReport()
        report.deposits = self.values.deposit.eur
        report.withdrawals = self.values.withdrawal.eur
        report.broker_fees = self.values.stockFees.eur
        report.all_fees_in_usd = self.values.fee.usd
        report.all_fees_in_euro = self.values.fee.eur
        report.interest_income = self.values.creditInterest.eur
        report.interest_expenses = self.values.debitInterest.eur
        report.dividends = self.values.dividend.eur
        report.paid_dividends = self.values.paidDividend.eur
        report.withholding_tax_z41 = self.values.withholdingTax.eur
        report.additional_order_fees = self.values.otherFees.eur
        report.stock_gains_z20 = self.values.stockProfits.eur
        report.stock_losses_z23 = self.values.stockLosses.eur
        report.stock_total = self.values.stockProfits.eur + self.values.stockLosses.eur
        report.investment_fund_gains = self.values.fundProfits.eur
        report.investment_fund_losses = self.values.fundLosses.eur
        report.fund_distributions_gross = self.values.fundDistributions.eur
        report.fund_distributions_exempt = self.values.fundDistributionExempt.eur
        report.fund_distributions_taxable = self.values.fundDistributionTaxable.eur
        report.investment_kap_inv = (
            self.values.fundProfits.eur
            + self.values.fundLosses.eur
            + self.values.fundDistributionTaxable.eur
        )
        report.option_holder_gains = self.values.shortOptionProfits.eur
        report.option_holder_losses = self.values.shortOptionLosses.eur
        report.option_holder_total = (
            self.values.shortOptionProfits.eur
            + self.values.shortOptionLosses.eur
        )
        report.long_option_gains = self.values.longOptionProfits.eur
        report.long_option_losses = self.values.longOptionLosses.eur
        report.long_option_worthless_expiry_losses = self.values.longOptionTotalLosses.eur
        report.long_option_total = (
            self.values.longOptionProfits.eur
            + self.values.longOptionLosses.eur
            + self.values.longOptionTotalLosses.eur
        )
        report.z21_term_gains = self.values.z21_termingeschaefsgewinne.eur
        report.z24_term_losses = self.values.z24_termingeschaefte_verluste.eur
        report.securities_lending_income = self.values.securitiesLendingIncome.eur
        report.interest_total = self.values.creditInterest.eur + self.values.debitInterest.eur
        report.z19_foreign_capital_gains = (
            self.values.dividend.eur
            + self.values.creditInterest.eur
            + self.values.securitiesLendingIncome.eur
            + self.values.fundDistributionTaxable.eur
        )
        return report

    def generateGermanTaxReport(self) -> GermanTaxReport:
        report = GermanTaxReport()
        report.einzahlungen = self.values.deposit.eur
        report.auszahlungen = self.values.withdrawal.eur
        report.brokergebuehren = self.values.stockFees.eur
        report.alle_gebuehren_in_usd = self.values.fee.usd
        report.alle_gebuehren_in_euro = self.values.fee.eur
        report.zinseinnahmen = self.values.creditInterest.eur
        report.zinsausgaben = self.values.debitInterest.eur
        report.dividenden = self.values.dividend.eur
        report.bezahlte_dividenden = self.values.paidDividend.eur
        report.quellensteuer_z41 = self.values.withholdingTax.eur
        report.zusatzliche_ordergebuehren = self.values.otherFees.eur
        report.aktiengewinne_z20 = self.values.stockProfits.eur
        report.aktienverluste_z23 = self.values.stockLosses.eur
        report.aktien_gesamt = self.values.stockProfits.eur + self.values.stockLosses.eur
        report.investmentfondsgewinne = self.values.fundProfits.eur
        report.investmentfondsverluste = self.values.fundLosses.eur
        report.fondsausschuettungen_brutto = self.values.fundDistributions.eur
        report.fondsausschuettungen_steuerfrei = self.values.fundDistributionExempt.eur
        report.fondsausschuettungen_steuerpflichtig = self.values.fundDistributionTaxable.eur
        report.anlage_kap_inv = (
            self.values.fundProfits.eur
            + self.values.fundLosses.eur
            + self.values.fundDistributionTaxable.eur
        )
        report.stillhalter_gewinne = self.values.shortOptionProfits.eur
        report.stillhalter_verluste = self.values.shortOptionLosses.eur
        report.stillhalter_gesamt = (
            self.values.shortOptionProfits.eur
            + self.values.shortOptionLosses.eur
        )
        report.long_optionen_gewinne = self.values.longOptionProfits.eur
        report.long_optionen_verluste = self.values.longOptionLosses.eur
        report.long_optionen_verfallverluste = self.values.longOptionTotalLosses.eur
        report.long_optionen_gesamt = (
            self.values.longOptionProfits.eur
            + self.values.longOptionLosses.eur
            + self.values.longOptionTotalLosses.eur
        )
        report.z21_termingeschaefsgewinne = self.values.z21_termingeschaefsgewinne.eur
        report.z24_termingeschaefte_verluste = self.values.z24_termingeschaefte_verluste.eur
        report.wertpapierleihe_einkommen = self.values.securitiesLendingIncome.eur
        report.zinsen_gesamt = self.values.creditInterest.eur + self.values.debitInterest.eur
        report.z19_auslaendische_kapitalertraege = (
            self.values.dividend.eur
            + self.values.creditInterest.eur
            + self.values.securitiesLendingIncome.eur
            + self.values.fundDistributionTaxable.eur
        )
        return report
