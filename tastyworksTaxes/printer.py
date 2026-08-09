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


def _kap_2025_fields(values: Values) -> tuple[float, float, float]:
    """Return VZ 2025 KAP lines 19, 22 and 23 using form signs.

    The BFinV VZ 2025 Anlage KAP instructions require foreign disposal results
    in line 19 and repeat losses as positive amounts in lines 22/23. Fund income
    belongs to Anlage KAP-INV and is therefore absent here.
    Official form: https://www.formulare-bfinv.de/ffw/action/invoke.do?id=034024_25
    Law: https://www.gesetze-im-internet.de/estg/__20.html
    Transition: https://www.gesetze-im-internet.de/estg/__52.html
    """
    line_19 = sum((
        values.dividend.eur,
        values.creditInterest.eur,
        values.securitiesLendingIncome.eur,
        values.stockProfits.eur,
        values.stockLosses.eur,
        values.z21_termingeschaefsgewinne.eur,
        values.z24_termingeschaefte_verluste.eur,
    ))
    line_22 = max(0.0, -values.z24_termingeschaefte_verluste.eur)
    line_23 = max(0.0, -values.stockLosses.eur)
    return line_19, line_22, line_23


def _has_fund_data(values: Values) -> bool:
    fund_amounts = (
        values.fundDistributions,
        values.fundDistributionExempt,
        values.fundDistributionTaxable,
        values.fundGrossProfits,
        values.fundGrossLosses,
        values.fundProfits,
        values.fundLosses,
    )
    return values.fundTaxReviewRequired or any(
        amount.eur != 0 or amount.usd != 0 for amount in fund_amounts
    )


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

    VZ 2025 form mapping (Anlage KAP):
      Zeile 19 contains the covered foreign capital-income net amount. Applicable
      non-stock losses remain negative in that net and are repeated as a positive
      amount in Zeile 22. Stock disposal losses are repeated positively in Zeile
      23. The stored former Zeile 21/24 components are diagnostics, not current
      form lines. Fund income is excluded and belongs to Anlage KAP-INV.

      The official VZ 2025 KAP-INV instructions require gross amounts before
      Teilfreistellung and separate disposal lines by fund type. This report lacks
      per-fund lines and Vorabpauschale, so every detected fund year is manual and
      not filing-ready.
      Official form: https://www.formulare-bfinv.de/ffw/action/invoke.do?id=035004_25
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
    # Former line names are retained as diagnostic component identifiers.
    z21_termingeschaefsgewinne: float = 0
    z24_termingeschaefte_verluste: float = 0
    kap_kap_inv: float = 0
    kap_kap_inv_kerst_soli: float = 0
    kap_kap_inv_verlustvortrag: float = 0
    cash_balance_usd: float = 0
    net_liquidating_value: float = 0
    wertpapierleihe_einkommen: float = 0
    long_optionen_verfallverluste: float = 0
    # Appended fields preserve all legacy positional constructor positions.
    z22_verluste_ohne_aktienveraeusserungen: float = 0
    fondveraeusserungsgewinne_brutto: float = 0
    fondveraeusserungsverluste_brutto: float = 0
    assessment_year: int | None = None
    fund_tax_review_required: bool = False

    def __str__(self) -> str:
        is_vz_2025 = self.assessment_year == 2025
        fund_gain_label = (
            'Diagnose: Fonds-Veräußerungsgewinne nach Teilfreistellung'
            if is_vz_2025 else 'Investmentfondsgewinne'
        )
        fund_loss_label = (
            'Diagnose: Fonds-Veräußerungsverluste nach Teilfreistellung'
            if is_vz_2025 else 'Investmentfondsverluste'
        )
        kap_inv_label = (
            'Diagnose: KAP-INV Saldo nach Teilfreistellung'
            if is_vz_2025 else 'Anlage KAP-INV'
        )
        fund_distribution_gross_label = (
            'KAP-INV Ausschüttungen brutto'
            if is_vz_2025 else 'Fondsausschüttungen brutto'
        )
        fund_distribution_exempt_label = (
            'Diagnose: Ausschüttungen teilfreigestellt'
            if is_vz_2025 else 'Fondsausschüttungen steuerfrei'
        )
        fund_distribution_taxable_label = (
            'Diagnose: Ausschüttungen nach Teilfreistellung'
            if is_vz_2025 else 'Fondsausschüttungen steuerpflichtig'
        )
        stock_gain_label = (
            'Anlage KAP Z20 Aktienveräußerungsgewinne'
            if is_vz_2025 else 'Aktiengewinne Z20'
        )
        stock_loss_label = (
            'Anlage KAP Z23 Aktienveräußerungsverluste'
            if is_vz_2025 else 'Aktienverluste Z23'
        )
        stock_total_label = (
            'Diagnose: Aktien-Nettoergebnis' if is_vz_2025 else 'Aktien Gesamt'
        )
        line_19_label = (
            'Anlage KAP Z19 Ausländische Kapitalerträge'
            if is_vz_2025 else 'Z19 Ausländische Kapitalerträge'
        )
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
            (fund_gain_label, self.investmentfondsgewinne),
            (fund_loss_label, self.investmentfondsverluste),
            (kap_inv_label, self.anlage_kap_inv),
            (fund_distribution_gross_label, self.fondsausschuettungen_brutto),
            (fund_distribution_exempt_label, self.fondsausschuettungen_steuerfrei),
            (fund_distribution_taxable_label, self.fondsausschuettungen_steuerpflichtig),
            (stock_gain_label, self.aktiengewinne_z20),
            (stock_loss_label, self.aktienverluste_z23),
            (stock_total_label, self.aktien_gesamt),
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
            (line_19_label, self.z19_auslaendische_kapitalertraege),
            *([] if is_vz_2025 else [
                ('Z21 Termingeschäfte+Stillhalter', self.z21_termingeschaefsgewinne),
                ('Z24 Termingeschäftsverluste', self.z24_termingeschaefte_verluste),
            ]),
            ('Cash Balance USD', self.cash_balance_usd),
            ('Net Liquidating Value', self.net_liquidating_value),
            ('Wertpapierleihe Einkommen', self.wertpapierleihe_einkommen),
        ]
        fields.extend([
            ('KAP-INV Fonds-Veräußerungsgewinne brutto', self.fondveraeusserungsgewinne_brutto),
            ('KAP-INV Fonds-Veräußerungsverluste brutto', self.fondveraeusserungsverluste_brutto),
        ])
        if is_vz_2025:
            fields.append((
                'Anlage KAP Z22 Verluste ohne Aktienveräußerungen',
                self.z22_verluste_ohne_aktienveraeusserungen,
            ))
            mapping_note = (
                'NOTE: VZ 2025 mapping uses Anlage KAP lines 19, 22 and 23; '
                'losses remain negative in line 19 and are positive in lines 22/23.\n'
            )
        else:
            mapping_note = (
                '*** ANLAGE KAP MAPPING NOT OFFICIALLY VALIDATED FOR '
                f'ASSESSMENT YEAR {self.assessment_year or "UNSPECIFIED"} - '
                'NOT FILING-READY ***\n'
            )
        diagnostics = []
        if is_vz_2025:
            diagnostics = [
                ('Diagnose: ehemalige Zeile 21 Gewinne', self.z21_termingeschaefsgewinne),
                ('Diagnose: ehemalige Zeile 24 Verluste', self.z24_termingeschaefte_verluste),
            ]
        fund_note = ''
        if self.fund_tax_review_required:
            fund_note = (
                '*** FUND YEAR - KAP-INV NOT FILING-READY ***\n'
                'Vorabpauschale and per-fund KAP-INV lines are manual. Gross '
                'distributions and disposals above are not a completed KAP-INV.\n'
            )
        return (
            ''.join(_format_german_report_line(label, value) for label, value in fields)
            + ''.join(_format_german_report_line(label, value) for label, value in diagnostics)
            + mapping_note
            + fund_note
            + 'NOTE: Soli/KESt are not computed; the Finanzamt computes German tax.\n'
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
    long_option_worthless_expiry_losses: float = 0
    # Appended fields preserve all legacy positional constructor positions.
    z22_non_stock_losses: float = 0
    fund_disposal_gains_gross: float = 0
    fund_disposal_losses_gross: float = 0
    assessment_year: int | None = None
    fund_tax_review_required: bool = False

    def __str__(self) -> str:
        is_vz_2025 = self.assessment_year == 2025
        fund_gain_label = (
            'diagnostic fund disposal gains after exemption'
            if is_vz_2025 else 'investment fund gains'
        )
        fund_loss_label = (
            'diagnostic fund disposal losses after exemption'
            if is_vz_2025 else 'investment fund losses'
        )
        kap_inv_label = (
            'diagnostic KAP-INV total after exemption'
            if is_vz_2025 else 'investment kap inv'
        )
        fund_distribution_taxable_label = (
            'diagnostic fund distributions after exemption'
            if is_vz_2025 else 'fund distributions taxable'
        )
        former_line_21_label = (
            'diagnostic former line 21 gains' if is_vz_2025 else 'z21 term gains'
        )
        former_line_24_label = (
            'diagnostic former line 24 losses' if is_vz_2025 else 'z24 term losses'
        )
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
            (fund_gain_label, self.investment_fund_gains),
            (fund_loss_label, self.investment_fund_losses),
            (kap_inv_label, self.investment_kap_inv),
            ('fund distributions gross', self.fund_distributions_gross),
            ('fund distributions exempt', self.fund_distributions_exempt),
            (fund_distribution_taxable_label, self.fund_distributions_taxable),
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
            (former_line_21_label, self.z21_term_gains),
            (former_line_24_label, self.z24_term_losses),
            ('cash balance usd', self.cash_balance_usd),
            ('net liquidating value', self.net_liquidating_value),
            ('securities lending income', self.securities_lending_income),
        ]
        fields.extend([
            ('KAP-INV fund disposal gains gross', self.fund_disposal_gains_gross),
            ('KAP-INV fund disposal losses gross', self.fund_disposal_losses_gross),
        ])
        if is_vz_2025:
            fields.append(('z22 non-stock losses', self.z22_non_stock_losses))
            mapping_note = 'NOTE: official German form mapping applies to VZ 2025 only.\n'
        else:
            mapping_note = (
                '*** GERMAN KAP MAPPING NOT OFFICIALLY VALIDATED FOR '
                f'ASSESSMENT YEAR {self.assessment_year or "UNSPECIFIED"} - '
                'NOT FILING-READY ***\n'
            )
        fund_note = ''
        if self.fund_tax_review_required:
            fund_note = (
                '*** FUND YEAR - KAP-INV NOT FILING-READY; '
                'Vorabpauschale and per-fund lines are manual. ***\n'
            )
        return (
            ''.join(_format_report_line(label, value) for label, value in fields)
            + mapping_note
            + fund_note
        )


class Printer(object):
    def __init__(
        self,
        values: Values,
        closed_trades: list,
        assessment_year: int | None = None,
    ) -> None:
        self.values = values
        self.closed_trades = closed_trades
        self.assessment_year = assessment_year

    def generateEnglishTaxReport(self) -> EnglishTaxReport:
        report = EnglishTaxReport()
        report.assessment_year = self.assessment_year
        report.fund_tax_review_required = _has_fund_data(self.values)
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
        report.fund_disposal_gains_gross = self.values.fundGrossProfits.eur
        report.fund_disposal_losses_gross = self.values.fundGrossLosses.eur
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
        if self.assessment_year == 2025:
            line_19, line_22, line_23 = _kap_2025_fields(self.values)
            report.z19_foreign_capital_gains = line_19
            report.z22_non_stock_losses = line_22
            report.stock_losses_z23 = line_23
            return report
        report.z19_foreign_capital_gains = (
            self.values.dividend.eur
            + self.values.creditInterest.eur
            + self.values.securitiesLendingIncome.eur
            + self.values.fundDistributionTaxable.eur
        )
        return report

    def generateGermanTaxReport(self) -> GermanTaxReport:
        report = GermanTaxReport()
        report.assessment_year = self.assessment_year
        report.fund_tax_review_required = _has_fund_data(self.values)
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
        report.fondveraeusserungsgewinne_brutto = self.values.fundGrossProfits.eur
        report.fondveraeusserungsverluste_brutto = self.values.fundGrossLosses.eur
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
        if self.assessment_year == 2025:
            line_19, line_22, line_23 = _kap_2025_fields(self.values)
            report.z19_auslaendische_kapitalertraege = line_19
            report.z22_verluste_ohne_aktienveraeusserungen = line_22
            report.aktienverluste_z23 = line_23
            return report
        report.z19_auslaendische_kapitalertraege = (
            self.values.dividend.eur
            + self.values.creditInterest.eur
            + self.values.securitiesLendingIncome.eur
            + self.values.fundDistributionTaxable.eur
        )
        return report
