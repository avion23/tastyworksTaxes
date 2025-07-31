import pytest
import logging
from tastyworksTaxes.asset_classifier import AssetClassifier
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.asset_definitions import ASSET_DEFINITIONS

class TestAssetClassifier:
    @pytest.fixture
    def classifier(self):
        return AssetClassifier()
    
    def test_classify_equity_etf(self, classifier):
        assert classifier.classify('SCHG', PositionType.stock) == 'EQUITY_ETF'
        assert classifier.classify('TECL', PositionType.stock) == 'EQUITY_ETF'
        assert classifier.classify('QQQ', PositionType.stock) == 'EQUITY_ETF'
    
    def test_classify_bond_etf(self, classifier):
        assert classifier.classify('PULS', PositionType.stock) == 'BOND_ETF'
        assert classifier.classify('VGSH', PositionType.stock) == 'BOND_ETF'
        assert classifier.classify('TLT', PositionType.stock) == 'BOND_ETF'
    
    def test_classify_mixed_fund_etf(self, classifier):
        assert classifier.classify('AOM', PositionType.stock) == 'MIXED_FUND_ETF'
        assert classifier.classify('AOR', PositionType.stock) == 'MIXED_FUND_ETF'
    
    def test_classify_real_estate_etf(self, classifier):
        assert classifier.classify('VNQ', PositionType.stock) == 'REAL_ESTATE_ETF'
        assert classifier.classify('IYR', PositionType.stock) == 'REAL_ESTATE_ETF'
    
    def test_classify_crypto_lambda(self, classifier):
        assert classifier.classify('BTC/USD', PositionType.stock) == 'CRYPTO'
        assert classifier.classify('ETH/EUR', PositionType.stock) == 'CRYPTO'
        assert classifier.classify('BTC', PositionType.stock) == 'CRYPTO'
    
    def test_classify_unknown_stock(self, classifier):
        assert classifier.classify('UNKNOWN_SYMBOL', PositionType.stock) == 'INDIVIDUAL_STOCK'
        assert classifier.classify('AAPL', PositionType.stock) == 'INDIVIDUAL_STOCK'
    
    def test_classify_options(self, classifier):
        assert classifier.classify('AAPL', PositionType.call) == 'CALL'
        assert classifier.classify('SPY', PositionType.put) == 'PUT'
    
    def test_get_exemption_percentage(self, classifier):
        assert classifier.get_exemption_percentage('EQUITY_ETF') == 30
        assert classifier.get_exemption_percentage('BOND_ETF') == 0
        assert classifier.get_exemption_percentage('MIXED_FUND_ETF') == 15
        assert classifier.get_exemption_percentage('REAL_ESTATE_ETF') == 60
        assert classifier.get_exemption_percentage('INDIVIDUAL_STOCK') == 0
        assert classifier.get_exemption_percentage('CRYPTO') == 0
    
    def test_get_tax_category(self, classifier):
        assert classifier.get_tax_category('EQUITY_ETF') == 'KAP-INV'
        assert classifier.get_tax_category('BOND_ETF') == 'KAP-INV'
        assert classifier.get_tax_category('CRYPTO') == 'SO'
        assert classifier.get_tax_category('INDIVIDUAL_STOCK') == 'KAP'
    
    def test_get_all_symbols_by_type(self, classifier):
        equity_symbols = classifier.get_all_symbols_by_type('EQUITY_ETF')
        assert 'SCHG' in equity_symbols
        assert 'TECL' in equity_symbols
        
        bond_symbols = classifier.get_all_symbols_by_type('BOND_ETF')
        assert 'PULS' in bond_symbols
        assert 'VGSH' in bond_symbols
        
        unknown_symbols = classifier.get_all_symbols_by_type('UNKNOWN_TYPE')
        assert unknown_symbols == set()
    
    def test_check_unsupported_assets_crypto(self, classifier, caplog):
        with caplog.at_level(logging.WARNING):
            classifier.check_unsupported_assets(['BTC/USD', 'SCHG'])
        
        assert "UNSUPPORTED TAX CATEGORY" in caplog.text
        assert "BTC/USD" in caplog.text
        assert "Anlage SO" in caplog.text
    
    def test_check_unsupported_assets_unknown(self, classifier, caplog):
        with caplog.at_level(logging.WARNING):
            classifier.check_unsupported_assets(['UNKNOWN_FUND'])
        
        assert "Unknown fund/stock type" in caplog.text
        assert "UNKNOWN_FUND" in caplog.text
        assert "Mischfonds or Immobilienfonds" in caplog.text
    
    def test_check_unsupported_assets_special_funds(self, classifier, caplog):
        with caplog.at_level(logging.WARNING):
            classifier.check_unsupported_assets(['AOM', 'VNQ'])
        
        assert "Special fund type detected" in caplog.text
        assert "AOM" in caplog.text and "15%" in caplog.text
        assert "VNQ" in caplog.text and "60%" in caplog.text
    
    def test_check_unsupported_assets_no_warnings_for_known(self, classifier, caplog):
        with caplog.at_level(logging.WARNING):
            classifier.check_unsupported_assets(['SCHG', 'PULS'])
        
        assert len(caplog.records) == 0