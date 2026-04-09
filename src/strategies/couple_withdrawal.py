"""
Couple withdrawal strategy optimization.

Determines optimal withdrawal amounts from each spouse's accounts to minimize
household tax and preserve government benefits.
"""

from typing import Dict, Tuple
from src.calculations.taxes import calculate_household_tax
from src.utils.constants import OAS_CLAWBACK_THRESHOLD


def calculate_couple_withdrawal_strategy(
    person1_rrsp_balance: float,
    person1_tfsa_balance: float,
    person1_nonreg_balance: float,
    person2_rrsp_balance: float,
    person2_tfsa_balance: float,
    person2_nonreg_balance: float,
    person1_age: int,
    person2_age: int,
    target_household_spending: float,
    person1_other_income: float,  # CPP, OAS
    person2_other_income: float,  # CPP, OAS
    person1_rrif_minimum: float = 0.0,
    person2_rrif_minimum: float = 0.0,
    strategy: str = 'tax_optimized',
) -> dict:
    """
    Determine optimal withdrawal amounts from each spouse's accounts.

    Args:
        person1_rrsp_balance: Person 1's RRSP balance
        person1_tfsa_balance: Person 1's TFSA balance
        person1_nonreg_balance: Person 1's non-registered balance
        person2_rrsp_balance: Person 2's RRSP balance
        person2_tfsa_balance: Person 2's TFSA balance
        person2_nonreg_balance: Person 2's non-registered balance
        person1_age: Person 1's current age
        person2_age: Person 2's current age
        target_household_spending: Target annual household spending
        person1_other_income: Person 1's other income (CPP, OAS)
        person2_other_income: Person 2's other income (CPP, OAS)
        person1_rrif_minimum: Person 1's RRIF minimum withdrawal (if applicable)
        person2_rrif_minimum: Person 2's RRIF minimum withdrawal (if applicable)
        strategy: Withdrawal strategy to use:
            - 'tax_optimized': Minimize household tax (TFSA first, balance RRSP/NonReg)
            - 'oas_clawback_aware': Keep both spouses below OAS clawback threshold
            - 'balanced': Proportional withdrawals maintaining relative account sizes
            - 'rrsp_meltdown': Prioritize RRSP withdrawals to minimize lifetime taxes

    Returns:
        Dictionary with optimal withdrawal amounts and tax information
    """
    if strategy == 'tax_optimized':
        return _tax_optimized_strategy(
            person1_rrsp_balance, person1_tfsa_balance, person1_nonreg_balance,
            person2_rrsp_balance, person2_tfsa_balance, person2_nonreg_balance,
            person1_age, person2_age,
            target_household_spending,
            person1_other_income, person2_other_income,
            person1_rrif_minimum, person2_rrif_minimum,
        )
    elif strategy == 'oas_clawback_aware':
        return _oas_clawback_aware_strategy(
            person1_rrsp_balance, person1_tfsa_balance, person1_nonreg_balance,
            person2_rrsp_balance, person2_tfsa_balance, person2_nonreg_balance,
            person1_age, person2_age,
            target_household_spending,
            person1_other_income, person2_other_income,
            person1_rrif_minimum, person2_rrif_minimum,
        )
    elif strategy == 'balanced':
        return _balanced_strategy(
            person1_rrsp_balance, person1_tfsa_balance, person1_nonreg_balance,
            person2_rrsp_balance, person2_tfsa_balance, person2_nonreg_balance,
            person1_age, person2_age,
            target_household_spending,
            person1_other_income, person2_other_income,
            person1_rrif_minimum, person2_rrif_minimum,
        )
    elif strategy == 'rrsp_meltdown':
        return _rrsp_meltdown_strategy(
            person1_rrsp_balance, person1_tfsa_balance, person1_nonreg_balance,
            person2_rrsp_balance, person2_tfsa_balance, person2_nonreg_balance,
            person1_age, person2_age,
            target_household_spending,
            person1_other_income, person2_other_income,
            person1_rrif_minimum, person2_rrif_minimum,
        )
    else:
        raise ValueError(f"Unknown withdrawal strategy: {strategy}")


def _tax_optimized_strategy(
    person1_rrsp_balance: float,
    person1_tfsa_balance: float,
    person1_nonreg_balance: float,
    person2_rrsp_balance: float,
    person2_tfsa_balance: float,
    person2_nonreg_balance: float,
    person1_age: int,
    person2_age: int,
    target_household_spending: float,
    person1_other_income: float,
    person2_other_income: float,
    person1_rrif_minimum: float,
    person2_rrif_minimum: float,
) -> dict:
    """
    Tax-optimized withdrawal strategy: minimize household tax.

    Strategy:
    1. Meet RRIF minimums first (mandatory)
    2. Withdraw from TFSA (tax-free)
    3. Balance remaining withdrawals to equalize marginal tax rates
    """
    # Start with RRIF minimums
    person1_rrsp_withdrawal = min(person1_rrif_minimum, person1_rrsp_balance)
    person2_rrsp_withdrawal = min(person2_rrif_minimum, person2_rrsp_balance)

    person1_tfsa_withdrawal = 0.0
    person2_tfsa_withdrawal = 0.0
    person1_nonreg_withdrawal = 0.0
    person2_nonreg_withdrawal = 0.0

    # Calculate how much more we need after RRIF minimums
    needed = target_household_spending - person1_rrsp_withdrawal - person2_rrsp_withdrawal

    if needed > 0:
        # Strategy: Withdraw from TFSA first (tax-free), then optimize
        total_tfsa = person1_tfsa_balance + person2_tfsa_balance

        if total_tfsa > 0:
            # Withdraw proportionally from both TFSAs
            tfsa_withdrawal_amount = min(needed, total_tfsa)
            person1_tfsa_withdrawal = min(
                tfsa_withdrawal_amount * (person1_tfsa_balance / total_tfsa),
                person1_tfsa_balance
            )
            person2_tfsa_withdrawal = min(
                tfsa_withdrawal_amount - person1_tfsa_withdrawal,
                person2_tfsa_balance
            )
            needed -= tfsa_withdrawal_amount

        if needed > 0:
            # Still need more - balance between RRSP and non-reg to minimize tax
            # Try to equalize marginal tax rates between spouses
            person1_income_so_far = person1_other_income + person1_rrsp_withdrawal
            person2_income_so_far = person2_other_income + person2_rrsp_withdrawal

            # Simple heuristic: withdraw more from person with lower current income
            # This tends to equalize marginal rates
            total_rrsp_available = (person1_rrsp_balance - person1_rrsp_withdrawal +
                                   person2_rrsp_balance - person2_rrsp_withdrawal)
            total_nonreg_available = person1_nonreg_balance + person2_nonreg_balance

            if person1_income_so_far <= person2_income_so_far:
                # Person 1 has lower income, prioritize their withdrawals
                if person1_nonreg_balance > 0:
                    person1_nonreg_withdrawal = min(needed, person1_nonreg_balance)
                    needed -= person1_nonreg_withdrawal

                if needed > 0 and person1_rrsp_balance - person1_rrsp_withdrawal > 0:
                    additional_rrsp = min(needed, person1_rrsp_balance - person1_rrsp_withdrawal)
                    person1_rrsp_withdrawal += additional_rrsp
                    needed -= additional_rrsp

                if needed > 0 and person2_nonreg_balance > 0:
                    person2_nonreg_withdrawal = min(needed, person2_nonreg_balance)
                    needed -= person2_nonreg_withdrawal

                if needed > 0 and person2_rrsp_balance - person2_rrsp_withdrawal > 0:
                    additional_rrsp = min(needed, person2_rrsp_balance - person2_rrsp_withdrawal)
                    person2_rrsp_withdrawal += additional_rrsp
                    needed -= additional_rrsp
            else:
                # Person 2 has lower income, prioritize their withdrawals
                if person2_nonreg_balance > 0:
                    person2_nonreg_withdrawal = min(needed, person2_nonreg_balance)
                    needed -= person2_nonreg_withdrawal

                if needed > 0 and person2_rrsp_balance - person2_rrsp_withdrawal > 0:
                    additional_rrsp = min(needed, person2_rrsp_balance - person2_rrsp_withdrawal)
                    person2_rrsp_withdrawal += additional_rrsp
                    needed -= additional_rrsp

                if needed > 0 and person1_nonreg_balance > 0:
                    person1_nonreg_withdrawal = min(needed, person1_nonreg_balance)
                    needed -= person1_nonreg_withdrawal

                if needed > 0 and person1_rrsp_balance - person1_rrsp_withdrawal > 0:
                    additional_rrsp = min(needed, person1_rrsp_balance - person1_rrsp_withdrawal)
                    person1_rrsp_withdrawal += additional_rrsp
                    needed -= additional_rrsp

    # Calculate tax with these withdrawals
    person1_total_income = person1_other_income + person1_rrsp_withdrawal + person1_nonreg_withdrawal * 0.5
    person2_total_income = person2_other_income + person2_rrsp_withdrawal + person2_nonreg_withdrawal * 0.5

    tax_result = calculate_household_tax(
        person1_total_income, person1_age, person1_rrsp_withdrawal,
        person2_total_income, person2_age, person2_rrsp_withdrawal,
        apply_income_splitting=True,
    )

    return {
        'person1_withdrawals': {
            'rrsp': person1_rrsp_withdrawal,
            'tfsa': person1_tfsa_withdrawal,
            'nonreg': person1_nonreg_withdrawal,
            'total': person1_rrsp_withdrawal + person1_tfsa_withdrawal + person1_nonreg_withdrawal,
        },
        'person2_withdrawals': {
            'rrsp': person2_rrsp_withdrawal,
            'tfsa': person2_tfsa_withdrawal,
            'nonreg': person2_nonreg_withdrawal,
            'total': person2_rrsp_withdrawal + person2_tfsa_withdrawal + person2_nonreg_withdrawal,
        },
        'total_household_withdrawal': (person1_rrsp_withdrawal + person1_tfsa_withdrawal + person1_nonreg_withdrawal +
                                       person2_rrsp_withdrawal + person2_tfsa_withdrawal + person2_nonreg_withdrawal),
        'household_tax': tax_result['total_household_tax'],
        'person1_tax': tax_result['person1_tax'],
        'person2_tax': tax_result['person2_tax'],
        'income_splitting_applied': tax_result['income_splitting_applied'],
        'income_splitting_savings': tax_result['income_splitting_savings'],
        'rationale': 'Tax-optimized: Prioritized TFSA, balanced remaining withdrawals to equalize marginal rates',
    }


def _oas_clawback_aware_strategy(
    person1_rrsp_balance: float,
    person1_tfsa_balance: float,
    person1_nonreg_balance: float,
    person2_rrsp_balance: float,
    person2_tfsa_balance: float,
    person2_nonreg_balance: float,
    person1_age: int,
    person2_age: int,
    target_household_spending: float,
    person1_other_income: float,
    person2_other_income: float,
    person1_rrif_minimum: float,
    person2_rrif_minimum: float,
) -> dict:
    """
    OAS clawback-aware strategy: try to keep both spouses below OAS threshold.

    Strategy:
    1. Meet RRIF minimums
    2. Check if either spouse is near OAS clawback threshold
    3. Prioritize TFSA withdrawals
    4. Balance RRSP/Non-Reg to keep both below threshold if possible
    """
    # Start with RRIF minimums
    person1_rrsp_withdrawal = min(person1_rrif_minimum, person1_rrsp_balance)
    person2_rrsp_withdrawal = min(person2_rrif_minimum, person2_rrsp_balance)

    person1_tfsa_withdrawal = 0.0
    person2_tfsa_withdrawal = 0.0
    person1_nonreg_withdrawal = 0.0
    person2_nonreg_withdrawal = 0.0

    needed = target_household_spending - person1_rrsp_withdrawal - person2_rrsp_withdrawal

    # Calculate current income including RRIF minimums
    person1_income = person1_other_income + person1_rrsp_withdrawal
    person2_income = person2_other_income + person2_rrsp_withdrawal

    # Calculate room before OAS clawback for each person
    person1_room = max(0, OAS_CLAWBACK_THRESHOLD - person1_income)
    person2_room = max(0, OAS_CLAWBACK_THRESHOLD - person2_income)

    if needed > 0:
        # Withdraw from TFSA first (doesn't affect OAS)
        total_tfsa = person1_tfsa_balance + person2_tfsa_balance
        if total_tfsa > 0:
            tfsa_withdrawal_amount = min(needed, total_tfsa)
            person1_tfsa_withdrawal = min(
                tfsa_withdrawal_amount * (person1_tfsa_balance / total_tfsa) if total_tfsa > 0 else 0,
                person1_tfsa_balance
            )
            person2_tfsa_withdrawal = min(
                tfsa_withdrawal_amount - person1_tfsa_withdrawal,
                person2_tfsa_balance
            )
            needed -= tfsa_withdrawal_amount

        if needed > 0:
            # Still need more - use person's room before OAS clawback
            # Person with more room should withdraw more
            if person1_room >= person2_room:
                # Person 1 has more room
                person1_additional = min(needed, person1_room)
                if person1_nonreg_balance > 0:
                    person1_nonreg = min(person1_additional * 2, person1_nonreg_balance)  # *2 because only 50% taxable
                    person1_nonreg_withdrawal = person1_nonreg
                    needed -= person1_nonreg / 2  # Only half affects income
                    person1_additional -= person1_nonreg / 2

                if person1_additional > 0 and person1_rrsp_balance - person1_rrsp_withdrawal > 0:
                    person1_rrsp_add = min(person1_additional, person1_rrsp_balance - person1_rrsp_withdrawal)
                    person1_rrsp_withdrawal += person1_rrsp_add
                    needed -= person1_rrsp_add

                # If still need more, use person 2
                if needed > 0:
                    if person2_nonreg_balance > 0:
                        person2_nonreg = min(needed * 2, person2_nonreg_balance)
                        person2_nonreg_withdrawal = person2_nonreg
                        needed -= person2_nonreg / 2

                    if needed > 0 and person2_rrsp_balance - person2_rrsp_withdrawal > 0:
                        person2_rrsp_add = min(needed, person2_rrsp_balance - person2_rrsp_withdrawal)
                        person2_rrsp_withdrawal += person2_rrsp_add
                        needed -= person2_rrsp_add
            else:
                # Person 2 has more room
                person2_additional = min(needed, person2_room)
                if person2_nonreg_balance > 0:
                    person2_nonreg = min(person2_additional * 2, person2_nonreg_balance)
                    person2_nonreg_withdrawal = person2_nonreg
                    needed -= person2_nonreg / 2
                    person2_additional -= person2_nonreg / 2

                if person2_additional > 0 and person2_rrsp_balance - person2_rrsp_withdrawal > 0:
                    person2_rrsp_add = min(person2_additional, person2_rrsp_balance - person2_rrsp_withdrawal)
                    person2_rrsp_withdrawal += person2_rrsp_add
                    needed -= person2_rrsp_add

                # If still need more, use person 1
                if needed > 0:
                    if person1_nonreg_balance > 0:
                        person1_nonreg = min(needed * 2, person1_nonreg_balance)
                        person1_nonreg_withdrawal = person1_nonreg
                        needed -= person1_nonreg / 2

                    if needed > 0 and person1_rrsp_balance - person1_rrsp_withdrawal > 0:
                        person1_rrsp_add = min(needed, person1_rrsp_balance - person1_rrsp_withdrawal)
                        person1_rrsp_withdrawal += person1_rrsp_add
                        needed -= person1_rrsp_add

    # Calculate tax
    person1_total_income = person1_other_income + person1_rrsp_withdrawal + person1_nonreg_withdrawal * 0.5
    person2_total_income = person2_other_income + person2_rrsp_withdrawal + person2_nonreg_withdrawal * 0.5

    tax_result = calculate_household_tax(
        person1_total_income, person1_age, person1_rrsp_withdrawal,
        person2_total_income, person2_age, person2_rrsp_withdrawal,
        apply_income_splitting=True,
    )

    return {
        'person1_withdrawals': {
            'rrsp': person1_rrsp_withdrawal,
            'tfsa': person1_tfsa_withdrawal,
            'nonreg': person1_nonreg_withdrawal,
            'total': person1_rrsp_withdrawal + person1_tfsa_withdrawal + person1_nonreg_withdrawal,
        },
        'person2_withdrawals': {
            'rrsp': person2_rrsp_withdrawal,
            'tfsa': person2_tfsa_withdrawal,
            'nonreg': person2_nonreg_withdrawal,
            'total': person2_rrsp_withdrawal + person2_tfsa_withdrawal + person2_nonreg_withdrawal,
        },
        'total_household_withdrawal': (person1_rrsp_withdrawal + person1_tfsa_withdrawal + person1_nonreg_withdrawal +
                                       person2_rrsp_withdrawal + person2_tfsa_withdrawal + person2_nonreg_withdrawal),
        'household_tax': tax_result['total_household_tax'],
        'person1_tax': tax_result['person1_tax'],
        'person2_tax': tax_result['person2_tax'],
        'income_splitting_applied': tax_result['income_splitting_applied'],
        'income_splitting_savings': tax_result['income_splitting_savings'],
        'person1_income': person1_total_income,
        'person2_income': person2_total_income,
        'person1_below_oas_threshold': person1_total_income < OAS_CLAWBACK_THRESHOLD,
        'person2_below_oas_threshold': person2_total_income < OAS_CLAWBACK_THRESHOLD,
        'rationale': 'OAS-aware: Prioritized keeping both spouses below OAS clawback threshold',
    }


def _balanced_strategy(
    person1_rrsp_balance: float,
    person1_tfsa_balance: float,
    person1_nonreg_balance: float,
    person2_rrsp_balance: float,
    person2_tfsa_balance: float,
    person2_nonreg_balance: float,
    person1_age: int,
    person2_age: int,
    target_household_spending: float,
    person1_other_income: float,
    person2_other_income: float,
    person1_rrif_minimum: float,
    person2_rrif_minimum: float,
) -> dict:
    """
    Balanced strategy: withdraw proportionally from both spouses' accounts.

    This maintains the relative account sizes between spouses.
    """
    person1_total_balance = person1_rrsp_balance + person1_tfsa_balance + person1_nonreg_balance
    person2_total_balance = person2_rrsp_balance + person2_tfsa_balance + person2_nonreg_balance
    household_total = person1_total_balance + person2_total_balance

    if household_total == 0:
        return {
            'person1_withdrawals': {'rrsp': 0, 'tfsa': 0, 'nonreg': 0, 'total': 0},
            'person2_withdrawals': {'rrsp': 0, 'tfsa': 0, 'nonreg': 0, 'total': 0},
            'total_household_withdrawal': 0,
            'household_tax': 0,
            'person1_tax': 0,
            'person2_tax': 0,
            'income_splitting_applied': False,
            'income_splitting_savings': 0,
            'rationale': 'Balanced: No funds available',
        }

    # Calculate proportional withdrawal targets
    person1_target = target_household_spending * (person1_total_balance / household_total)
    person2_target = target_household_spending * (person2_total_balance / household_total)

    # Ensure RRIF minimums are met
    person1_rrsp_withdrawal = max(person1_rrif_minimum, min(person1_target, person1_rrsp_balance))
    person2_rrsp_withdrawal = max(person2_rrif_minimum, min(person2_target, person2_rrsp_balance))

    # Withdraw remaining proportionally from TFSA and Non-Reg
    person1_remaining = max(0, person1_target - person1_rrsp_withdrawal)
    person2_remaining = max(0, person2_target - person2_rrsp_withdrawal)

    person1_tfsa_withdrawal = min(person1_remaining, person1_tfsa_balance)
    person2_tfsa_withdrawal = min(person2_remaining, person2_tfsa_balance)

    person1_remaining -= person1_tfsa_withdrawal
    person2_remaining -= person2_tfsa_withdrawal

    person1_nonreg_withdrawal = min(person1_remaining, person1_nonreg_balance)
    person2_nonreg_withdrawal = min(person2_remaining, person2_nonreg_balance)

    # Calculate tax
    person1_total_income = person1_other_income + person1_rrsp_withdrawal + person1_nonreg_withdrawal * 0.5
    person2_total_income = person2_other_income + person2_rrsp_withdrawal + person2_nonreg_withdrawal * 0.5

    tax_result = calculate_household_tax(
        person1_total_income, person1_age, person1_rrsp_withdrawal,
        person2_total_income, person2_age, person2_rrsp_withdrawal,
        apply_income_splitting=True,
    )

    return {
        'person1_withdrawals': {
            'rrsp': person1_rrsp_withdrawal,
            'tfsa': person1_tfsa_withdrawal,
            'nonreg': person1_nonreg_withdrawal,
            'total': person1_rrsp_withdrawal + person1_tfsa_withdrawal + person1_nonreg_withdrawal,
        },
        'person2_withdrawals': {
            'rrsp': person2_rrsp_withdrawal,
            'tfsa': person2_tfsa_withdrawal,
            'nonreg': person2_nonreg_withdrawal,
            'total': person2_rrsp_withdrawal + person2_tfsa_withdrawal + person2_nonreg_withdrawal,
        },
        'total_household_withdrawal': (person1_rrsp_withdrawal + person1_tfsa_withdrawal + person1_nonreg_withdrawal +
                                       person2_rrsp_withdrawal + person2_tfsa_withdrawal + person2_nonreg_withdrawal),
        'household_tax': tax_result['total_household_tax'],
        'person1_tax': tax_result['person1_tax'],
        'person2_tax': tax_result['person2_tax'],
        'income_splitting_applied': tax_result['income_splitting_applied'],
        'income_splitting_savings': tax_result['income_splitting_savings'],
        'rationale': 'Balanced: Proportional withdrawals from both spouses maintain relative account sizes',
    }


def _rrsp_meltdown_strategy(
    person1_rrsp_balance: float,
    person1_tfsa_balance: float,
    person1_nonreg_balance: float,
    person2_rrsp_balance: float,
    person2_tfsa_balance: float,
    person2_nonreg_balance: float,
    person1_age: int,
    person2_age: int,
    target_household_spending: float,
    person1_other_income: float,
    person2_other_income: float,
    person1_rrif_minimum: float,
    person2_rrif_minimum: float,
) -> dict:
    """
    RRSP meltdown strategy: Prioritize RRSP withdrawals to minimize lifetime taxes.

    Strategy:
    1. Meet RRIF minimums first (mandatory)
    2. Withdraw from RRSP accounts (highest withdrawal priority)
    3. Withdraw from Non-Registered accounts (capital gains tax efficient)
    4. Preserve TFSA for last (tax-free growth and emergency funds)

    Benefits:
    - Reduces RRSP balance before age 72 RRIF conversion
    - Minimizes future mandatory RRIF withdrawals
    - Reduces OAS clawback risk in later years
    - Maximizes after-tax legacy value (TFSA grows tax-free)
    - Depletes highest-taxed accounts first
    """
    # Start with RRIF minimums
    person1_rrsp_withdrawal = min(person1_rrif_minimum, person1_rrsp_balance)
    person2_rrsp_withdrawal = min(person2_rrif_minimum, person2_rrsp_balance)

    person1_tfsa_withdrawal = 0.0
    person2_tfsa_withdrawal = 0.0
    person1_nonreg_withdrawal = 0.0
    person2_nonreg_withdrawal = 0.0

    # Calculate how much more we need after RRIF minimums
    needed = target_household_spending - person1_rrsp_withdrawal - person2_rrsp_withdrawal

    if needed > 0:
        # Step 1: Withdraw additional RRSP (beyond minimums) - PRIORITY
        # Balance between spouses to optimize tax brackets
        person1_income_so_far = person1_other_income + person1_rrsp_withdrawal
        person2_income_so_far = person2_other_income + person2_rrsp_withdrawal

        person1_rrsp_available = person1_rrsp_balance - person1_rrsp_withdrawal
        person2_rrsp_available = person2_rrsp_balance - person2_rrsp_withdrawal
        total_rrsp_available = person1_rrsp_available + person2_rrsp_available

        if total_rrsp_available > 0:
            rrsp_withdrawal_amount = min(needed, total_rrsp_available)

            # Withdraw more from person with lower income to balance marginal rates
            if person1_income_so_far <= person2_income_so_far and person1_rrsp_available > 0:
                # Person 1 has lower income - prioritize their RRSP withdrawal
                person1_rrsp_add = min(rrsp_withdrawal_amount, person1_rrsp_available)
                person1_rrsp_withdrawal += person1_rrsp_add
                needed -= person1_rrsp_add

                # If still need more, withdraw from person 2
                if needed > 0 and person2_rrsp_available > 0:
                    person2_rrsp_add = min(needed, person2_rrsp_available)
                    person2_rrsp_withdrawal += person2_rrsp_add
                    needed -= person2_rrsp_add
            else:
                # Person 2 has lower income or equal - prioritize their RRSP withdrawal
                if person2_rrsp_available > 0:
                    person2_rrsp_add = min(rrsp_withdrawal_amount, person2_rrsp_available)
                    person2_rrsp_withdrawal += person2_rrsp_add
                    needed -= person2_rrsp_add

                # If still need more, withdraw from person 1
                if needed > 0 and person1_rrsp_available > 0:
                    person1_rrsp_add = min(needed, person1_rrsp_available)
                    person1_rrsp_withdrawal += person1_rrsp_add
                    needed -= person1_rrsp_add

        # Step 2: Withdraw from Non-Registered if RRSP depleted (capital gains preferred)
        if needed > 0:
            total_nonreg = person1_nonreg_balance + person2_nonreg_balance
            if total_nonreg > 0:
                # Withdraw proportionally from both non-reg accounts
                nonreg_withdrawal_amount = min(needed, total_nonreg)
                person1_nonreg_withdrawal = min(
                    nonreg_withdrawal_amount * (person1_nonreg_balance / total_nonreg),
                    person1_nonreg_balance
                )
                person2_nonreg_withdrawal = min(
                    nonreg_withdrawal_amount - person1_nonreg_withdrawal,
                    person2_nonreg_balance
                )
                needed -= nonreg_withdrawal_amount

        # Step 3: Preserve TFSA for last resort (tax-free growth maximization)
        if needed > 0:
            total_tfsa = person1_tfsa_balance + person2_tfsa_balance
            if total_tfsa > 0:
                # Withdraw proportionally from both TFSAs
                tfsa_withdrawal_amount = min(needed, total_tfsa)
                person1_tfsa_withdrawal = min(
                    tfsa_withdrawal_amount * (person1_tfsa_balance / total_tfsa),
                    person1_tfsa_balance
                )
                person2_tfsa_withdrawal = min(
                    tfsa_withdrawal_amount - person1_tfsa_withdrawal,
                    person2_tfsa_balance
                )
                needed -= tfsa_withdrawal_amount

    # Calculate tax with these withdrawals
    person1_total_income = person1_other_income + person1_rrsp_withdrawal + person1_nonreg_withdrawal * 0.5
    person2_total_income = person2_other_income + person2_rrsp_withdrawal + person2_nonreg_withdrawal * 0.5

    tax_result = calculate_household_tax(
        person1_total_income, person1_age, person1_rrsp_withdrawal,
        person2_total_income, person2_age, person2_rrsp_withdrawal,
        apply_income_splitting=True,
    )

    return {
        'person1_withdrawals': {
            'rrsp': person1_rrsp_withdrawal,
            'tfsa': person1_tfsa_withdrawal,
            'nonreg': person1_nonreg_withdrawal,
            'total': person1_rrsp_withdrawal + person1_tfsa_withdrawal + person1_nonreg_withdrawal,
        },
        'person2_withdrawals': {
            'rrsp': person2_rrsp_withdrawal,
            'tfsa': person2_tfsa_withdrawal,
            'nonreg': person2_nonreg_withdrawal,
            'total': person2_rrsp_withdrawal + person2_tfsa_withdrawal + person2_nonreg_withdrawal,
        },
        'total_household_withdrawal': (person1_rrsp_withdrawal + person1_tfsa_withdrawal + person1_nonreg_withdrawal +
                                       person2_rrsp_withdrawal + person2_tfsa_withdrawal + person2_nonreg_withdrawal),
        'household_tax': tax_result['total_household_tax'],
        'person1_tax': tax_result['person1_tax'],
        'person2_tax': tax_result['person2_tax'],
        'income_splitting_applied': tax_result['income_splitting_applied'],
        'income_splitting_savings': tax_result['income_splitting_savings'],
        'rationale': 'RRSP Meltdown: Prioritizes RRSP withdrawals to minimize lifetime taxes and maximize tax-free TFSA growth',
    }
