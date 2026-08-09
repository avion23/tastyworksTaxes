import logging
from datetime import date, timedelta
from pathlib import Path

from tastyworksTaxes.asset_definitions import CLASSIFICATIONS, AssetDefinition, load_asset_registry
from tastyworksTaxes.position import PositionType

logger = logging.getLogger(__name__)


class AssetClassifier:
    def __init__(self, registry_path: Path | None = None, on_date: date | None = None):
        self._definitions = load_asset_registry(registry_path)
        self._on_date = on_date
        logger.debug("AssetClassifier initialized")

    def _definition(self, symbol: str, on_date: date | None = None) -> AssetDefinition | None:
        normalized = symbol.upper()
        effective_date = on_date or self._on_date or date.today()
        for definition in self._definitions:
            if definition.symbol == normalized and definition.is_effective(effective_date):
                return definition
        if normalized.endswith(("/USD", "/EUR")):
            return AssetDefinition(normalized, "CRYPTO", "SO", 0, True,
                                   date.min, None, "Currency pair notation")
        return None

    def is_explicitly_classified(self, symbol: str, position_type: PositionType,
                                 on_date: date | None = None) -> bool:
        if position_type != PositionType.stock:
            return True
        return self._definition(symbol, on_date) is not None

    def is_verified(self, symbol: str, position_type: PositionType,
                    on_date: date | None = None) -> bool:
        if position_type != PositionType.stock:
            return True
        definition = self._definition(symbol, on_date)
        return definition is not None and definition.verified

    def classify(self, symbol: str, position_type: PositionType,
                 on_date: date | None = None) -> str:
        if position_type != PositionType.stock:
            return position_type.name.upper()
        definition = self._definition(symbol, on_date)
        return definition.classification if definition else "INDIVIDUAL_STOCK"

    def classify_for_tax(self, symbol: str, position_type: PositionType,
                         on_date: date | None = None) -> str:
        if position_type != PositionType.stock:
            return position_type.name.upper()
        definition = self._definition(symbol, on_date)
        if definition is None or not definition.verified:
            return "INDIVIDUAL_STOCK"
        return definition.classification

    def get_tax_category(self, classification: str) -> str:
        return CLASSIFICATIONS.get(classification, ("KAP", 0))[0]

    def get_exemption_percentage(self, classification: str) -> int:
        return CLASSIFICATIONS.get(classification, ("KAP", 0))[1]

    def get_exemption_percentage_for(self, symbol: str, position_type: PositionType,
                                     on_date: date | None = None) -> int:
        if position_type != PositionType.stock:
            return 0
        definition = self._definition(symbol, on_date)
        return definition.teilfreistellung_pct if definition and definition.verified else 0

    def get_all_symbols_by_type(self, asset_type: str) -> set[str]:
        return {item.symbol for item in self._definitions
                if item.classification == asset_type
                and item.is_effective(self._on_date or date.today())}

    def effective_checkpoints(
        self, symbol: str, period_start: date, period_end: date
    ) -> tuple[date, ...]:
        """Return dates representing every registry segment or gap in a period."""
        normalized = symbol.upper()
        checkpoints = {period_start}
        for definition in self._definitions:
            if definition.symbol != normalized:
                continue
            if period_start <= definition.effective_from <= period_end:
                checkpoints.add(definition.effective_from)
            if (
                definition.effective_to is not None
                and definition.effective_to < date.max
            ):
                gap_start = definition.effective_to + timedelta(days=1)
                if period_start <= gap_start <= period_end:
                    checkpoints.add(gap_start)
        return tuple(sorted(checkpoints))

    def unsupported_asset_state(
        self, symbol: str, on_date: date | None = None
    ) -> tuple[str, str] | None:
        """Identify the warning state, including classification for deduplication."""
        definition = self._definition(symbol, on_date)
        classification = self.classify(symbol, PositionType.stock, on_date)
        if definition is None:
            return "unknown", classification
        if not definition.verified:
            return "unverified", classification
        if self.get_tax_category(classification) == "SO":
            return "unsupported_tax_category", classification
        return None

    def check_unsupported_assets(
        self, symbols: list[str], on_date: date | None = None
    ) -> None:
        for symbol in symbols:
            state = self.unsupported_asset_state(symbol, on_date)
            if state is None:
                continue
            warning_kind, _ = state
            if warning_kind == "unsupported_tax_category":
                logger.warning("Unsupported tax category requires manual review")
                continue
            logger.warning("Asset classification requires manual review")
