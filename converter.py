import logging
import pprint
from dataclasses import dataclass
from dataclasses_json import dataclass_json
from unittest.mock import Mock, patch
from tabulate import tabulate


logger = logging.getLogger(__name__)
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.WARNING,
    datefmt='%Y-%m-%d %H:%M:%S')
for key in logging.Logger.manager.loggerDict:  # disable logging for imported modules
    temp = logging.getLogger(key)
    temp.propagate = True
    temp.setLevel(logging.INFO)
    if temp.name == "converter":
        temp.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.StreamHandler()
    logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


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

    def __str__(self) -> str:
        """ returns a tabulized string representation of the object


        # test output by filling the object with ascending numbers
        # >>> print(GermanTaxReport(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58))
        """
        ret: str = ""
        ret += f"{'Einzahlungen':<40}{self.einzahlungen: .2f}\n"
        ret += f"{'Auszahlungen':<40}{self.auszahlungen: .2f}\n"
        ret += f"{'Brokergebühren':<40}{self.brokergebuehren: .2f}\n"
        ret += f"{'Alle Gebühren in USD':<40}{self.alle_gebuehren_in_usd: .2f}\n"
        ret += f"{'Alle Gebühren in EUR':<40}{self.alle_gebuehren_in_euro: .2f}\n"
        ret += f"{'Währungsgewinne USD':<40}{self.waehrungsgewinne_usd: .2f}\n"
        ret += f"{'Währungsgewinne USD steuerfrei':<40}{self.waehrungsgewinne_usd_steuerfrei: .2f}\n"
        ret += f"{'Währungsgewinne USD Gesamt':<40}{self.waehrungsgewinne_usd_gesamt: .2f}\n"
        ret += f"{'Krypto Gewinne':<40}{self.krypto_gewinne: .2f}\n"
        ret += f"{'Krypto Verluste':<40}{self.krypto_verluste: .2f}\n"
        ret += f"{'Anlage SO':<40}{self.anlage_so: .2f}\n"
        ret += f"{'Anlage SO Steuerbetrag':<40}{self.anlage_so_steuerbetrag: .2f}\n"
        ret += f"{'Anlage SO Verlustvortrag':<40}{self.anlage_so_verlustvortrag: .2f}\n"
        ret += f"{'Investmentfondsgewinne':<40}{self.investmentfondsgewinne: .2f}\n"
        ret += f"{'Investmentfondsverluste':<40}{self.investmentfondsverluste: .2f}\n"
        ret += f"{'Anlage KAP+INV':<40}{self.anlage_kap_inv: .2f}\n"
        ret += f"{'Aktiengewinne Z20':<40}{self.aktiengewinne_z20: .2f}\n"
        ret += f"{'Aktienverluste Z23':<40}{self.aktienverluste_z23: .2f}\n"
        ret += f"{'Aktien Gesamt':<40}{self.aktien_gesamt: .2f}\n"
        ret += f"{'Aktien Steuerbetrag':<40}{self.aktien_steuerbetrag: .2f}\n"
        ret += f"{'Aktien Verlustvortrag':<40}{self.aktien_verlustvortrag: .2f}\n"
        ret += f"{'Sonstige Gewinne':<40}{self.sonstige_gewinne: .2f}\n"
        ret += f"{'Sonstige Verluste':<40}{self.sonstige_verluste: .2f}\n"
        ret += f"{'Sonstige Gesamt':<40}{self.sonstige_gesamt: .2f}\n"
        ret += f"{'Stillhalter Gewinne':<40}{self.stillhalter_gewinne: .2f}\n"
        ret += f"{'Stillhalter Verluste':<40}{self.stillhalter_verluste: .2f}\n"
        ret += f"{'Stillhalter Gesamt':<40}{self.stillhalter_gesamt: .2f}\n"
        ret += f"{'Durchschnitt behaltene Prämien pro Tag':<40}{self.durchschnitt_behaltene_praemien_pro_tag: .2f}\n"
        ret += f"{'Stillhalter Gewinne Calls (FIFO)':<40}{self.stillhalter_gewinne_calls_fifo: .2f}\n"
        ret += f"{'Stillhalter Verluste Calls (FIFO)':<40}{self.stillhalter_verluste_calls_fifo: .2f}\n"
        ret += f"{'Stillhalter Calls Gesamt (FIFO)':<40}{self.stillhalter_calls_gesamt_fifo: .2f}\n"
        ret += f"{'Stillhalter Gewinne Puts (FIFO)':<40}{self.stillhalter_gewinne_puts_fifo: .2f}\n"
        ret += f"{'Stillhalter Verluste Puts (FIFO)':<40}{self.stillhalter_verluste_puts_fifo: .2f}\n"
        ret += f"{'Stillhalter Puts Gesamt (FIFO)':<40}{self.stillhalter_puts_gesamt_fifo: .2f}\n"
        ret += f"{'Stillhalter-Gewinne (FIFO)':<40}{self.stillhalter_gewinne_fifo: .2f}\n"
        ret += f"{'Stillhalter-Verluste (FIFO)':<40}{self.stillhalter_verluste_fifo: .2f}\n"
        ret += f"{'Stillhalter-Gesamt (FIFO)':<40}{self.stillhalter_gesamt_fifo: .2f}\n"
        ret += f"{'Long-Optionen-Gewinne':<40}{self.long_optionen_gewinne: .2f}\n"
        ret += f"{'Long-Optionen-Verluste':<40}{self.long_optionen_verluste: .2f}\n"
        ret += f"{'Long-Optionen-Gesamt':<40}{self.long_optionen_gesamt: .2f}\n"
        ret += f"{'Future-Gewinne ':<40}{self.future_gewinne: .2f}\n"
        ret += f"{'Future-Verluste':<40}{self.future_verluste: .2f}\n"
        ret += f"{'Future-Gesamt':<40}{self.future_gesamt: .2f}\n"
        ret += f"{'zusätzliche Ordergebühren':<40}{self.zusatzliche_ordergebuehren: .2f}\n"
        ret += f"{'Dividenden':<40}{self.dividenden: .2f}\n"
        ret += f"{'bezahlte Dividenden':<40}{self.bezahlte_dividenden: .2f}\n"
        ret += f"{'Quellensteuer':<40}{self.quellensteuer_z41: .2f}\n"
        ret += f"{'Zinseinnahmen':<40}{self.zinseinnahmen: .2f}\n"
        ret += f"{'Zinsausgaben':<40}{self.zinsausgaben: .2f}\n"
        ret += f"{'Zinsen insgesamt':<40}{self.zinsen_gesamt: .2f}\n"
        ret += f"{'Z19 Ausländische Kapitalerträge':<40}{self.z19_auslaendische_kapitalertraege: .2f}\n"
        ret += f"{'Z21 Termingeschäfte+Stillhalter':<40}{self.z21_termingeschaefsgewinne_stillhalter: .2f}\n"
        ret += f"{'Z24 Termingeschäftsverluste':<40}{self.z24_termingeschaefte_verluste: .2f}\n"
        ret += f"{'KAP+KAP-INV':<40}{self.kap_kap_inv: .2f}\n"
        ret += f"{'KAP+KAP-INV KErSt+Soli':<40}{self.kap_kap_inv_kerst_soli: .2f}\n"
        ret += f"{'KAP+KAP-INV Verlustvortrag':<40}{self.kap_kap_inv_verlustvortrag: .2f}\n"
        ret += f"{'Cash Balance USD':<40}{self.cash_balance_usd: .2f}\n"
        ret += f"{'Net Liquidating Value':<40}{self.net_liquidating_value: .2f}\n"
        return ret


@ dataclass_json
@ dataclass
class EnglishTaxReport(object):
    """ this is the same as the german tax report, but with english variable names.

    It also includes a translation function to convert to the german tax report
    """
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


    def __str__(self) -> str:
        """ returns a tabulized string representation of the object

        # >>> print(EnglishTaxReport(1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48))
        """
        ret: str = ""
        ret += f"{'deposits':<40}{self.deposits: .2f}\n"
        ret += f"{'withdrawals':<40}{self.withdrawals: .2f}\n"
        ret += f"{'broker fees':<40}{self.broker_fees: .2f}\n"
        ret += f"{'all fees in USD':<40}{self.all_fees_in_usd: .2f}\n"
        ret += f"{'all fees in EUR':<40}{self.all_fees_in_euro: .2f}\n"
        ret += f"{'currency gains usd':<40}{self.currency_gains_usd: .2f}\n"
        ret += f"{'currency gains usd tax free':<40}{self.currency_gains_usd_tax_free: .2f}\n"
        ret += f"{'currency gains usd total':<40}{self.currency_gains_usd_total: .2f}\n"
        ret += f"{'crypto gains':<40}{self.crypto_gains: .2f}\n"
        ret += f"{'crypto losses':<40}{self.crypto_losses: .2f}\n"
        ret += f"{'investment so':<40}{self.investment_so: .2f}\n"
        ret += f"{'investment so tax amount':<40}{self.investment_so_tax_amount: .2f}\n"
        ret += f"{'investment so loss carryforward':<40}{self.investment_so_loss_carryforward: .2f}\n"
        ret += f"{'investment fund gains':<40}{self.investment_fund_gains: .2f}\n"
        ret += f"{'investment fund losses':<40}{self.investment_fund_losses: .2f}\n"
        ret += f"{'investment kap inv':<40}{self.investment_kap_inv: .2f}\n"
        ret += f"{'stock gains z20':<40}{self.stock_gains_z20: .2f}\n"
        ret += f"{'stock losses z23':<40}{self.stock_losses_z23: .2f}\n"
        ret += f"{'stock total':<40}{self.stock_total: .2f}\n"
        ret += f"{'stock tax amount':<40}{self.stock_tax_amount: .2f}\n"
        ret += f"{'stock loss carryforward':<40}{self.stock_loss_carryforward: .2f}\n"
        ret += f"{'other gains':<40}{self.other_gains: .2f}\n"
        ret += f"{'other losses':<40}{self.other_losses: .2f}\n"
        ret += f"{'other total':<40}{self.other_total: .2f}\n"
        ret += f"{'option holder gains':<40}{self.option_holder_gains: .2f}\n"
        ret += f"{'option holder losses':<40}{self.option_holder_losses: .2f}\n"
        ret += f"{'option holder total':<40}{self.option_holder_total: .2f}\n"
        ret += f"{'average held premium per day':<40}{self.average_held_premium_per_day: .2f}\n"
        ret += f"{'option holder gains calls fifo':<40}{self.option_holder_gains_calls_fifo: .2f}\n"
        ret += f"{'option holder losses calls fifo':<40}{self.option_holder_losses_calls_fifo: .2f}\n"
        ret += f"{'option holder calls total fifo':<40}{self.option_holder_calls_total_fifo: .2f}\n"
        ret += f"{'option holder gains puts fifo':<40}{self.option_holder_gains_puts_fifo: .2f}\n"
        ret += f"{'option holder losses puts fifo':<40}{self.option_holder_losses_puts_fifo: .2f}\n"
        ret += f"{'option holder puts total fifo':<40}{self.option_holder_puts_total_fifo: .2f}\n"
        ret += f"{'option holder gains fifo':<40}{self.option_holder_gains_fifo: .2f}\n"
        ret += f"{'option holder losses fifo':<40}{self.option_holder_losses_fifo: .2f}\n"
        ret += f"{'option holder total fifo':<40}{self.option_holder_total_fifo: .2f}\n"
        ret += f"{'long option gains':<40}{self.long_option_gains: .2f}\n"
        ret += f"{'long option losses':<40}{self.long_option_losses: .2f}\n"
        ret += f"{'long option total':<40}{self.long_option_total: .2f}\n"
        ret += f"{'future gains':<40}{self.future_gains: .2f}\n"
        ret += f"{'future losses':<40}{self.future_losses: .2f}\n"
        ret += f"{'future total':<40}{self.future_total: .2f}\n"
        ret += f"{'z21 term gains option holder':<40}{self.z21_term_gains_option_holder: .2f}\n"
        ret += f"{'z24 term losses':<40}{self.z24_term_losses: .2f}\n"
        ret += f"{'kap kap inv':<40}{self.kap_kap_inv: .2f}\n"
        ret += f"{'kap kap inv kerst soli':<40}{self.kap_kap_inv_kerst_soli: .2f}\n"
        ret += f"{'kap kap inv loss carryforward':<40}{self.kap_kap_inv_loss_carryforward: .2f}\n"
        ret += f"{'cash balance usd':<40}{self.cash_balance_usd: .2f}\n"
        ret += f"{'net liquidating value':<40}{self.net_liquidating_value: .2f}\n"
        return ret


class Converter(object):
    def __init__(self, path: str) -> None:
        self.path = path

    def toGerman(self, input: dict) -> dict:
        return {}


if __name__ == "__main__":
    import doctest
    # doctest.testmod(extraglobs={"t": Tasty("test/merged.csv")})
    doctest.testmod()
