import logging
from datetime import date
from pathlib import Path

from tastyworksTaxes.asset_definitions import CLASSIFICATIONS, AssetDefinition, load_asset_registry
from tastyworksTaxes.position import PositionType

logger = logging.getLogger(__name__)


class AssetClassifier:
    def __init__(self, registry_path: Path | None = None, on_date: date | None = None):
        self._definitions = load_asset_registry(registry_path)
        self._on_date = on_date or date.today()
        logger.debug("AssetClassifier initialized")

    def _definition(self, symbol: str) -> AssetDefinition | None:
        normalized = symbol.upper()
        for definition in self._definitions:
            if definition.symbol == normalized and definition.is_effective(self._on_date):
                return definition
        if normalized.endswith(("/USD", "/EUR")):
            return AssetDefinition(normalized, "CRYPTO", "SO", 0, True,
                                   date.min, None, "Currency pair notation")
        return None

    def is_explicitly_classified(self, symbol: str, position_type: PositionType) -> bool:
        if position_type != PositionType.stock:
            return True
        return self._definition(symbol) is not None

    def is_verified(self, symbol: str, position_type: PositionType) -> bool:
        if position_type != PositionType.stock:
            return True
        definition = self._definition(symbol)
        return definition is not None and definition.verified

    def classify(self, symbol: str, position_type: PositionType) -> str:
        if position_type != PositionType.stock:
            return position_type.name.upper()
        definition = self._definition(symbol)
        return definition.classification if definition else "INDIVIDUAL_STOCK"

    def get_tax_category(self, classification: str) -> str:
        return CLASSIFICATIONS.get(classification, ("KAP", 0))[0]

    def get_exemption_percentage(self, classification: str) -> int:
        return CLASSIFICATIONS.get(classification, ("KAP", 0))[1]

    def get_exemption_percentage_for(self, symbol: str, position_type: PositionType) -> int:
        if position_type != PositionType.stock:
            return 0
        definition = self._definition(symbol)
        return definition.teilfreistellung_pct if definition and definition.verified else 0

    def get_all_symbols_by_type(self, asset_type: str) -> set[str]:
        return {item.symbol for item in self._definitions
                if item.classification == asset_type and item.is_effective(self._on_date)}

    def check_unsupported_assets(self, symbols: list[str]) -> None:
        for symbol in symbols:
            classification = self.classify(symbol, PositionType.stock)
            tax_category = self.get_tax_category(classification)
            if tax_category == "SO":
                logger.warning("UNSUPPORTED TAX CATEGORY: Symbol '%s' (%s) belongs in 'Anlage SO'. "
                               "This program does not handle this. You must calculate it manually.",
                               symbol, classification)
            elif classification == "INDIVIDUAL_STOCK":
                logger.warning("Unknown fund/stock type for symbol '%s' - treating as individual stock. "
                               "If this is a Mischfonds or Immobilienfonds, different Teilfreistellung rates apply.", symbol)
            elif classification in {"MIXED_FUND_ETF", "REAL_ESTATE_ETF"}:
                logger.warning("Special fund type detected: '%s' (%s) has %s%% Teilfreistellung "
                               "but automatic calculation is not fully implemented.", symbol, classification,
                               self.get_exemption_percentage(classification))
