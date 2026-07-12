import pytest
import logging
from tastyworksTaxes.asset_classifier import AssetClassifier
from tastyworksTaxes.position import PositionType

class TestAssetClassifier:
    @pytest.fixture
    def classifier(self):
        return AssetClassifier()
    
    def test_classify_equity_etf(self, classifier):
        assert classifier.classify('SCHG', PositionType.stock) == 'EQUITY_ETF'
        assert classifier.classify('TECL', PositionType.stock) == 'EQUITY_ETF'
        assert classifier.classify('QQQ', PositionType.stock) == 'EQUITY_ETF'
        assert classifier.classify('TQQQ', PositionType.stock) == 'EQUITY_ETF'
    
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

    def test_explicit_classification_is_distinct_from_fallback(self, classifier):
        assert classifier.is_explicitly_classified('TECL', PositionType.stock)
        assert not classifier.is_explicitly_classified('AAPL', PositionType.stock)
        assert classifier.is_explicitly_classified('AAPL', PositionType.call)
    
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


def test_unverified_registry_rows_do_not_grant_partial_exemption():
    classifier = AssetClassifier()
    assert classifier.classify('TECL', PositionType.stock) == 'EQUITY_ETF'
    assert not classifier.is_verified('TECL', PositionType.stock)
    assert classifier.get_exemption_percentage_for('TECL', PositionType.stock) == 0


def test_verified_registry_row_grants_partial_exemption(tmp_path):
    registry = tmp_path / 'assets.csv'
    registry.write_text(
        'symbol,classification,tax_category,teilfreistellung_pct,verified,effective_from,effective_to,evidence\n'
        'TEST,EQUITY_ETF,KAP-INV,30,true,2024-01-01,,Prospectus section 2\n',
        encoding='utf-8',
    )
    classifier = AssetClassifier(registry, on_date=__import__('datetime').date(2025, 1, 1))
    assert classifier.is_verified('TEST', PositionType.stock)
    assert classifier.get_exemption_percentage_for('TEST', PositionType.stock) == 30


@pytest.mark.parametrize('row, message', [
    ('test,EQUITY_ETF,KAP-INV,30,true,2024-01-01,,evidence', 'invalid symbol'),
    ('TEST,EQUITY_ETF,KAP-INV,15,true,2024-01-01,,evidence', 'tax properties'),
    ('TEST,EQUITY_ETF,KAP-INV,30,yes,2024-01-01,,evidence', 'verified'),
    ('TEST,EQUITY_ETF,KAP-INV,30,true,2025-01-01,2024-01-01,evidence', 'precedes'),
    ('TEST,EQUITY_ETF,KAP-INV,30,true,2024-01-01,,', 'evidence is required'),
])
def test_registry_validation(tmp_path, row, message):
    registry = tmp_path / 'assets.csv'
    registry.write_text(
        'symbol,classification,tax_category,teilfreistellung_pct,verified,effective_from,effective_to,evidence\n'
        + row + '\n', encoding='utf-8')
    with pytest.raises(ValueError, match=message):
        AssetClassifier(registry)
