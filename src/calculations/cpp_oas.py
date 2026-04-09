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
        years_in_canada: Years of residence in Canada after age 18 (accumulated at this age)
        start_age: Age at which OAS starts (65-70). Deferring increases benefit by 0.6%/month

    Returns:
        Monthly OAS benefit amount (after clawback if applicable)

    Note:
        Requires 40 years for full OAS. Prorated for fewer years (e.g., 30 years = 75% of full OAS).
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

        # Accumulate years in Canada (add years passed since current age, capped at 40)
        years_accumulated = min(years_in_canada + (age - current_age), 40)

        oas_monthly = calculate_oas_benefit(age, total_income, years_accumulated)
        oas_annual = oas_monthly * 12

        projections['cpp_monthly'].append(cpp_monthly)
        projections['oas_monthly'].append(oas_monthly)
        projections['cpp_annual'].append(cpp_annual)
        projections['oas_annual'].append(oas_annual)
        projections['total_annual'].append(cpp_annual + oas_annual)

    return projections


def project_couple_cpp_oas_income(
    person1_current_age: int,
    person2_current_age: int,
    projection_years: int,
    person1_cpp_params: dict,
    person2_cpp_params: dict,
    person1_oas_params: dict,
    person2_oas_params: dict,
    income_func_person1=None,
    income_func_person2=None,
) -> dict:
    """
    Project CPP and OAS for both spouses, considering age differences.

    Args:
        person1_current_age: Person 1's current age
        person2_current_age: Person 2's current age
        projection_years: Number of years to project
        person1_cpp_params: Person 1's CPP parameters (dict with start_age, contribution_years, earnings_ratio)
        person2_cpp_params: Person 2's CPP parameters
        person1_oas_params: Person 1's OAS parameters (dict with start_age, years_in_canada)
        person2_oas_params: Person 2's OAS parameters
        income_func_person1: Function(age) -> income for Person 1 (for OAS clawback)
        income_func_person2: Function(age) -> income for Person 2 (for OAS clawback)

    Returns:
        Dictionary with yearly projections for both spouses
    """
    projections = {
        'year': [],
        'person1_age': [],
        'person2_age': [],
        'person1_cpp_monthly': [],
        'person1_oas_monthly': [],
        'person1_cpp_annual': [],
        'person1_oas_annual': [],
        'person1_total_annual': [],
        'person2_cpp_monthly': [],
        'person2_oas_monthly': [],
        'person2_cpp_annual': [],
        'person2_oas_annual': [],
        'person2_total_annual': [],
        'household_cpp_annual': [],
        'household_oas_annual': [],
        'household_total_annual': [],
    }

    # Calculate base CPP benefits for both
    person1_base_cpp = calculate_cpp_benefit(
        person1_cpp_params['start_age'],
        person1_cpp_params.get('contribution_years', 40),
        person1_cpp_params.get('earnings_ratio', 1.0)
    )

    person2_base_cpp = calculate_cpp_benefit(
        person2_cpp_params['start_age'],
        person2_cpp_params.get('contribution_years', 40),
        person2_cpp_params.get('earnings_ratio', 1.0)
    )

    for year in range(projection_years):
        person1_age = person1_current_age + year
        person2_age = person2_current_age + year

        projections['year'].append(year)
        projections['person1_age'].append(person1_age)
        projections['person2_age'].append(person2_age)

        # Person 1 CPP
        if person1_age >= person1_cpp_params['start_age']:
            person1_cpp_monthly = person1_base_cpp
            person1_cpp_annual = person1_cpp_monthly * 12
        else:
            person1_cpp_monthly = 0.0
            person1_cpp_annual = 0.0

        # Person 2 CPP
        if person2_age >= person2_cpp_params['start_age']:
            person2_cpp_monthly = person2_base_cpp
            person2_cpp_annual = person2_cpp_monthly * 12
        else:
            person2_cpp_monthly = 0.0
            person2_cpp_annual = 0.0

        # Person 1 OAS (with income-based clawback)
        if income_func_person1:
            person1_total_income = income_func_person1(person1_age)
        else:
            person1_total_income = person1_cpp_annual

        # Accumulate years in Canada for Person 1 (add years passed, capped at 40)
        person1_years_accumulated = min(
            person1_oas_params.get('years_in_canada', 40) + (person1_age - person1_current_age),
            40
        )

        person1_oas_monthly = calculate_oas_benefit(
            person1_age,
            person1_total_income,
            person1_years_accumulated,
            person1_oas_params.get('start_age', 65)
        )
        person1_oas_annual = person1_oas_monthly * 12

        # Person 2 OAS (with income-based clawback)
        if income_func_person2:
            person2_total_income = income_func_person2(person2_age)
        else:
            person2_total_income = person2_cpp_annual

        # Accumulate years in Canada for Person 2 (add years passed, capped at 40)
        person2_years_accumulated = min(
            person2_oas_params.get('years_in_canada', 40) + (person2_age - person2_current_age),
            40
        )

        person2_oas_monthly = calculate_oas_benefit(
            person2_age,
            person2_total_income,
            person2_years_accumulated,
            person2_oas_params.get('start_age', 65)
        )
        person2_oas_annual = person2_oas_monthly * 12

        # Store all projections
        projections['person1_cpp_monthly'].append(person1_cpp_monthly)
        projections['person1_oas_monthly'].append(person1_oas_monthly)
        projections['person1_cpp_annual'].append(person1_cpp_annual)
        projections['person1_oas_annual'].append(person1_oas_annual)
        projections['person1_total_annual'].append(person1_cpp_annual + person1_oas_annual)

        projections['person2_cpp_monthly'].append(person2_cpp_monthly)
        projections['person2_oas_monthly'].append(person2_oas_monthly)
        projections['person2_cpp_annual'].append(person2_cpp_annual)
        projections['person2_oas_annual'].append(person2_oas_annual)
        projections['person2_total_annual'].append(person2_cpp_annual + person2_oas_annual)

        projections['household_cpp_annual'].append(person1_cpp_annual + person2_cpp_annual)
        projections['household_oas_annual'].append(person1_oas_annual + person2_oas_annual)
        projections['household_total_annual'].append(
            person1_cpp_annual + person1_oas_annual +
            person2_cpp_annual + person2_oas_annual
        )

    return projections


def calculate_survivor_benefits(
    deceased_cpp_monthly: float,
    survivor_age: int,
    survivor_cpp_monthly: float = 0.0,
) -> dict:
    """
    Calculate CPP survivor benefits when one spouse passes.

    Canadian CPP survivor benefit rules:
    - Survivor under 65: Receives flat-rate survivor pension plus 37.5% of deceased's CPP
    - Survivor 65+: Receives 60% of deceased's CPP
    - If survivor already receiving CPP: Combined benefit is subject to maximum
    - OAS: No survivor benefit; survivor continues receiving their own OAS only

    Args:
        deceased_cpp_monthly: Monthly CPP benefit the deceased was receiving
        survivor_age: Current age of the survivor
        survivor_cpp_monthly: Monthly CPP benefit survivor is receiving (if any)

    Returns:
        Dictionary with survivor benefit details
    """
    # CPP maximum monthly (2026)
    cpp_maximum = CPP_MAX_MONTHLY_2026

    if survivor_age < 65:
        # Under 65: Flat-rate survivor pension + 37.5% of deceased's CPP
        # Flat-rate survivor pension is about $215/month in 2026
        flat_rate_survivor_pension = 215.0
        survivor_cpp_benefit = flat_rate_survivor_pension + (deceased_cpp_monthly * 0.375)

        # If survivor also receiving their own CPP, combine them (subject to maximum)
        if survivor_cpp_monthly > 0:
            combined_cpp = survivor_cpp_monthly + survivor_cpp_benefit
            # Apply maximum cap
            combined_cpp = min(combined_cpp, cpp_maximum)
            additional_from_survivor_benefit = combined_cpp - survivor_cpp_monthly
        else:
            combined_cpp = survivor_cpp_benefit
            additional_from_survivor_benefit = survivor_cpp_benefit

        return {
            'survivor_age': survivor_age,
            'deceased_cpp_monthly': deceased_cpp_monthly,
            'survivor_cpp_before': survivor_cpp_monthly,
            'survivor_cpp_benefit': survivor_cpp_benefit,
            'combined_cpp_monthly': combined_cpp,
            'additional_cpp_from_survivor_benefit': additional_from_survivor_benefit,
            'survivor_cpp_annual': combined_cpp * 12,
            'note': 'Under age 65: Flat-rate pension + 37.5% of deceased CPP, subject to maximum'
        }
    else:
        # Age 65+: Survivor receives 60% of deceased's CPP
        survivor_cpp_benefit = deceased_cpp_monthly * 0.60

        # If survivor also receiving their own CPP, combine them (subject to maximum)
        if survivor_cpp_monthly > 0:
            combined_cpp = survivor_cpp_monthly + survivor_cpp_benefit
            # Apply maximum cap (at 65+, maximum is higher)
            combined_cpp = min(combined_cpp, cpp_maximum)
            additional_from_survivor_benefit = combined_cpp - survivor_cpp_monthly
        else:
            combined_cpp = survivor_cpp_benefit
            additional_from_survivor_benefit = survivor_cpp_benefit

        return {
            'survivor_age': survivor_age,
            'deceased_cpp_monthly': deceased_cpp_monthly,
            'survivor_cpp_before': survivor_cpp_monthly,
            'survivor_cpp_benefit': survivor_cpp_benefit,
            'combined_cpp_monthly': combined_cpp,
            'additional_cpp_from_survivor_benefit': additional_from_survivor_benefit,
            'survivor_cpp_annual': combined_cpp * 12,
            'note': 'Age 65+: 60% of deceased CPP, combined with own CPP up to maximum'
        }
