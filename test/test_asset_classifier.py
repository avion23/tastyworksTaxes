import pytest
import logging
from tastyworksTaxes.asset_classifier import AssetClassifier
from tastyworksTaxes.asset_definitions import CLASSIFICATIONS, load_asset_registry
from tastyworksTaxes.position import PositionType


@pytest.fixture
def unverified_fund_classifier(tmp_path):
    registry = tmp_path / 'assets.csv'
    registry.write_text(
        'symbol,classification,tax_category,teilfreistellung_pct,verified,effective_from,effective_to,evidence\n'
        'TESTUF,OTHER_FUND,KAP-INV,0,false,2020-01-01,,synthetic unverified fixture\n'
        'TESTVF,EQUITY_ETF,KAP-INV,30,true,2020-01-01,,synthetic verified fixture\n',
        encoding='utf-8',
    )
    return AssetClassifier(registry_path=registry)


class TestAssetClassifier:
    @pytest.fixture
    def classifier(self):
        return AssetClassifier()
    
    def test_classify_equity_etf(self, classifier):
        assert classifier.classify('SCHG', PositionType.stock) == 'EQUITY_ETF'
        assert classifier.classify('QQQ', PositionType.stock) == 'EQUITY_ETF'
        assert classifier.classify('VNQ', PositionType.stock) == 'EQUITY_ETF'
    
    def test_classify_bond_etf(self, classifier):
        assert classifier.classify('TECL', PositionType.stock) == 'OTHER_FUND'
        assert classifier.classify('TQQQ', PositionType.stock) == 'OTHER_FUND'
        assert classifier.classify('PULS', PositionType.stock) == 'BOND_ETF'
        assert classifier.classify('VGSH', PositionType.stock) == 'BOND_ETF'
        assert classifier.classify('TLT', PositionType.stock) == 'BOND_ETF'
    
    def test_classify_mixed_fund_etf(self, classifier):
        assert classifier.classify('AOA', PositionType.stock) == 'MIXED_FUND_ETF'
        assert classifier.classify('AOR', PositionType.stock) == 'MIXED_FUND_ETF'

    def test_classify_other_fund(self, classifier):
        for symbol in ('TECL', 'TQQQ', 'UPRO', 'SQQQ', 'SOXL', 'MSTY', 'NVDY', 'YMAG'):
            assert classifier.classify(symbol, PositionType.stock) == 'OTHER_FUND'
        assert classifier.classify('AOM', PositionType.stock) == 'OTHER_FUND'
        assert classifier.classify('AOK', PositionType.stock) == 'OTHER_FUND'
    
    def test_classify_real_estate_etf(self, classifier):
        assert classifier.classify('VNQ', PositionType.stock) == 'EQUITY_ETF'
        assert classifier.classify('IYR', PositionType.stock) == 'EQUITY_ETF'
    
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
        assert classifier.get_exemption_percentage('OTHER_FUND') == 0
        assert classifier.get_exemption_percentage('MIXED_FUND_ETF') == 15
        assert classifier.get_exemption_percentage('REAL_ESTATE_ETF') == 60
        assert classifier.get_exemption_percentage('INDIVIDUAL_STOCK') == 0
        assert classifier.get_exemption_percentage('CRYPTO') == 0
    
    def test_get_tax_category(self, classifier):
        assert classifier.get_tax_category('EQUITY_ETF') == 'KAP-INV'
        assert classifier.get_tax_category('BOND_ETF') == 'KAP-INV'
        assert classifier.get_tax_category('OTHER_FUND') == 'KAP-INV'
        assert classifier.get_tax_category('CRYPTO') == 'SO'
        assert classifier.get_tax_category('INDIVIDUAL_STOCK') == 'KAP'
    
    def test_get_all_symbols_by_type(self, classifier):
        equity_symbols = classifier.get_all_symbols_by_type('EQUITY_ETF')
        assert 'SCHG' in equity_symbols
        assert 'AOR' not in equity_symbols
        
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
        
        assert len(caplog.records) == 0
    
    def test_check_unsupported_assets_warns_for_unverified_known_funds(
        self, unverified_fund_classifier, caplog
    ):
        assert unverified_fund_classifier.classify('TESTUF', PositionType.stock) == 'OTHER_FUND'
        with caplog.at_level(logging.WARNING):
            unverified_fund_classifier.check_unsupported_assets(['TESTUF'])

        assert len(caplog.records) == 1
        assert "UNVERIFIED ASSET CLASSIFICATION" in caplog.text
        assert "TESTUF" in caplog.text


def test_unverified_registry_rows_do_not_grant_partial_exemption(unverified_fund_classifier):
    assert not unverified_fund_classifier.is_verified('TESTUF', PositionType.stock)
    assert unverified_fund_classifier.get_exemption_percentage_for('TESTUF', PositionType.stock) == 0


def test_verified_leveraged_single_stock_etfs_classified_as_other_fund():
    classifier = AssetClassifier()

    for symbol in ('GGLL', 'METU'):
        assert classifier.classify(symbol, PositionType.stock) == 'OTHER_FUND'
        assert classifier.classify_for_tax(symbol, PositionType.stock) == 'OTHER_FUND'
        assert classifier.is_verified(symbol, PositionType.stock)
        assert classifier.get_exemption_percentage_for(symbol, PositionType.stock) == 0


def test_registry_loads_verified_schg_as_an_equity_fund():
    registry = load_asset_registry()
    schg = next(definition for definition in registry if definition.symbol == 'SCHG')

    assert schg.classification == 'EQUITY_ETF'
    assert schg.verified


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


def test_verified_foreign_real_estate_fund_grants_80_percent_exemption(tmp_path):
    registry = tmp_path / 'assets.csv'
    registry.write_text(
        'symbol,classification,tax_category,teilfreistellung_pct,verified,effective_from,effective_to,evidence\n'
        'TEST,FOREIGN_REAL_ESTATE_ETF,KAP-INV,80,true,2024-01-01,,Prospectus section 2\n',
        encoding='utf-8',
    )
    classifier = AssetClassifier(registry, on_date=__import__('datetime').date(2025, 1, 1))

    assert classifier.classify_for_tax('TEST', PositionType.stock) == 'FOREIGN_REAL_ESTATE_ETF'
    assert classifier.get_exemption_percentage_for('TEST', PositionType.stock) == 80


def test_effective_date_is_selected_per_operation(tmp_path):
    registry = tmp_path / 'assets.csv'
    registry.write_text(
        'symbol,classification,tax_category,teilfreistellung_pct,verified,effective_from,effective_to,evidence\n'
        'TEST,EQUITY_ETF,KAP-INV,30,true,2020-01-01,2020-12-31,Prospectus section 2\n',
        encoding='utf-8',
    )
    classifier = AssetClassifier(registry)
    date = __import__('datetime').date

    assert classifier.classify_for_tax('TEST', PositionType.stock, date(2020, 6, 1)) == 'EQUITY_ETF'
    assert classifier.get_exemption_percentage_for('TEST', PositionType.stock, date(2020, 6, 1)) == 30
    assert classifier.classify_for_tax('TEST', PositionType.stock, date(2021, 1, 1)) == 'INDIVIDUAL_STOCK'
    assert classifier.get_exemption_percentage_for('TEST', PositionType.stock, date(2021, 1, 1)) == 0


def test_unverified_classification_does_not_select_tax_category(unverified_fund_classifier):
    assert unverified_fund_classifier.classify('TESTUF', PositionType.stock) == 'OTHER_FUND'

    assert unverified_fund_classifier.classify_for_tax('TESTUF', PositionType.stock) == 'INDIVIDUAL_STOCK'
    assert unverified_fund_classifier.get_tax_category(
        unverified_fund_classifier.classify_for_tax('TESTUF', PositionType.stock)
    ) == 'KAP'


def test_registry_rows_match_classification_tax_properties_and_classify():
    classifier = AssetClassifier()
    registry = load_asset_registry()

    for definition in registry:
        assert (
            definition.classification,
            definition.tax_category,
            definition.teilfreistellung_pct,
        ) == (definition.classification, *CLASSIFICATIONS[definition.classification])
        if definition.verified and definition.tax_category == 'KAP-INV':
            assert '; src: https://' in definition.evidence
        if definition.verified and definition.classification in {
            'EQUITY_ETF', 'BOND_ETF', 'OTHER_FUND',
        }:
            assert classifier.classify(definition.symbol, PositionType.stock) == definition.classification

    expected_classes = {
        'TECL': 'OTHER_FUND', 'TQQQ': 'OTHER_FUND', 'UPRO': 'OTHER_FUND',
        'SQQQ': 'OTHER_FUND', 'SOXL': 'OTHER_FUND', 'MSTY': 'OTHER_FUND',
        'NVDY': 'OTHER_FUND', 'YMAG': 'OTHER_FUND', 'PULS': 'BOND_ETF',
        'TLT': 'BOND_ETF', 'SCHG': 'EQUITY_ETF', 'QQQ': 'EQUITY_ETF',
        'AOA': 'MIXED_FUND_ETF', 'AOR': 'MIXED_FUND_ETF',
        'AOM': 'OTHER_FUND', 'AOK': 'OTHER_FUND',
    }
    for symbol, classification in expected_classes.items():
        assert classifier.classify(symbol, PositionType.stock) == classification


@pytest.mark.parametrize('row, message', [
    ('test,EQUITY_ETF,KAP-INV,30,true,2024-01-01,,evidence', 'invalid symbol'),
    ('TEST,EQUITY_ETF,KAP-INV,15,true,2024-01-01,,evidence', 'tax properties'),
    ('TEST,EQUITY_ETF,KAP-INV,30,yes,2024-01-01,,evidence', 'verified'),
    ('TEST,EQUITY_ETF,KAP-INV,30,true,2025-01-01,2024-01-01,evidence', 'precedes'),
    ('TEST,EQUITY_ETF,KAP-INV,30,true,2024-01-01,,', 'evidence is required'),
    ('TEST,EQUITY_ETF,KAP-INV,30,true,2024-01-01,,evidence,extra', 'malformed'),
])
def test_registry_validation(tmp_path, row, message):
    registry = tmp_path / 'assets.csv'
    registry.write_text(
        'symbol,classification,tax_category,teilfreistellung_pct,verified,effective_from,effective_to,evidence\n'
        + row + '\n', encoding='utf-8')
    with pytest.raises(ValueError, match=message):
        AssetClassifier(registry)
