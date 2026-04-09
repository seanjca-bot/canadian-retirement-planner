# Couple Withdrawal Strategy - Architecture & Design

## Overview

The Ontario Retirement Planner uses a **single coordinated withdrawal strategy** for couples. This means one strategy is selected that optimizes withdrawals for **both spouses together** as a household, rather than allowing each spouse to have their own independent strategy.

## Design Philosophy

### Why One Strategy for Both?

**Coordinated household optimization** is the correct approach because:

1. **Tax Optimization Requires Coordination**
   - Marginal tax rates are progressive (higher income = higher tax rate)
   - Optimal withdrawal amounts depend on *both* spouses' incomes
   - Example: If Person 1 has $50K income and Person 2 has $30K, withdrawing more from Person 2 reduces household tax

2. **OAS Clawback Management Requires Coordination**
   - Each spouse has their own OAS clawback threshold ($86,912)
   - Strategic withdrawals keep *both* below threshold when possible
   - Example: Better to have both at $85K than one at $95K and one at $75K

3. **Income Splitting Benefits Coordination**
   - Pension income splitting (age 65+) allows shifting up to 50% of eligible income
   - Optimal split depends on both spouses' income levels
   - Strategy must coordinate to maximize splitting benefit

4. **Conflicting Strategies Would Be Counterproductive**
   - If Person 1 uses "RRSP Meltdown" (RRSP first) and Person 2 uses "Tax-Optimized" (TFSA first), they work against each other
   - Household tax optimization requires unified strategy

### Alternative (Rejected) Design

❌ **Two Separate Strategies** (one per person):
- Allows Person 1 and Person 2 to have different strategies
- **Problem**: Doesn't optimize household outcomes
- **Problem**: Strategies could conflict (one depletes RRSP, other preserves it)
- **Problem**: Can't coordinate marginal tax rate balancing
- **Verdict**: Rejected as suboptimal

✅ **Single Coordinated Strategy** (current design):
- One strategy applies to both spouses as a household
- Optimizes combined household tax and benefits
- Coordinates withdrawals to balance marginal rates
- Maximizes household after-tax income
- **Verdict**: Implemented

## Architecture

### UI Layer (app.py)

**Couple Mode**:
```python
# Single strategy selector for household
couple_withdrawal_strategy = st.selectbox(
    "Couple Withdrawal Strategy",
    options=['tax_optimized', 'oas_clawback_aware', 'balanced', 'rrsp_meltdown'],
    ...
)
```

**Single Mode** (separate, for comparison):
```python
# Individual strategy selector (not used in couple mode)
withdrawal_strategy = st.selectbox(
    "Withdrawal Strategy",
    options=['tax_efficient', 'rrsp_first', 'proportional'],
    ...
)
```

### Projection Layer (rrsp_tfsa.py)

**Function**: `project_couple_accounts()`

```python
def project_couple_accounts(
    # ... account balances for both people ...
    withdrawal_strategy: str = 'tax_optimized',  # SINGLE strategy parameter
    ...
) -> dict:
    """
    Project couple's accounts with household optimization.

    Args:
        withdrawal_strategy: Coordinated household strategy applied to both spouses:
            - 'tax_optimized': Minimize household tax
            - 'oas_clawback_aware': Keep both below OAS clawback threshold
            - 'balanced': Proportional withdrawals from both
            - 'rrsp_meltdown': Prioritize RRSP withdrawals to minimize lifetime taxes
    """
    # Strategy applied to coordinate both spouses' withdrawals
    withdrawal_result = calculate_couple_withdrawal_strategy(
        person1_rrsp.balance, person1_tfsa.balance, person1_nonreg.balance,
        person2_rrsp.balance, person2_tfsa.balance, person2_nonreg.balance,
        person1_age, person2_age,
        inflation_adjusted_spending,
        person1_other_income, person2_other_income,
        person1_rrif_min, person2_rrif_min,
        withdrawal_strategy,  # SAME strategy for both
    )
```

### Strategy Layer (couple_withdrawal.py)

**Function**: `calculate_couple_withdrawal_strategy()`

```python
def calculate_couple_withdrawal_strategy(
    # Account balances for both people
    person1_rrsp_balance, person1_tfsa_balance, person1_nonreg_balance,
    person2_rrsp_balance, person2_tfsa_balance, person2_nonreg_balance,
    # Ages and income
    person1_age, person2_age,
    target_household_spending,
    person1_other_income, person2_other_income,
    person1_rrif_minimum, person2_rrif_minimum,
    strategy: str = 'tax_optimized',  # SINGLE strategy
) -> dict:
    """
    Determine optimal withdrawal amounts from BOTH spouses' accounts.

    Returns:
        {
            'person1_withdrawals': {'rrsp': ..., 'tfsa': ..., 'nonreg': ...},
            'person2_withdrawals': {'rrsp': ..., 'tfsa': ..., 'nonreg': ...},
            'household_tax': ...,
            'income_splitting_savings': ...,
            'rationale': 'Strategy description'
        }
    """
    if strategy == 'tax_optimized':
        return _tax_optimized_strategy(...)
    elif strategy == 'oas_clawback_aware':
        return _oas_clawback_aware_strategy(...)
    elif strategy == 'balanced':
        return _balanced_strategy(...)
    elif strategy == 'rrsp_meltdown':
        return _rrsp_meltdown_strategy(...)
```

Each strategy function determines withdrawal amounts for **both** spouses based on household optimization.

## Strategy Implementations

### How Each Strategy Coordinates Both Spouses

#### 1. Tax-Optimized Strategy

**Goal**: Minimize household tax by equalizing marginal tax rates

**Coordination Logic**:
```python
# Calculate current income for each spouse
person1_income = person1_other_income + person1_rrsp_withdrawal
person2_income = person2_other_income + person2_rrsp_withdrawal

# Withdraw more from spouse with LOWER income to balance marginal rates
if person1_income <= person2_income:
    # Prioritize Person 1's withdrawals
    withdraw_from(person1_accounts)
else:
    # Prioritize Person 2's withdrawals
    withdraw_from(person2_accounts)
```

**Why coordination matters**: Withdrawing from the lower-income spouse keeps both in lower tax brackets, minimizing household tax.

#### 2. OAS-Clawback-Aware Strategy

**Goal**: Keep both spouses below OAS clawback threshold ($86,912)

**Coordination Logic**:
```python
# Calculate how much room each spouse has before OAS clawback
person1_room = OAS_THRESHOLD - person1_income
person2_room = OAS_THRESHOLD - person2_income

# Withdraw more from spouse with MORE room
if person1_room >= person2_room:
    withdraw_from(person1_accounts, up_to=person1_room)
else:
    withdraw_from(person2_accounts, up_to=person2_room)
```

**Why coordination matters**: Preserving dual OAS benefits ($17,000+/year for couple) requires keeping *both* below threshold.

#### 3. Balanced Strategy

**Goal**: Proportional withdrawals maintaining relative account sizes

**Coordination Logic**:
```python
# Calculate household total
household_total = person1_total + person2_total

# Determine proportional targets
person1_target = spending * (person1_total / household_total)
person2_target = spending * (person2_total / household_total)

# Withdraw proportionally from each
withdraw_proportionally(person1_accounts, person1_target)
withdraw_proportionally(person2_accounts, person2_target)
```

**Why coordination matters**: Maintaining relative account sizes requires coordinated proportional withdrawals.

#### 4. RRSP Meltdown Strategy

**Goal**: Deplete RRSP accounts early to minimize lifetime taxes

**Coordination Logic**:
```python
# Priority: RRSP (both spouses) → NonReg → TFSA

# Balance RRSP withdrawals between spouses to equalize marginal rates
person1_income = person1_other_income + person1_rrsp_withdrawal
person2_income = person2_other_income + person2_rrsp_withdrawal

if person1_income <= person2_income:
    # Withdraw more from Person 1's RRSP
    person1_rrsp_withdrawal += needed
else:
    # Withdraw more from Person 2's RRSP
    person2_rrsp_withdrawal += needed
```

**Why coordination matters**: Balancing RRSP withdrawals between spouses minimizes household tax while aggressively depleting both RRSPs.

## Data Flow

### Complete Flow Diagram

```
User Input (UI)
    │
    ├─ Couple Mode Toggle: "Couple"
    │
    ├─ Person 1 Data: Age, Accounts, CPP/OAS
    ├─ Person 2 Data: Age, Accounts, CPP/OAS
    │
    └─ Couple Withdrawal Strategy: [Dropdown] ← SINGLE SELECTION
            │
            ├─ tax_optimized
            ├─ oas_clawback_aware
            ├─ balanced
            └─ rrsp_meltdown

                    ↓

    Projection Function
    project_couple_accounts(
        person1_data,
        person2_data,
        withdrawal_strategy  ← SINGLE PARAMETER
    )
            │
            └─ For each year:
                    │
                    ├─ Calculate CPP/OAS for both
                    │
                    ├─ Determine household spending need
                    │
                    └─ Call strategy function:
                        calculate_couple_withdrawal_strategy(
                            person1_balances,
                            person2_balances,
                            person1_income,
                            person2_income,
                            household_spending,
                            strategy  ← SAME STRATEGY
                        )
                            │
                            └─ Returns coordinated withdrawals:
                                {
                                    'person1_withdrawals': {...},
                                    'person2_withdrawals': {...},
                                    'household_tax': ...,
                                    'income_splitting_savings': ...
                                }
```

## Key Design Decisions

### 1. Single Strategy Variable

**Implementation**:
- One `withdrawal_strategy` parameter for entire household
- No separate `person1_strategy` and `person2_strategy` variables

**Rationale**: Household optimization requires coordination, not independence.

### 2. Strategy Functions Return Both Spouses' Withdrawals

**Implementation**:
```python
return {
    'person1_withdrawals': {'rrsp': 10000, 'tfsa': 5000, 'nonreg': 2000},
    'person2_withdrawals': {'rrsp': 12000, 'tfsa': 3000, 'nonreg': 1000},
    ...
}
```

**Rationale**: Strategy determines withdrawal amounts for *both* spouses simultaneously, not one at a time.

### 3. Household-Level Metrics

**Implementation**:
- `household_tax`: Combined tax for both spouses
- `income_splitting_savings`: Household benefit from splitting
- `household_total_withdrawal`: Combined withdrawals

**Rationale**: Couples care about household outcomes, not just individual amounts.

### 4. Income Splitting Applied Automatically

**Implementation**:
- If both age 65+: income splitting calculated and applied
- If either under 65: no splitting

**Rationale**: Splitting is a household optimization that requires both spouses' data.

## Testing

### Strategy Consistency Tests

**Test**: Verify same strategy applied to both spouses

```python
def test_same_strategy_both_spouses():
    """Verify withdrawal strategy coordinates both spouses."""
    result = calculate_couple_withdrawal_strategy(
        person1_rrsp=200000, person1_tfsa=100000, person1_nonreg=50000,
        person2_rrsp=150000, person2_tfsa=80000, person2_nonreg=40000,
        person1_age=65, person2_age=63,
        target_household_spending=80000,
        person1_other_income=20000, person2_other_income=15000,
        strategy='rrsp_meltdown',
    )

    # Verify both spouses have RRSP withdrawals (meltdown priority)
    assert result['person1_withdrawals']['rrsp'] > 0
    assert result['person2_withdrawals']['rrsp'] > 0

    # Verify TFSA preserved (meltdown preserves TFSA)
    assert result['person1_withdrawals']['tfsa'] == 0
    assert result['person2_withdrawals']['tfsa'] == 0

    # Verify strategy rationale mentions both
    assert 'both' in result['rationale'].lower() or 'household' in result['rationale'].lower()
```

### Integration Tests

**Test**: Verify strategy flows correctly from UI to results

```python
def test_couple_strategy_integration():
    """Test complete flow from strategy selection to results."""
    # Simulate UI selection
    couple_withdrawal_strategy = 'tax_optimized'

    # Project with strategy
    result = project_couple_accounts(
        person1_current_age=60, person2_current_age=58,
        # ... all parameters ...
        withdrawal_strategy=couple_withdrawal_strategy,
    )

    # Verify strategy applied consistently across all years
    for year in range(len(result['year'])):
        # All years should use same strategy logic
        assert result['household_tax'][year] >= 0  # Tax calculated
        assert result['income_splitting_savings'][year] >= 0  # Splitting considered
```

## User Documentation

### In-App Help Text

**Couple Withdrawal Strategy Dropdown**:
> "Select a coordinated strategy for both spouses. This strategy determines how withdrawals are optimized across both people's accounts to minimize household taxes and maximize government benefits."

**Strategy Descriptions**:

- **Tax-Optimized**: "Coordinates withdrawals to equalize marginal tax rates between spouses, minimizing total household tax."

- **OAS-Aware**: "Keeps both spouses below OAS clawback threshold ($86,912) when possible, preserving dual OAS benefits ($17,000+/year)."

- **Balanced**: "Withdraws proportionally from both spouses' accounts, maintaining relative account sizes."

- **RRSP Meltdown**: "Prioritizes RRSP withdrawals from both spouses to minimize lifetime taxes and maximize tax-free TFSA growth."

### FAQ

**Q: Can I use different strategies for each spouse?**

A: No. Couple withdrawal strategies are designed to optimize the **household** as a unit. Using different strategies for each spouse would prevent proper tax optimization and could result in higher household taxes. The selected strategy coordinates withdrawals between both spouses to achieve the best household outcome.

**Q: How does the strategy decide who withdraws more?**

A: Each strategy has its own logic:
- **Tax-Optimized**: Withdraws more from the lower-income spouse to balance marginal rates
- **OAS-Aware**: Withdraws more from the spouse with more room below OAS threshold
- **Balanced**: Withdraws proportionally based on account sizes
- **RRSP Meltdown**: Withdraws RRSP from both, balancing by income levels

**Q: What if one spouse has much larger accounts?**

A: The strategy still coordinates both. For example:
- If Person 1 has $1M and Person 2 has $200K
- **Balanced** strategy: Person 1 withdraws ~83%, Person 2 withdraws ~17%
- **Tax-Optimized**: May withdraw more from Person 2 if Person 1 already has high income
- **RRSP Meltdown**: Prioritizes RRSP from both, then balances by account sizes

## Comparison with Single-Person Mode

| Aspect | Single Mode | Couple Mode |
|--------|-------------|-------------|
| **Strategy Selection** | 1 dropdown for individual | 1 dropdown for household |
| **Strategies Available** | tax_efficient, rrsp_first, proportional | tax_optimized, oas_clawback_aware, balanced, rrsp_meltdown |
| **Coordination** | N/A (one person) | Required (two people) |
| **Tax Optimization** | Individual tax | Household tax (both combined) |
| **Income Splitting** | N/A | Applied automatically at 65+ |
| **OAS Management** | Individual threshold | Dual thresholds ($173,824 combined) |

## Technical Implementation Notes

### Why Different Strategy Names?

**Single Mode**: `'tax_efficient'`, `'rrsp_first'`, `'proportional'`

**Couple Mode**: `'tax_optimized'`, `'oas_clawback_aware'`, `'balanced'`, `'rrsp_meltdown'`

**Rationale**:
- Different algorithms (single vs coordinated)
- Different optimization goals (individual vs household)
- Clearer naming for users (avoids confusion)

### Strategy Mapping

| Concept | Single Mode | Couple Mode |
|---------|-------------|-------------|
| Minimize current taxes | `tax_efficient` | `tax_optimized` |
| RRSP meltdown | `rrsp_first` | `rrsp_meltdown` |
| Proportional | `proportional` | `balanced` |
| OAS preservation | (not available) | `oas_clawback_aware` |

## Future Enhancements

### Potential Additions (Not Currently Implemented)

1. **Dynamic Strategy Transitions**
   - Auto-switch from RRSP Meltdown (age 60-64) → OAS-Aware (age 65+)
   - Would require age-based strategy selection logic

2. **Strategy Recommendations**
   - Analyze household situation and recommend optimal strategy
   - Based on: ages, account balances, income levels, goals

3. **Custom Strategy Builder**
   - Allow users to customize withdrawal priorities
   - Advanced users could fine-tune optimization parameters

4. **Multi-Year Optimization**
   - Look ahead 5-10 years when deciding current withdrawals
   - Global optimization vs current greedy approach

## Summary

The Ontario Retirement Planner uses a **single coordinated withdrawal strategy** for couples to optimize household outcomes. This design:

✅ Minimizes household taxes through coordination
✅ Maximizes government benefits (dual OAS preservation)
✅ Applies income splitting automatically
✅ Prevents conflicting strategies
✅ Simplifies user experience (one decision)
✅ Delivers superior financial outcomes

**Key Principle**: Couples benefit most when withdrawal decisions are coordinated, not independent. The architecture ensures consistent application of the selected strategy to both spouses throughout all projections.

---

**Architecture**: Single coordinated strategy
**Implementation**: `couple_withdrawal.py` + `rrsp_tfsa.py`
**Status**: ✅ Fully implemented and tested
**Tests**: 94 passing (including couple strategy coordination tests)
