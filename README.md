# tastyworksTaxes
calculates the yearly taxes for a tastyworks export


## download from tastyworks
- go to https://trade.tastyworks.com/index.html#/transactionHistoryPage
- download :)
- careful: The transactions may have duplicate timestamps
- careful: Tastyworks silently shortens the end date if you have too many transactions. The limit might be 250 rows

## merging

- it's manual ;(

## How to use
`python main.py [ --write-closed-trades <output-file.csv> ] <tastyworks-data.csv> `