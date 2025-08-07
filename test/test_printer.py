

from dataclasses import dataclass
from dataclasses_json import dataclass_json
from unittest.mock import Mock, patch
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pprint import pprint


from tastyworksTaxes.printer import Printer
from tastyworksTaxes.tasty import Tasty

def test_uso():
    """Tests with the uso file"""
    tw_pnl_output = """
                                            2020   total
    Einzahlungen                              0.00    0.00
    Auszahlungen                              0.00    0.00
    Brokergebühren                            0.00    0.00
    Alle Gebühren in USD                     15.37   15.37
    Alle Gebühren in Euro                    14.25   14.25
    Währungsgewinne USD                       0.00    0.00
    Währungsgewinne USD (steuerfrei)         -5.73   -5.73
    Währungsgewinne USD Gesamt               -5.73   -5.73
    Krypto-Gewinne                            0.00    0.00
    Krypto-Verluste                           0.00    0.00
    Anlage SO                                 0.00    0.00
    Anlage SO Steuerbetrag                    0.00    0.00
    Anlage SO Verlustvortrag                  0.00    0.00
    Investmentfondsgewinne                    0.00    0.00
    Investmentfondsverluste                   0.00    0.00
    Anlage KAP-INV                            0.00    0.00
    Aktiengewinne (Z20)                       0.00    0.00
    Aktienverluste (Z23)                      0.00    0.00
    Aktien Gesamt                             0.00    0.00
    Aktien Steuerbetrag                       0.00    0.00
    Aktien Verlustvortrag                     0.00    0.00
    Sonstige Gewinne                          0.00    0.00
    Sonstige Verluste                         0.00    0.00
    Sonstige Gesamt                           0.00    0.00
    Stillhalter-Gewinne                     595.19  595.19
    Stillhalter-Verluste                   -345.96 -345.96
    Stillhalter Gesamt                      249.23  249.23
    Durchschnitt behaltene Prämien pro Tag    1.00    1.00
    Stillhalter-Gewinne Calls (FIFO)          0.00    0.00
    Stillhalter-Verluste Calls (FIFO)         0.00    0.00
    Stillhalter Calls Gesamt (FIFO)           0.00    0.00
    Stillhalter-Gewinne Puts (FIFO)         249.23  249.23
    Stillhalter-Verluste Puts (FIFO)          0.00    0.00
    Stillhalter Puts Gesamt (FIFO)          249.23  249.23
    Stillhalter-Gewinne (FIFO)              249.23  249.23
    Stillhalter-Verluste (FIFO)               0.00    0.00
    Stillhalter Gesamt (FIFO)               249.23  249.23
    Long-Optionen-Gewinne                     0.00    0.00
    Long-Optionen-Verluste                 -141.25 -141.25
    Long-Optionen Gesamt                   -141.25 -141.25
    Future-Gewinne                            0.00    0.00
    Future-Verluste                           0.00    0.00
    Future Gesamt                             0.00    0.00
    zusätzliche Ordergebühren                 0.00    0.00
    Dividenden                                0.00    0.00
    bezahlte Dividenden                       0.00    0.00
    Quellensteuer (Z41)                       0.00    0.00
    Zinseinnahmen                             0.00    0.00
    Zinsausgaben                              0.00    0.00
    Zinsen Gesamt                             0.00    0.00
    Z19 Ausländische Kapitalerträge         107.98  107.98
    Z21 Termingeschäftsgewinne+Stillhalter    0.00    0.00
    Z24 Termingeschäftsverluste               0.00    0.00
    KAP+KAP-INV                             107.98  107.98
    KAP+KAP-INV KErSt+Soli                   28.48   28.48
    KAP+KAP-INV Verlustvortrag                0.00    0.00
    Cash Balance USD                        110.63  110.63
    Net Liquidating Value                   110.63  110.63"""

    tw_pnl_dict = {
        "Einzahlungen": 0.00,
        "Auszahlungen": 0.00,
        "Brokergebühren": 0.00,
        "Alle Gebühren in USD": 15.37,
        "Alle Gebühren in Euro": 14.25,
        "Währungsgewinne USD": 0.00,
        "Währungsgewinne USD (steuerfrei)": -5.73,
        "Währungsgewinne USD Gesamt": -5.73,
        "Krypto-Gewinne": 0.00,
        "Krypto-Verluste": 0.00,
        "Anlage SO": 0.00,
        "Anlage SO Steuerbetrag": 0.00,
        "Anlage SO Verlustvortrag": 0.00,
        "Investmentfondsgewinne": 0.00,
        "Investmentfondsverluste": 0.00,
        "Anlage KAP-INV": 0.00,
        "Aktiengewinne (Z20)": 0.00,
        "Aktienverluste (Z23)": 0.00,
        "Aktien Gesamt": 0.00,
        "Aktien Steuerbetrag": 0.00,
        "Aktien Verlustvortrag": 0.00,
        "Sonstige Gewinne": 0.00,
        "Sonstige Verluste": 0.00,
        "Sonstige Gesamt": 0.00,
        "Stillhalter-Gewinne": 595.19,
        "Stillhalter-Verluste": -345.96,
        "Stillhalter Gesamt": 249.23,
        "Durchschnitt behaltene Prämien pro Tag": 1.00,
        "Stillhalter-Gewinne Calls (FIFO)": 0.00,
        "Stillhalter-Verluste Calls (FIFO)": 0.00,
        "Stillhalter Calls Gesamt (FIFO)": 0.00,
        "Stillhalter-Gewinne Puts (FIFO)": 249.23,
        "Stillhalter-Verluste Puts (FIFO)": 0.00,
        "Stillhalter Puts Gesamt (FIFO)": 249.23,
        "Stillhalter-Gewinne (FIFO)": 249.23,
        "Stillhalter-Verluste (FIFO)": 0.00,
        "Stillhalter Gesamt (FIFO)": 249.23,
        "Long-Optionen-Gewinne": 0.00,
        "Long-Optionen-Verluste": -141.25,
        "Long-Optionen Gesamt": -141.25,
        "Future-Gewinne": 0.00,
        "Future-Verluste": 0.00,
        "Future Gesamt": 0.00,
        "zusätzliche Ordergebühren": 0.00,
        "Dividenden": 0.00,
        "bezahlte Dividenden": 0.00,
        "Quellensteuer (Z41)": 0.00,
        "Zinseinnahmen": 0.00,
        "Zinsausgaben": 0.00,
        "Zinsen Gesamt": 0.00,
        "Z19 Ausländische Kapitalerträge": 107.98,
        "Z21 Termingeschäftsgewinne+Stillhalter": 0.00,
        "Z24 Termingeschäftsverluste": 0.00,
        "KAP+KAP-INV": 107.98,
        "KAP+KAP-INV KErSt+Soli": 28.48,
        "KAP+KAP-INV Verlustvortrag": 0.00,
        "Cash Balance USD": 110.63,
        "Net Liquidating Value": 110.63,
    }

    # given
    t = Tasty("test/uso.csv")
    values = t.run()
    pprint(t)
    pprint(values)
    # printer = Printer(t.yearValues[2020], t.position_manager.closed_trades)
    pprint(t.position_manager.closed_trades)
    # de = printer.GermanTaxReport()
    # en = printer.EnglishTaxReport()
    # assert (de == en)
