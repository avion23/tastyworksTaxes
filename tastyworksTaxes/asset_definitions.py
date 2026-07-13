import csv
from dataclasses import dataclass
from datetime import date
from importlib.resources import files
from pathlib import Path


CLASSIFICATIONS = {
    "EQUITY_ETF": ("KAP-INV", 30),
    "BOND_ETF": ("KAP-INV", 0),
    "MIXED_FUND_ETF": ("KAP-INV", 15),
    "REAL_ESTATE_ETF": ("KAP-INV", 60),
    "FOREIGN_REAL_ESTATE_ETF": ("KAP-INV", 80),
    "CRYPTO": ("SO", 0),
}
_COLUMNS = {
    "symbol", "classification", "tax_category", "teilfreistellung_pct",
    "verified", "effective_from", "effective_to", "evidence",
}

@dataclass(frozen=True)
class AssetDefinition:
    symbol: str
    classification: str
    tax_category: str
    teilfreistellung_pct: int
    verified: bool
    effective_from: date
    effective_to: date | None
    evidence: str

    def is_effective(self, on_date: date) -> bool:
        return self.effective_from <= on_date and (
            self.effective_to is None or on_date <= self.effective_to
        )


def _date(value: str, field: str, row: int, required: bool = True) -> date | None:
    if not value and not required:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"asset registry row {row}: invalid {field}: {value!r}") from exc


def load_asset_registry(path: Path | None = None) -> tuple[AssetDefinition, ...]:
    registry_path = path or Path(files("tastyworksTaxes").joinpath("asset_registry.csv"))
    with registry_path.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        if set(reader.fieldnames or ()) != _COLUMNS:
            raise ValueError(f"asset registry columns must be exactly {sorted(_COLUMNS)}")
        definitions = []
        for row_number, row in enumerate(reader, start=2):
            if any(value is None for value in row.values()):
                raise ValueError(f"asset registry row {row_number}: malformed CSV row")
            symbol = row["symbol"].strip()
            classification = row["classification"].strip()
            expected = CLASSIFICATIONS.get(classification)
            if not symbol or symbol != symbol.upper() or any(char.isspace() for char in symbol):
                raise ValueError(f"asset registry row {row_number}: invalid symbol {symbol!r}")
            if expected is None:
                raise ValueError(f"asset registry row {row_number}: unknown classification {classification!r}")
            try:
                exemption = int(row["teilfreistellung_pct"])
            except ValueError as exc:
                raise ValueError(f"asset registry row {row_number}: invalid teilfreistellung_pct") from exc
            tax_category = row["tax_category"].strip()
            if (tax_category, exemption) != expected:
                raise ValueError(f"asset registry row {row_number}: tax properties do not match {classification}")
            if row["verified"] not in {"true", "false"}:
                raise ValueError(f"asset registry row {row_number}: verified must be true or false")
            evidence = row["evidence"].strip()
            if not evidence:
                raise ValueError(f"asset registry row {row_number}: evidence is required")
            start = _date(row["effective_from"], "effective_from", row_number)
            end = _date(row["effective_to"], "effective_to", row_number, required=False)
            if end is not None and end < start:
                raise ValueError(f"asset registry row {row_number}: effective_to precedes effective_from")
            definitions.append(AssetDefinition(symbol, classification, tax_category, exemption,
                                               row["verified"] == "true", start, end, evidence))
    for index, definition in enumerate(definitions):
        for other in definitions[index + 1:]:
            if definition.symbol == other.symbol and not (
                definition.effective_to is not None and definition.effective_to < other.effective_from
                or other.effective_to is not None and other.effective_to < definition.effective_from
            ):
                raise ValueError(f"asset registry has overlapping effective dates for {definition.symbol}")
    return tuple(definitions)
