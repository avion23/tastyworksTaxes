from pathlib import Path

import pandas as pd
import pytest

from tastyworksTaxes.history import History


BROKER_COLUMNS = [
    'Date', 'Type', 'Sub Type', 'Action', 'Symbol', 'Instrument Type',
    'Description', 'Value', 'Quantity', 'Average Price', 'Commissions',
    'Fees', 'Multiplier', 'Root Symbol', 'Underlying Symbol',
    'Expiration Date', 'Strike Price', 'Call or Put', 'Order #', 'Currency',
]


def broker_row(**updates):
    row = {
        'Date': '2024-01-02T12:00:00+00:00',
        'Type': 'Money Movement',
        'Sub Type': 'Deposit',
        'Action': '',
        'Symbol': '',
        'Instrument Type': '',
        'Description': 'SYNTHETIC TRANSACTION',
        'Value': '100.00',
        'Quantity': '0',
        'Average Price': '',
        'Commissions': '',
        'Fees': '0.00',
        'Multiplier': '',
        'Root Symbol': '',
        'Underlying Symbol': '',
        'Expiration Date': '',
        'Strike Price': '',
        'Call or Put': '',
        'Order #': '',
        'Currency': 'USD',
    }
    row.update(updates)
    return row


def stock_trade(**updates):
    row = broker_row(**{
        'Type': 'Trade',
        'Sub Type': 'Buy to Open',
        'Action': 'BUY_TO_OPEN',
        'Symbol': 'SYN',
        'Instrument Type': 'Equity',
        'Description': 'SYNTHETIC STOCK FILL',
        'Value': '-100.00',
        'Quantity': '10',
        'Average Price': '10.00',
        'Commissions': '-1.00',
        'Fees': '-0.10',
        'Root Symbol': 'SYN',
        'Underlying Symbol': 'SYN',
        'Order #': 'ORDER-1',
    })
    row.update(updates)
    return row


def write_broker_csv(path: Path, rows):
    pd.DataFrame(rows, columns=BROKER_COLUMNS).to_csv(path, index=False)


@pytest.fixture(autouse=True)
def deterministic_fx(monkeypatch):
    monkeypatch.setattr(
        'tastyworksTaxes.history.convert_usd_to_eur',
        lambda amount, date: amount,
    )


def test_complete_usd_broker_export_is_normalized_and_retains_identity(tmp_path):
    source = tmp_path / 'transactions.csv'
    write_broker_csv(source, [stock_trade()])

    history = History.fromFile(source)

    assert history.loc[0, 'Currency'] == 'USD'
    assert history.loc[0, 'Order #'] == 'ORDER-1'
    assert history.loc[0, 'Fees'] == pytest.approx(1.10)
    assert history.loc[0, 'Amount'] == -100
    assert history.loc[0, 'Date/Time'] == pd.Timestamp('2024-01-02 12:00:00')


@pytest.mark.parametrize('currency', ['', 'EUR', 'usd-eur'])
def test_non_usd_or_blank_currency_fails_closed(tmp_path, currency):
    source = tmp_path / 'transactions.csv'
    write_broker_csv(source, [broker_row(Currency=currency)])

    with pytest.raises(ValueError, match='Only USD'):
        History.fromFile(source)


@pytest.mark.parametrize('missing', ['Currency', 'Order #'])
def test_incomplete_broker_header_fails_closed(tmp_path, missing):
    source = tmp_path / 'transactions.csv'
    columns = [column for column in BROKER_COLUMNS if column != missing]
    pd.DataFrame([broker_row()], columns=columns).to_csv(source, index=False)

    with pytest.raises(ValueError, match='Unsupported CSV schema'):
        History.fromFile(source)


@pytest.mark.parametrize('value', ['', 'NaN', 'Inf', '-Inf', '1,23'])
def test_invalid_required_amount_never_defaults_to_zero(tmp_path, value):
    source = tmp_path / 'transactions.csv'
    write_broker_csv(source, [broker_row(Value=value)])

    with pytest.raises(ValueError, match="Value"):
        History.fromFile(source)


@pytest.mark.parametrize(
    'field',
    ['Symbol', 'Instrument Type', 'Action', 'Quantity', 'Average Price',
     'Commissions', 'Fees', 'Order #'],
)
def test_trade_fields_are_required_by_transaction_type(tmp_path, field):
    source = tmp_path / 'transactions.csv'
    write_broker_csv(source, [stock_trade(**{field: ''})])

    with pytest.raises(ValueError, match=field.replace('#', r'\#')):
        History.fromFile(source)


def test_absolute_sort_preserves_each_local_wall_time(tmp_path):
    source = tmp_path / 'transactions.csv'
    absolute_earlier = broker_row(
        Date='2024-01-02T10:00:00+02:00',
        Description='ABSOLUTE EARLIER',
        **{'Order #': 'B'},
    )
    absolute_later = broker_row(
        Date='2024-01-02T08:30:00+00:00',
        Description='ABSOLUTE LATER',
        **{'Order #': 'A'},
    )
    write_broker_csv(source, [absolute_later, absolute_earlier])

    history = History.fromFile(source)

    assert history['Description'].tolist() == [
        'ABSOLUTE EARLIER', 'ABSOLUTE LATER'
    ]
    assert history['Date/Time'].tolist() == [
        pd.Timestamp('2024-01-02 10:00:00'),
        pd.Timestamp('2024-01-02 08:30:00'),
    ]


def test_broker_order_then_source_row_break_absolute_time_ties(tmp_path):
    source = tmp_path / 'transactions.csv'
    rows = [
        broker_row(Description='ORDER B', **{'Order #': 'B'}),
        broker_row(Description='ORDER A FIRST', **{'Order #': 'A'}, Value='1'),
        broker_row(Description='ORDER A SECOND', **{'Order #': 'A'}, Value='2'),
    ]
    write_broker_csv(source, rows)

    history = History.fromFile(source)

    assert history['Description'].tolist() == [
        'ORDER A FIRST', 'ORDER A SECOND', 'ORDER B'
    ]


def test_ambiguous_identical_rows_require_manual_review(tmp_path):
    source = tmp_path / 'transactions.csv'
    write_broker_csv(source, [stock_trade(), stock_trade()])

    with pytest.raises(
        ValueError,
        match='ambiguous identical rows.*cannot distinguish.*legitimate identical fills',
    ):
        History.fromFile(source)


def test_distinct_fills_with_same_broker_order_are_retained(tmp_path):
    source = tmp_path / 'transactions.csv'
    write_broker_csv(source, [
        stock_trade(Value='-100.00', **{'Average Price': '10.00'}),
        stock_trade(Value='-55.00', Quantity='5', **{'Average Price': '11.00'}),
    ])

    history = History.fromFile(source)

    assert len(history) == 2
    assert history['Amount'].tolist() == [-100, -55]


def test_internal_schema_requires_nonnegative_normalized_fee_cost(tmp_path):
    source = tmp_path / 'internal.csv'
    pd.DataFrame([{
        'Date/Time': '2024-01-02 12:00:00',
        'Transaction Code': 'Trade',
        'Transaction Subcode': 'Buy to Open',
        'Symbol': 'SYN',
        'Buy/Sell': 'Buy',
        'Open/Close': 'Open',
        'Quantity': '1',
        'Expiration Date': '',
        'Strike': '0',
        'Call/Put': '',
        'Price': '10',
        'Fees': '-1',
        'Amount': '-10',
        'Description': 'SYNTHETIC INTERNAL TRANSACTION',
    }]).to_csv(source, index=False)

    with pytest.raises(ValueError, match='Fees must be nonnegative costs'):
        History.fromFile(source)


def test_utf8_bom_is_accepted_and_non_utf8_has_actionable_error(tmp_path):
    utf8_source = tmp_path / 'utf8.csv'
    pd.DataFrame([broker_row()], columns=BROKER_COLUMNS).to_csv(
        utf8_source, index=False, encoding='utf-8-sig'
    )
    assert len(History.fromFile(utf8_source)) == 1

    non_utf8_source = tmp_path / 'non_utf8.csv'
    pd.DataFrame([broker_row(Description='SYNTHETIC CAFÉ')], columns=BROKER_COLUMNS).to_csv(
        non_utf8_source, index=False, encoding='cp1252'
    )
    with pytest.raises(ValueError, match='must be UTF-8 encoded'):
        History.fromFile(non_utf8_source)


@pytest.mark.parametrize('mutation', ['extra', 'reordered'])
def test_broker_header_must_match_exact_order_without_extras(tmp_path, mutation):
    source = tmp_path / 'transactions.csv'
    columns = list(BROKER_COLUMNS)
    row = broker_row()
    if mutation == 'extra':
        columns.append('Unexpected')
        row['Unexpected'] = 'value'
    else:
        columns[0], columns[1] = columns[1], columns[0]
    pd.DataFrame([row], columns=columns).to_csv(source, index=False)

    with pytest.raises(ValueError, match='ordered 20-column|Unsupported CSV schema'):
        History.fromFile(source)


def test_decimal_to_float_overflow_fails_closed(tmp_path):
    source = tmp_path / 'transactions.csv'
    write_broker_csv(source, [broker_row(Value='9' * 400)])

    with pytest.raises(ValueError, match='overflows finite float range.*Value'):
        History.fromFile(source)


def internal_option_row(**updates):
    row = {
        'Date/Time': '2024-01-02 12:00:00',
        'Transaction Code': 'Trade',
        'Transaction Subcode': 'Buy to Open',
        'Symbol': 'SYN',
        'Buy/Sell': 'Buy',
        'Open/Close': 'Open',
        'Quantity': '1',
        'Expiration Date': '2024-06-21',
        'Strike': '10',
        'Call/Put': 'C',
        'Price': '1',
        'Fees': '1',
        'Amount': '-100',
        'Description': 'SYNTHETIC INTERNAL OPTION',
        'Multiplier': '100',
    }
    row.update(updates)
    return row


@pytest.mark.parametrize(
    'updates',
    [
        {'Strike': '0'},
        {'Strike': '-1'},
        {'Multiplier': '0'},
        {'Multiplier': '-1'},
        {'Call/Put': ''},
        {'Expiration Date': ''},
        {'Expiration Date': 'not-a-date'},
    ],
)
def test_internal_option_fields_must_be_complete_and_positive(tmp_path, updates):
    source = tmp_path / 'internal_option.csv'
    pd.DataFrame([internal_option_row(**updates)]).to_csv(source, index=False)

    with pytest.raises(ValueError, match='Normalized option rows require'):
        History.fromFile(source)


def test_valid_internal_option_fields_are_retained(tmp_path):
    source = tmp_path / 'internal_option.csv'
    pd.DataFrame([internal_option_row()]).to_csv(source, index=False)

    history = History.fromFile(source)

    assert history.loc[0, 'Call/Put'] == 'C'
    assert history.loc[0, 'Strike'] == 10
    assert history.loc[0, 'Multiplier'] == 100
