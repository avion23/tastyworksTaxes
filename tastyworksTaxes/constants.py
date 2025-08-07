from enum import Enum

class TransactionSubcode(Enum):
    BUY_TO_OPEN = "Buy to Open"
    SELL_TO_OPEN = "Sell to Open"
    BUY_TO_CLOSE = "Buy to Close"
    SELL_TO_CLOSE = "Sell to Close"
    ASSIGNMENT = "Assignment"
    EXPIRATION = "Expiration"
    REVERSE_SPLIT = "Reverse Split"
    SYMBOL_CHANGE = "Symbol Change"
    STOCK_MERGER = "Stock Merger"

class TransactionCode(Enum):
    TRADE = "Trade"
    RECEIVE_DELIVER = "Receive Deliver"
    MONEY_MOVEMENT = "Money Movement"

class OpenClose(Enum):
    OPEN = "Open"
    CLOSE = "Close"

class Fields(Enum):
    SYMBOL = "Symbol"
    QUANTITY = "Quantity"
    AMOUNT = "Amount"
    AMOUNT_EURO = "AmountEuro"
    FEES = "Fees"
    FEES_EURO = "FeesEuro"
    CALL_PUT = "Call/Put"
    STRIKE = "Strike"
    EXPIRATION_DATE = "Expiration Date"
    TRANSACTION_SUBCODE = "Transaction Subcode"
    TRANSACTION_CODE = "Transaction Code"
    OPEN_CLOSE = "Open/Close"
    DATE_TIME = "Date/Time"
    BUY_SELL = "Buy/Sell"
    DESCRIPTION = "Description"

class MoneyMovementType(Enum):
    TRANSFER = "Transfer"
    WITHDRAWAL = "Withdrawal"
    BALANCE_ADJUSTMENT = "Balance Adjustment"
    FEE = "Fee"
    DEPOSIT = "Deposit"
    CREDIT_INTEREST = "Credit Interest"
    DEBIT_INTEREST = "Debit Interest"
    DIVIDEND = "Dividend"
    STOCK_LENDING = "Fully Paid Stock Lending Income"

# Transaction validation sets
CLOSING_SUBCODES = {
    TransactionSubcode.ASSIGNMENT.value,
    TransactionSubcode.EXPIRATION.value,
    TransactionSubcode.BUY_TO_CLOSE.value,
    TransactionSubcode.SELL_TO_CLOSE.value
}

VALID_OPTION_TYPES = {"P", "C"}

VALID_TRANSACTION_CODES = {
    TransactionCode.TRADE.value,
    TransactionCode.RECEIVE_DELIVER.value,
    TransactionCode.MONEY_MOVEMENT.value
}