"""
Test that years in Canada accumulates correctly in projections.
"""

import pytest
from src.calculations.cpp_oas import (
    calculate_oas_benefit,
    project_cpp_oas_income,
    project_couple_cpp_oas_income,
)


class TestYearsInCanadaAccumulation:
    """Test that years in Canada increases during projections."""

    def test_years_accumulate_single_person(self):
        """Test that OAS benefit increases as years in Canada accumulate."""
        # Person age 50 with 32 years in Canada
        # After 15 years (age 65), should have 47 years (capped at 40)

        result = project_cpp_oas_income(
            current_age=50,
            cpp_start_age=65,
            projection_years=20,  # Age 50 to 70
            cpp_contribution_years=35,
            cpp_earnings_ratio=1.0,
            years_in_canada=32,  # Currently 32 years
        )

        # At age 50 (year 0): 32 years → 80% OAS (32/40)
        oas_at_50 = result['oas_monthly'][0]

        # At age 65 (year 15): 32+15=47 years (capped at 40) → 100% OAS
        oas_at_65 = result['oas_monthly'][15]

        # At age 70 (year 20): Still 40 years (capped) → 100% OAS
        oas_at_70 = result['oas_monthly'][19]

        # OAS at 50 should be 0 (not age 65 yet)
        assert oas_at_50 == 0

        # OAS at 65 should be higher than if stuck at 32 years
        # With 40 years: full OAS = $718.33
        # With 32 years: 80% OAS = $574.66
        assert oas_at_65 > 650  # Should be close to full OAS
        assert oas_at_65 > oas_at_50

        # OAS at 70 should be even higher (10% age 75+ bonus doesn't apply yet)
        # But should still be full OAS amount
        assert oas_at_70 > 650

    def test_partial_years_accumulate_correctly(self):
        """Test exact OAS calculation with partial years."""
        # Person age 60 with 30 years
        # At age 65: 30+5=35 years → 35/40 = 87.5% OAS

        result = project_cpp_oas_income(
            current_age=60,
            cpp_start_age=65,
            projection_years=10,
            cpp_contribution_years=35,
            cpp_earnings_ratio=1.0,
            years_in_canada=30,  # Currently 30 years
        )

        # At age 65 (year 5): 30+5=35 years → 87.5% OAS
        oas_at_65 = result['oas_monthly'][5]

        # Full OAS = $718.33, so 87.5% = $628.54
        expected_oas = 718.33 * (35 / 40)
        assert abs(oas_at_65 - expected_oas) < 5  # Allow $5 tolerance

    def test_years_capped_at_40(self):
        """Test that years in Canada is capped at 40."""
        # Person age 50 with 35 years
        # At age 65: 35+15=50 years, but capped at 40

        result = project_cpp_oas_income(
            current_age=50,
            cpp_start_age=65,
            projection_years=20,
            cpp_contribution_years=35,
            cpp_earnings_ratio=1.0,
            years_in_canada=35,  # Currently 35 years
        )

        # At age 65: should use 40 years (not 50)
        oas_at_65 = result['oas_monthly'][15]

        # Should be full OAS amount
        full_oas = 718.33
        assert abs(oas_at_65 - full_oas) < 1

    def test_already_40_years_stays_100_percent(self):
        """Test that someone with 40 years stays at 100% OAS."""
        result = project_cpp_oas_income(
            current_age=60,
            cpp_start_age=65,
            projection_years=10,
            cpp_contribution_years=35,
            cpp_earnings_ratio=1.0,
            years_in_canada=40,  # Already at maximum
        )

        # At age 65: should be full OAS
        oas_at_65 = result['oas_monthly'][5]
        full_oas = 718.33
        assert abs(oas_at_65 - full_oas) < 1


class TestCoupleYearsInCanadaAccumulation:
    """Test years in Canada accumulation for couples."""

    def test_couple_both_accumulate_years(self):
        """Test that both spouses accumulate years independently."""
        # Person 1: age 60, 32 years → at 65 should have 37 years
        # Person 2: age 58, 25 years → at 65 should have 32 years

        result = project_couple_cpp_oas_income(
            person1_current_age=60,
            person2_current_age=58,
            projection_years=15,
            person1_cpp_params={'start_age': 65, 'contribution_years': 35, 'earnings_ratio': 1.0},
            person2_cpp_params={'start_age': 65, 'contribution_years': 30, 'earnings_ratio': 0.8},
            person1_oas_params={'start_age': 65, 'years_in_canada': 32},
            person2_oas_params={'start_age': 65, 'years_in_canada': 25},
        )

        # Person 1 at age 65 (year 5): 32+5=37 years → 92.5% OAS
        person1_oas_at_65 = result['person1_oas_monthly'][5]
        expected_person1 = 718.33 * (37 / 40)
        assert abs(person1_oas_at_65 - expected_person1) < 5

        # Person 2 at age 65 (year 7, when person1 is 67): 25+7=32 years → 80% OAS
        person2_oas_at_65 = result['person2_oas_monthly'][7]
        expected_person2 = 718.33 * (32 / 40)
        assert abs(person2_oas_at_65 - expected_person2) < 5

        # Person 1's OAS should be higher than Person 2's (more years)
        assert person1_oas_at_65 > person2_oas_at_65

    def test_couple_different_accumulation_rates(self):
        """Test couples with different starting years accumulate correctly."""
        # Person 1: age 55, 40 years (already maximum)
        # Person 2: age 50, 20 years (will reach 35 years by age 65)

        result = project_couple_cpp_oas_income(
            person1_current_age=55,
            person2_current_age=50,
            projection_years=20,
            person1_cpp_params={'start_age': 65, 'contribution_years': 40, 'earnings_ratio': 1.0},
            person2_cpp_params={'start_age': 65, 'contribution_years': 35, 'earnings_ratio': 1.0},
            person1_oas_params={'start_age': 65, 'years_in_canada': 40},
            person2_oas_params={'start_age': 65, 'years_in_canada': 20},
        )

        # Person 1 at age 65 (year 10): 40 years → 100% OAS
        person1_oas_at_65 = result['person1_oas_monthly'][10]
        assert abs(person1_oas_at_65 - 718.33) < 1

        # Person 2 at age 65 (year 15): 20+15=35 years → 87.5% OAS
        person2_oas_at_65 = result['person2_oas_monthly'][15]
        expected_person2 = 718.33 * (35 / 40)
        assert abs(person2_oas_at_65 - expected_person2) < 5


class TestYearsInCanadaEdgeCases:
    """Test edge cases for years in Canada accumulation."""

    def test_zero_years_accumulate_from_zero(self):
        """Test person with 0 years in Canada accumulates from start."""
        # Person age 50 with 0 years (new immigrant)
        # At age 65: 0+15=15 years → 37.5% OAS

        result = project_cpp_oas_income(
            current_age=50,
            cpp_start_age=65,
            projection_years=20,
            cpp_contribution_years=20,
            cpp_earnings_ratio=1.0,
            years_in_canada=0,  # New immigrant
        )

        # At age 65: 15 years → 37.5% OAS
        oas_at_65 = result['oas_monthly'][15]
        expected_oas = 718.33 * (15 / 40)
        assert abs(oas_at_65 - expected_oas) < 5

    def test_very_old_person_with_few_years(self):
        """Test elderly person with insufficient years (edge case)."""
        # Person age 70 with 10 years in Canada
        # Cannot accumulate to 40 by OAS age, so will have reduced OAS

        result = project_cpp_oas_income(
            current_age=70,
            cpp_start_age=65,
            projection_years=10,
            cpp_contribution_years=10,
            cpp_earnings_ratio=0.5,
            years_in_canada=10,  # Only 10 years
        )

        # At age 70 (year 0): 10 years → 25% OAS (plus 10% age 75+ bonus later)
        oas_at_70 = result['oas_monthly'][0]
        expected_oas = 718.33 * (10 / 40)
        assert abs(oas_at_70 - expected_oas) < 5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
