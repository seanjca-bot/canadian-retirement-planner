"""
Unit tests for couple-specific calculations (household tax, income splitting).
"""

import pytest
from src.calculations.taxes import (
    calculate_pension_income_splitting,
    calculate_household_tax,
    calculate_total_tax,
)


class TestPensionIncomeSplitting:
    """Test income splitting optimization."""

    def test_income_splitting_reduces_tax_high_low_earner(self):
        """Test that splitting reduces tax when one spouse has high income, other low."""
        # Person 1: High pension income, Person 2: Low pension income
        result = calculate_pension_income_splitting(
            person1_pension_income=80000,  # High
            person2_pension_income=20000,  # Low
            person1_other_income=10000,
            person2_other_income=10000,
            person1_age=65,
            person2_age=65,
        )

        # Splitting should be applied
        assert result['eligible_for_splitting'] is True
        assert result['tax_savings'] > 0  # Should save tax
        assert result['optimal_split_ratio'] > 0  # Some splitting should occur

        # Total household tax should be less than baseline
        person1_baseline = calculate_total_tax(90000, 65, 80000)['total_tax']
        person2_baseline = calculate_total_tax(30000, 65, 20000)['total_tax']
        baseline_total = person1_baseline + person2_baseline

        assert result['total_household_tax'] < baseline_total

    def test_income_splitting_equal_incomes(self):
        """Test that splitting has minimal effect when incomes are equal."""
        # Equal pension incomes
        result = calculate_pension_income_splitting(
            person1_pension_income=50000,
            person2_pension_income=50000,
            person1_other_income=10000,
            person2_other_income=10000,
            person1_age=65,
            person2_age=65,
        )

        # Splitting eligible but minimal benefit
        assert result['eligible_for_splitting'] is True
        # Tax savings should be minimal (within rounding)
        assert result['tax_savings'] < 100

    def test_income_splitting_not_eligible_under_65(self):
        """Test that splitting is not applied when either spouse under 65."""
        # Person 1 is 64, Person 2 is 65
        result = calculate_pension_income_splitting(
            person1_pension_income=80000,
            person2_pension_income=20000,
            person1_other_income=10000,
            person2_other_income=10000,
            person1_age=64,  # Under 65
            person2_age=65,
        )

        # Not eligible
        assert result['eligible_for_splitting'] is False
        assert result['tax_savings'] == 0
        assert result['optimal_split_ratio'] == 0

    def test_income_splitting_both_under_65(self):
        """Test no splitting when both under 65."""
        result = calculate_pension_income_splitting(
            person1_pension_income=80000,
            person2_pension_income=20000,
            person1_other_income=10000,
            person2_other_income=10000,
            person1_age=62,
            person2_age=63,
        )

        assert result['eligible_for_splitting'] is False
        assert result['tax_savings'] == 0

    def test_income_splitting_optimal_ratio_range(self):
        """Test that optimal split ratio is within valid range (0-0.5)."""
        result = calculate_pension_income_splitting(
            person1_pension_income=100000,
            person2_pension_income=10000,
            person1_other_income=5000,
            person2_other_income=5000,
            person1_age=65,
            person2_age=65,
        )

        # Split ratio should be between 0 and 0.5 (50%)
        assert 0 <= result['optimal_split_ratio'] <= 0.5

    def test_income_splitting_no_pension_income(self):
        """Test splitting when one spouse has no pension income."""
        result = calculate_pension_income_splitting(
            person1_pension_income=60000,
            person2_pension_income=0,  # No pension
            person1_other_income=15000,
            person2_other_income=15000,
            person1_age=65,
            person2_age=65,
        )

        # Should still optimize
        assert result['eligible_for_splitting'] is True
        # Some splitting should occur (Person 1 shares with Person 2)
        assert result['optimal_split_ratio'] > 0


class TestHouseholdTax:
    """Test household tax calculations."""

    def test_household_tax_with_splitting_enabled(self):
        """Test household tax with income splitting enabled."""
        result = calculate_household_tax(
            person1_income=90000,
            person1_age=65,
            person1_rrsp_withdrawal=80000,
            person2_income=30000,
            person2_age=65,
            person2_rrsp_withdrawal=20000,
            apply_income_splitting=True,
        )

        # Splitting should be applied
        assert result['income_splitting_applied'] is True
        assert result['income_splitting_savings'] > 0

        # Total household tax should be sum of both
        assert result['total_household_tax'] == result['person1_tax'] + result['person2_tax']

    def test_household_tax_with_splitting_disabled(self):
        """Test household tax with income splitting disabled."""
        result = calculate_household_tax(
            person1_income=90000,
            person1_age=65,
            person1_rrsp_withdrawal=80000,
            person2_income=30000,
            person2_age=65,
            person2_rrsp_withdrawal=20000,
            apply_income_splitting=False,
        )

        # Splitting should not be applied
        assert result['income_splitting_applied'] is False
        assert result['income_splitting_savings'] == 0

        # Should match individual calculations
        person1_calc = calculate_total_tax(90000, 65, 80000)
        person2_calc = calculate_total_tax(30000, 65, 20000)

        assert abs(result['person1_tax'] - person1_calc['total_tax']) < 1
        assert abs(result['person2_tax'] - person2_calc['total_tax']) < 1

    def test_household_tax_under_65_no_splitting(self):
        """Test that splitting not applied when under 65."""
        result = calculate_household_tax(
            person1_income=90000,
            person1_age=64,  # Under 65
            person1_rrsp_withdrawal=80000,
            person2_income=30000,
            person2_age=65,
            person2_rrsp_withdrawal=20000,
            apply_income_splitting=True,
        )

        # Should not split due to age
        assert result['income_splitting_applied'] is False
        assert result['income_splitting_savings'] == 0

    def test_household_tax_no_rrsp_withdrawal(self):
        """Test household tax when no RRSP withdrawals."""
        result = calculate_household_tax(
            person1_income=50000,
            person1_age=65,
            person1_rrsp_withdrawal=0,  # No RRSP
            person2_income=40000,
            person2_age=65,
            person2_rrsp_withdrawal=0,  # No RRSP
            apply_income_splitting=True,
        )

        # No RRSP means no pension income splitting
        assert result['income_splitting_applied'] is False
        assert result['income_splitting_savings'] == 0

    def test_household_tax_person_details_included(self):
        """Test that individual tax details are included."""
        result = calculate_household_tax(
            person1_income=70000,
            person1_age=65,
            person1_rrsp_withdrawal=50000,
            person2_income=50000,
            person2_age=65,
            person2_rrsp_withdrawal=30000,
            apply_income_splitting=True,
        )

        # Should include detailed breakdowns
        assert 'person1_details' in result
        assert 'person2_details' in result
        assert 'federal_tax' in result['person1_details']
        assert 'ontario_tax' in result['person1_details']


class TestIncomeSplittingEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_high_income_disparity(self):
        """Test splitting with very high income disparity."""
        result = calculate_pension_income_splitting(
            person1_pension_income=150000,  # Very high
            person2_pension_income=5000,    # Very low
            person1_other_income=0,
            person2_other_income=0,
            person1_age=65,
            person2_age=65,
        )

        # Should split significantly
        assert result['eligible_for_splitting'] is True
        assert result['tax_savings'] > 10000  # Substantial savings
        assert result['optimal_split_ratio'] > 0.3  # Significant split

    def test_zero_pension_income_both_spouses(self):
        """Test when both spouses have zero pension income."""
        result = calculate_pension_income_splitting(
            person1_pension_income=0,
            person2_pension_income=0,
            person1_other_income=50000,
            person2_other_income=50000,
            person1_age=65,
            person2_age=65,
        )

        # No pension to split
        assert result['eligible_for_splitting'] is True  # Age eligible
        assert result['tax_savings'] == 0  # But no savings (no pension)

    def test_age_exactly_65(self):
        """Test boundary condition when both are exactly 65."""
        result = calculate_pension_income_splitting(
            person1_pension_income=60000,
            person2_pension_income=40000,
            person1_other_income=10000,
            person2_other_income=10000,
            person1_age=65,  # Exactly 65
            person2_age=65,  # Exactly 65
        )

        # Should be eligible at exactly 65
        assert result['eligible_for_splitting'] is True


class TestHouseholdTaxIntegration:
    """Integration tests for household tax calculations."""

    def test_household_tax_consistency(self):
        """Test that household tax is consistent with individual calculations when no splitting."""
        person1_income = 70000
        person2_income = 50000
        person1_age = 64  # Under 65, no splitting
        person2_age = 63

        household_result = calculate_household_tax(
            person1_income, person1_age, 50000,
            person2_income, person2_age, 30000,
            apply_income_splitting=True,
        )

        # Calculate individually
        person1_individual = calculate_total_tax(person1_income, person1_age, 50000)
        person2_individual = calculate_total_tax(person2_income, person2_age, 30000)

        # Should match (no splitting due to age)
        assert abs(household_result['person1_tax'] - person1_individual['total_tax']) < 1
        assert abs(household_result['person2_tax'] - person2_individual['total_tax']) < 1
        assert abs(household_result['total_household_tax'] -
                  (person1_individual['total_tax'] + person2_individual['total_tax'])) < 1

    def test_splitting_reduces_total_tax(self):
        """Test that splitting reduces total household tax in typical scenario."""
        # Without splitting
        no_split = calculate_household_tax(
            80000, 65, 70000,
            40000, 65, 30000,
            apply_income_splitting=False,
        )

        # With splitting
        with_split = calculate_household_tax(
            80000, 65, 70000,
            40000, 65, 30000,
            apply_income_splitting=True,
        )

        # Splitting should reduce total tax
        assert with_split['total_household_tax'] <= no_split['total_household_tax']
        assert with_split['income_splitting_savings'] >= 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
