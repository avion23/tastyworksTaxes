# `tastyworksTaxes`

Automate the calculation of yearly taxes for a tastyworks export in the context of the German private asset management tax situation.

⚠️ **Note:** This software is currently a work in progress. While extensive test driven development has been done with real data, users should be cautious and verify results independently.

❗ **UPDATE (December 2024)**: The 20,000 EUR limit on offsetting losses from options trading has been abolished. The German Bundesrat approved this change on November 22, 2024 (Jahressteuergesetz 2024). Losses from derivatives can now be fully offset against capital gains, with retroactive application to all open cases. This follows the Federal Fiscal Court ruling that the previous restriction was unconstitutional.

**Development Status**:
- Currently, the program does not differentiate between various asset classes; it only recognizes stocks and options. This does not accurately reflect all trading scenarios.
- **Please triple-check your results.** Accurately assigning losses, profits, fees, interest, etc., to their specific categories is challenging and this software remains a work in progress.

**Stocks**:

- Gains and losses are calculated using the FIFO (first-in, first-out) method.
- Transaction costs are fully deductible when incurred.
- Other account and deposit fees are already covered under the flat rate operating expenses deduction.
- Dividends from certain German companies like Vonovia, Deutsche Telekom, Freenet are tax-free.
- Losses can only be offset against gains from stocks in the same year. Remaining losses are carried forward indefinitely.

**Options**:

- Each option trade is settled individually, no combined calculation for complex strategies.
- For writing (selling) options, gains/losses are calculated when the position is closed, either by buying back the option or through expiration/assignment.
- For buying options, gains/losses are calculated similar to stocks based on sale proceeds less purchase costs using the FIFO method.
- The FIFO method is used to match opening and closing transactions for accurate profit/loss calculation.

## Installation & Setup

### Dependencies Installation

Before running the project, ensure all dependencies are installed. Execute the following command:

```bash
pip install -r requirements.txt
```

## Downloading Data from Tastyworks (changed in March 2024)

1. Go to https://my.tastytrade.com/app.html#/trading/activity
2. Set the date filter.
3. Set to show only "filled" trades.
4. Click the little "upload" button (it's an upload symbol, not download) to export.

⚠️ Heads Up
- Export limit is now 1000 rows.
- If you use the new platform, you need to convert the new data format to the old format using the `legacy.py` tool.
- New data format might be mergable automatically.

### Converting New Format to Legacy Format

For the new platform data format, use the legacy converter:

```bash
python tastyworksTaxes/legacy.py <new-format.csv> <output-legacy-format.csv>
```

## Usage

After installing the dependencies, you can run the main program using:

```bash
python tastyworksTaxes/main.py [--write-closed-trades <output-file.csv>] <tastyworks-data.csv>
```

### Merging Multiple CSV Files

If you have multiple export files from Tastyworks due to the 1000 row limit, you can merge them before processing:

```bash
cat file1.csv file2.csv file3.csv > merged.csv
# Remove duplicate headers before processing
awk '!seen[$0]++' merged.csv > merged_clean.csv
```

### Test-Driven Development

The project uses pytest for test-driven development. To run tests, use:

```bash
pytest test/
```

For verbose debugging output, use:

```bash
python -m pytest test -s --log-cli-level=DEBUG
```

## Recent Improvements

- **Corporate Actions Fixed**: Symbol Changes and Stock Mergers now preserve original cost basis instead of incorrectly realizing gains/losses
- **Enhanced Partial Exemptions**: Partial exemption (Teilfreistellung) calculation improved for equity ETFs (30%). Other fund types (Mixed, Real Estate) are correctly identified and generate warnings, but their specific exemption rates are not yet applied in the final tax summary
- **Improved FIFO Processing**: Refactored to forward-chronological processing for more accurate trade matching

## Known Issues

⚠️ **Critical**: This software remains a work in progress. I am not a tax expert - there is tax law I don't fully understand.

**Unimplemented Tax Requirements**:
- ETF advance tax payment ("Vorabpauschale") is not implemented. This is yearly fictitious taxable income on accumulating ETFs (70% of base interest rate × fund value at start of year, minus distributions). Required by German tax law since 2018.
- Short selling stocks beyond annual limits: 30% substitute assessment base (§ 43a Absatz 2 Satz 7 EStG) is not implemented.

**Corporate Actions**:
- While Symbol Changes and Stock Mergers are now handled correctly, **Reverse Splits with unrecognized description formats may be incorrectly processed as taxable trades**. These events should be manually verified.

**Other Limitations**:
- Fee calculations remain uncertain and should be double-checked
- Partial exemption rates only cover equity ETFs - other fund types need manual handling

## Contributing

Contributions are welcome, this software was a lot of work. Try opening an issue or better a pull request.

## License

This software is under the MIT License.
