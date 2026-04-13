"""
RRSP and TFSA account growth and withdrawal modeling.
"""

import numpy as np
from src.utils.constants import (
    RRIF_CONVERSION_AGE,
    RRIF_MIN_WITHDRAWAL_RATES,
    EXPECTED_RETURN_MEAN,
    INFLATION_RATE,
)


class RegisteredAccount:
    """Base class for registered accounts (RRSP/TFSA)."""

    def __init__(self, initial_balance: float, account_type: str):
        """
        Initialize a registered account.

        Args:
            initial_balance: Starting balance
            account_type: 'RRSP' or 'TFSA'
        """
        self.balance = initial_balance
        self.account_type = account_type
        self.history = []

    def apply_return(self, annual_return: float) -> None:
        """Apply annual investment return."""
        self.balance *= (1 + annual_return)

    def contribute(self, amount: float) -> None:
        """Add a contribution to the account."""
        if amount > 0:
            self.balance += amount

    def withdraw(self, amount: float) -> float:
        """
        Withdraw from the account.

        Args:
            amount: Amount to withdraw

        Returns:
            Actual amount withdrawn (may be less if insufficient balance)
        """
        actual_withdrawal = min(amount, self.balance)
        self.balance -= actual_withdrawal
        return actual_withdrawal

    def record_year(self, age: int, contribution: float, withdrawal: float,
                    annual_return: float) -> None:
        """Record account activity for the year."""
        self.history.append({
            'age': age,
            'starting_balance': self.balance + withdrawal - contribution,
            'contribution': contribution,
            'withdrawal': withdrawal,
            'return': annual_return,
            'ending_balance': self.balance,
        })


class RRSPAccount(RegisteredAccount):
    """RRSP/RRIF account with conversion and minimum withdrawal rules."""

    def __init__(self, initial_balance: float):
        super().__init__(initial_balance, 'RRSP')
        self.is_rrif = False
        self.rrif_conversion_age = None

    def convert_to_rrif(self, age: int) -> None:
        """Convert RRSP to RRIF."""
        self.is_rrif = True
        self.rrif_conversion_age = age

    def get_minimum_withdrawal(self, age: int) -> float:
        """
        Calculate minimum RRIF withdrawal for the year.

        Args:
            age: Current age

        Returns:
            Minimum withdrawal amount (0 if not yet a RRIF)
        """
        if not self.is_rrif:
            return 0.0

        # Use RRIF minimum withdrawal rate table
        if age >= 95:
            rate = RRIF_MIN_WITHDRAWAL_RATES[95]
        elif age in RRIF_MIN_WITHDRAWAL_RATES:
            rate = RRIF_MIN_WITHDRAWAL_RATES[age]
        else:
            # For ages below 65, use 1/(90-age) formula
            rate = 1 / (90 - age) if age < 90 else 0.20

        return self.balance * rate


class TFSAAccount(RegisteredAccount):
    """TFSA account with tax-free growth and withdrawals."""

    def __init__(self, initial_balance: float):
        super().__init__(initial_balance, 'TFSA')


class NonRegisteredAccount(RegisteredAccount):
    """
    Non-registered investment account with capital gains tax treatment.

    Tracks adjusted cost base (ACB) for capital gains calculation.
    Assumes all growth is treated as capital gains (50% inclusion rate).
    """

    def __init__(self, initial_balance: float, initial_acb: float = None):
        super().__init__(initial_balance, 'Non-Registered')
        # Adjusted Cost Base - tracks original investment amount for tax purposes
        self.acb = initial_acb if initial_acb is not None else initial_balance
        self.total_contributions = initial_acb if initial_acb is not None else initial_balance

    def contribute(self, amount: float) -> None:
        """Add contribution and increase ACB."""
        if amount > 0:
            self.balance += amount
            self.acb += amount
            self.total_contributions += amount

    def withdraw(self, amount: float) -> dict:
        """
        Withdraw from account and calculate capital gains tax.

        Returns:
            Dictionary with 'amount', 'capital_gain', and 'taxable_gain'
        """
        if amount <= 0:
            return {'amount': 0, 'capital_gain': 0, 'taxable_gain': 0}

        actual_withdrawal = min(amount, self.balance)

        # Calculate proportion of ACB being withdrawn
        if self.balance > 0:
            acb_proportion = actual_withdrawal / self.balance
            acb_withdrawn = self.acb * acb_proportion
        else:
            acb_withdrawn = 0

        # Capital gain is withdrawal amount minus ACB
        capital_gain = max(actual_withdrawal - acb_withdrawn, 0)
        taxable_gain = capital_gain * 0.5  # 50% inclusion rate

        # Update balance and ACB
        self.balance -= actual_withdrawal
        self.acb -= acb_withdrawn

        return {
            'amount': actual_withdrawal,
            'capital_gain': capital_gain,
            'taxable_gain': taxable_gain,
            'acb_withdrawn': acb_withdrawn
        }

    def get_unrealized_gain(self) -> float:
        """Calculate unrealized capital gain."""
        return max(self.balance - self.acb, 0)

    def get_taxable_unrealized_gain(self) -> float:
        """Calculate taxable portion of unrealized gain."""
        return self.get_unrealized_gain() * 0.5


def project_registered_accounts(
    current_age: int,
    retirement_age: int,
    projection_years: int,
    rrsp_balance: float,
    tfsa_balance: float,
    annual_contribution: float = 0,
    withdrawal_strategy: str = 'minimum',
    annual_withdrawal_amount: float = 0,
    investment_returns: list = None,
) -> dict:
    """
    Project RRSP/TFSA balances over time.

    Args:
        current_age: Current age
        retirement_age: Age at retirement (when contributions stop)
        projection_years: Number of years to project
        rrsp_balance: Initial RRSP balance
        tfsa_balance: Initial TFSA balance
        annual_contribution: Annual contribution before retirement (split 70/30 RRSP/TFSA)
        withdrawal_strategy: 'minimum' (RRIF minimum), 'fixed' (fixed amount), or 'percentage'
        annual_withdrawal_amount: Amount for 'fixed' strategy or percentage for 'percentage'
        investment_returns: List of annual returns (if None, uses expected return)

    Returns:
        Dictionary with yearly projections for both accounts
    """
    rrsp = RRSPAccount(rrsp_balance)
    tfsa = TFSAAccount(tfsa_balance)

    projections = {
        'age': [],
        'rrsp_balance': [],
        'tfsa_balance': [],
        'total_balance': [],
        'rrsp_withdrawal': [],
        'tfsa_withdrawal': [],
        'total_withdrawal': [],
        'is_rrif': [],
    }

    for year in range(projection_years):
        age = current_age + year
        projections['age'].append(age)

        # Determine investment return for this year
        if investment_returns and year < len(investment_returns):
            annual_return = investment_returns[year]
        else:
            annual_return = EXPECTED_RETURN_MEAN

        # Contributions (before retirement)
        if age < retirement_age:
            rrsp_contribution = annual_contribution * 0.7
            tfsa_contribution = annual_contribution * 0.3
            rrsp.contribute(rrsp_contribution)
            tfsa.contribute(tfsa_contribution)
        else:
            rrsp_contribution = 0
            tfsa_contribution = 0

        # RRSP to RRIF conversion at age 71 (end of year you turn 71)
        if age > RRIF_CONVERSION_AGE and not rrsp.is_rrif:
            rrsp.convert_to_rrif(age)

        # Calculate withdrawals (in retirement)
        rrsp_withdrawal = 0
        tfsa_withdrawal = 0

        if age >= retirement_age:
            if withdrawal_strategy == 'minimum':
                # RRIF minimum withdrawal
                rrsp_withdrawal = rrsp.get_minimum_withdrawal(age)
            elif withdrawal_strategy == 'fixed':
                # Fixed dollar amount, try RRSP first, then TFSA
                rrsp_withdrawal = min(annual_withdrawal_amount, rrsp.balance)
                remaining = annual_withdrawal_amount - rrsp_withdrawal
                if remaining > 0:
                    tfsa_withdrawal = min(remaining, tfsa.balance)
            elif withdrawal_strategy == 'percentage':
                # Percentage of total portfolio
                total_balance = rrsp.balance + tfsa.balance
                target_withdrawal = total_balance * annual_withdrawal_amount
                # Withdraw proportionally
                if total_balance > 0:
                    rrsp_portion = rrsp.balance / total_balance
                    rrsp_withdrawal = min(target_withdrawal * rrsp_portion, rrsp.balance)
                    tfsa_withdrawal = min(target_withdrawal * (1 - rrsp_portion), tfsa.balance)

        # Execute withdrawals
        rrsp.withdraw(rrsp_withdrawal)
        tfsa.withdraw(tfsa_withdrawal)

        # Apply investment returns
        rrsp.apply_return(annual_return)
        tfsa.apply_return(annual_return)

        # Record history
        rrsp.record_year(age, rrsp_contribution, rrsp_withdrawal, annual_return)
        tfsa.record_year(age, tfsa_contribution, tfsa_withdrawal, annual_return)

        # Record projections
        projections['rrsp_balance'].append(rrsp.balance)
        projections['tfsa_balance'].append(tfsa.balance)
        projections['total_balance'].append(rrsp.balance + tfsa.balance)
        projections['rrsp_withdrawal'].append(rrsp_withdrawal)
        projections['tfsa_withdrawal'].append(tfsa_withdrawal)
        projections['total_withdrawal'].append(rrsp_withdrawal + tfsa_withdrawal)
        projections['is_rrif'].append(rrsp.is_rrif)

    return projections


def calculate_rrif_minimum_table(starting_age: int = 65, ending_age: int = 95) -> dict:
    """
    Generate RRIF minimum withdrawal rate table.

    Args:
        starting_age: Starting age for table
        ending_age: Ending age for table

    Returns:
        Dictionary of age: rate pairs
    """
    table = {}
    for age in range(starting_age, ending_age + 1):
        if age in RRIF_MIN_WITHDRAWAL_RATES:
            table[age] = RRIF_MIN_WITHDRAWAL_RATES[age]
        elif age < 90:
            table[age] = 1 / (90 - age)
        else:
            table[age] = 0.20  # 20% for 90+

    return table


def project_all_accounts(
    current_age: int,
    retirement_age: int,
    projection_years: int,
    rrsp_balance: float,
    tfsa_balance: float,
    nonreg_balance: float,
    annual_contribution: float = 0,
    withdrawal_strategy: str = 'tax_efficient',
    annual_withdrawal_amount: float = 0,
    investment_returns: list = None,
    inflation_rate: float = INFLATION_RATE,
) -> dict:
    """
    Project RRSP/TFSA/Non-Registered balances with various withdrawal strategies.

    Args:
        current_age: Current age
        retirement_age: Age at retirement
        projection_years: Number of years to project
        rrsp_balance: Initial RRSP balance
        tfsa_balance: Initial TFSA balance
        nonreg_balance: Initial non-registered balance
        annual_contribution: Annual contribution before retirement (split 50/30/20)
        withdrawal_strategy:
            - 'tax_efficient': TFSA → Non-Reg → RRSP (minimize taxes)
            - 'rrsp_first': RRSP → Non-Reg → TFSA (RRSP meltdown, preserve TFSA)
            - 'proportional': Withdraw proportionally from all accounts
            - 'fixed': RRSP → TFSA → Non-Reg
        annual_withdrawal_amount: Target withdrawal amount (first year, then adjusted for inflation)
        investment_returns: List of annual returns (if None, uses EXPECTED_RETURN_MEAN)
        inflation_rate: Annual inflation rate for spending adjustments (default: INFLATION_RATE)

    Returns:
        Dictionary with yearly projections for all accounts
    """
    rrsp = RRSPAccount(rrsp_balance)
    tfsa = TFSAAccount(tfsa_balance)
    nonreg = NonRegisteredAccount(nonreg_balance)

    projections = {
        'age': [],
        'rrsp_balance': [],
        'tfsa_balance': [],
        'nonreg_balance': [],
        'total_balance': [],
        'rrsp_withdrawal': [],
        'tfsa_withdrawal': [],
        'nonreg_withdrawal': [],
        'nonreg_capital_gain': [],
        'nonreg_taxable_gain': [],
        'total_withdrawal': [],
        'is_rrif': [],
    }

    for year in range(projection_years):
        age = current_age + year
        projections['age'].append(age)

        # Investment return
        if investment_returns and year < len(investment_returns):
            annual_return = investment_returns[year]
        else:
            annual_return = EXPECTED_RETURN_MEAN

        # Contributions (before retirement)
        if age < retirement_age:
            rrsp_contribution = annual_contribution * 0.5
            tfsa_contribution = annual_contribution * 0.3
            nonreg_contribution = annual_contribution * 0.2
            rrsp.contribute(rrsp_contribution)
            tfsa.contribute(tfsa_contribution)
            nonreg.contribute(nonreg_contribution)
        else:
            rrsp_contribution = 0
            tfsa_contribution = 0
            nonreg_contribution = 0

        # RRSP to RRIF conversion
        if age > RRIF_CONVERSION_AGE and not rrsp.is_rrif:
            rrsp.convert_to_rrif(age)

        # Withdrawals (in retirement)
        rrsp_withdrawal = 0
        tfsa_withdrawal = 0
        nonreg_withdrawal_info = {'amount': 0, 'capital_gain': 0, 'taxable_gain': 0}

        # Apply inflation to withdrawal amount (compounds each year after retirement)
        years_in_retirement = max(0, age - retirement_age)
        inflation_adjusted_withdrawal = annual_withdrawal_amount * ((1 + inflation_rate) ** years_in_retirement)

        if age >= retirement_age and inflation_adjusted_withdrawal > 0:
            if withdrawal_strategy == 'tax_efficient':
                # Tax-efficient order: TFSA first (tax-free), then Non-Reg (50% taxable), then RRSP (100% taxable)
                remaining = inflation_adjusted_withdrawal

                # 1. TFSA (tax-free)
                tfsa_withdrawal = min(remaining, tfsa.balance)
                remaining -= tfsa_withdrawal

                # 2. Non-registered (capital gains - 50% taxable)
                if remaining > 0:
                    nonreg_withdrawal_info = nonreg.withdraw(min(remaining, nonreg.balance))
                    remaining -= nonreg_withdrawal_info['amount']

                # 3. RRSP (100% taxable), respecting RRIF minimum
                if remaining > 0:
                    rrif_min = rrsp.get_minimum_withdrawal(age)
                    rrsp_withdrawal = max(min(remaining, rrsp.balance), rrif_min)
                else:
                    # Still need to take RRIF minimum if applicable
                    rrsp_withdrawal = rrsp.get_minimum_withdrawal(age)

            elif withdrawal_strategy == 'rrsp_first':
                # RRSP meltdown strategy: RRSP first, then Non-Reg, then TFSA (keep TFSA for emergency)
                remaining = inflation_adjusted_withdrawal

                # 1. RRSP first (deplete before TFSA, manage OAS clawback)
                rrif_min = rrsp.get_minimum_withdrawal(age)
                rrsp_withdrawal = max(min(remaining, rrsp.balance), rrif_min)
                remaining -= rrsp_withdrawal

                # 2. Non-registered (capital gains - 50% taxable)
                if remaining > 0:
                    nonreg_withdrawal_info = nonreg.withdraw(min(remaining, nonreg.balance))
                    remaining -= nonreg_withdrawal_info['amount']

                # 3. TFSA last (preserve as emergency fund)
                if remaining > 0:
                    tfsa_withdrawal = min(remaining, tfsa.balance)

            elif withdrawal_strategy == 'proportional':
                # Withdraw proportionally from all accounts
                total = rrsp.balance + tfsa.balance + nonreg.balance
                if total > 0:
                    target = min(inflation_adjusted_withdrawal, total)
                    rrsp_withdrawal = min(target * (rrsp.balance / total), rrsp.balance)
                    tfsa_withdrawal = min(target * (tfsa.balance / total), tfsa.balance)
                    nonreg_target = target * (nonreg.balance / total)
                    nonreg_withdrawal_info = nonreg.withdraw(nonreg_target)

            elif withdrawal_strategy == 'fixed':
                # Try RRSP, then TFSA, then Non-Reg
                remaining = inflation_adjusted_withdrawal
                rrsp_withdrawal = min(remaining, rrsp.balance)
                remaining -= rrsp_withdrawal
                if remaining > 0:
                    tfsa_withdrawal = min(remaining, tfsa.balance)
                    remaining -= tfsa_withdrawal
                if remaining > 0:
                    nonreg_withdrawal_info = nonreg.withdraw(remaining)

        # Execute withdrawals
        rrsp.withdraw(rrsp_withdrawal)
        tfsa.withdraw(tfsa_withdrawal)

        # Apply investment returns
        rrsp.apply_return(annual_return)
        tfsa.apply_return(annual_return)
        nonreg.apply_return(annual_return)

        # Record projections
        projections['rrsp_balance'].append(rrsp.balance)
        projections['tfsa_balance'].append(tfsa.balance)
        projections['nonreg_balance'].append(nonreg.balance)
        projections['total_balance'].append(rrsp.balance + tfsa.balance + nonreg.balance)
        projections['rrsp_withdrawal'].append(rrsp_withdrawal)
        projections['tfsa_withdrawal'].append(tfsa_withdrawal)
        projections['nonreg_withdrawal'].append(nonreg_withdrawal_info['amount'])
        projections['nonreg_capital_gain'].append(nonreg_withdrawal_info['capital_gain'])
        projections['nonreg_taxable_gain'].append(nonreg_withdrawal_info['taxable_gain'])
        projections['total_withdrawal'].append(
            rrsp_withdrawal + tfsa_withdrawal + nonreg_withdrawal_info['amount']
        )
        projections['is_rrif'].append(rrsp.is_rrif)

    return projections


def project_couple_accounts(
    person1_current_age: int,
    person2_current_age: int,
    person1_retirement_age: int,
    person2_retirement_age: int,
    projection_years: int,
    person1_rrsp_balance: float,
    person1_tfsa_balance: float,
    person1_nonreg_balance: float,
    person2_rrsp_balance: float,
    person2_tfsa_balance: float,
    person2_nonreg_balance: float,
    person1_annual_savings: float = 0,
    person2_annual_savings: float = 0,
    household_annual_spending: float = 0,
    person1_cpp_oas_func=None,
    person2_cpp_oas_func=None,
    withdrawal_strategy: str = 'tax_optimized',
    investment_returns: list = None,
    inflation_rate: float = INFLATION_RATE,
    province: str = 'Ontario',
) -> dict:
    """
    Project couple's accounts over time with household optimization.

    Args:
        person1_current_age: Person 1's current age
        person2_current_age: Person 2's current age
        person1_retirement_age: Person 1's retirement age
        person2_retirement_age: Person 2's retirement age
        projection_years: Number of years to project
        person1_rrsp_balance: Person 1's initial RRSP balance
        person1_tfsa_balance: Person 1's initial TFSA balance
        person1_nonreg_balance: Person 1's initial non-registered balance
        person2_rrsp_balance: Person 2's initial RRSP balance
        person2_tfsa_balance: Person 2's initial TFSA balance
        person2_nonreg_balance: Person 2's initial non-registered balance
        person1_annual_savings: Person 1's annual contributions (before retirement)
        person2_annual_savings: Person 2's annual contributions (before retirement)
        household_annual_spending: Target annual household spending (first year, then adjusted for inflation)
        person1_cpp_oas_func: Function(year) -> (cpp_annual, oas_annual) for person 1
        person2_cpp_oas_func: Function(year) -> (cpp_annual, oas_annual) for person 2
        withdrawal_strategy: Coordinated household strategy applied to both spouses:
            - 'tax_optimized': Minimize household tax
            - 'oas_clawback_aware': Keep both below OAS clawback threshold
            - 'balanced': Proportional withdrawals from both
            - 'rrsp_meltdown': Prioritize RRSP withdrawals to minimize lifetime taxes
        investment_returns: List of annual returns (if None, uses EXPECTED_RETURN_MEAN)
        inflation_rate: Annual inflation rate for spending adjustments (default: INFLATION_RATE)

    Returns:
        Dictionary with yearly projections for both spouses
    """
    from src.strategies.couple_withdrawal import calculate_couple_withdrawal_strategy

    # Create account objects for each person
    person1_rrsp = RRSPAccount(person1_rrsp_balance)
    person1_tfsa = TFSAAccount(person1_tfsa_balance)
    person1_nonreg = NonRegisteredAccount(person1_nonreg_balance)

    person2_rrsp = RRSPAccount(person2_rrsp_balance)
    person2_tfsa = TFSAAccount(person2_tfsa_balance)
    person2_nonreg = NonRegisteredAccount(person2_nonreg_balance)

    projections = {
        'year': [],
        'person1_age': [],
        'person2_age': [],
        # Person 1 balances
        'person1_rrsp_balance': [],
        'person1_tfsa_balance': [],
        'person1_nonreg_balance': [],
        'person1_total_balance': [],
        # Person 2 balances
        'person2_rrsp_balance': [],
        'person2_tfsa_balance': [],
        'person2_nonreg_balance': [],
        'person2_total_balance': [],
        # Household
        'household_total_balance': [],
        # Person 1 withdrawals
        'person1_rrsp_withdrawal': [],
        'person1_tfsa_withdrawal': [],
        'person1_nonreg_withdrawal': [],
        'person1_total_withdrawal': [],
        # Person 2 withdrawals
        'person2_rrsp_withdrawal': [],
        'person2_tfsa_withdrawal': [],
        'person2_nonreg_withdrawal': [],
        'person2_total_withdrawal': [],
        # Household withdrawals and tax
        'household_total_withdrawal': [],
        'household_tax': [],
        'income_splitting_savings': [],
        'person1_is_rrif': [],
        'person2_is_rrif': [],
        # CPP/OAS tracking (for survivor scenarios)
        'person1_cpp_annual': [],
        'person1_oas_annual': [],
        'person2_cpp_annual': [],
        'person2_oas_annual': [],
    }

    for year in range(projection_years):
        person1_age = person1_current_age + year
        person2_age = person2_current_age + year

        projections['year'].append(year)
        projections['person1_age'].append(person1_age)
        projections['person2_age'].append(person2_age)

        # Investment return
        if investment_returns and year < len(investment_returns):
            annual_return = investment_returns[year]
        else:
            annual_return = EXPECTED_RETURN_MEAN

        # Contributions (before retirement)
        if person1_age < person1_retirement_age:
            # Split person 1's savings: 50% RRSP, 30% TFSA, 20% Non-Reg
            person1_rrsp.contribute(person1_annual_savings * 0.5)
            person1_tfsa.contribute(person1_annual_savings * 0.3)
            person1_nonreg.contribute(person1_annual_savings * 0.2)

        if person2_age < person2_retirement_age:
            # Split person 2's savings: 50% RRSP, 30% TFSA, 20% Non-Reg
            person2_rrsp.contribute(person2_annual_savings * 0.5)
            person2_tfsa.contribute(person2_annual_savings * 0.3)
            person2_nonreg.contribute(person2_annual_savings * 0.2)

        # RRSP to RRIF conversion
        if person1_age > RRIF_CONVERSION_AGE and not person1_rrsp.is_rrif:
            person1_rrsp.convert_to_rrif(person1_age)

        if person2_age > RRIF_CONVERSION_AGE and not person2_rrsp.is_rrif:
            person2_rrsp.convert_to_rrif(person2_age)

        # Calculate CPP/OAS income for both
        if person1_cpp_oas_func:
            person1_cpp, person1_oas = person1_cpp_oas_func(year)
        else:
            person1_cpp, person1_oas = 0, 0

        if person2_cpp_oas_func:
            person2_cpp, person2_oas = person2_cpp_oas_func(year)
        else:
            person2_cpp, person2_oas = 0, 0

        person1_other_income = person1_cpp + person1_oas
        person2_other_income = person2_cpp + person2_oas

        # Withdrawals (if either person is retired and household needs spending)
        person1_retired = person1_age >= person1_retirement_age
        person2_retired = person2_age >= person2_retirement_age

        if (person1_retired or person2_retired) and household_annual_spending > 0:
            # Apply inflation to household spending (compounds each year after first person retires)
            first_retirement_age = min(person1_retirement_age, person2_retirement_age)
            years_since_first_retirement = max(0, year - (first_retirement_age - min(person1_current_age, person2_current_age)))
            inflation_adjusted_spending = household_annual_spending * ((1 + inflation_rate) ** years_since_first_retirement)

            # Calculate RRIF minimums
            person1_rrif_min = person1_rrsp.get_minimum_withdrawal(person1_age)
            person2_rrif_min = person2_rrsp.get_minimum_withdrawal(person2_age)

            # Use couple withdrawal strategy
            withdrawal_result = calculate_couple_withdrawal_strategy(
                person1_rrsp.balance,
                person1_tfsa.balance,
                person1_nonreg.balance,
                person2_rrsp.balance,
                person2_tfsa.balance,
                person2_nonreg.balance,
                person1_age,
                person2_age,
                inflation_adjusted_spending,
                person1_other_income,
                person2_other_income,
                person1_rrif_min,
                person2_rrif_min,
                withdrawal_strategy,
                province,
            )

            # Extract withdrawal amounts
            person1_rrsp_withdrawal = withdrawal_result['person1_withdrawals']['rrsp']
            person1_tfsa_withdrawal = withdrawal_result['person1_withdrawals']['tfsa']
            person1_nonreg_withdrawal = withdrawal_result['person1_withdrawals']['nonreg']

            person2_rrsp_withdrawal = withdrawal_result['person2_withdrawals']['rrsp']
            person2_tfsa_withdrawal = withdrawal_result['person2_withdrawals']['tfsa']
            person2_nonreg_withdrawal = withdrawal_result['person2_withdrawals']['nonreg']

            household_tax = withdrawal_result['household_tax']
            income_splitting_savings = withdrawal_result.get('income_splitting_savings', 0)
        else:
            # No withdrawals
            person1_rrsp_withdrawal = 0
            person1_tfsa_withdrawal = 0
            person1_nonreg_withdrawal = 0
            person2_rrsp_withdrawal = 0
            person2_tfsa_withdrawal = 0
            person2_nonreg_withdrawal = 0
            household_tax = 0
            income_splitting_savings = 0

        # Execute withdrawals
        person1_rrsp.withdraw(person1_rrsp_withdrawal)
        person1_tfsa.withdraw(person1_tfsa_withdrawal)
        person1_nonreg_withdrawal_info = person1_nonreg.withdraw(person1_nonreg_withdrawal)

        person2_rrsp.withdraw(person2_rrsp_withdrawal)
        person2_tfsa.withdraw(person2_tfsa_withdrawal)
        person2_nonreg_withdrawal_info = person2_nonreg.withdraw(person2_nonreg_withdrawal)

        # Apply investment returns
        person1_rrsp.apply_return(annual_return)
        person1_tfsa.apply_return(annual_return)
        person1_nonreg.apply_return(annual_return)

        person2_rrsp.apply_return(annual_return)
        person2_tfsa.apply_return(annual_return)
        person2_nonreg.apply_return(annual_return)

        # Record projections
        # Person 1 balances
        projections['person1_rrsp_balance'].append(person1_rrsp.balance)
        projections['person1_tfsa_balance'].append(person1_tfsa.balance)
        projections['person1_nonreg_balance'].append(person1_nonreg.balance)
        person1_total = person1_rrsp.balance + person1_tfsa.balance + person1_nonreg.balance
        projections['person1_total_balance'].append(person1_total)

        # Person 2 balances
        projections['person2_rrsp_balance'].append(person2_rrsp.balance)
        projections['person2_tfsa_balance'].append(person2_tfsa.balance)
        projections['person2_nonreg_balance'].append(person2_nonreg.balance)
        person2_total = person2_rrsp.balance + person2_tfsa.balance + person2_nonreg.balance
        projections['person2_total_balance'].append(person2_total)

        # Household
        projections['household_total_balance'].append(person1_total + person2_total)

        # Person 1 withdrawals
        projections['person1_rrsp_withdrawal'].append(person1_rrsp_withdrawal)
        projections['person1_tfsa_withdrawal'].append(person1_tfsa_withdrawal)
        projections['person1_nonreg_withdrawal'].append(person1_nonreg_withdrawal_info['amount'])
        projections['person1_total_withdrawal'].append(
            person1_rrsp_withdrawal + person1_tfsa_withdrawal + person1_nonreg_withdrawal_info['amount']
        )

        # Person 2 withdrawals
        projections['person2_rrsp_withdrawal'].append(person2_rrsp_withdrawal)
        projections['person2_tfsa_withdrawal'].append(person2_tfsa_withdrawal)
        projections['person2_nonreg_withdrawal'].append(person2_nonreg_withdrawal_info['amount'])
        projections['person2_total_withdrawal'].append(
            person2_rrsp_withdrawal + person2_tfsa_withdrawal + person2_nonreg_withdrawal_info['amount']
        )

        # Household
        projections['household_total_withdrawal'].append(
            projections['person1_total_withdrawal'][-1] + projections['person2_total_withdrawal'][-1]
        )
        projections['household_tax'].append(household_tax)
        projections['income_splitting_savings'].append(income_splitting_savings)

        # RRIF status
        projections['person1_is_rrif'].append(person1_rrsp.is_rrif)
        projections['person2_is_rrif'].append(person2_rrsp.is_rrif)

        # CPP/OAS tracking
        projections['person1_cpp_annual'].append(person1_cpp)
        projections['person1_oas_annual'].append(person1_oas)
        projections['person2_cpp_annual'].append(person2_cpp)
        projections['person2_oas_annual'].append(person2_oas)

    return projections
