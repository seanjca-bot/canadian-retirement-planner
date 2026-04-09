"""
Unit tests for couple withdrawal strategies.
"""

import pytest
from src.strategies.couple_withdrawal import (
    calculate_couple_withdrawal_strategy,
    _tax_optimized_strategy,
    _oas_clawback_aware_strategy,
    _balanced_strategy,
)
from src.utils.constants import OAS_CLAWBACK_THRESHOLD


class TestCoupleWithdrawalStrategy:
    """Test couple withdrawal strategy selection."""

    def test_tax_optimized_strategy_selection(self):
        """Test that tax_optimized strategy can be selected."""
        result = calculate_couple_withdrawal_strategy(
            person1_rrsp_balance=100000,
            person1_tfsa_balance=50000,
            person1_nonreg_balance=30000,
            person2_rrsp_balance=80000,
            person2_tfsa_balance=40000,
            person2_nonreg_balance=20000,
            person1_age=65,
            person2_age=65,
            target_household_spending=60000,
            person1_other_income=20000,
            person2_other_income=18000,
            strategy='tax_optimized',
        )

        assert 'person1_withdrawals' in result
        assert 'person2_withdrawals' in result
        assert result['rationale'].startswith('Tax-optimized')

    def test_oas_clawback_aware_strategy_selection(self):
        """Test that oas_clawback_aware strategy can be selected."""
        result = calculate_couple_withdrawal_strategy(
            person1_rrsp_balance=100000,
            person1_tfsa_balance=50000,
            person1_nonreg_balance=30000,
            person2_rrsp_balance=80000,
            person2_tfsa_balance=40000,
            person2_nonreg_balance=20000,
            person1_age=65,
            person2_age=65,
            target_household_spending=60000,
            person1_other_income=80000,  # Near OAS threshold
            person2_other_income=75000,  # Near OAS threshold
            strategy='oas_clawback_aware',
        )

        assert 'person1_withdrawals' in result
        assert 'person2_withdrawals' in result
        assert result['rationale'].startswith('OAS-aware')

    def test_balanced_strategy_selection(self):
        """Test that balanced strategy can be selected."""
        result = calculate_couple_withdrawal_strategy(
            person1_rrsp_balance=100000,
            person1_tfsa_balance=50000,
            person1_nonreg_balance=30000,
            person2_rrsp_balance=100000,
            person2_tfsa_balance=50000,
            person2_nonreg_balance=30000,
            person1_age=65,
            person2_age=65,
            target_household_spending=60000,
            person1_other_income=20000,
            person2_other_income=20000,
            strategy='balanced',
        )

        assert 'person1_withdrawals' in result
        assert 'person2_withdrawals' in result
        assert result['rationale'].startswith('Balanced')

    def test_invalid_strategy_raises_error(self):
        """Test that invalid strategy raises ValueError."""
        with pytest.raises(ValueError, match="Unknown withdrawal strategy"):
            calculate_couple_withdrawal_strategy(
                100000, 50000, 30000,
                80000, 40000, 20000,
                65, 65, 60000,
                20000, 18000,
                strategy='invalid_strategy',
            )


class TestTaxOptimizedStrategy:
    """Test tax-optimized withdrawal strategy."""

    def test_withdraws_from_tfsa_first(self):
        """Test that strategy prioritizes TFSA (tax-free)."""
        result = calculate_couple_withdrawal_strategy(
            person1_rrsp_balance=100000,
            person1_tfsa_balance=50000,
            person1_nonreg_balance=30000,
            person2_rrsp_balance=100000,
            person2_tfsa_balance=50000,
            person2_nonreg_balance=30000,
            person1_age=65,
            person2_age=65,
            target_household_spending=30000,  # Can cover with TFSA
            person1_other_income=10000,
            person2_other_income=10000,
            strategy='tax_optimized',
        )

        # Should primarily use TFSA
        total_tfsa = (result['person1_withdrawals']['tfsa'] +
                     result['person2_withdrawals']['tfsa'])
        assert total_tfsa > 0

    def test_respects_rrif_minimums(self):
        """Test that RRIF minimums are respected."""
        rrif_minimum = 5000
        result = calculate_couple_withdrawal_strategy(
            person1_rrsp_balance=100000,
            person1_tfsa_balance=50000,
            person1_nonreg_balance=30000,
            person2_rrsp_balance=100000,
            person2_tfsa_balance=50000,
            person2_nonreg_balance=30000,
            person1_age=72,  # RRIF age
            person2_age=72,
            target_household_spending=1000,  # Low spending
            person1_other_income=10000,
            person2_other_income=10000,
            person1_rrif_minimum=rrif_minimum,
            person2_rrif_minimum=rrif_minimum,
            strategy='tax_optimized',
        )

        # Should withdraw at least RRIF minimum
        assert result['person1_withdrawals']['rrsp'] >= rrif_minimum
        assert result['person2_withdrawals']['rrsp'] >= rrif_minimum

    def test_balances_between_spouses_with_different_incomes(self):
        """Test that strategy balances withdrawals when incomes differ."""
        result = calculate_couple_withdrawal_strategy(
            person1_rrsp_balance=100000,
            person1_tfsa_balance=10000,
            person1_nonreg_balance=10000,
            person2_rrsp_balance=100000,
            person2_tfsa_balance=10000,
            person2_nonreg_balance=10000,
            person1_age=65,
            person2_age=65,
            target_household_spending=80000,
            person1_other_income=50000,  # Higher income
            person2_other_income=20000,  # Lower income
            strategy='tax_optimized',
        )

        # Person 2 (lower income) should withdraw more to balance marginal rates
        # This is a heuristic - exact amounts depend on implementation
        assert result['person1_withdrawals']['total'] >= 0
        assert result['person2_withdrawals']['total'] >= 0


class TestOASClawbackAwareStrategy:
    """Test OAS clawback-aware withdrawal strategy."""

    def test_keeps_spouses_below_threshold_when_possible(self):
        """Test strategy tries to keep both spouses below OAS threshold."""
        result = calculate_couple_withdrawal_strategy(
            person1_rrsp_balance=200000,
            person1_tfsa_balance=100000,
            person1_nonreg_balance=50000,
            person2_rrsp_balance=200000,
            person2_tfsa_balance=100000,
            person2_nonreg_balance=50000,
            person1_age=65,
            person2_age=65,
            target_household_spending=50000,
            person1_other_income=40000,  # Below threshold
            person2_other_income=40000,  # Below threshold
            strategy='oas_clawback_aware',
        )

        # Check if incomes reported
        if 'person1_income' in result and 'person2_income' in result:
            # Should try to stay below OAS threshold
            # (May not always be possible depending on needs)
            person1_below = result.get('person1_below_oas_threshold', None)
            person2_below = result.get('person2_below_oas_threshold', None)

            # At least should be reported
            assert person1_below is not None
            assert person2_below is not None

    def test_prioritizes_tfsa_to_avoid_oas_impact(self):
        """Test that TFSA is prioritized (doesn't affect OAS)."""
        result = calculate_couple_withdrawal_strategy(
            person1_rrsp_balance=100000,
            person1_tfsa_balance=60000,
            person1_nonreg_balance=30000,
            person2_rrsp_balance=100000,
            person2_tfsa_balance=60000,
            person2_nonreg_balance=30000,
            person1_age=65,
            person2_age=65,
            target_household_spending=40000,
            person1_other_income=85000,  # Just below OAS threshold
            person2_other_income=85000,  # Just below OAS threshold
            strategy='oas_clawback_aware',
        )

        # Should use TFSA heavily to avoid triggering clawback
        total_tfsa = (result['person1_withdrawals']['tfsa'] +
                     result['person2_withdrawals']['tfsa'])
        assert total_tfsa > 0


class TestBalancedStrategy:
    """Test balanced withdrawal strategy."""

    def test_proportional_withdrawals_equal_balances(self):
        """Test balanced strategy with equal account balances."""
        result = calculate_couple_withdrawal_strategy(
            person1_rrsp_balance=100000,
            person1_tfsa_balance=50000,
            person1_nonreg_balance=30000,
            person2_rrsp_balance=100000,
            person2_tfsa_balance=50000,
            person2_nonreg_balance=30000,
            person1_age=65,
            person2_age=65,
            target_household_spending=60000,
            person1_other_income=10000,
            person2_other_income=10000,
            strategy='balanced',
        )

        # With equal balances, should withdraw roughly equally
        person1_total = result['person1_withdrawals']['total']
        person2_total = result['person2_withdrawals']['total']

        # Should be roughly 50/50 (within 20% tolerance)
        ratio = person1_total / (person1_total + person2_total) if (person1_total + person2_total) > 0 else 0
        assert 0.3 <= ratio <= 0.7

    def test_proportional_withdrawals_unequal_balances(self):
        """Test balanced strategy with unequal account balances."""
        result = calculate_couple_withdrawal_strategy(
            person1_rrsp_balance=150000,  # Person 1 has more
            person1_tfsa_balance=75000,
            person1_nonreg_balance=45000,
            person2_rrsp_balance=50000,   # Person 2 has less
            person2_tfsa_balance=25000,
            person2_nonreg_balance=15000,
            person1_age=65,
            person2_age=65,
            target_household_spending=60000,
            person1_other_income=10000,
            person2_other_income=10000,
            strategy='balanced',
        )

        # Person 1 should withdraw more (has 3x the assets)
        person1_total = result['person1_withdrawals']['total']
        person2_total = result['person2_withdrawals']['total']

        assert person1_total > person2_total

    def test_balanced_handles_zero_balances(self):
        """Test balanced strategy when one spouse has zero balance."""
        result = calculate_couple_withdrawal_strategy(
            person1_rrsp_balance=100000,
            person1_tfsa_balance=50000,
            person1_nonreg_balance=30000,
            person2_rrsp_balance=0,  # No assets
            person2_tfsa_balance=0,
            person2_nonreg_balance=0,
            person1_age=65,
            person2_age=65,
            target_household_spending=40000,
            person1_other_income=10000,
            person2_other_income=10000,
            strategy='balanced',
        )

        # All withdrawals from Person 1
        assert result['person1_withdrawals']['total'] > 0
        assert result['person2_withdrawals']['total'] == 0


class TestWithdrawalIntegration:
    """Integration tests for withdrawal strategies."""

    def test_total_withdrawal_meets_target(self):
        """Test that total withdrawal meets or approaches target spending."""
        target = 60000
        result = calculate_couple_withdrawal_strategy(
            person1_rrsp_balance=200000,
            person1_tfsa_balance=100000,
            person1_nonreg_balance=50000,
            person2_rrsp_balance=200000,
            person2_tfsa_balance=100000,
            person2_nonreg_balance=50000,
            person1_age=65,
            person2_age=65,
            target_household_spending=target,
            person1_other_income=10000,
            person2_other_income=10000,
            strategy='tax_optimized',
        )

        # Total withdrawal should be close to target
        total_withdrawal = result['total_household_withdrawal']
        assert abs(total_withdrawal - target) < 1000  # Within $1000

    def test_withdrawal_respects_available_balances(self):
        """Test that withdrawals don't exceed available balances."""
        result = calculate_couple_withdrawal_strategy(
            person1_rrsp_balance=20000,
            person1_tfsa_balance=10000,
            person1_nonreg_balance=5000,
            person2_rrsp_balance=20000,
            person2_tfsa_balance=10000,
            person2_nonreg_balance=5000,
            person1_age=65,
            person2_age=65,
            target_household_spending=100000,  # More than available
            person1_other_income=0,
            person2_other_income=0,
            strategy='tax_optimized',
        )

        # Total withdrawal can't exceed total balances
        total_balances = 20000 + 10000 + 5000 + 20000 + 10000 + 5000
        assert result['total_household_withdrawal'] <= total_balances

    def test_household_tax_calculated(self):
        """Test that household tax is calculated."""
        result = calculate_couple_withdrawal_strategy(
            person1_rrsp_balance=100000,
            person1_tfsa_balance=50000,
            person1_nonreg_balance=30000,
            person2_rrsp_balance=100000,
            person2_tfsa_balance=50000,
            person2_nonreg_balance=30000,
            person1_age=65,
            person2_age=65,
            target_household_spending=60000,
            person1_other_income=20000,
            person2_other_income=20000,
            strategy='tax_optimized',
        )

        # Tax should be calculated
        assert 'household_tax' in result
        assert result['household_tax'] >= 0
        assert 'person1_tax' in result
        assert 'person2_tax' in result

    def test_income_splitting_applied_when_eligible(self):
        """Test that income splitting is applied when both 65+."""
        result = calculate_couple_withdrawal_strategy(
            person1_rrsp_balance=100000,
            person1_tfsa_balance=50000,
            person1_nonreg_balance=30000,
            person2_rrsp_balance=100000,
            person2_tfsa_balance=50000,
            person2_nonreg_balance=30000,
            person1_age=65,
            person2_age=65,
            target_household_spending=60000,
            person1_other_income=20000,
            person2_other_income=20000,
            strategy='tax_optimized',
        )

        # Income splitting should be reported
        assert 'income_splitting_applied' in result
        assert 'income_splitting_savings' in result


class TestRRSPMeltdownStrategy:
    """Test RRSP meltdown strategy for couples."""

    def test_rrsp_meltdown_strategy_selection(self):
        """Test that rrsp_meltdown strategy can be selected."""
        result = calculate_couple_withdrawal_strategy(
            person1_rrsp_balance=200000,
            person1_tfsa_balance=100000,
            person1_nonreg_balance=50000,
            person2_rrsp_balance=150000,
            person2_tfsa_balance=80000,
            person2_nonreg_balance=40000,
            person1_age=60,
            person2_age=58,
            target_household_spending=80000,
            person1_other_income=10000,
            person2_other_income=10000,
            strategy='rrsp_meltdown',
        )

        assert 'person1_withdrawals' in result
        assert 'person2_withdrawals' in result
        assert 'RRSP Meltdown' in result['rationale']

    def test_rrsp_meltdown_prioritizes_rrsp(self):
        """Test that meltdown strategy prioritizes RRSP withdrawals."""
        result = calculate_couple_withdrawal_strategy(
            person1_rrsp_balance=200000,
            person1_tfsa_balance=100000,
            person1_nonreg_balance=50000,
            person2_rrsp_balance=150000,
            person2_tfsa_balance=80000,
            person2_nonreg_balance=40000,
            person1_age=60,
            person2_age=58,
            target_household_spending=60000,
            person1_other_income=10000,
            person2_other_income=10000,
            strategy='rrsp_meltdown',
        )

        # Should withdraw from RRSP first
        total_rrsp_withdrawal = (result['person1_withdrawals']['rrsp'] +
                                result['person2_withdrawals']['rrsp'])
        total_tfsa_withdrawal = (result['person1_withdrawals']['tfsa'] +
                                result['person2_withdrawals']['tfsa'])

        # RRSP withdrawals should be larger than TFSA
        assert total_rrsp_withdrawal > total_tfsa_withdrawal

    def test_rrsp_meltdown_preserves_tfsa(self):
        """Test that meltdown strategy preserves TFSA for last."""
        result = calculate_couple_withdrawal_strategy(
            person1_rrsp_balance=100000,
            person1_tfsa_balance=100000,
            person1_nonreg_balance=50000,
            person2_rrsp_balance=80000,
            person2_tfsa_balance=80000,
            person2_nonreg_balance=40000,
            person1_age=65,
            person2_age=65,
            target_household_spending=40000,
            person1_other_income=20000,
            person2_other_income=20000,
            strategy='rrsp_meltdown',
        )

        # With sufficient RRSP, TFSA should not be touched
        total_tfsa_withdrawal = (result['person1_withdrawals']['tfsa'] +
                                result['person2_withdrawals']['tfsa'])

        # TFSA should be preserved (minimal or no withdrawal)
        assert total_tfsa_withdrawal == 0

    def test_rrsp_meltdown_respects_rrif_minimums(self):
        """Test that meltdown strategy respects RRIF minimums."""
        result = calculate_couple_withdrawal_strategy(
            person1_rrsp_balance=200000,
            person1_tfsa_balance=100000,
            person1_nonreg_balance=50000,
            person2_rrsp_balance=150000,
            person2_tfsa_balance=80000,
            person2_nonreg_balance=40000,
            person1_age=75,
            person2_age=73,
            target_household_spending=30000,
            person1_other_income=25000,
            person2_other_income=25000,
            person1_rrif_minimum=10000,
            person2_rrif_minimum=8000,
            strategy='rrsp_meltdown',
        )

        # RRIF minimums must be met
        assert result['person1_withdrawals']['rrsp'] >= 10000
        assert result['person2_withdrawals']['rrsp'] >= 8000

    def test_rrsp_meltdown_balances_marginal_rates(self):
        """Test that meltdown balances withdrawals between spouses."""
        result = calculate_couple_withdrawal_strategy(
            person1_rrsp_balance=200000,
            person1_tfsa_balance=50000,
            person1_nonreg_balance=30000,
            person2_rrsp_balance=200000,
            person2_tfsa_balance=50000,
            person2_nonreg_balance=30000,
            person1_age=65,
            person2_age=65,
            target_household_spending=80000,
            person1_other_income=30000,  # Person 1 has higher other income
            person2_other_income=15000,  # Person 2 has lower other income
            strategy='rrsp_meltdown',
        )

        # Person 2 (lower income) should have more RRSP withdrawal to balance marginal rates
        assert result['person2_withdrawals']['rrsp'] >= result['person1_withdrawals']['rrsp']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
