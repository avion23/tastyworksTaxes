import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tastyworksTaxes.values import Values
from dataclasses_json import dataclass_json
from dataclasses import dataclass
import logging
import pandas as pd
import locale

logger = logging.getLogger(__name__)
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.WARNING,
    datefmt='%Y-%m-%d %H:%M:%S')
for key in logging.Logger.manager.loggerDict:
    temp = logging.getLogger(key)
    temp.propagate = True
    temp.setLevel(logging.INFO)
    if temp.name == "converter":
        temp.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.StreamHandler()
    logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


def _format_report_line(label: str, value: float, width: int = 40) -> str:
    """Helper to format tax report lines consistently"""
    return f"{label:<{width}}{value: .2f}\n"


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
    KAP+KAP-INV
    KAP+KAP-INV KErSt+Soli
    KAP+KAP-INV Verlustvortrag
    Cash Balance USD
    Net Liquidating Value
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
    z21_termingeschaefsgewinne_stillhalter: float = 0
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
            ('Brokergebühren', self.brokergebuehren),
            ('Alle Gebühren in USD', self.alle_gebuehren_in_usd),
            ('Alle Gebühren in EUR', self.alle_gebuehren_in_euro),
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
            ('Anlage KAP+INV', self.anlage_kap_inv),
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
            ('Long-Optionen-Gesamt', self.long_optionen_gesamt),
            ('Future-Gewinne', self.future_gewinne),
            ('Future-Verluste', self.future_verluste),
            ('Future-Gesamt', self.future_gesamt),
            ('zusätzliche Ordergebühren', self.zusatzliche_ordergebuehren),
            ('Dividenden', self.dividenden),
            ('bezahlte Dividenden', self.bezahlte_dividenden),
            ('Quellensteuer', self.quellensteuer_z41),
            ('Zinseinnahmen', self.zinseinnahmen),
            ('Zinsausgaben', self.zinsausgaben),
            ('Zinsen insgesamt', self.zinsen_gesamt),
            ('Z19 Ausländische Kapitalerträge', self.z19_auslaendische_kapitalertraege),
            ('Z21 Termingeschäfte+Stillhalter', self.z21_termingeschaefsgewinne_stillhalter),
            ('Z24 Termingeschäftsverluste', self.z24_termingeschaefte_verluste),
            ('KAP+KAP-INV', self.kap_kap_inv),
            ('KAP+KAP-INV KErSt+Soli', self.kap_kap_inv_kerst_soli),
            ('KAP+KAP-INV Verlustvortrag', self.kap_kap_inv_verlustvortrag),
            ('Cash Balance USD', self.cash_balance_usd),
            ('Net Liquidating Value', self.net_liquidating_value),
            ('Wertpapierleihe Einkommen', self.wertpapierleihe_einkommen),
        ]
        return ''.join(_format_report_line(label, value) for label, value in fields)


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
    z21_term_gains_option_holder: float = 0
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
            ('broker fees', self.broker_fees),
            ('all fees in USD', self.all_fees_in_usd),
            ('all fees in EUR', self.all_fees_in_euro),
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
            ('stock gains z20', self.stock_gains_z20),
            ('stock losses z23', self.stock_losses_z23),
            ('stock total', self.stock_total),
            ('stock tax amount', self.stock_tax_amount),
            ('stock loss carryforward', self.stock_loss_carryforward),
            ('other gains', self.other_gains),
            ('other losses', self.other_losses),
            ('other total', self.other_total),
            ('option holder gains', self.option_holder_gains),
            ('option holder losses', self.option_holder_losses),
            ('option holder total', self.option_holder_total),
            ('average held premium per day', self.average_held_premium_per_day),
            ('option holder gains calls fifo', self.option_holder_gains_calls_fifo),
            ('option holder losses calls fifo', self.option_holder_losses_calls_fifo),
            ('option holder calls total fifo', self.option_holder_calls_total_fifo),
            ('option holder gains puts fifo', self.option_holder_gains_puts_fifo),
            ('option holder losses puts fifo', self.option_holder_losses_puts_fifo),
            ('option holder puts total fifo', self.option_holder_puts_total_fifo),
            ('option holder gains fifo', self.option_holder_gains_fifo),
            ('option holder losses fifo', self.option_holder_losses_fifo),
            ('option holder total fifo', self.option_holder_total_fifo),
            ('long option gains', self.long_option_gains),
            ('long option losses', self.long_option_losses),
            ('long option total', self.long_option_total),
            ('future gains', self.future_gains),
            ('future losses', self.future_losses),
            ('future total', self.future_total),
            ('z21 term gains option holder', self.z21_term_gains_option_holder),
            ('z24 term losses', self.z24_term_losses),
            ('kap kap inv', self.kap_kap_inv),
            ('kap kap inv kerst soli', self.kap_kap_inv_kerst_soli),
            ('kap kap inv loss carryforward', self.kap_kap_inv_loss_carryforward),
            ('cash balance usd', self.cash_balance_usd),
            ('net liquidating value', self.net_liquidating_value),
            ('securities lending income', self.securities_lending_income),
        ]
        return ''.join(_format_report_line(label, value) for label, value in fields)


class Printer(object):
    def __init__(self, values: Values, closedTrades: pd.DataFrame) -> None:
        self.values = values
        self.closedTrades = closedTrades

    def generateEnglishTaxReport(self) -> EnglishTaxReport:
        report = EnglishTaxReport()
        report.deposits = self.values.deposit.eur
        report.withdrawals = self.values.withdrawal.eur
        report.interest_income = self.values.creditInterest.eur
        report.interest_expenses = self.values.debitInterest.eur
        report.dividends = self.values.dividend.eur
        report.additional_order_fees = self.values.otherFees.eur
        report.stock_gains_z20 = self.values.stockProfits.eur
        report.stock_losses_z23 = self.values.stockLoss.eur
        report.other_losses = self.values.otherLoss.eur
        report.securities_lending_income = self.values.securitiesLendingIncome.eur
        return report

    def generateGermanTaxReport(self) -> GermanTaxReport:
        report = GermanTaxReport()
        report.einzahlungen = self.values.deposit.eur
        report.auszahlungen = self.values.withdrawal.eur
        report.zinseinnahmen = self.values.creditInterest.eur
        report.zinsausgaben = self.values.debitInterest.eur
        report.dividenden = self.values.dividend.eur
        report.zusatzliche_ordergebuehren = self.values.otherFees.eur
        report.aktiengewinne_z20 = self.values.stockProfits.eur
        report.aktienverluste_z23 = self.values.stockLoss.eur
        report.sonstige_verluste = self.values.otherLoss.eur
        report.wertpapierleihe_einkommen = self.values.securitiesLendingIncome.eur
        return report

    def generateDummyReport(self):
        CATEGORIES = {
            "Transaktionen": {
                "withdrawal": "Abhebungen",
                "deposit": "Einzahlungen",
                "transfer": "Transfers",
                "balanceAdjustment": "Kontokorrekturen"
            },
            "Zinsen & Dividenden": {
                "creditInterest": "Guthabenzinsen",
                "debitInterest": "Sollzinsen",
                "dividend": "Dividendenzahlungen",
                "securitiesLendingIncome": "Wertpapierleihe-Einkommen"
            },
            "Aktien & Optionen": {
                "stockAndOptionsSum": "Summe Aktien und Optionen",
                "stockSum": "Summe Aktienhandel",
                "stockProfits": "Aktiengewinne",
                "stockLoss": "Aktienverluste",
                "optionSum": "Summe Optionshandel",
                "longOptionProfits": "Long Optionen Gewinne",
                "longOptionLosses": "Long Optionen Verluste",
                "longOptionTotalLosses": "Long Optionen Totalverluste",
                "shortOptionProfits": "Short Optionen Gewinne",
                "shortOptionLosses": "Short Optionen Verluste",
                "grossOptionDifferential": "Max Optionen-Delta",
            },
            "Gebühren & Verluste": {
                "fee": "Summe Gebühren Aktien + Optionen",
                "stockFees": "Aktiengebühren",
                "otherFees": "Optionsgebühren",
            }
        }
        locale.setlocale(locale.LC_ALL, 'de_DE')

        values_attrs = vars(self.values)
        all_translations = {attr: trans for category in CATEGORIES.values() for attr, trans in category.items()}

        max_attr_width = max(len(all_translations.get(attr, attr)) for attr in values_attrs)
        max_value_width = max(len(f"{value.eur:.2f}") for value in values_attrs.values())

        report = []

        for category, translations in CATEGORIES.items():
            for attr, translation in translations.items():
                value = values_attrs.get(attr)
                if value:
                    formatted_value = locale.format_string("%.2f", value.eur, grouping=True)
                    line = f"{translation.ljust(max_attr_width)}\t{formatted_value.rjust(max_value_width)}\n"
                    report.append(line)

        printed_keys = set(attr for translations in CATEGORIES.values() for attr in translations.keys())
        missing_keys = set(values_attrs.keys()) - printed_keys
        if missing_keys:
            raise ValueError(f"The following keys were not printed: {', '.join(missing_keys)}")

        return ''.join(report)
