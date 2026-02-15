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
        annual_withdrawal_amount: Target withdrawal amount
        investment_returns: List of annual returns

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

        if age >= retirement_age and annual_withdrawal_amount > 0:
            if withdrawal_strategy == 'tax_efficient':
                # Tax-efficient order: TFSA first (tax-free), then Non-Reg (50% taxable), then RRSP (100% taxable)
                remaining = annual_withdrawal_amount

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
                remaining = annual_withdrawal_amount

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
                    target = min(annual_withdrawal_amount, total)
                    rrsp_withdrawal = min(target * (rrsp.balance / total), rrsp.balance)
                    tfsa_withdrawal = min(target * (tfsa.balance / total), tfsa.balance)
                    nonreg_target = target * (nonreg.balance / total)
                    nonreg_withdrawal_info = nonreg.withdraw(nonreg_target)

            elif withdrawal_strategy == 'fixed':
                # Try RRSP, then TFSA, then Non-Reg
                remaining = annual_withdrawal_amount
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
