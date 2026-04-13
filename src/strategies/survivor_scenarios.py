"""
Survivor scenario analysis for couple retirement planning.

Models the financial impact when one spouse passes away, including:
- CPP survivor benefits
- Asset transfers and tax implications
- Income and spending changes
- Portfolio sustainability for the survivor
"""

from typing import Dict, Optional, List
from src.calculations.cpp_oas import calculate_survivor_benefits, calculate_oas_benefit
from src.calculations.rrsp_tfsa import RRSPAccount, TFSAAccount, NonRegisteredAccount, RRIF_CONVERSION_AGE
from src.calculations.taxes import calculate_total_tax
from src.utils.constants import EXPECTED_RETURN_MEAN, DEFAULT_PROVINCE


def project_survivor_scenario(
    deceased_person_params: dict,
    survivor_params: dict,
    death_age: int,
    projection_years_after_death: int,
    survivor_annual_spending: float,
    deceased_cpp_monthly: float,
    deceased_oas_monthly: float,
    survivor_cpp_monthly: float,
    survivor_oas_monthly: float,
    investment_return: float = EXPECTED_RETURN_MEAN,
    inflation_rate: float = 0.02,
    province: str = DEFAULT_PROVINCE,
) -> dict:
    """
    Project financial situation for survivor after spouse passes.

    Args:
        deceased_person_params: Dictionary with deceased's financial info
            - rrsp_balance_at_death
            - tfsa_balance_at_death
            - nonreg_balance_at_death
            - age_at_death
            - name (optional)
        survivor_params: Dictionary with survivor's financial info
            - current_age
            - rrsp_balance
            - tfsa_balance
            - nonreg_balance
            - years_in_canada
            - oas_start_age
            - name (optional)
        death_age: Age of deceased at death
        projection_years_after_death: Years to project after death
        survivor_annual_spending: Survivor's annual spending (typically 70% of couple spending)
        deceased_cpp_monthly: CPP benefit deceased was receiving
        deceased_oas_monthly: OAS benefit deceased was receiving
        survivor_cpp_monthly: CPP benefit survivor is receiving
        survivor_oas_monthly: OAS benefit survivor is receiving
        investment_return: Expected annual investment return
        inflation_rate: Annual inflation rate for spending adjustments (default: 2%)

    Returns:
        Dictionary with survivor projections
    """
    # Calculate CPP survivor benefit
    survivor_age_at_death = survivor_params['current_age']
    cpp_survivor_benefit = calculate_survivor_benefits(
        deceased_cpp_monthly,
        survivor_age_at_death,
        survivor_cpp_monthly,
    )

    # Calculate taxes triggered by death (RRSP deemed disposition)
    deceased_rrsp = deceased_person_params.get('rrsp_balance_at_death', 0)
    deceased_tfsa = deceased_person_params.get('tfsa_balance_at_death', 0)
    deceased_nonreg = deceased_person_params.get('nonreg_balance_at_death', 0)

    # RRSP is fully taxable in year of death (deemed disposition)
    # Assuming survivor is beneficiary, can transfer to own RRSP/RRIF tax-deferred
    # For simplicity, we'll assume survivor transfers to own RRSP
    death_year_taxable_income = 0  # If transferred to survivor's RRSP
    death_taxes = 0  # No immediate tax if rolled over

    # If survivor doesn't have RRSP room, it would be taxable
    # For conservative estimate, we'll assume some tax
    if deceased_rrsp > 100000:  # Large RRSP may trigger some tax
        # Assume 50% can be rolled over, rest is taxable
        death_year_taxable_income = deceased_rrsp * 0.5
        death_taxes = calculate_total_tax(
            death_year_taxable_income,
            deceased_person_params.get('age_at_death', death_age),
            death_year_taxable_income,
            province=province,
        )['total_tax']

    # Asset transfers to survivor
    # TFSA: Transfers tax-free to survivor (doesn't use up TFSA room)
    # Non-Registered: 50% capital gains tax on accrued gains (deemed disposition)
    # Assume 30% of non-reg balance is accrued gains
    nonreg_accrued_gains = deceased_nonreg * 0.30
    nonreg_capital_gains_tax = nonreg_accrued_gains * 0.5 * 0.26  # 50% inclusion, ~26% marginal rate

    total_death_taxes = death_taxes + nonreg_capital_gains_tax

    # Survivor's new account balances after inheritance
    survivor_rrsp_balance = survivor_params['rrsp_balance'] + deceased_rrsp * 0.5  # 50% rollover
    survivor_tfsa_balance = survivor_params['tfsa_balance'] + deceased_tfsa
    survivor_nonreg_balance = (
        survivor_params['nonreg_balance'] +
        deceased_nonreg - nonreg_accrued_gains * 0.5  # After capital gains tax
    )

    # Create account objects for survivor
    survivor_rrsp = RRSPAccount(survivor_rrsp_balance)
    survivor_tfsa = TFSAAccount(survivor_tfsa_balance)
    survivor_nonreg = NonRegisteredAccount(survivor_nonreg_balance)

    # Check if RRSP should already be RRIF
    if survivor_age_at_death > RRIF_CONVERSION_AGE:
        survivor_rrsp.convert_to_rrif(survivor_age_at_death)

    # Project survivor's finances
    projections = {
        'year': [],
        'survivor_age': [],
        'survivor_rrsp_balance': [],
        'survivor_tfsa_balance': [],
        'survivor_nonreg_balance': [],
        'survivor_total_balance': [],
        'survivor_cpp_income': [],
        'survivor_oas_income': [],
        'survivor_total_income': [],
        'survivor_rrsp_withdrawal': [],
        'survivor_tfsa_withdrawal': [],
        'survivor_nonreg_withdrawal': [],
        'survivor_total_withdrawal': [],
        'survivor_tax': [],
        'survivor_after_tax_income': [],
        'is_rrif': [],
    }

    # Income lost from deceased spouse (for tracking)
    income_lost_cpp = deceased_cpp_monthly * 12
    income_lost_oas = deceased_oas_monthly * 12

    for year in range(projection_years_after_death):
        survivor_age = survivor_age_at_death + year

        projections['year'].append(year)
        projections['survivor_age'].append(survivor_age)

        # RRSP to RRIF conversion if needed
        if survivor_age > RRIF_CONVERSION_AGE and not survivor_rrsp.is_rrif:
            survivor_rrsp.convert_to_rrif(survivor_age)

        # CPP survivor benefit (already calculated)
        survivor_cpp_income = cpp_survivor_benefit['survivor_cpp_annual']

        # OAS benefit (survivor keeps their own OAS, no survivor OAS benefit)
        # Recalculate based on income for clawback
        survivor_oas_monthly_current = calculate_oas_benefit(
            survivor_age,
            survivor_cpp_income,  # Will be adjusted with withdrawals
            survivor_params.get('years_in_canada', 40),
            survivor_params.get('oas_start_age', 65),
        )
        survivor_oas_income = survivor_oas_monthly_current * 12

        # Total other income before withdrawals
        other_income = survivor_cpp_income + survivor_oas_income

        # Apply inflation to survivor spending (compounds each year after death)
        inflation_adjusted_spending = survivor_annual_spending * ((1 + inflation_rate) ** year)

        # Calculate required withdrawals
        # Simple strategy: TFSA first, then Non-Reg, then RRSP
        remaining_needed = inflation_adjusted_spending

        # TFSA (tax-free)
        tfsa_withdrawal = min(remaining_needed, survivor_tfsa.balance)
        survivor_tfsa.withdraw(tfsa_withdrawal)
        remaining_needed -= tfsa_withdrawal

        # Non-Registered (50% taxable)
        nonreg_withdrawal_info = {'amount': 0, 'capital_gain': 0, 'taxable_gain': 0}
        if remaining_needed > 0:
            nonreg_withdrawal_info = survivor_nonreg.withdraw(min(remaining_needed, survivor_nonreg.balance))
            remaining_needed -= nonreg_withdrawal_info['amount']

        # RRSP/RRIF (100% taxable, must take minimum if RRIF)
        rrif_minimum = survivor_rrsp.get_minimum_withdrawal(survivor_age)
        if remaining_needed > 0:
            rrsp_withdrawal = max(min(remaining_needed, survivor_rrsp.balance), rrif_minimum)
        else:
            rrsp_withdrawal = rrif_minimum

        survivor_rrsp.withdraw(rrsp_withdrawal)

        # Calculate total income for tax purposes
        total_income = (
            other_income +
            rrsp_withdrawal +
            nonreg_withdrawal_info['taxable_gain']  # Only 50% of capital gains
        )

        # Calculate tax
        tax_calc = calculate_total_tax(total_income, survivor_age, rrsp_withdrawal, province=province)
        survivor_tax = tax_calc['total_tax']
        survivor_after_tax = total_income - survivor_tax

        # Apply investment returns
        survivor_rrsp.apply_return(investment_return)
        survivor_tfsa.apply_return(investment_return)
        survivor_nonreg.apply_return(investment_return)

        # Record projections
        projections['survivor_rrsp_balance'].append(survivor_rrsp.balance)
        projections['survivor_tfsa_balance'].append(survivor_tfsa.balance)
        projections['survivor_nonreg_balance'].append(survivor_nonreg.balance)
        projections['survivor_total_balance'].append(
            survivor_rrsp.balance + survivor_tfsa.balance + survivor_nonreg.balance
        )
        projections['survivor_cpp_income'].append(survivor_cpp_income)
        projections['survivor_oas_income'].append(survivor_oas_income)
        projections['survivor_total_income'].append(total_income)
        projections['survivor_rrsp_withdrawal'].append(rrsp_withdrawal)
        projections['survivor_tfsa_withdrawal'].append(tfsa_withdrawal)
        projections['survivor_nonreg_withdrawal'].append(nonreg_withdrawal_info['amount'])
        projections['survivor_total_withdrawal'].append(
            rrsp_withdrawal + tfsa_withdrawal + nonreg_withdrawal_info['amount']
        )
        projections['survivor_tax'].append(survivor_tax)
        projections['survivor_after_tax_income'].append(survivor_after_tax)
        projections['is_rrif'].append(survivor_rrsp.is_rrif)

    # Summary statistics
    final_balance = projections['survivor_total_balance'][-1]
    depletion_age = None
    for i, balance in enumerate(projections['survivor_total_balance']):
        if balance <= 0:
            depletion_age = projections['survivor_age'][i]
            break

    return {
        'projections': projections,
        'death_summary': {
            'deceased_age_at_death': death_age,
            'survivor_age_at_death': survivor_age_at_death,
            'assets_transferred': deceased_rrsp + deceased_tfsa + deceased_nonreg,
            'death_taxes': total_death_taxes,
            'rrsp_transferred': deceased_rrsp * 0.5,
            'tfsa_transferred': deceased_tfsa,
            'nonreg_transferred': deceased_nonreg - nonreg_accrued_gains * 0.5,
        },
        'income_changes': {
            'cpp_before_death': survivor_cpp_monthly * 12,
            'cpp_after_death': survivor_cpp_income,
            'cpp_survivor_benefit_added': cpp_survivor_benefit['additional_cpp_from_survivor_benefit'] * 12,
            'oas_before_death': survivor_oas_monthly * 12,
            'oas_after_death': survivor_oas_income,
            'income_lost_from_deceased': income_lost_cpp + income_lost_oas,
        },
        'portfolio_sustainability': {
            'final_balance_at_age_95': final_balance,
            'depletion_age': depletion_age,
            'portfolio_sustainable': final_balance > 0,
        },
        'survivor_name': survivor_params.get('name', 'Survivor'),
        'deceased_name': deceased_person_params.get('name', 'Deceased'),
    }


def analyze_survivor_scenarios(
    person1_params: dict,
    person2_params: dict,
    couple_projection: dict,
    household_spending: float,
    survivor_spending_ratio: float = 0.70,
    death_ages: List[int] = None,
    province: str = DEFAULT_PROVINCE,
) -> dict:
    """
    Analyze multiple survivor scenarios for sensitivity analysis.

    Args:
        person1_params: Person 1's parameters (dict with age, balances, CPP/OAS)
        person2_params: Person 2's parameters
        couple_projection: Full couple projection results
        household_spending: Couple's annual spending
        survivor_spending_ratio: Survivor spending as % of couple spending
        death_ages: List of ages to test (default: [75, 80, 85, 90])

    Returns:
        Dictionary with scenarios for both spouses dying at different ages
    """
    if death_ages is None:
        death_ages = [75, 80, 85, 90]

    survivor_annual_spending = household_spending * survivor_spending_ratio

    scenarios = {
        'person1_dies_first': [],
        'person2_dies_first': [],
    }

    # Scenario 1: Person 1 dies first, Person 2 survives
    for death_age in death_ages:
        if death_age < person1_params['current_age']:
            continue

        # Find the year index in couple projection
        year_idx = death_age - person1_params['current_age']
        if year_idx >= len(couple_projection['person1_age']):
            continue

        deceased_params = {
            'rrsp_balance_at_death': couple_projection['person1_rrsp_balance'][year_idx],
            'tfsa_balance_at_death': couple_projection['person1_tfsa_balance'][year_idx],
            'nonreg_balance_at_death': couple_projection['person1_nonreg_balance'][year_idx],
            'age_at_death': death_age,
            'name': 'Person 1',
        }

        survivor_params_dict = {
            'current_age': person2_params['current_age'] + year_idx,
            'rrsp_balance': couple_projection['person2_rrsp_balance'][year_idx],
            'tfsa_balance': couple_projection['person2_tfsa_balance'][year_idx],
            'nonreg_balance': couple_projection['person2_nonreg_balance'][year_idx],
            'years_in_canada': person2_params.get('years_in_canada', 40),
            'oas_start_age': person2_params.get('oas_start_age', 65),
            'name': 'Person 2',
        }

        # Get CPP/OAS at time of death
        person1_cpp = couple_projection['person1_cpp_annual'][year_idx] if 'person1_cpp_annual' in couple_projection else 0
        person1_oas = couple_projection['person1_oas_annual'][year_idx] if 'person1_oas_annual' in couple_projection else 0
        person2_cpp = couple_projection['person2_cpp_annual'][year_idx] if 'person2_cpp_annual' in couple_projection else 0
        person2_oas = couple_projection['person2_oas_annual'][year_idx] if 'person2_oas_annual' in couple_projection else 0

        scenario = project_survivor_scenario(
            deceased_params,
            survivor_params_dict,
            death_age,
            95 - (person2_params['current_age'] + year_idx),
            survivor_annual_spending,
            person1_cpp / 12,
            person1_oas / 12,
            person2_cpp / 12,
            person2_oas / 12,
            province=province,
        )

        scenarios['person1_dies_first'].append({
            'death_age': death_age,
            'scenario': scenario,
        })

    # Scenario 2: Person 2 dies first, Person 1 survives
    for death_age in death_ages:
        if death_age < person2_params['current_age']:
            continue

        # Find the year index
        year_idx = death_age - person2_params['current_age']
        if year_idx >= len(couple_projection['person2_age']):
            continue

        deceased_params = {
            'rrsp_balance_at_death': couple_projection['person2_rrsp_balance'][year_idx],
            'tfsa_balance_at_death': couple_projection['person2_tfsa_balance'][year_idx],
            'nonreg_balance_at_death': couple_projection['person2_nonreg_balance'][year_idx],
            'age_at_death': death_age,
            'name': 'Person 2',
        }

        # Person 1's age at person 2's death
        person1_age_at_death = person1_params['current_age'] + year_idx

        survivor_params_dict = {
            'current_age': person1_age_at_death,
            'rrsp_balance': couple_projection['person1_rrsp_balance'][year_idx],
            'tfsa_balance': couple_projection['person1_tfsa_balance'][year_idx],
            'nonreg_balance': couple_projection['person1_nonreg_balance'][year_idx],
            'years_in_canada': person1_params.get('years_in_canada', 40),
            'oas_start_age': person1_params.get('oas_start_age', 65),
            'name': 'Person 1',
        }

        # Get CPP/OAS at time of death
        person1_cpp = couple_projection['person1_cpp_annual'][year_idx] if 'person1_cpp_annual' in couple_projection else 0
        person1_oas = couple_projection['person1_oas_annual'][year_idx] if 'person1_oas_annual' in couple_projection else 0
        person2_cpp = couple_projection['person2_cpp_annual'][year_idx] if 'person2_cpp_annual' in couple_projection else 0
        person2_oas = couple_projection['person2_oas_annual'][year_idx] if 'person2_oas_annual' in couple_projection else 0

        scenario = project_survivor_scenario(
            deceased_params,
            survivor_params_dict,
            death_age,
            95 - person1_age_at_death,
            survivor_annual_spending,
            person2_cpp / 12,
            person2_oas / 12,
            person1_cpp / 12,
            person1_oas / 12,
            province=province,
        )

        scenarios['person2_dies_first'].append({
            'death_age': death_age,
            'scenario': scenario,
        })

    return scenarios


def compare_survivor_impact(
    scenarios: dict,
) -> dict:
    """
    Compare the financial impact of different survivor scenarios.

    Args:
        scenarios: Output from analyze_survivor_scenarios()

    Returns:
        Dictionary with comparison metrics
    """
    comparison = {
        'person1_dies_scenarios': [],
        'person2_dies_scenarios': [],
        'worst_case_scenario': None,
        'best_case_scenario': None,
    }

    # Analyze Person 1 dies scenarios
    for scenario_data in scenarios['person1_dies_first']:
        scenario = scenario_data['scenario']
        comparison['person1_dies_scenarios'].append({
            'death_age': scenario_data['death_age'],
            'final_balance': scenario['portfolio_sustainability']['final_balance_at_age_95'],
            'depletion_age': scenario['portfolio_sustainability']['depletion_age'],
            'sustainable': scenario['portfolio_sustainability']['portfolio_sustainable'],
        })

    # Analyze Person 2 dies scenarios
    for scenario_data in scenarios['person2_dies_first']:
        scenario = scenario_data['scenario']
        comparison['person2_dies_scenarios'].append({
            'death_age': scenario_data['death_age'],
            'final_balance': scenario['portfolio_sustainability']['final_balance_at_age_95'],
            'depletion_age': scenario['portfolio_sustainability']['depletion_age'],
            'sustainable': scenario['portfolio_sustainability']['portfolio_sustainable'],
        })

    # Find worst and best case
    all_scenarios = comparison['person1_dies_scenarios'] + comparison['person2_dies_scenarios']
    if all_scenarios:
        worst_case = min(all_scenarios, key=lambda x: x['final_balance'])
        best_case = max(all_scenarios, key=lambda x: x['final_balance'])

        comparison['worst_case_scenario'] = worst_case
        comparison['best_case_scenario'] = best_case

    return comparison
