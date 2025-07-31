import pytest
import pandas as pd
from tastyworksTaxes.values import Values
from tastyworksTaxes.money import Money
from tastyworksTaxes.printer import Printer

class TestPrinterLabels:
    def test_equity_etf_profits_label_accuracy(self):
        values = Values()
        values.equityEtfProfits = Money(usd=100.0, eur=80.0)
        
        empty_df = pd.DataFrame()
        printer = Printer(values, empty_df)
        
        report = printer.generateDummyReport()
        
        assert "Aktien-ETF steuerpflichtige Gewinne (nach Teilfreistellung)" in report
        assert "80,00" in report
        
        assert "Aktien-ETF Gewinne (Teilfreistellung)" not in report
    
    def test_all_required_categories_present(self):
        values = Values()
        values.stockFees = Money(usd=10.0, eur=8.0)
        values.otherFees = Money(usd=5.0, eur=4.0)
        values.equityEtfProfits = Money(usd=100.0, eur=80.0)
        values.otherStockAndBondProfits = Money(usd=50.0, eur=40.0)
        values.stockAndEtfLosses = Money(usd=-20.0, eur=-16.0)
        
        empty_df = pd.DataFrame()
        printer = Printer(values, empty_df)
        
        report = printer.generateDummyReport()
        
        assert "Aktiengebühren" in report
        assert "Optionsgebühren" in report
        assert "8,00" in report
        assert "4,00" in report