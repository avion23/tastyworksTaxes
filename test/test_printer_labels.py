from tastyworksTaxes.money import Money
from tastyworksTaxes.printer import Printer
from tastyworksTaxes.values import Values


def test_rendered_reports_disclose_fees_and_reconcile_option_details():
    values = Values(
        deposit=Money(eur=-0.004),
        fee=Money(usd=-5, eur=-4),
        stockFees=Money(usd=-1.25, eur=-1),
        otherFees=Money(usd=-3.75, eur=-3),
        shortOptionProfits=Money(eur=10),
        shortOptionLosses=Money(eur=-2),
        longOptionProfits=Money(eur=20),
        longOptionLosses=Money(eur=-5),
        longOptionTotalLosses=Money(eur=-12.34),
    )

    printer = Printer(values, [])
    german_report = printer.generateGermanTaxReport()
    english_report = printer.generateEnglishTaxReport()
    german = str(german_report)
    english = str(english_report)

    assert (
        german_report.brokergebuehren,
        german_report.alle_gebuehren_in_usd,
        german_report.alle_gebuehren_in_euro,
        german_report.zusatzliche_ordergebuehren,
    ) == (-1, -5, -4, -3)
    assert (
        german_report.long_optionen_gewinne
        + german_report.long_optionen_verluste
        + german_report.long_optionen_verfallverluste
        == german_report.long_optionen_gesamt
        == 2.66
    )
    assert (
        english_report.long_option_gains
        + english_report.long_option_losses
        + english_report.long_option_worthless_expiry_losses
        == english_report.long_option_total
        == 2.66
    )
    assert "Aktiengebühren (Info; bereits im Nettoergebnis)-1,00" in german
    assert "Optionsgebühren (Info; bereits im Nettoergebnis)-3,00" in german
    assert any(
        line.startswith("long option worthless-expiry losses")
        and line.endswith("-12.34")
        for line in english.splitlines()
    )
    assert any(
        line.startswith("short option writer gains")
        and line.endswith("10.00")
        for line in english.splitlines()
    )
    assert "option holder" not in english
    assert german_report.einzahlungen == english_report.deposits == -0.004
    assert "-0,00" not in german
    assert "-0.00" not in english
