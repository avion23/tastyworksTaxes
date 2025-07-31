import logging
from tastyworksTaxes.position import PositionType
from tastyworksTaxes.asset_definitions import ASSET_DEFINITIONS

logger = logging.getLogger(__name__)

class AssetClassifier:
    def __init__(self):
        self._definitions = ASSET_DEFINITIONS
        logger.debug("AssetClassifier initialized")

    def classify(self, symbol: str, position_type: PositionType) -> str:
        if position_type != PositionType.stock:
            return position_type.name.upper()

        rules = self._definitions.get(PositionType.stock, {})
        for category, definition in rules.items():
            checker = definition['symbols']
            if callable(checker):
                if checker(symbol):
                    return category
            elif isinstance(checker, set):
                if symbol in checker:
                    return category
        
        return 'INDIVIDUAL_STOCK'

    def get_tax_category(self, classification: str) -> str:
        for def_type in self._definitions.values():
            if classification in def_type:
                return def_type[classification].get('tax_category', 'KAP')
        return 'KAP'

    def get_exemption_percentage(self, classification: str) -> int:
        for def_type in self._definitions.values():
            if classification in def_type:
                return def_type[classification]['properties'].get('teilfreistellung_pct', 0)
        return 0
    
    def get_all_symbols_by_type(self, asset_type: str) -> set:
        rules = self._definitions.get(PositionType.stock, {})
        if asset_type in rules:
            checker = rules[asset_type]['symbols']
            if isinstance(checker, set):
                return checker
        return set()
    
    def check_unsupported_assets(self, symbols: list) -> None:
        for symbol in symbols:
            classification = self.classify(symbol, PositionType.stock)
            tax_category = self.get_tax_category(classification)
            
            if tax_category == 'SO':
                logger.warning(f"UNSUPPORTED TAX CATEGORY: Symbol '{symbol}' ({classification}) belongs in 'Anlage SO'. "
                             f"This program does not handle this. You must calculate it manually.")
            elif classification == 'INDIVIDUAL_STOCK':
                logger.warning(f"Unknown fund/stock type for symbol '{symbol}' - treating as individual stock. "
                             f"If this is a Mischfonds or Immobilienfonds, different Teilfreistellung rates apply.")
            elif classification in ['MIXED_FUND_ETF', 'REAL_ESTATE_ETF']:
                exemption_pct = self.get_exemption_percentage(classification)
                logger.warning(f"Special fund type detected: '{symbol}' ({classification}) has {exemption_pct}% Teilfreistellung "
                             f"but automatic calculation is not fully implemented.")