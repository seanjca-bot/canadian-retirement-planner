"""
Unit tests for calculation modules.
"""

import pytest
import numpy as np
from src.calculations.cpp_oas import calculate_cpp_benefit, calculate_oas_benefit
from src.calculations.taxes import calculate_total_tax, calculate_marginal_rate
from src.calculations.rrsp_tfsa import RRSPAccount, TFSAAccount


class TestCPPCalculations:
    """Test CPP benefit calculations."""

    def test_cpp_at_standard_age(self):
        """Test CPP at age 65 with maximum contributions."""
        benefit = calculate_cpp_benefit(start_age=65, contribution_years=40, average_earnings_ratio=1.0)
        assert benefit > 0
        assert benefit <= 1364.60  # 2026 maximum

    def test_cpp_early_penalty(self):
        """Test CPP early start penalty (0.6% per month)."""
        benefit_60 = calculate_cpp_benefit(start_age=60, contribution_years=40, average_earnings_ratio=1.0)
        benefit_65 = calculate_cpp_benefit(start_age=65, contribution_years=40, average_earnings_ratio=1.0)

        # At 60, should be ~64% of age 65 amount (36% reduction for 60 months)
        expected_ratio = 1 - (60 * 0.006)  # 0.64
        assert abs(benefit_60 / benefit_65 - expected_ratio) < 0.01

    def test_cpp_late_bonus(self):
        """Test CPP late start bonus (0.7% per month)."""
        benefit_65 = calculate_cpp_benefit(start_age=65, contribution_years=40, average_earnings_ratio=1.0)
        benefit_70 = calculate_cpp_benefit(start_age=70, contribution_years=40, average_earnings_ratio=1.0)

        # At 70, should be ~142% of age 65 amount (42% increase for 60 months)
        expected_ratio = 1 + (60 * 0.007)  # 1.42
        assert abs(benefit_70 / benefit_65 - expected_ratio) < 0.01

    def test_cpp_partial_earnings(self):
        """Test CPP with partial earnings history."""
        benefit_full = calculate_cpp_benefit(start_age=65, contribution_years=40, average_earnings_ratio=1.0)
        benefit_half = calculate_cpp_benefit(start_age=65, contribution_years=40, average_earnings_ratio=0.5)

        # Half earnings should result in roughly half benefits
        assert abs(benefit_half / benefit_full - 0.5) < 0.1

    def test_cpp_invalid_age(self):
        """Test CPP with invalid age raises error."""
        with pytest.raises(ValueError):
            calculate_cpp_benefit(start_age=55)  # Too young

        with pytest.raises(ValueError):
            calculate_cpp_benefit(start_age=75)  # Too old


class TestOASCalculations:
    """Test OAS benefit calculations."""

    def test_oas_no_clawback(self):
        """Test OAS with income below clawback threshold."""
        benefit = calculate_oas_benefit(age=65, annual_income=50000, years_in_canada=40)
        assert benefit > 0
        assert benefit <= 718.33  # 2026 maximum

    def test_oas_partial_clawback(self):
        """Test OAS with partial clawback."""
        benefit_low = calculate_oas_benefit(age=65, annual_income=50000, years_in_canada=40)
        benefit_medium = calculate_oas_benefit(age=65, annual_income=100000, years_in_canada=40)

        # Higher income should result in lower benefit due to clawback
        assert benefit_medium < benefit_low

    def test_oas_full_clawback(self):
        """Test OAS with income above elimination threshold."""
        benefit = calculate_oas_benefit(age=65, annual_income=150000, years_in_canada=40)
        assert benefit == 0  # Fully clawed back

    def test_oas_age_75_increase(self):
        """Test 10% OAS increase at age 75."""
        benefit_65 = calculate_oas_benefit(age=65, annual_income=50000, years_in_canada=40)
        benefit_75 = calculate_oas_benefit(age=75, annual_income=50000, years_in_canada=40)

        # Age 75 should be 10% higher
        assert abs(benefit_75 / benefit_65 - 1.10) < 0.01

    def test_oas_partial_residency(self):
        """Test OAS with partial Canadian residency."""
        benefit_full = calculate_oas_benefit(age=65, annual_income=50000, years_in_canada=40)
        benefit_partial = calculate_oas_benefit(age=65, annual_income=50000, years_in_canada=20)

        # 20 years should result in 50% of full benefit
        assert abs(benefit_partial / benefit_full - 0.5) < 0.01

    def test_oas_under_65(self):
        """Test OAS returns 0 for under age 65."""
        benefit = calculate_oas_benefit(age=60, annual_income=50000, years_in_canada=40)
        assert benefit == 0


class TestTaxCalculations:
    """Test tax calculations."""

    def test_basic_personal_amount(self):
        """Test that basic personal amount results in no tax for low income."""
        result = calculate_total_tax(total_income=15000, age=65)
        assert result['total_tax'] == 0

    def test_age_amount_credit(self):
        """Test age amount credit for seniors."""
        result_senior = calculate_total_tax(total_income=40000, age=65)
        result_younger = calculate_total_tax(total_income=40000, age=55)

        # Senior should pay less tax due to age amount credit
        assert result_senior['total_tax'] < result_younger['total_tax']

    def test_progressive_brackets(self):
        """Test progressive tax brackets."""
        result_50k = calculate_total_tax(total_income=50000, age=65)
        result_100k = calculate_total_tax(total_income=100000, age=65)

        # Tax should more than double due to progressive rates
        assert result_100k['total_tax'] > result_50k['total_tax'] * 2

    def test_effective_rate_calculation(self):
        """Test effective tax rate calculation."""
        result = calculate_total_tax(total_income=100000, age=65)

        expected_rate = (result['total_tax'] / 100000) * 100
        assert abs(result['effective_rate'] - expected_rate) < 0.01

    def test_marginal_rate(self):
        """Test marginal rate calculation."""
        rate = calculate_marginal_rate(income=50000, age=65)
        assert 0 <= rate <= 1
        assert rate > 0.20  # Should be in second bracket or higher


class TestRRSPAccount:
    """Test RRSP account functionality."""

    def test_account_initialization(self):
        """Test RRSP account initialization."""
        account = RRSPAccount(initial_balance=100000)
        assert account.balance == 100000
        assert account.account_type == 'RRSP'
        assert not account.is_rrif

    def test_contribution(self):
        """Test RRSP contribution."""
        account = RRSPAccount(initial_balance=100000)
        account.contribute(10000)
        assert account.balance == 110000

    def test_withdrawal(self):
        """Test RRSP withdrawal."""
        account = RRSPAccount(initial_balance=100000)
        withdrawn = account.withdraw(10000)
        assert withdrawn == 10000
        assert account.balance == 90000

    def test_withdrawal_exceeds_balance(self):
        """Test withdrawal when amount exceeds balance."""
        account = RRSPAccount(initial_balance=100000)
        withdrawn = account.withdraw(150000)
        assert withdrawn == 100000  # Only withdraws available amount
        assert account.balance == 0

    def test_investment_return(self):
        """Test applying investment return."""
        account = RRSPAccount(initial_balance=100000)
        account.apply_return(0.06)  # 6% return
        assert account.balance == 106000

    def test_rrif_conversion(self):
        """Test RRSP to RRIF conversion."""
        account = RRSPAccount(initial_balance=100000)
        account.convert_to_rrif(age=72)
        assert account.is_rrif
        assert account.rrif_conversion_age == 72

    def test_rrif_minimum_withdrawal(self):
        """Test RRIF minimum withdrawal calculation."""
        account = RRSPAccount(initial_balance=100000)
        account.convert_to_rrif(age=72)

        minimum = account.get_minimum_withdrawal(age=72)
        assert minimum > 0
        assert minimum == 100000 * 0.054  # 5.4% at age 72


class TestTFSAAccount:
    """Test TFSA account functionality."""

    def test_tfsa_initialization(self):
        """Test TFSA account initialization."""
        account = TFSAAccount(initial_balance=50000)
        assert account.balance == 50000
        assert account.account_type == 'TFSA'

    def test_tfsa_operations(self):
        """Test basic TFSA operations."""
        account = TFSAAccount(initial_balance=50000)
        account.contribute(10000)
        assert account.balance == 60000

        account.apply_return(0.05)
        assert account.balance == 63000

        withdrawn = account.withdraw(13000)
        assert withdrawn == 13000
        assert account.balance == 50000


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
