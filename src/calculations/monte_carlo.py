"""
Monte Carlo simulation for retirement planning.
"""

import numpy as np
from typing import Callable
from src.utils.constants import (
    EXPECTED_RETURN_MEAN,
    EXPECTED_RETURN_STD_DEV,
    INFLATION_RATE,
)


def generate_return_scenarios(
    num_years: int,
    num_simulations: int,
    mean_return: float = EXPECTED_RETURN_MEAN,
    std_dev: float = EXPECTED_RETURN_STD_DEV,
    random_seed: int = None,
) -> np.ndarray:
    """
    Generate Monte Carlo return scenarios.

    Args:
        num_years: Number of years to simulate
        num_simulations: Number of simulation runs
        mean_return: Expected mean annual return
        std_dev: Standard deviation of returns
        random_seed: Random seed for reproducibility

    Returns:
        Array of shape (num_simulations, num_years) with annual returns
    """
    if random_seed is not None:
        np.random.seed(random_seed)

    # Generate random returns using normal distribution
    returns = np.random.normal(mean_return, std_dev, (num_simulations, num_years))

    return returns


def simulate_portfolio_balance(
    initial_balance: float,
    annual_returns: np.ndarray,
    annual_withdrawals: list,
    annual_contributions: list = None,
) -> np.ndarray:
    """
    Simulate portfolio balance over time given returns and cash flows.

    Args:
        initial_balance: Starting portfolio balance
        annual_returns: Array of annual returns for each year
        annual_withdrawals: List of withdrawal amounts for each year
        annual_contributions: List of contribution amounts for each year

    Returns:
        Array of portfolio balances at the end of each year
    """
    num_years = len(annual_withdrawals)
    balances = np.zeros(num_years)

    if annual_contributions is None:
        annual_contributions = [0] * num_years

    current_balance = initial_balance

    for year in range(num_years):
        # Add contribution at start of year
        current_balance += annual_contributions[year]

        # Subtract withdrawal at start of year
        current_balance -= annual_withdrawals[year]

        # Apply return for the year
        if current_balance > 0:
            current_balance *= (1 + annual_returns[year])
        else:
            current_balance = 0  # Can't go negative

        balances[year] = current_balance

    return balances


def run_monte_carlo_simulation(
    initial_balance: float,
    annual_withdrawals: list,
    num_simulations: int = 1000,
    annual_contributions: list = None,
    mean_return: float = EXPECTED_RETURN_MEAN,
    std_dev: float = EXPECTED_RETURN_STD_DEV,
    random_seed: int = None,
) -> dict:
    """
    Run Monte Carlo simulation for retirement portfolio.

    Args:
        initial_balance: Starting portfolio balance
        annual_withdrawals: List of withdrawal amounts for each year
        num_simulations: Number of Monte Carlo simulations
        annual_contributions: List of contribution amounts
        mean_return: Expected mean return
        std_dev: Standard deviation of returns
        random_seed: Random seed for reproducibility

    Returns:
        Dictionary with simulation results and statistics
    """
    num_years = len(annual_withdrawals)

    # Generate return scenarios
    return_scenarios = generate_return_scenarios(
        num_years,
        num_simulations,
        mean_return,
        std_dev,
        random_seed,
    )

    # Run simulations
    all_balances = np.zeros((num_simulations, num_years))
    success_count = 0

    for sim in range(num_simulations):
        balances = simulate_portfolio_balance(
            initial_balance,
            return_scenarios[sim],
            annual_withdrawals,
            annual_contributions,
        )
        all_balances[sim] = balances

        # Count as success if never runs out of money
        if np.all(balances >= 0):
            success_count += 1

    # Calculate statistics
    success_rate = success_count / num_simulations

    # Percentile analysis for each year
    percentiles = {
        'p10': np.percentile(all_balances, 10, axis=0),
        'p25': np.percentile(all_balances, 25, axis=0),
        'p50': np.percentile(all_balances, 50, axis=0),
        'p75': np.percentile(all_balances, 75, axis=0),
        'p90': np.percentile(all_balances, 90, axis=0),
    }

    # Final year statistics
    final_balances = all_balances[:, -1]
    final_stats = {
        'mean': np.mean(final_balances),
        'median': np.median(final_balances),
        'min': np.min(final_balances),
        'max': np.max(final_balances),
        'std': np.std(final_balances),
    }

    return {
        'success_rate': success_rate,
        'num_simulations': num_simulations,
        'num_years': num_years,
        'all_balances': all_balances,
        'percentiles': percentiles,
        'final_stats': final_stats,
        'mean_balance_by_year': np.mean(all_balances, axis=0),
    }


def calculate_safe_withdrawal_rate(
    initial_balance: float,
    num_years: int,
    target_success_rate: float = 0.95,
    num_simulations: int = 1000,
    mean_return: float = EXPECTED_RETURN_MEAN,
    std_dev: float = EXPECTED_RETURN_STD_DEV,
    inflation_adjustment: bool = True,
) -> dict:
    """
    Calculate safe withdrawal rate using Monte Carlo simulation.

    Args:
        initial_balance: Starting portfolio balance
        num_years: Retirement horizon in years
        target_success_rate: Desired probability of success (e.g., 0.95 for 95%)
        num_simulations: Number of Monte Carlo simulations
        mean_return: Expected mean return
        std_dev: Standard deviation of returns
        inflation_adjustment: Whether to adjust withdrawals for inflation

    Returns:
        Dictionary with safe withdrawal rate and analysis
    """
    # Binary search for the withdrawal rate
    low_rate = 0.00
    high_rate = 0.10
    tolerance = 0.0001

    best_rate = 0
    best_success_rate = 0

    while high_rate - low_rate > tolerance:
        test_rate = (low_rate + high_rate) / 2

        # Generate withdrawal schedule
        first_year_withdrawal = initial_balance * test_rate
        annual_withdrawals = [first_year_withdrawal]

        for year in range(1, num_years):
            if inflation_adjustment:
                annual_withdrawals.append(annual_withdrawals[-1] * (1 + INFLATION_RATE))
            else:
                annual_withdrawals.append(first_year_withdrawal)

        # Run simulation
        results = run_monte_carlo_simulation(
            initial_balance,
            annual_withdrawals,
            num_simulations,
            mean_return=mean_return,
            std_dev=std_dev,
        )

        success_rate = results['success_rate']

        if success_rate >= target_success_rate:
            best_rate = test_rate
            best_success_rate = success_rate
            low_rate = test_rate
        else:
            high_rate = test_rate

    return {
        'safe_withdrawal_rate': best_rate,
        'success_rate': best_success_rate,
        'first_year_withdrawal': initial_balance * best_rate,
        'target_success_rate': target_success_rate,
    }


def compare_strategies(
    initial_balance: float,
    strategies: dict,
    num_simulations: int = 1000,
    mean_return: float = EXPECTED_RETURN_MEAN,
    std_dev: float = EXPECTED_RETURN_STD_DEV,
) -> dict:
    """
    Compare multiple withdrawal strategies using Monte Carlo.

    Args:
        initial_balance: Starting balance
        strategies: Dictionary of strategy_name: withdrawal_list pairs
        num_simulations: Number of simulations
        mean_return: Expected mean return
        std_dev: Standard deviation

    Returns:
        Dictionary comparing strategy results
    """
    results = {}

    for strategy_name, annual_withdrawals in strategies.items():
        sim_results = run_monte_carlo_simulation(
            initial_balance,
            annual_withdrawals,
            num_simulations,
            mean_return=mean_return,
            std_dev=std_dev,
        )

        results[strategy_name] = {
            'success_rate': sim_results['success_rate'],
            'final_balance_median': sim_results['final_stats']['median'],
            'final_balance_mean': sim_results['final_stats']['mean'],
            'percentiles': sim_results['percentiles'],
        }

    return results
