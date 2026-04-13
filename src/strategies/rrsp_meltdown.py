"""
RRSP Meltdown strategy optimizer.

The RRSP meltdown strategy involves strategically withdrawing from RRSP before age 72
to minimize lifetime taxes and OAS clawback. This is particularly beneficial for high-income
retirees who would face OAS clawback at age 65+.
"""

import numpy as np
from src.calculations.taxes import calculate_total_tax
from src.calculations.cpp_oas import calculate_oas_benefit
from src.utils.constants import (
    RRIF_CONVERSION_AGE,
    OAS_CLAWBACK_THRESHOLD,
    INFLATION_RATE,
    DEFAULT_PROVINCE,
)


def calculate_optimal_rrsp_withdrawal(
    age: int,
    rrsp_balance: float,
    other_income: float,
    target_income_threshold: float = None,
) -> float:
    """
    Calculate optimal RRSP withdrawal to stay below OAS clawback threshold.

    Args:
        age: Current age
        rrsp_balance: Current RRSP balance
        other_income: Other income for the year (CPP, employment, etc.)
        target_income_threshold: Target income level (defaults to OAS clawback threshold)

    Returns:
        Recommended RRSP withdrawal amount
    """
    if target_income_threshold is None:
        target_income_threshold = OAS_CLAWBACK_THRESHOLD

    # Calculate maximum withdrawal to stay at threshold
    max_withdrawal_for_threshold = max(target_income_threshold - other_income, 0)

    # Don't withdraw more than available balance
    recommended_withdrawal = min(max_withdrawal_for_threshold, rrsp_balance)

    return recommended_withdrawal


def simulate_meltdown_strategy(
    current_age: int,
    retirement_age: int,
    rrsp_balance: float,
    tfsa_balance: float,
    annual_income_before_65: float,
    cpp_amount: float,
    years_in_canada: int = 40,
    target_income_threshold: float = None,
    investment_return: float = 0.06,
    annual_spending: float = 60000,
    oas_start_age: int = 65,
    province: str = DEFAULT_PROVINCE,
) -> dict:
    """
    Simulate RRSP meltdown strategy over retirement.

    The strategy:
    1. Before OAS start age: Withdraw RRSP to target income level
    2. After OAS starts: Minimize RRSP withdrawals to avoid OAS clawback
    3. Age 72: Convert remaining RRSP to RRIF with minimum withdrawals

    Args:
        current_age: Current age
        retirement_age: Age at retirement
        rrsp_balance: Current RRSP balance
        tfsa_balance: Current TFSA balance
        annual_income_before_65: Annual income before age 65 (employment, etc.)
        cpp_amount: Monthly CPP amount (starts at 65)
        years_in_canada: Years of Canadian residence
        target_income_threshold: Target income to stay below (default: OAS clawback)
        investment_return: Expected annual return
        oas_start_age: Age at which to start OAS (65-70)
        annual_spending: Annual spending requirement

    Returns:
        Dictionary with year-by-year projections
    """
    if target_income_threshold is None:
        target_income_threshold = OAS_CLAWBACK_THRESHOLD

    max_age = 95
    years = max_age - current_age + 1

    projections = {
        'age': [],
        'rrsp_balance': [],
        'tfsa_balance': [],
        'rrsp_withdrawal': [],
        'tfsa_withdrawal': [],
        'other_income': [],
        'cpp_income': [],
        'oas_income': [],
        'total_income': [],
        'total_tax': [],
        'after_tax_income': [],
        'spending': [],
        'net_cash_flow': [],
    }

    current_rrsp = rrsp_balance
    current_tfsa = tfsa_balance

    for year in range(years):
        age = current_age + year
        projections['age'].append(age)

        # Determine other income (before RRSP withdrawal)
        if age < retirement_age:
            other_income = annual_income_before_65
        elif age < 65:
            other_income = 0
        else:
            other_income = 0

        # CPP starts at 65
        cpp_annual = cpp_amount * 12 if age >= 65 else 0

        # Calculate OAS (will be calculated after determining total income)
        # For planning purposes, estimate based on threshold

        # Determine RRSP withdrawal strategy
        if age < 65:
            # Before 65: Withdraw up to target threshold
            target_withdrawal = calculate_optimal_rrsp_withdrawal(
                age, current_rrsp, other_income + cpp_annual, target_income_threshold
            )
            rrsp_withdrawal = min(target_withdrawal, current_rrsp)
        elif age <= RRIF_CONVERSION_AGE:
            # Age 65-71: Minimize withdrawals to avoid OAS clawback
            # Only withdraw what's needed beyond other sources
            other_sources = other_income + cpp_annual
            needed = max(annual_spending - other_sources, 0)
            rrsp_withdrawal = min(needed * 0.5, current_rrsp)  # Conservative approach
        else:
            # Age 72+: RRIF minimum withdrawal
            rrif_age = age
            if rrif_age >= 95:
                min_rate = 0.20
            elif rrif_age >= 65:
                # Simplified RRIF formula
                min_rate = 1 / (90 - rrif_age) if rrif_age < 90 else 0.20
            else:
                min_rate = 0.05
            rrsp_withdrawal = min(current_rrsp * min_rate, current_rrsp)

        # TFSA withdrawal to cover remaining spending needs
        total_income_before_tfsa = other_income + cpp_annual + rrsp_withdrawal

        # Calculate OAS based on income before TFSA withdrawal
        oas_monthly = calculate_oas_benefit(age, total_income_before_tfsa, years_in_canada, oas_start_age)
        oas_annual = oas_monthly * 12

        # Calculate tax on taxable income (TFSA withdrawals not taxed)
        taxable_income = total_income_before_tfsa + oas_annual
        tax_calc = calculate_total_tax(taxable_income, age, rrsp_withdrawal, province=province)
        total_tax = tax_calc['total_tax']

        # After-tax income including OAS
        after_tax_from_taxable = taxable_income - total_tax

        # Determine if TFSA withdrawal is needed
        spending_adjusted = annual_spending * ((1 + INFLATION_RATE) ** year)
        shortfall = max(spending_adjusted - after_tax_from_taxable, 0)
        tfsa_withdrawal = min(shortfall, current_tfsa)

        total_after_tax = after_tax_from_taxable + tfsa_withdrawal
        net_cash_flow = total_after_tax - spending_adjusted

        # Update balances
        current_rrsp -= rrsp_withdrawal
        current_tfsa -= tfsa_withdrawal

        # Apply investment returns
        current_rrsp = max(current_rrsp * (1 + investment_return), 0)
        current_tfsa = max(current_tfsa * (1 + investment_return), 0)

        # Record projections
        projections['rrsp_balance'].append(current_rrsp)
        projections['tfsa_balance'].append(current_tfsa)
        projections['rrsp_withdrawal'].append(rrsp_withdrawal)
        projections['tfsa_withdrawal'].append(tfsa_withdrawal)
        projections['other_income'].append(other_income)
        projections['cpp_income'].append(cpp_annual)
        projections['oas_income'].append(oas_annual)
        projections['total_income'].append(taxable_income + tfsa_withdrawal)
        projections['total_tax'].append(total_tax)
        projections['after_tax_income'].append(total_after_tax)
        projections['spending'].append(spending_adjusted)
        projections['net_cash_flow'].append(net_cash_flow)

    return projections


def compare_meltdown_vs_traditional(
    current_age: int,
    retirement_age: int,
    rrsp_balance: float,
    tfsa_balance: float,
    annual_income_before_65: float,
    cpp_amount: float,
    years_in_canada: int = 40,
    investment_return: float = 0.06,
    annual_spending: float = 60000,
    oas_start_age: int = 65,
    province: str = DEFAULT_PROVINCE,
) -> dict:
    """
    Compare RRSP meltdown strategy vs traditional approach.

    Traditional approach: Minimal RRSP withdrawals until RRIF minimum required
    Meltdown approach: Strategic withdrawals before OAS to minimize lifetime taxes

    Args:
        oas_start_age: Age at which to start OAS (65-70)

    Returns:
        Dictionary comparing both strategies
    """
    # Simulate meltdown strategy
    meltdown = simulate_meltdown_strategy(
        current_age,
        retirement_age,
        rrsp_balance,
        tfsa_balance,
        annual_income_before_65,
        cpp_amount,
        years_in_canada,
        OAS_CLAWBACK_THRESHOLD,
        investment_return,
        annual_spending,
        oas_start_age,
        province,
    )

    # Simulate traditional strategy (minimal withdrawals)
    traditional = simulate_meltdown_strategy(
        current_age,
        retirement_age,
        rrsp_balance,
        tfsa_balance,
        annual_income_before_65,
        cpp_amount,
        years_in_canada,
        target_income_threshold=200000,  # High threshold = minimal early withdrawals
        investment_return=investment_return,
        annual_spending=annual_spending,
        oas_start_age=oas_start_age,
        province=province,
    )

    # Calculate lifetime totals
    meltdown_lifetime_tax = sum(meltdown['total_tax'])
    traditional_lifetime_tax = sum(traditional['total_tax'])

    meltdown_lifetime_oas = sum(meltdown['oas_income'])
    traditional_lifetime_oas = sum(traditional['oas_income'])

    tax_savings = traditional_lifetime_tax - meltdown_lifetime_tax
    oas_advantage = meltdown_lifetime_oas - traditional_lifetime_oas
    total_advantage = tax_savings + oas_advantage

    return {
        'meltdown_strategy': meltdown,
        'traditional_strategy': traditional,
        'comparison': {
            'meltdown_lifetime_tax': meltdown_lifetime_tax,
            'traditional_lifetime_tax': traditional_lifetime_tax,
            'tax_savings': tax_savings,
            'meltdown_lifetime_oas': meltdown_lifetime_oas,
            'traditional_lifetime_oas': traditional_lifetime_oas,
            'oas_advantage': oas_advantage,
            'total_financial_advantage': total_advantage,
        }
    }
