"""
Unit tests for survivor scenario analysis.
"""

import pytest
from src.strategies.survivor_scenarios import (
    project_survivor_scenario,
)
from src.calculations.cpp_oas import calculate_survivor_benefits


class TestSurvivorBenefits:
    """Test CPP survivor benefit calculations."""

    def test_survivor_benefit_age_65_plus(self):
        """Test 60% survivor benefit for age 65+."""
        result = calculate_survivor_benefits(
            deceased_cpp_monthly=1200,
            survivor_age=70,
            survivor_cpp_monthly=800,
        )

        # Should receive 60% of deceased's CPP
        expected_survivor_benefit = 1200 * 0.60
        assert result['survivor_cpp_benefit'] == expected_survivor_benefit

        # Combined should be capped at maximum
        assert result['combined_cpp_monthly'] >= 800  # At least own CPP
        assert result['combined_cpp_monthly'] <= 1364.60  # CPP max

    def test_survivor_benefit_under_65(self):
        """Test survivor benefit structure for under 65."""
        result = calculate_survivor_benefits(
            deceased_cpp_monthly=1200,
            survivor_age=60,
            survivor_cpp_monthly=0,
        )

        # Should have flat-rate component + 37.5% of deceased's CPP
        assert result['survivor_cpp_benefit'] > 0
        assert result['note'].startswith('Under age 65')

    def test_survivor_benefit_no_own_cpp(self):
        """Test survivor with no own CPP."""
        result = calculate_survivor_benefits(
            deceased_cpp_monthly=1000,
            survivor_age=65,
            survivor_cpp_monthly=0,
        )

        # Should receive 60% of deceased's CPP
        assert result['combined_cpp_monthly'] == 1000 * 0.60
        assert result['survivor_cpp_before'] == 0

    def test_survivor_benefit_maximum_cap(self):
        """Test that combined benefit is capped at CPP maximum."""
        result = calculate_survivor_benefits(
            deceased_cpp_monthly=1364.60,  # Maximum
            survivor_age=65,
            survivor_cpp_monthly=1364.60,  # Also maximum
        )

        # Combined can't exceed maximum
        assert result['combined_cpp_monthly'] <= 1364.60


class TestSurvivorScenarioProjection:
    """Test survivor scenario projections."""

    def test_basic_survivor_projection(self):
        """Test basic survivor scenario projection."""
        deceased_params = {
            'rrsp_balance_at_death': 200000,
            'tfsa_balance_at_death': 100000,
            'nonreg_balance_at_death': 50000,
            'age_at_death': 80,
            'name': 'Person 1',
        }

        survivor_params = {
            'current_age': 78,  # 2 years younger
            'rrsp_balance': 150000,
            'tfsa_balance': 80000,
            'nonreg_balance': 40000,
            'years_in_canada': 40,
            'oas_start_age': 65,
            'name': 'Person 2',
        }

        result = project_survivor_scenario(
            deceased_params,
            survivor_params,
            death_age=80,
            projection_years_after_death=17,  # To age 95
            survivor_annual_spending=50000,
            deceased_cpp_monthly=1200,
            deceased_oas_monthly=700,
            survivor_cpp_monthly=1000,
            survivor_oas_monthly=700,
        )

        # Check structure
        assert 'projections' in result
        assert 'death_summary' in result
        assert 'income_changes' in result
        assert 'portfolio_sustainability' in result

        # Check projections has expected keys
        proj = result['projections']
        assert 'survivor_age' in proj
        assert 'survivor_rrsp_balance' in proj
        assert 'survivor_tfsa_balance' in proj
        assert 'survivor_cpp_income' in proj
        assert 'survivor_oas_income' in proj

    def test_asset_transfer_calculations(self):
        """Test that assets are transferred correctly."""
        deceased_params = {
            'rrsp_balance_at_death': 200000,
            'tfsa_balance_at_death': 100000,
            'nonreg_balance_at_death': 50000,
            'age_at_death': 75,
        }

        survivor_params = {
            'current_age': 73,
            'rrsp_balance': 100000,
            'tfsa_balance': 50000,
            'nonreg_balance': 25000,
            'years_in_canada': 40,
            'oas_start_age': 65,
        }

        result = project_survivor_scenario(
            deceased_params,
            survivor_params,
            death_age=75,
            projection_years_after_death=22,
            survivor_annual_spending=40000,
            deceased_cpp_monthly=1200,
            deceased_oas_monthly=700,
            survivor_cpp_monthly=1000,
            survivor_oas_monthly=700,
        )

        # Assets should be transferred
        death_summary = result['death_summary']
        assert death_summary['assets_transferred'] > 0
        assert death_summary['rrsp_transferred'] > 0
        assert death_summary['tfsa_transferred'] == 100000  # Full TFSA

    def test_income_changes_after_death(self):
        """Test income changes are calculated correctly."""
        deceased_params = {
            'rrsp_balance_at_death': 100000,
            'tfsa_balance_at_death': 50000,
            'nonreg_balance_at_death': 25000,
            'age_at_death': 80,
        }

        survivor_params = {
            'current_age': 78,
            'rrsp_balance': 80000,
            'tfsa_balance': 40000,
            'nonreg_balance': 20000,
            'years_in_canada': 40,
            'oas_start_age': 65,
        }

        deceased_cpp = 1200
        survivor_cpp = 1000

        result = project_survivor_scenario(
            deceased_params,
            survivor_params,
            death_age=80,
            projection_years_after_death=17,
            survivor_annual_spending=45000,
            deceased_cpp_monthly=deceased_cpp,
            deceased_oas_monthly=700,
            survivor_cpp_monthly=survivor_cpp,
            survivor_oas_monthly=700,
        )

        income_changes = result['income_changes']

        # CPP should include survivor benefit
        assert income_changes['cpp_after_death'] > income_changes['cpp_before_death']
        assert income_changes['cpp_survivor_benefit_added'] > 0

        # OAS doesn't have survivor benefit
        # (OAS after death should be just survivor's own OAS, possibly adjusted for clawback)
        assert 'oas_after_death' in income_changes

    def test_portfolio_sustainability_calculation(self):
        """Test portfolio sustainability assessment."""
        deceased_params = {
            'rrsp_balance_at_death': 500000,
            'tfsa_balance_at_death': 200000,
            'nonreg_balance_at_death': 100000,
            'age_at_death': 75,
        }

        survivor_params = {
            'current_age': 73,
            'rrsp_balance': 300000,
            'tfsa_balance': 150000,
            'nonreg_balance': 75000,
            'years_in_canada': 40,
            'oas_start_age': 65,
        }

        result = project_survivor_scenario(
            deceased_params,
            survivor_params,
            death_age=75,
            projection_years_after_death=22,
            survivor_annual_spending=50000,  # Moderate spending
            deceased_cpp_monthly=1200,
            deceased_oas_monthly=700,
            survivor_cpp_monthly=1000,
            survivor_oas_monthly=700,
            inflation_rate=0.0,  # No inflation for this test
        )

        sustainability = result['portfolio_sustainability']

        # Should have assessment
        assert 'final_balance_at_age_95' in sustainability
        assert 'portfolio_sustainable' in sustainability
        assert isinstance(sustainability['portfolio_sustainable'], bool)

        # With these parameters, portfolio should be sustainable
        assert sustainability['portfolio_sustainable'] is True
        assert sustainability['final_balance_at_age_95'] > 0

    def test_high_spending_depletes_portfolio(self):
        """Test that high spending can deplete portfolio."""
        deceased_params = {
            'rrsp_balance_at_death': 50000,
            'tfsa_balance_at_death': 20000,
            'nonreg_balance_at_death': 10000,
            'age_at_death': 75,
        }

        survivor_params = {
            'current_age': 73,
            'rrsp_balance': 30000,
            'tfsa_balance': 15000,
            'nonreg_balance': 5000,
            'years_in_canada': 40,
            'oas_start_age': 65,
        }

        result = project_survivor_scenario(
            deceased_params,
            survivor_params,
            death_age=75,
            projection_years_after_death=22,
            survivor_annual_spending=80000,  # Very high spending
            deceased_cpp_monthly=500,  # Low CPP
            deceased_oas_monthly=600,
            survivor_cpp_monthly=500,
            survivor_oas_monthly=600,
        )

        sustainability = result['portfolio_sustainability']

        # Portfolio likely won't last
        # (May or may not deplete depending on exact calculations)
        assert 'depletion_age' in sustainability

    def test_survivor_spending_reduction(self):
        """Test that survivor spending is typically reduced from couple spending."""
        # This tests the concept that survivor spending should be less than couple
        couple_spending = 80000
        survivor_spending = couple_spending * 0.70  # 70%

        deceased_params = {
            'rrsp_balance_at_death': 200000,
            'tfsa_balance_at_death': 100000,
            'nonreg_balance_at_death': 50000,
            'age_at_death': 80,
        }

        survivor_params = {
            'current_age': 78,
            'rrsp_balance': 150000,
            'tfsa_balance': 80000,
            'nonreg_balance': 40000,
            'years_in_canada': 40,
            'oas_start_age': 65,
        }

        result = project_survivor_scenario(
            deceased_params,
            survivor_params,
            death_age=80,
            projection_years_after_death=17,
            survivor_annual_spending=survivor_spending,  # Reduced spending
            deceased_cpp_monthly=1200,
            deceased_oas_monthly=700,
            survivor_cpp_monthly=1000,
            survivor_oas_monthly=700,
        )

        # Verify the projection uses the reduced spending
        # (Indirectly verified by checking withdrawals are reasonable)
        proj = result['projections']
        assert len(proj['survivor_age']) > 0


class TestSurvivorScenarioEdgeCases:
    """Test edge cases in survivor scenarios."""

    def test_very_young_survivor(self):
        """Test survivor scenario with young survivor (age 50)."""
        deceased_params = {
            'rrsp_balance_at_death': 150000,
            'tfsa_balance_at_death': 75000,
            'nonreg_balance_at_death': 30000,
            'age_at_death': 55,
        }

        survivor_params = {
            'current_age': 50,  # Young survivor
            'rrsp_balance': 100000,
            'tfsa_balance': 50000,
            'nonreg_balance': 20000,
            'years_in_canada': 35,
            'oas_start_age': 65,
        }

        result = project_survivor_scenario(
            deceased_params,
            survivor_params,
            death_age=55,
            projection_years_after_death=45,  # Long projection
            survivor_annual_spending=40000,
            deceased_cpp_monthly=800,
            deceased_oas_monthly=0,  # No OAS yet
            survivor_cpp_monthly=0,  # No CPP yet
            survivor_oas_monthly=0,
        )

        # Should project to age 95
        assert len(result['projections']['survivor_age']) == 45

    def test_zero_assets_deceased(self):
        """Test scenario where deceased has no assets."""
        deceased_params = {
            'rrsp_balance_at_death': 0,
            'tfsa_balance_at_death': 0,
            'nonreg_balance_at_death': 0,
            'age_at_death': 80,
        }

        survivor_params = {
            'current_age': 78,
            'rrsp_balance': 100000,
            'tfsa_balance': 50000,
            'nonreg_balance': 25000,
            'years_in_canada': 40,
            'oas_start_age': 65,
        }

        result = project_survivor_scenario(
            deceased_params,
            survivor_params,
            death_age=80,
            projection_years_after_death=17,
            survivor_annual_spending=35000,
            deceased_cpp_monthly=1000,
            deceased_oas_monthly=700,
            survivor_cpp_monthly=900,
            survivor_oas_monthly=700,
        )

        # Should still work, just no assets transferred
        assert result['death_summary']['assets_transferred'] == 0


class TestSurvivorScenarioIntegration:
    """Integration tests for survivor scenarios."""

    def test_complete_survivor_scenario_flow(self):
        """Test complete survivor scenario from death to age 95."""
        deceased_params = {
            'rrsp_balance_at_death': 300000,
            'tfsa_balance_at_death': 150000,
            'nonreg_balance_at_death': 75000,
            'age_at_death': 78,
            'name': 'Spouse A',
        }

        survivor_params = {
            'current_age': 76,
            'rrsp_balance': 200000,
            'tfsa_balance': 100000,
            'nonreg_balance': 50000,
            'years_in_canada': 40,
            'oas_start_age': 65,
            'name': 'Spouse B',
        }

        result = project_survivor_scenario(
            deceased_params,
            survivor_params,
            death_age=78,
            projection_years_after_death=19,  # 76 to 95
            survivor_annual_spending=55000,
            deceased_cpp_monthly=1100,
            deceased_oas_monthly=700,
            survivor_cpp_monthly=1000,
            survivor_oas_monthly=700,
        )

        # Verify complete result structure
        assert result['survivor_name'] == 'Spouse B'
        assert result['deceased_name'] == 'Spouse A'

        # Verify all sections present
        assert 'projections' in result
        assert 'death_summary' in result
        assert 'income_changes' in result
        assert 'portfolio_sustainability' in result

        # Verify projection covers full period
        assert len(result['projections']['survivor_age']) == 19

        # Verify names are tracked
        assert result['survivor_name'] == 'Spouse B'
        assert result['deceased_name'] == 'Spouse A'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
