import pytest

from tastyworksTaxes.vorabpauschale import (
    BASISZINS,
    calculate_vorabpauschale,
    vorabpauschale_deemed_received_year,
)


def calculate(**overrides):
    inputs = {
        "start_of_year_value_eur": 10_000.0,
        "basiszins": BASISZINS[2024],
        "teilfreistellung_pct": 0,
        "distributions_eur": 0.0,
        "value_increase_eur": 1_000.0,
        "months_before_acquisition": 0,
    }
    inputs.update(overrides)
    return calculate_vorabpauschale(**inputs)


def test_canonical_worked_example():
    # Basisertrag = 70% * 2.29% * €10,000 = €160.30; (€160.30 - €100) * 70% = €42.21.
    result = calculate(
        teilfreistellung_pct=30,
        distributions_eur=100.0,
        value_increase_eur=800.0,
    )

    assert result == pytest.approx(42.21)


def test_basisertrag_caps_vorabpauschale():
    assert calculate(value_increase_eur=2_000.0) == pytest.approx(160.30)


def test_value_increase_caps_vorabpauschale():
    assert calculate(value_increase_eur=100.0) == pytest.approx(100.0)


def test_distributions_can_reduce_vorabpauschale_to_zero():
    assert calculate(distributions_eur=200.0) == 0.0


def test_acquisition_year_is_reduced_by_full_preceding_months():
    assert calculate(months_before_acquisition=6) == pytest.approx(80.15)


def test_teilfreistellung_reduces_taxable_amount():
    assert calculate(teilfreistellung_pct=30) == pytest.approx(112.21)


@pytest.mark.parametrize("calendar_year, assessment_year", [(2024, 2025), (2025, 2026)])
def test_deemed_received_year(calendar_year, assessment_year):
    assert vorabpauschale_deemed_received_year(calendar_year) == assessment_year


def test_basiszins_contains_2018_through_2025():
    assert set(range(2018, 2026)) <= BASISZINS.keys()


@pytest.mark.parametrize(
    "overrides",
    [
        {"start_of_year_value_eur": 0.0},
        {"basiszins": 0.0},
        {"basiszins": BASISZINS[2021]},
        {"value_increase_eur": 0.0},
        {"value_increase_eur": -100.0},
        {"months_before_acquisition": 11, "start_of_year_value_eur": 0.0},
    ],
)
def test_zero_and_nonpositive_yield_edges_return_zero(overrides):
    assert calculate(**overrides) == 0.0


@pytest.mark.parametrize(
    "overrides",
    [
        {"start_of_year_value_eur": -1.0},
        {"distributions_eur": -1.0},
        {"teilfreistellung_pct": 20},
        {"months_before_acquisition": -1},
        {"months_before_acquisition": 12},
    ],
)
def test_invalid_inputs_raise_value_error(overrides):
    with pytest.raises(ValueError):
        calculate(**overrides)


def test_noninteger_acquisition_month_count_is_rejected():
    with pytest.raises(TypeError):
        calculate(months_before_acquisition=1.5)
