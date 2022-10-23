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

    Einzahlungen: float
    Auszahlungen: float
    Brokergebuehren: float
    Alle_Gebuehren_in_USD: float
    Alle_Gebuehren_in_Euro: float
    Waehrungsgewinne_USD: float
    Waehrungsgewinne_USD_steuerfrei: float
    Waehrungsgewinne_USD_Gesamt: float
    Krypto_Gewinne: float
    Krypto_Verluste: float
    Anlage_SO: float
    Anlage_SO_Steuerbetrag: float
    Anlage_SO_Verlustvortrag: float
    Investmentfondsgewinne: float
    Investmentfondsverluste: float
    Anlage_KAP_INV: float
    Aktiengewinne_Z20: float
    Aktienverluste_Z23: float
    Aktien_Gesamt: float
    Aktien_Steuerbetrag: float
    Aktien_Verlustvortrag: float
    Sonstige_Gewinne: float
    Sonstige_Verluste: float
    Sonstige_Gesamt: float
    Stillhalter_Gewinne: float
    Stillhalter_Verluste: float
    Stillhalter_Gesamt: float
    Durchschnitt_behaltene_Praemien_pro_Tag: float
    Stillhalter_Gewinne_Calls_FIFO: float
    Stillhalter_Verluste_Calls_FIFO: float
    Stillhalter_Calls_Gesamt_FIFO: float
    Stillhalter_Gewinne_Puts_FIFO: float
    Stillhalter_Verluste_Puts_FIFO: float
    Stillhalter_Puts_Gesamt_FIFO: float
    Stillhalter_Gewinne_FIFO: float
    Stillhalter_Verluste_FIFO: float
    Stillhalter_Gesamt_FIFO: float
    Long_Optionen_Gewinne: float
    Long_Optionen_Verluste: float
    Long_Optionen_Gesamt: float
    Future_Gewinne: float
    Future_Verluste: float
    Future_Gesamt: float
    zusaetzliche_Ordergebuehren: float
    Dividenden: float
    bezahlte_Dividenden: float
    Quellensteuer_Z41: float
    Zinseinnahmen: float
    Zinsausgaben: float
    Zinsausgaben_Steuerbetrag: float
    Zinsausgaben_Verlustvortrag: float
    Sonstige_Ausgaben: float
    Sonstige_Ausgaben_Steuerbetrag: float
    Sonstige_Ausgaben_Verlustvortrag: float
    Verlustvortrag: float
    Verlustvortrag_Steuerbetrag: float
    Verlustvortrag_Verlustvortrag: float

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
