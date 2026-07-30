"""Pure helpers for the Vorabpauschale under §§ 18–19 InvStG.

Under § 18 Abs. 1 InvStG, the Basisertrag is 70 percent of the Basiszins
multiplied by the value at the beginning of the year. It is capped at the
increase from the first to the last redemption price plus distributions.
The calculation also follows the BMF guidance of 25 July 2023. Amounts are
returned without currency rounding so callers can round only when presenting
or aggregating tax results.
"""

import math
from numbers import Real


BASISZINS = {
    2018: 0.0087,
    2019: 0.0052,
    2020: 0.0007,
    2021: -0.0045,
    2022: -0.0005,
    2023: 0.0255,
    2024: 0.0229,
    2025: 0.0253,
    2026: 0.0320,
}

_TEILFREISTELLUNG_PERCENTAGES = {0, 15, 30, 60, 80}


def _validate_finite_number(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a number")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


def calculate_vorabpauschale(
    start_of_year_value_eur: float,
    basiszins: float,
    teilfreistellung_pct: float,
    distributions_eur: float,
    value_increase_eur: float,
    months_before_acquisition: int = 0,
) -> float:
    """Return the taxable Vorabpauschale in euros.

    The Basisertrag is capped by the increase in value plus distributions.
    Distributions are then deducted, followed by the reduction for a mid-year
    acquisition and the Teilfreistellung. In the year of acquisition,
    ``months_before_acquisition`` is the number of full calendar months before
    the acquisition month. ``start_of_year_value_eur`` is the fund's redemption
    price (or exchange/market price) at the beginning of the calendar year, not
    the investor's acquisition cost. If a fund was launched during the year,
    its legally applicable first redemption, exchange, or market price may be
    used. See § 18 InvStG and the BMF letter of 25 July 2023 on application of
    the InvStG.
    """
    _validate_finite_number("start_of_year_value_eur", start_of_year_value_eur)
    _validate_finite_number("basiszins", basiszins)
    _validate_finite_number("teilfreistellung_pct", teilfreistellung_pct)
    _validate_finite_number("distributions_eur", distributions_eur)
    _validate_finite_number("value_increase_eur", value_increase_eur)

    if start_of_year_value_eur < 0:
        raise ValueError("start_of_year_value_eur must not be negative")
    if distributions_eur < 0:
        raise ValueError("distributions_eur must not be negative")
    if teilfreistellung_pct not in _TEILFREISTELLUNG_PERCENTAGES:
        raise ValueError("teilfreistellung_pct must be one of 0, 15, 30, 60, or 80")
    if isinstance(months_before_acquisition, bool) or not isinstance(
        months_before_acquisition, int
    ):
        raise TypeError("months_before_acquisition must be an integer")
    if not 0 <= months_before_acquisition <= 11:
        raise ValueError("months_before_acquisition must be between 0 and 11")

    basisertrag = 0.7 * basiszins * start_of_year_value_eur
    capped_basisertrag = min(
        basisertrag,
        value_increase_eur + distributions_eur,
    )
    raw_vorabpauschale = max(capped_basisertrag - distributions_eur, 0.0)
    holding_adjusted_vorabpauschale = (
        raw_vorabpauschale * (12 - months_before_acquisition) / 12
    )
    return holding_adjusted_vorabpauschale * (1 - teilfreistellung_pct / 100)


def vorabpauschale_deemed_received_year(calendar_year: int) -> int:
    """Return the assessment year in which a calendar year's amount is received.

    Under § 18 Abs. 3 InvStG, the Vorabpauschale is deemed received on the
    first working day of the following calendar year.
    """
    if isinstance(calendar_year, bool) or not isinstance(calendar_year, int):
        raise TypeError("calendar_year must be an integer")
    return calendar_year + 1
