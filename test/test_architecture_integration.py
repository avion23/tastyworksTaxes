import subprocess
import sys

from tastyworksTaxes.asset_classifier import AssetClassifier
from tastyworksTaxes.position import PositionType


def test_classifier_tax_categories_and_exemptions_are_integrated():
    classifier = AssetClassifier()

    expected = {
        "SCHG": ("EQUITY_ETF", "KAP-INV", 30),
        "PULS": ("BOND_ETF", "KAP-INV", 0),
        "AOM": ("OTHER_FUND", "KAP-INV", 0),
        "AAPL": ("INDIVIDUAL_STOCK", "KAP", 0),
    }
    for symbol, (classification, category, exemption) in expected.items():
        actual = classifier.classify_for_tax(symbol, PositionType.stock)
        assert actual == classification
        assert classifier.get_tax_category(actual) == category
        assert classifier.get_exemption_percentage_for(symbol, PositionType.stock) == exemption


def test_cli_and_reports_do_not_import_standalone_vorabpauschale():
    check_imports = """
import sys
import tastyworksTaxes.main
import tastyworksTaxes.printer

assert "tastyworksTaxes.vorabpauschale" not in sys.modules
"""
    subprocess.run([sys.executable, "-c", check_imports], check=True)
