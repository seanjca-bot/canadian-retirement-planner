"""
CPP (Canada Pension Plan) and OAS (Old Age Security) calculations.
"""

from src.utils.constants import (
    CPP_MAX_MONTHLY_2026,
    CPP_EARLY_PENALTY_PER_MONTH,
    CPP_LATE_BONUS_PER_MONTH,
    CPP_MIN_AGE,
    CPP_STANDARD_AGE,
    CPP_MAX_AGE,
    OAS_MAX_MONTHLY_2026,
    OAS_AGE_75_INCREASE,
    OAS_MIN_AGE,
    OAS_CLAWBACK_THRESHOLD,
    OAS_CLAWBACK_RATE,
    OAS_CLAWBACK_ELIMINATION,
)


def calculate_cpp_benefit(
    start_age: int,
    contribution_years: int = 40,
    average_earnings_ratio: float = 1.0,
) -> float:
    """
    Calculate monthly CPP benefit based on start age and contribution history.

    Args:
        start_age: Age at which to start receiving CPP (60-70)
        contribution_years: Number of years of CPP contributions
        average_earnings_ratio: Ratio of average earnings to YMPE (0.0-1.0)
            1.0 = always earned at or above YMPE
            0.5 = earned 50% of YMPE on average

    Returns:
        Monthly CPP benefit amount
    """
    if start_age < CPP_MIN_AGE or start_age > CPP_MAX_AGE:
        raise ValueError(f"CPP start age must be between {CPP_MIN_AGE} and {CPP_MAX_AGE}")

    if average_earnings_ratio < 0 or average_earnings_ratio > 1:
        raise ValueError("Average earnings ratio must be between 0 and 1")

    # Base benefit based on contribution history
    # Maximum benefit assumes 39+ years of maximum contributions
    contribution_factor = min(contribution_years / 39, 1.0)
    base_benefit = CPP_MAX_MONTHLY_2026 * average_earnings_ratio * contribution_factor

    # Adjust for early or late start
    months_from_65 = (start_age - CPP_STANDARD_AGE) * 12

    if months_from_65 < 0:
        # Early retirement penalty
        adjustment = 1 - (abs(months_from_65) * CPP_EARLY_PENALTY_PER_MONTH)
    elif months_from_65 > 0:
        # Late retirement bonus
        adjustment = 1 + (months_from_65 * CPP_LATE_BONUS_PER_MONTH)
    else:
        adjustment = 1.0

    return base_benefit * adjustment


def calculate_oas_benefit(
    age: int,
    annual_income: float,
    years_in_canada: int = 40,
    start_age: int = 65,
) -> float:
    """
    Calculate monthly OAS benefit based on age, income, and residency.

    Args:
        age: Current age
        annual_income: Total annual income (for clawback calculation)
        years_in_canada: Years of residence in Canada after age 18
        start_age: Age at which OAS starts (65-70). Deferring increases benefit by 0.6%/month

    Returns:
        Monthly OAS benefit amount (after clawback if applicable)
    """
    # Don't receive OAS if below start age
    if age < start_age:
        return 0.0

    # Base OAS amount (requires 40 years of Canadian residence for full amount)
    residency_factor = min(years_in_canada / 40, 1.0)
    base_oas = OAS_MAX_MONTHLY_2026 * residency_factor

    # Apply deferral bonus (0.6% per month, or 7.2% per year)
    if start_age > OAS_MIN_AGE:
        months_deferred = (start_age - OAS_MIN_AGE) * 12
        deferral_bonus = months_deferred * 0.006  # 0.6% per month
        base_oas *= (1 + deferral_bonus)

    # 10% increase at age 75
    if age >= 75:
        base_oas *= OAS_AGE_75_INCREASE

    # Calculate clawback
    if annual_income <= OAS_CLAWBACK_THRESHOLD:
        clawback = 0.0
    elif annual_income >= OAS_CLAWBACK_ELIMINATION:
        return 0.0  # Fully clawed back
    else:
        excess_income = annual_income - OAS_CLAWBACK_THRESHOLD
        annual_clawback = excess_income * OAS_CLAWBACK_RATE
        monthly_clawback = annual_clawback / 12
        clawback = min(monthly_clawback, base_oas)

    return max(base_oas - clawback, 0.0)


def project_cpp_oas_income(
    current_age: int,
    cpp_start_age: int,
    projection_years: int,
    cpp_contribution_years: int = 40,
    cpp_earnings_ratio: float = 1.0,
    years_in_canada: int = 40,
    annual_income_func=None,
) -> dict:
    """
    Project CPP and OAS income over multiple years.

    Args:
        current_age: Current age
        cpp_start_age: Age to start receiving CPP
        projection_years: Number of years to project
        cpp_contribution_years: Years of CPP contributions
        cpp_earnings_ratio: Average earnings ratio to YMPE
        years_in_canada: Years of Canadian residence after 18
        annual_income_func: Function that takes age and returns total annual income
            (used for OAS clawback calculation)

    Returns:
        Dictionary with yearly projections
    """
    projections = {
        'age': [],
        'cpp_monthly': [],
        'oas_monthly': [],
        'cpp_annual': [],
        'oas_annual': [],
        'total_annual': [],
    }

    # Calculate base CPP benefit (same for all years once started)
    base_cpp = calculate_cpp_benefit(
        cpp_start_age,
        cpp_contribution_years,
        cpp_earnings_ratio
    )

    for year in range(projection_years):
        age = current_age + year
        projections['age'].append(age)

        # CPP starts at specified age
        if age >= cpp_start_age:
            cpp_monthly = base_cpp
            cpp_annual = cpp_monthly * 12
        else:
            cpp_monthly = 0.0
            cpp_annual = 0.0

        # Calculate OAS (starts at 65, with clawback based on income)
        if annual_income_func:
            total_income = annual_income_func(age)
        else:
            total_income = cpp_annual

        oas_monthly = calculate_oas_benefit(age, total_income, years_in_canada)
        oas_annual = oas_monthly * 12

        projections['cpp_monthly'].append(cpp_monthly)
        projections['oas_monthly'].append(oas_monthly)
        projections['cpp_annual'].append(cpp_annual)
        projections['oas_annual'].append(oas_annual)
        projections['total_annual'].append(cpp_annual + oas_annual)

    return projections
