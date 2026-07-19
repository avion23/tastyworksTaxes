"""Pure helpers for the Vorabpauschale under §§ 18–19 InvStG.

The calculation follows § 18 InvStG and the BMF guidance of 25 July 2023.
Amounts are returned without currency rounding so callers can round only when
presenting or aggregating tax results.
"""


BASISZINS = {
    2018: 0.0087,
    2019: 0.0052,
    2020: 0.0007,
    2021: -0.0045,
    2022: -0.0005,
    2023: 0.0255,
    2024: 0.0229,
    2025: 0.0253,
}

_TEILFREISTELLUNG_PERCENTAGES = {0, 15, 30, 60, 80}


def calculate_vorabpauschale(
    start_of_year_value_eur: float,
    basiszins: float,
    teilfreistellung_pct: float,
    distributions_eur: float,
    value_increase_eur: float,
    months_before_acquisition: int = 0,
) -> float:
    """Return the taxable Vorabpauschale in euros.

    The Basisertrag, value-increase cap, distributions, acquisition-year
    reduction, and Teilfreistellung are applied in that order. In the year of
    acquisition, ``months_before_acquisition`` is the number of full calendar
    months before the acquisition month. See § 18 InvStG and the BMF letter of
    25 July 2023 on application of the InvStG.
    """
    if start_of_year_value_eur < 0:
        raise ValueError("start_of_year_value_eur must not be negative")
    if distributions_eur < 0:
        raise ValueError("distributions_eur must not be negative")
    if teilfreistellung_pct not in _TEILFREISTELLUNG_PERCENTAGES:
        raise ValueError("teilfreistellung_pct must be one of 0, 15, 30, 60, or 80")
    if not isinstance(months_before_acquisition, int):
        raise TypeError("months_before_acquisition must be an integer")
    if not 0 <= months_before_acquisition <= 11:
        raise ValueError("months_before_acquisition must be between 0 and 11")

    basisertrag = 0.7 * basiszins * start_of_year_value_eur
    raw_vorabpauschale = max(
        min(basisertrag, value_increase_eur) - distributions_eur,
        0.0,
    )
    prorated = raw_vorabpauschale * (12 - months_before_acquisition) / 12
    return prorated * (1 - teilfreistellung_pct / 100)


def vorabpauschale_deemed_received_year(calendar_year: int) -> int:
    """Return the assessment year in which a calendar year's amount is received.

    Under § 18 Abs. 3 InvStG, the Vorabpauschale is deemed received on the
    first working day of the following calendar year.
    """
    return calendar_year + 1
