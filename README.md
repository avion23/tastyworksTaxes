# `tastyworksTaxes`

Automate the calculation of yearly taxes for a tastyworks export in the context of the German private asset management tax situation.

⚠️ **Note:** This software is currently a work in progress. While extensive test driven development has been done with real data, users should be cautious and verify results independently.

🚨🚨🚨 WARNING ON TAXES FOR OPTIONS TRADING 🚨🚨🚨

If you have over 20,000 EUR in annual revenue from options trading, you will be taxed on this revenue even if you did not actually earn a profit! 

This is because losses on long options are subject to a 20,000 EUR deduction limit per year in Germany. Any losses above this cannot be deducted from your taxable income. 

Losses from "terminating transactions" (Termingeschäfte) such as options are subject to a 20,000 EUR deduction limit per year in Germany. This is as per § 20 Abs. 6 Satz 5 EStG (Einkommensteuergesetz).

Any losses above 20,000 EUR cannot be deducted from taxable income and are carried forward to future years.

This means with options trading revenue over 20,000 EUR, you may pay taxes on that revenue even if your actual profit is lower due to undeductible losses.

**Development Status**:
- Currently, the program does not differentiate between various asset classes; it only recognizes stocks and options. This does not accurately reflect all trading scenarios.
- Please triple-check your results. Accurately assigning losses, profits, fees, interest, etc., to their specific categories is challenging.

**Stocks**:

- Gains and losses are calculated using the FIFO (first-in, first-out) method.
- Transaction costs are fully deductible when incurred.
- Other account and deposit fees are already covered under the flat rate operating expenses deduction.
- Dividends from certain German companies like Vonovia, Deutsche Telekom, Freenet are tax-free.
- Losses can only be offset against gains from stocks in the same year. Remaining losses are carried forward indefinitely.

**Options**:

- Each option trade is settled individually, no combined calculation for complex strategies.
- For writing (selling) options, the full premium received is immediately taxed at the time of sale.
- For closing out a written option, the premium paid is deducted and lowers the taxable income.
- For buying options, gains/losses are calculated similar to stocks based on sale proceeds less purchase costs using the FIFO method.
- Losses for long options are subject to the 20,000 EUR annual loss deduction limit for derivatives (Termingeschäfte) in Germany. Any losses above 20,000 EUR cannot be deducted from taxable income and are carried forward to future years. See § 20 Abs. 6 Satz 5 EStG (Einkommensteuergesetz).


## Installation & Setup

### Dependencies Installation

Before running the project, ensure all dependencies are installed. Execute the following command:

```bash
pip install -r requirements.txt
```


## Downloading Data from Tastyworks

1. Visit Tastyworks Transaction History Page.
2. Set Type filter to "all" and specify the date range.
3. Click the CSV button to download.

⚠️ Heads Up
- Transactions may have duplicate timestamps.
- Tastyworks might shorten end dates for data sets exceeding 250 rows.

## Merging Data

Merging is manual. I didn't manage even a half-way automatic merge because of duplicate timestamps.

## Usage

After installing the dependencies, you can run the main program using:
    python tastyworksTaxes/main.py [ --write-closed-trades <output-file.csv> ] <tastyworks-data.csv>

### Test-Driven Development

The project uses pytest for test-driven development. To run tests, use:

    pytest test/

The project also incorporates doctest to test interactive examples within docstrings. These tests can be triggered by executing:

    python -m doctest tastyworksTaxes/*.py

## Known Issues
- Symbol changes currently count as sales. While this simplification doesn't matter if you sell within the same year, it's simply wrong.
- I am not sure about fee calculations.
- In the case of short selling stocks (beyond an annual limit), 30% of the price is taxed with the capital gains tax as a substitute assessment base (§ 43a Absatz 2 Satz 7 EStG), and only offset with the covering. This is not implemented.

## Contributing

Contributions are welcome, this software was a lot of work. Try opening an issue or better a pull request

## License

This software is under the MIT License.
