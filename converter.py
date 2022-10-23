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

        # >>> print(GermanTaxReport(1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48))
        """
        ret: str = ""
        ret = tabulate(self.__dict__.items(), headers=["Typ", "Wert"])

        return ret


@ dataclass_json
@ dataclass
class EnglishTaxReport(object):
    """ this is the same as the german tax report, but with english variable names.

    It also includes a translation function to convert to the german tax report
    """
    deposits: float
    withdrawals: float
    broker_fees: float
    all_fees_in_usd: float
    all_fees_in_euro: float
    currency_gains_usd: float
    currency_gains_usd_tax_free: float
    currency_gains_usd_total: float
    crypto_gains: float
    crypto_losses: float
    attachment_so: float
    attachment_so_taxed: float
    attachment_so_losses_carryforward: float
    investment_fund_gains: float
    investment_fund_losses: float
    attachment_KAP_INV: float
    stock_gains: float
    stock_losses: float
    stock_total: float
    stock_tax_amount: float
    stock_loss_carry_forward: float
    other_gains: float
    other_losses: float
    other_total: float
    option_gains: float
    option_losses: float
    option_total: float
    average_option_premiums_per_day: float
    option_gains_calls_fifo: float
    option_losses_calls_fifo: float
    option_total_calls_fifo: float
    option_gains_puts_fifo: float
    option_losses_puts_fifo: float
    option_total_puts_fifo: float
    option_gains_fifo: float
    option_losses_fifo: float
    option_total_fifo: float
    long_option_gains: float
    long_option_losses: float
    long_option_total: float
    future_gains: float
    future_losses: float
    future_total: float
    additional_order_fees: float
    dividends: float
    paid_dividends: float
    withholding_tax: float
    interest_income: float

    def __str__(self) -> str:
        """ returns a tabulized string representation of the object

        >>> print(EnglishTaxReport(1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48))     
        """
        ret: str = ""
        ret = tabulate(self.__dict__.items(), headers=["Type", "Value"])

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
