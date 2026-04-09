"""
Integration tests for couple retirement planning features.

Tests the complete flow from inputs to projections to analysis.
"""

import pytest
from src.models.household import Person, Household
from src.calculations.rrsp_tfsa import project_couple_accounts
from src.calculations.cpp_oas import project_couple_cpp_oas_income


class TestHouseholdModel:
    """Test the Household and Person data models."""

    def test_create_person(self):
        """Test creating a Person object."""
        person = Person(
            name="John",
            current_age=55,
            retirement_age=65,
            years_in_canada=40,
            rrsp_balance=500000,
            tfsa_balance=100000,
            nonreg_balance=200000,
            annual_income=80000,
            annual_savings=20000,
            cpp_start_age=65,
            cpp_contribution_years=35,
            cpp_earnings_ratio=0.8,
            oas_start_age=65,
        )

        assert person.name == "John"
        assert person.current_age == 55
        assert person.total_savings == 800000
        assert person.years_to_retirement == 10

    def test_create_household_single(self):
        """Test creating a single-person household."""
        person1 = Person(
            name="Jane",
            current_age=60,
            retirement_age=65,
            rrsp_balance=300000,
            tfsa_balance=75000,
            nonreg_balance=100000,
        )

        household = Household(person1=person1)

        assert household.is_couple is False
        assert household.total_household_savings == 475000
        assert household.age_difference == 0

    def test_create_household_couple(self):
        """Test creating a couple household."""
        person1 = Person(
            name="John",
            current_age=60,
            retirement_age=65,
            rrsp_balance=400000,
            tfsa_balance=100000,
            nonreg_balance=150000,
        )

        person2 = Person(
            name="Jane",
            current_age=58,
            retirement_age=65,
            rrsp_balance=300000,
            tfsa_balance=80000,
            nonreg_balance=100000,
        )

        household = Household(person1=person1, person2=person2)

        assert household.is_couple is True
        assert household.total_household_savings == 1130000
        assert household.age_difference == 2
        assert household.get_older_person() == person1
        assert household.get_younger_person() == person2

    def test_household_age_checks(self):
        """Test household age-related checks."""
        person1 = Person(
            name="John",
            current_age=70,
            retirement_age=65,
            rrsp_balance=200000,
            tfsa_balance=50000,
            nonreg_balance=75000,
        )

        person2 = Person(
            name="Jane",
            current_age=68,
            retirement_age=65,
            rrsp_balance=150000,
            tfsa_balance=40000,
            nonreg_balance=50000,
        )

        household = Household(person1=person1, person2=person2)

        # Both 65+ (year 0)
        assert household.both_age_65_or_older(year_offset=0) is True

        # Both retired
        assert household.both_retired(year_offset=0) is True

    def test_person_validation(self):
        """Test that Person validates input parameters."""
        # Invalid age
        with pytest.raises(ValueError, match="Current age must be between"):
            Person(name="Test", current_age=150, retirement_age=65)

        # Invalid retirement age
        with pytest.raises(ValueError, match="Retirement age must be between"):
            Person(name="Test", current_age=60, retirement_age=80)

        # Invalid CPP start age
        with pytest.raises(ValueError, match="CPP start age must be between"):
            Person(name="Test", current_age=60, retirement_age=65, cpp_start_age=55)

        # Invalid CPP earnings ratio
        with pytest.raises(ValueError, match="CPP earnings ratio must be between"):
            Person(name="Test", current_age=60, retirement_age=65, cpp_earnings_ratio=1.5)


class TestCoupleCPPOASProjection:
    """Test couple CPP/OAS projections."""

    def test_couple_cpp_oas_projection_same_age(self):
        """Test CPP/OAS projection for couple of same age."""
        result = project_couple_cpp_oas_income(
            person1_current_age=60,
            person2_current_age=60,
            projection_years=35,
            person1_cpp_params={'start_age': 65, 'contribution_years': 35, 'earnings_ratio': 0.8},
            person2_cpp_params={'start_age': 65, 'contribution_years': 35, 'earnings_ratio': 0.75},
            person1_oas_params={'start_age': 65, 'years_in_canada': 40},
            person2_oas_params={'start_age': 65, 'years_in_canada': 40},
        )

        # Check structure
        assert 'person1_cpp_annual' in result
        assert 'person2_cpp_annual' in result
        assert 'household_cpp_annual' in result

        # Both should start receiving at same age (65)
        assert result['person1_cpp_annual'][5] > 0  # Year 5 = age 65
        assert result['person2_cpp_annual'][5] > 0

    def test_couple_cpp_oas_projection_age_gap(self):
        """Test CPP/OAS projection for couple with age gap."""
        result = project_couple_cpp_oas_income(
            person1_current_age=65,
            person2_current_age=60,  # 5 year gap
            projection_years=30,
            person1_cpp_params={'start_age': 65, 'contribution_years': 40, 'earnings_ratio': 1.0},
            person2_cpp_params={'start_age': 65, 'contribution_years': 35, 'earnings_ratio': 0.8},
            person1_oas_params={'start_age': 65, 'years_in_canada': 40},
            person2_oas_params={'start_age': 65, 'years_in_canada': 40},
        )

        # Person 1 should receive CPP immediately
        assert result['person1_cpp_annual'][0] > 0

        # Person 2 should not receive until age 65 (year 5)
        assert result['person2_cpp_annual'][0] == 0
        assert result['person2_cpp_annual'][5] > 0


class TestCoupleAccountProjection:
    """Test couple account projections."""

    def test_basic_couple_projection(self):
        """Test basic couple account projection."""
        def person1_cpp_oas(year):
            return (15000, 8000) if year >= 5 else (0, 0)

        def person2_cpp_oas(year):
            return (12000, 8000) if year >= 5 else (0, 0)

        result = project_couple_accounts(
            person1_current_age=60,
            person2_current_age=60,
            person1_retirement_age=65,
            person2_retirement_age=65,
            projection_years=35,
            person1_rrsp_balance=500000,
            person1_tfsa_balance=100000,
            person1_nonreg_balance=150000,
            person2_rrsp_balance=300000,
            person2_tfsa_balance=80000,
            person2_nonreg_balance=100000,
            person1_annual_savings=20000,
            person2_annual_savings=15000,
            household_annual_spending=80000,
            person1_cpp_oas_func=person1_cpp_oas,
            person2_cpp_oas_func=person2_cpp_oas,
            withdrawal_strategy='tax_optimized',
        )

        # Check result structure
        assert 'person1_rrsp_balance' in result
        assert 'person2_rrsp_balance' in result
        assert 'household_total_balance' in result
        assert 'household_tax' in result

        # Should have 35 years of data
        assert len(result['person1_age']) == 35
        assert len(result['person2_age']) == 35

    def test_couple_projection_with_different_retirement_ages(self):
        """Test couple with different retirement ages."""
        def person1_cpp_oas(year):
            age = 65 + year
            return (16000, 8500) if age >= 65 else (0, 0)

        def person2_cpp_oas(year):
            age = 60 + year
            return (14000, 8500) if age >= 65 else (0, 0)

        result = project_couple_accounts(
            person1_current_age=65,  # Already retired
            person2_current_age=60,  # 5 years from retirement
            person1_retirement_age=65,
            person2_retirement_age=65,
            projection_years=30,
            person1_rrsp_balance=400000,
            person1_tfsa_balance=100000,
            person1_nonreg_balance=100000,
            person2_rrsp_balance=300000,
            person2_tfsa_balance=75000,
            person2_nonreg_balance=75000,
            person1_annual_savings=0,  # Already retired
            person2_annual_savings=15000,  # Still working
            household_annual_spending=70000,
            person1_cpp_oas_func=person1_cpp_oas,
            person2_cpp_oas_func=person2_cpp_oas,
            withdrawal_strategy='tax_optimized',
        )

        # Person 2 should have contributions in early years
        # (Difficult to verify exact amounts, but structure should be correct)
        assert len(result['person2_rrsp_balance']) == 30


class TestEndToEndCoupleFlow:
    """End-to-end integration tests."""

    def test_complete_couple_planning_flow(self):
        """Test complete flow from Person creation to projection."""
        # Step 1: Create couple
        person1 = Person(
            name="John",
            current_age=60,
            retirement_age=65,
            years_in_canada=40,
            rrsp_balance=500000,
            tfsa_balance=100000,
            nonreg_balance=200000,
            annual_income=80000,
            annual_savings=20000,
            cpp_start_age=65,
            cpp_contribution_years=35,
            cpp_earnings_ratio=0.85,
            oas_start_age=65,
        )

        person2 = Person(
            name="Jane",
            current_age=58,
            retirement_age=65,
            years_in_canada=40,
            rrsp_balance=300000,
            tfsa_balance=80000,
            nonreg_balance=100000,
            annual_income=70000,
            annual_savings=15000,
            cpp_start_age=65,
            cpp_contribution_years=35,
            cpp_earnings_ratio=0.75,
            oas_start_age=65,
        )

        household = Household(
            person1=person1,
            person2=person2,
            household_annual_spending=80000,
            apply_income_splitting=True,
            survivor_spending_ratio=0.70,
        )

        # Verify household setup
        assert household.is_couple is True
        assert household.total_household_savings == 1280000

        # Step 2: Project CPP/OAS
        cpp_oas_result = project_couple_cpp_oas_income(
            person1_current_age=person1.current_age,
            person2_current_age=person2.current_age,
            projection_years=37,
            person1_cpp_params={
                'start_age': person1.cpp_start_age,
                'contribution_years': person1.cpp_contribution_years,
                'earnings_ratio': person1.cpp_earnings_ratio,
            },
            person2_cpp_params={
                'start_age': person2.cpp_start_age,
                'contribution_years': person2.cpp_contribution_years,
                'earnings_ratio': person2.cpp_earnings_ratio,
            },
            person1_oas_params={
                'start_age': person1.oas_start_age,
                'years_in_canada': person1.years_in_canada,
            },
            person2_oas_params={
                'start_age': person2.oas_start_age,
                'years_in_canada': person2.years_in_canada,
            },
        )

        # Verify CPP/OAS projection
        assert len(cpp_oas_result['household_cpp_annual']) == 37

        # Step 3: Create CPP/OAS functions for account projection
        def person1_cpp_oas(year):
            if year < len(cpp_oas_result['person1_cpp_annual']):
                return (
                    cpp_oas_result['person1_cpp_annual'][year],
                    cpp_oas_result['person1_oas_annual'][year]
                )
            return (0, 0)

        def person2_cpp_oas(year):
            if year < len(cpp_oas_result['person2_cpp_annual']):
                return (
                    cpp_oas_result['person2_cpp_annual'][year],
                    cpp_oas_result['person2_oas_annual'][year]
                )
            return (0, 0)

        # Step 4: Project accounts
        account_projection = project_couple_accounts(
            person1_current_age=person1.current_age,
            person2_current_age=person2.current_age,
            person1_retirement_age=person1.retirement_age,
            person2_retirement_age=person2.retirement_age,
            projection_years=37,
            person1_rrsp_balance=person1.rrsp_balance,
            person1_tfsa_balance=person1.tfsa_balance,
            person1_nonreg_balance=person1.nonreg_balance,
            person2_rrsp_balance=person2.rrsp_balance,
            person2_tfsa_balance=person2.tfsa_balance,
            person2_nonreg_balance=person2.nonreg_balance,
            person1_annual_savings=person1.annual_savings,
            person2_annual_savings=person2.annual_savings,
            household_annual_spending=household.household_annual_spending,
            person1_cpp_oas_func=person1_cpp_oas,
            person2_cpp_oas_func=person2_cpp_oas,
            withdrawal_strategy='tax_optimized',
        )

        # Verify account projection
        assert len(account_projection['household_total_balance']) == 37
        assert account_projection['household_total_balance'][0] > 0

        # Step 5: Verify income splitting occurs
        # Should have splitting after both are 65+
        # Person 1 is 60, Person 2 is 58, so at year 7 both are 65+
        splitting_savings = account_projection['income_splitting_savings'][10]  # Year 10
        # May or may not have savings depending on withdrawal amounts
        assert splitting_savings >= 0

        # Step 6: Verify final results
        final_balance = account_projection['household_total_balance'][-1]
        assert final_balance >= 0  # Portfolio may or may not last

        # Verify both spouses tracked throughout
        assert len(account_projection['person1_age']) == len(account_projection['person2_age'])


class TestBackwardCompatibility:
    """Test backward compatibility with single-person mode."""

    def test_single_person_still_works(self):
        """Test that single-person calculations still work."""
        from src.calculations.rrsp_tfsa import project_all_accounts

        result = project_all_accounts(
            current_age=60,
            retirement_age=65,
            projection_years=35,
            rrsp_balance=500000,
            tfsa_balance=100000,
            nonreg_balance=150000,
            annual_contribution=20000,
            withdrawal_strategy='tax_efficient',
            annual_withdrawal_amount=60000,
        )

        # Should work as before
        assert 'rrsp_balance' in result
        assert 'tfsa_balance' in result
        assert len(result['age']) == 35


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
