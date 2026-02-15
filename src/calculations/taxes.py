"""
Federal and Ontario tax calculations for retirement income.
"""

from src.utils.constants import (
    FEDERAL_TAX_BRACKETS,
    ONTARIO_TAX_BRACKETS,
    FEDERAL_BASIC_PERSONAL_AMOUNT,
    ONTARIO_BASIC_PERSONAL_AMOUNT,
    AGE_AMOUNT_CREDIT,
    AGE_AMOUNT_THRESHOLD,
    AGE_AMOUNT_REDUCTION_RATE,
    PENSION_INCOME_AMOUNT,
)


def calculate_bracket_tax(income: float, brackets: list) -> float:
    """
    Calculate tax based on progressive tax brackets.

    Args:
        income: Taxable income
        brackets: List of (threshold, rate) tuples

    Returns:
        Total tax amount
    """
    if income <= 0:
        return 0.0

    tax = 0.0
    previous_threshold = 0

    for threshold, rate in brackets:
        if income <= previous_threshold:
            break

        taxable_in_bracket = min(income, threshold) - previous_threshold
        tax += taxable_in_bracket * rate
        previous_threshold = threshold

        if income <= threshold:
            break

    return tax


def calculate_federal_tax(
    total_income: float,
    age: int,
    rrsp_withdrawal: float = 0,
    eligible_pension_income: float = 0,
) -> dict:
    """
    Calculate federal income tax and credits.

    Args:
        total_income: Total annual income
        age: Age (for age amount credit)
        rrsp_withdrawal: RRSP/RRIF withdrawal amount
        eligible_pension_income: Eligible pension income (for pension income credit)

    Returns:
        Dictionary with tax breakdown
    """
    # Basic personal amount credit
    bpa_credit = FEDERAL_BASIC_PERSONAL_AMOUNT * 0.15  # 15% federal rate

    # Age amount credit (for 65+)
    age_credit = 0.0
    if age >= 65:
        if total_income <= AGE_AMOUNT_THRESHOLD:
            age_credit = AGE_AMOUNT_CREDIT * 0.15
        elif total_income < AGE_AMOUNT_THRESHOLD + (AGE_AMOUNT_CREDIT / AGE_AMOUNT_REDUCTION_RATE):
            # Reduced age amount
            excess = total_income - AGE_AMOUNT_THRESHOLD
            reduction = excess * AGE_AMOUNT_REDUCTION_RATE
            reduced_amount = max(AGE_AMOUNT_CREDIT - reduction, 0)
            age_credit = reduced_amount * 0.15
        # else: fully phased out

    # Pension income amount credit
    pension_credit = 0.0
    if age >= 65 and (rrsp_withdrawal > 0 or eligible_pension_income > 0):
        # Can claim up to $2,000 of eligible pension income
        eligible_amount = min(rrsp_withdrawal + eligible_pension_income, PENSION_INCOME_AMOUNT)
        pension_credit = eligible_amount * 0.15

    # Calculate tax on brackets
    gross_tax = calculate_bracket_tax(total_income, FEDERAL_TAX_BRACKETS)

    # Apply credits
    total_credits = bpa_credit + age_credit + pension_credit
    net_tax = max(gross_tax - total_credits, 0)

    return {
        'gross_tax': gross_tax,
        'bpa_credit': bpa_credit,
        'age_credit': age_credit,
        'pension_credit': pension_credit,
        'total_credits': total_credits,
        'net_tax': net_tax,
    }


def calculate_ontario_tax(
    total_income: float,
    age: int,
    rrsp_withdrawal: float = 0,
) -> dict:
    """
    Calculate Ontario provincial income tax and credits.

    Args:
        total_income: Total annual income
        age: Age (for age amount credit)
        rrsp_withdrawal: RRSP/RRIF withdrawal amount

    Returns:
        Dictionary with tax breakdown
    """
    # Basic personal amount credit
    bpa_credit = ONTARIO_BASIC_PERSONAL_AMOUNT * 0.0505  # 5.05% Ontario rate

    # Ontario age amount credit (for 65+)
    ontario_age_amount = 5537  # 2026 amount
    ontario_age_threshold = 42335
    age_credit = 0.0
    if age >= 65:
        if total_income <= ontario_age_threshold:
            age_credit = ontario_age_amount * 0.0505
        elif total_income < ontario_age_threshold + (ontario_age_amount / 0.15):
            # Reduced age amount
            excess = total_income - ontario_age_threshold
            reduction = excess * 0.15
            reduced_amount = max(ontario_age_amount - reduction, 0)
            age_credit = reduced_amount * 0.0505
        # else: fully phased out

    # Ontario pension income credit
    pension_credit = 0.0
    if age >= 65 and rrsp_withdrawal > 0:
        eligible_amount = min(rrsp_withdrawal, 1605)  # Ontario pension income amount
        pension_credit = eligible_amount * 0.0505

    # Calculate tax on brackets
    gross_tax = calculate_bracket_tax(total_income, ONTARIO_TAX_BRACKETS)

    # Apply credits
    total_credits = bpa_credit + age_credit + pension_credit
    net_tax = max(gross_tax - total_credits, 0)

    return {
        'gross_tax': gross_tax,
        'bpa_credit': bpa_credit,
        'age_credit': age_credit,
        'pension_credit': pension_credit,
        'total_credits': total_credits,
        'net_tax': net_tax,
    }


def calculate_total_tax(
    total_income: float,
    age: int,
    rrsp_withdrawal: float = 0,
    eligible_pension_income: float = 0,
) -> dict:
    """
    Calculate combined federal and Ontario tax.

    Args:
        total_income: Total annual income
        age: Age
        rrsp_withdrawal: RRSP/RRIF withdrawal amount
        eligible_pension_income: Other eligible pension income

    Returns:
        Dictionary with complete tax breakdown
    """
    federal = calculate_federal_tax(total_income, age, rrsp_withdrawal, eligible_pension_income)
    ontario = calculate_ontario_tax(total_income, age, rrsp_withdrawal)

    combined_tax = federal['net_tax'] + ontario['net_tax']
    effective_rate = (combined_tax / total_income * 100) if total_income > 0 else 0

    return {
        'total_income': total_income,
        'federal_tax': federal['net_tax'],
        'ontario_tax': ontario['net_tax'],
        'total_tax': combined_tax,
        'after_tax_income': total_income - combined_tax,
        'effective_rate': effective_rate,
        'federal_details': federal,
        'ontario_details': ontario,
    }


def calculate_marginal_rate(income: float, age: int = 65) -> float:
    """
    Calculate marginal tax rate at a given income level.

    Args:
        income: Current income level
        age: Age (affects available credits)

    Returns:
        Marginal tax rate as a decimal
    """
    # Test with small increment
    increment = 1000
    tax_at_income = calculate_total_tax(income, age)['total_tax']
    tax_at_higher = calculate_total_tax(income + increment, age)['total_tax']

    marginal_rate = (tax_at_higher - tax_at_income) / increment
    return marginal_rate


def project_lifetime_taxes(
    ages: list,
    incomes: list,
    rrsp_withdrawals: list = None,
) -> dict:
    """
    Project taxes over multiple years.

    Args:
        ages: List of ages for each year
        incomes: List of total income for each year
        rrsp_withdrawals: List of RRSP withdrawals for each year

    Returns:
        Dictionary with yearly tax projections
    """
    if rrsp_withdrawals is None:
        rrsp_withdrawals = [0] * len(ages)

    projections = {
        'age': [],
        'income': [],
        'federal_tax': [],
        'ontario_tax': [],
        'total_tax': [],
        'after_tax_income': [],
        'effective_rate': [],
    }

    for i, age in enumerate(ages):
        income = incomes[i]
        rrsp_withdrawal = rrsp_withdrawals[i] if i < len(rrsp_withdrawals) else 0

        tax_calc = calculate_total_tax(income, age, rrsp_withdrawal)

        projections['age'].append(age)
        projections['income'].append(income)
        projections['federal_tax'].append(tax_calc['federal_tax'])
        projections['ontario_tax'].append(tax_calc['ontario_tax'])
        projections['total_tax'].append(tax_calc['total_tax'])
        projections['after_tax_income'].append(tax_calc['after_tax_income'])
        projections['effective_rate'].append(tax_calc['effective_rate'])

    return projections
