# `tastyworksTaxes`

[![Tests](https://github.com/avion23/tastyworksTaxes/actions/workflows/tests.yml/badge.svg)](https://github.com/avion23/tastyworksTaxes/actions)

`tastyworksTaxes` is a batch ETL-style accounting and reporting pipeline for
TastyTrade/Tastyworks transaction exports in the context of German private
investment taxation. It:

1. extracts transactions from a CSV export;
2. normalizes the supported broker schema and sorts transactions by time;
3. converts USD amounts and fees to EUR;
4. applies FIFO lot accounting, configured corporate actions, and reviewed
   asset classifications; and
5. prints annual German tax-report categories and can export closed trades.

## Validation status and disclaimer

This project is an open-source tax-preparation aid, not tax advice. Tax law,
broker exports, exchange-rate data, and individual circumstances change. Review
the generated figures against broker statements and consult a qualified tax
advisor before filing.

A report is **not filing-ready** when the command emits a warning or an explicit
`NOT FILING-READY` marker. Unknown or unverified assets, unsupported tax
categories, ambiguous corporate actions, exchange-rate fallbacks, unmatched
option exercise records, and closed short-stock trades all require review.

The pipeline covers stocks, options, selected corporate actions, dividends,
interest, fees, and USD/EUR conversion. Verified registry entries can apply
partial exemptions of 30% for equity funds, 15% for mixed funds, 60% for
domestic real-estate funds, and 80% for foreign real-estate funds. Registry
coverage is instrument- and date-specific.

The former EUR 20,000 offset limit for derivative losses was removed by the
Jahressteuergesetz 2024 with retroactive effect for open cases. The program
reports option gains and losses without applying that former limit.

## Requirements and installation

CI verifies Python 3.10, 3.11, and 3.12. The direct runtime, test, and build
dependencies have exact pins in `pyproject.toml`. Their transitive dependencies
remain resolved by `pip` and can vary between installations. Install the package
inside an isolated Python environment:

```bash
python -m pip install .
```

This installs the `tastyworks-taxes` console command and both packaged data
resources. For development and scenario verification, install the test extra:

```bash
python -m pip install '.[test]'
python -m pytest test/
```

`python -m pip install -r requirements.txt` is an equivalent checkout-local
shortcut for the package plus its test extra. A system Python managed by an OS
package manager can reject global `pip` installs; use that platform's isolated
environment or application installer instead of overriding its protection.

## Obtain a supported export

Export **Transactions** history from the TastyTrade activity page, not Orders
or Activity data. Broker exports can have a row limit, so use non-overlapping
date ranges when one file is not enough.

The parser does not select a schema by a claimed column count. The TastyTrade
broker export header must exactly match the ordered 20-column schema:

- `Date`, `Type`, `Sub Type`, `Action`, `Symbol`, `Instrument Type`,
  `Description`, `Value`, `Quantity`, `Average Price`, `Commissions`, `Fees`,
  `Multiplier`, `Root Symbol`, `Underlying Symbol`, `Expiration Date`,
  `Strike Price`, `Call or Put`, `Order #`, `Currency`

The current 21-column variant with `Total` between `Order #` and `Currency` is
accepted as well; the `Total` column is ignored. Nothing in the broker format
is optional: a file with only a subset of these columns (for example just
`Date`, `Type`, `Sub Type`, `Value`, `Description`) is rejected, and `Date`
must be ISO 8601 with a timezone offset. Other broker layouts are rejected. A
normalized 14-column internal schema is also accepted for programmatic
workflows, but that is not a promise of compatibility with an old broker
export; only the internal schema fills defaults for absent fields (`Underlying
Symbol` falls back to `Symbol`, `Multiplier` defaults to `100`, `Order #` to
empty, and `Currency` to `USD`).

## Run the batch pipeline

```bash
tastyworks-taxes [--write-closed-trades <output-file.csv>] <transactions.csv>
```

For example:

```bash
tastyworks-taxes --write-closed-trades closed-trades.csv transactions.csv
```

The input must be a file. The output directory must already exist, and the
closed-trades output cannot overwrite the input. Annual reports go to standard
output; diagnostics go to standard error.

The module entry point is equivalent:

```bash
python -m tastyworksTaxes.main transactions.csv
```

## Duplicate rows in exports

Tastytrade can export byte-identical rows for one order: an order filled in
several identical sub-fills (execution legs) and an echo of a single fill are
indistinguishable from the export alone. Review of real exports found that most
identical-row groups balance only as real positions (their close quantity
matches the number of rows), so automatic removal is unsafe.

The loader therefore rejects every file containing identical rows unless you
explicitly opt in. The default `--duplicates fail` raises the
"ambiguous identical rows" error and requires manual review before accounting.
`--duplicates keep` loads every byte-identical row as a separate fill and logs
the loaded count without any financial details:

```bash
tastyworks-taxes --duplicates keep transactions.csv
```

`keep` is only safe for a single-source export that was never assembled by
concatenating overlapping export windows, where a real fill can appear twice.
Review the broker activity page before choosing `keep`.

## Merge non-overlapping exports

The loader sorts normalized transactions from oldest to newest before
processing. Keeping the merged file in the same order makes it easier to audit:

```python
import pandas as pd

frames = [pd.read_csv(path) for path in ("file1.csv", "file2.csv", "file3.csv")]
merged = pd.concat(frames, ignore_index=True)
merged = merged.drop_duplicates()  # only for exact overlap between exports
merged = merged.sort_values("Date", ascending=True)
merged.to_csv("transactions.csv", index=False)
```

Do not drop rows merely because two legitimate transactions look similar.
Review overlap boundaries and broker order identifiers before removing anything.

## Configuration data

Asset classifications are bundled in `tastyworksTaxes/asset_registry.csv`.
Each row records the symbol, classification, tax category, partial-exemption
rate, verification state, effective dates, and evidence. The loader rejects
malformed rows, unknown categories, inconsistent rates, and overlapping date
ranges.

A `verified=false` row remains a review record only. The calculator treats it
as an individual stock for tax calculations, applies no partial exemption, and
marks affected annual output not filing-ready. Do not infer fund status from a
ticker or product name. Verify the exact share class, preferably by ISIN,
against applicable binding investment terms before changing registry data.

Configured reverse-split ratios are bundled in
`tastyworksTaxes/corporate_actions.csv`. An ambiguous split without an explicit,
finite, positive ratio fails before lot mutation. Changes to either bundled file
are source changes: review them, retain evidence, run the scenarios, and rebuild
the package. The current CLI does not load arbitrary user registry paths.

## USD to EUR conversion of cash flows

USD amounts convert to EUR with the ECB reference rates bundled with the
`currencyconverter` package. Within the bundled rate range, non-publication
dates (weekends and ECB holidays) use the nearest earlier ECB reference rate,
for both securities transactions and cash flows recorded as `Money Movement`
(deposits, withdrawals, dividends, interest, fees). Dates outside the bundled
rate range fail with an explicit error that asks to update the bundled ECB
reference-rate data; `get_used_rate` remains strict and only accepts exact ECB
publication dates. A zero amount returns `0.00` EUR without any rate lookup.
The current 21-column export with the `Total` column between `Order #` and
`Currency` is accepted in addition to the 20-column export; the `Total` column
is ignored. Byte-identical rows are handled by the explicit `--duplicates`
policy described below.

## Standalone Vorabpauschale utility

`tastyworksTaxes.vorabpauschale.calculate_vorabpauschale` is a standalone
utility. The report pipeline never computes Vorabpauschale and never emits
amounts for it, but for every detected fund year the report prints an
automatic "Vorabpauschale and per-fund KAP-INV lines are manual" note. The
caller must supply all applicable EUR values,
including the opening redemption/exchange/market price, distributions, value
increase, Basiszins, partial-exemption rate, and acquisition timing. Its result
does not account for holdings or distributions outside the supplied values.

## Current limitations

- Stock short-selling cases that can require a 30% substitute assessment base
  under § 43a Absatz 2 Satz 7 EStG are detected but not calculated.
- Fee treatment must be checked against the applicable form instructions and
  broker statement.
- Missing or unverified asset classifications require manual review. The
  bundled registry currently contains no verified domestic or foreign
  real-estate fund entries.
- Symbol changes and mergers preserve original basis. Unsupported or ambiguous
  corporate-action records fail rather than being estimated.
- Option reverse-split Close/Open bookkeeping requires an OCC contract token,
  explicit Open/Close operation, and valid option fields.
- Vorabpauschale remains outside the batch report.

## Verification approach

The repository uses requirement tests for pure calculation rules and scenario
tests for complete workflows. CI builds a wheel, installs that wheel with the
`test` extra, verifies both packaged CSV resources and the console command, and
runs the copied test suite outside the source checkout. CI rejects unexpected
skipped scenarios. This checks the installed artifact rather than only imports
from the repository directory.

## License

MIT. See `LICENSE`.
