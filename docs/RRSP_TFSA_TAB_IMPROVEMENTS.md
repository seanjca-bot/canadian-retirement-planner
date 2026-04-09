# RRSP/TFSA Tab Improvements - Couple Mode Support

## Issue Identified

The RRSP/TFSA tab (Tab 3) only displayed **single-person** withdrawal strategy comparisons and had **no couple-mode specific content**. This meant that in couple mode, users either saw incorrect single-person visualizations or encountered errors.

## The Problem

### Before Fix ❌

**Couple Mode RRSP/TFSA Tab**:
- Showed single-person strategy comparisons (Tax-Efficient, RRSP First, Proportional)
- Used `current_age`, `rrsp_balance`, `tfsa_balance` variables that don't exist in couple mode
- No visibility into individual spouse account balances
- No explanation of how the selected couple withdrawal strategy affects each person
- Misleading or broken visualizations

**Result**: Users in couple mode couldn't see how the withdrawal strategy affected each spouse's accounts.

## The Solution

### After Fix ✅

**Couple Mode RRSP/TFSA Tab** (New):
- Shows selected couple withdrawal strategy name
- Displays all 6 accounts (Person 1 RRSP/TFSA/NonReg + Person 2 RRSP/TFSA/NonReg)
- Visualizes account balance projections for both spouses
- Shows final balances for each spouse at age 95
- Displays annual withdrawal breakdown by spouse and account type
- Explains the selected strategy's coordination logic
- Includes RRIF minimum withdrawal table with explanation

**Single Mode RRSP/TFSA Tab** (Unchanged):
- Still shows 3-strategy comparison (Tax-Efficient, RRSP First, Proportional)
- Maintains existing functionality

## Implementation

### Code Changes

**File**: `app.py` (lines 566-880)

**Structure**:
```python
# Tab 3: All Account Withdrawal Strategies
with tab3:
    if is_couple_mode:
        # NEW: Couple-specific content
        st.header("Couple Account Balances & Withdrawal Strategy")

        # 1. Show selected strategy name
        # 2. Household account projections chart (all 6 accounts)
        # 3. Final balances for both spouses
        # 4. Annual withdrawal breakdown
        # 5. Strategy explanation
        # 6. RRIF table

    else:
        # EXISTING: Single-person content
        st.header("Withdrawal Strategies (RRSP/TFSA/Non-Registered)")

        # 1. Three-strategy comparison
        # 2. Selected strategy details
        # 3. Withdrawal breakdown
        # 4. RRIF table
```

### New Couple Mode Features

#### 1. Selected Strategy Display

```python
st.markdown(f"""
**Selected Strategy**: {couple_withdrawal_strategy.replace('_', ' ').title()}

This shows how your selected withdrawal strategy affects both spouses' account balances over time.
""")
```

Shows: "Tax Optimized", "Oas Clawback Aware", "Balanced", or "Rrsp Meltdown"

#### 2. Household Account Projections Chart

**Visual**: Stacked area chart showing all 6 accounts over time

**Person 1 Accounts** (darker colors):
- 🔵 RRSP (blue, 0.7 opacity)
- 🔴 TFSA (red/orange, 0.7 opacity)
- 🟢 Non-Reg (green, 0.7 opacity)

**Person 2 Accounts** (lighter colors):
- 🔵 RRSP (blue, 0.4 opacity)
- 🔴 TFSA (red/orange, 0.4 opacity)
- 🟢 Non-Reg (green, 0.4 opacity)

**Benefits**:
- See both spouses' accounts in one view
- Identify which accounts deplete faster
- Understand household asset allocation over time
- Visualize strategy impact on each person

#### 3. Final Balances Side-by-Side

```
👤 Person 1 Final Balances (Age 95)    👤 Person 2 Final Balances (Age 95)
RRSP:     $X                            RRSP:     $Y
TFSA:     $X                            TFSA:     $Y
Non-Reg:  $X                            Non-Reg:  $Y
Total:    $X                            Total:    $Y
```

**Benefits**:
- Compare final outcomes for each spouse
- Identify estate planning implications
- See which accounts preserved vs depleted

#### 4. Annual Withdrawal Breakdown Chart

**Visual**: Stacked bar chart showing withdrawals by account type and spouse

**Shows**:
- Person 1: RRSP withdrawals (dark blue)
- Person 1: TFSA withdrawals (dark orange)
- Person 1: Non-Reg withdrawals (dark green)
- Person 2: RRSP withdrawals (light blue)
- Person 2: TFSA withdrawals (light orange)
- Person 2: Non-Reg withdrawals (light green)

**Benefits**:
- See who withdraws more each year
- Understand strategy's account prioritization
- Identify coordination between spouses
- Visualize RRSP meltdown vs preservation strategies

#### 5. Strategy Explanations

**Each strategy has a detailed explanation**:

**Tax-Optimized**:
> Minimizes household tax by coordinating withdrawals to equalize marginal tax rates between spouses. Withdraws more from the lower-income spouse to keep both in lower tax brackets.

**OAS-Clawback-Aware**:
> Keeps both spouses below the OAS clawback threshold ($86,912) when possible to preserve dual OAS benefits. Prioritizes TFSA withdrawals (don't affect OAS) and balances taxable withdrawals between spouses.

**Balanced**:
> Withdraws proportionally from both spouses' accounts based on their relative account sizes. Maintains the ratio of assets between spouses throughout retirement.

**RRSP Meltdown**:
> Prioritizes RRSP withdrawals from both spouses to minimize lifetime taxes. Depletes RRSPs early (before mandatory RRIF withdrawals), preserves TFSAs for tax-free growth, and balances withdrawals by income levels to minimize household tax.

#### 6. RRIF Information

**Includes**:
- RRIF minimum withdrawal rate table (age 65-95)
- Explanation of RRSP-to-RRIF conversion at age 72
- Note about how RRSP Meltdown reduces mandatory withdrawals

## User Experience Improvements

### What Users See Now

**Couple Mode**:
1. Navigate to "💼 RRSP/TFSA" tab
2. See header: "Couple Account Balances & Withdrawal Strategy"
3. View selected strategy name (e.g., "RRSP Meltdown")
4. See combined chart with all 6 accounts
5. Compare final balances for both spouses
6. Analyze withdrawal patterns for each person
7. Read strategy explanation
8. Reference RRIF table

**Single Mode** (unchanged):
1. Navigate to "💼 RRSP/TFSA" tab
2. See header: "Withdrawal Strategies (RRSP/TFSA/Non-Registered)"
3. View 3-strategy comparison charts
4. See selected strategy highlighted
5. View withdrawal breakdown
6. Reference RRIF table

### Key Improvements

✅ **Couple visibility**: See both spouses' accounts clearly
✅ **Strategy clarity**: Understand how selected strategy affects each person
✅ **Coordination insight**: Visualize how withdrawals coordinate between spouses
✅ **Account prioritization**: See which accounts depleted first
✅ **Final outcomes**: Compare estate outcomes for each spouse
✅ **Educational**: Strategy explanations help users understand coordination logic

## Visualizations

### Chart 1: Household Account Projections

**Type**: Stacked area chart with 2 stackgroups

**Data**:
- X-axis: Person 1 Age (55 to 95)
- Y-axis: Balance ($)
- Stack 1: Person 1's 3 accounts (darker colors)
- Stack 2: Person 2's 3 accounts (lighter colors)

**Insights**:
- Total household portfolio trajectory
- Relative sizes of each account type
- Which accounts deplete vs grow
- Age at which accounts run out (if applicable)

**Example**: RRSP Meltdown strategy shows:
- RRSPs (both spouses) deplete early
- TFSAs (both spouses) preserved longer
- Non-Reg used as middle priority

### Chart 2: Annual Withdrawal Breakdown

**Type**: Stacked bar chart

**Data**:
- X-axis: Person 1 Age (year by year)
- Y-axis: Withdrawal amount ($)
- Bars: 6 account types (3 per spouse) stacked

**Insights**:
- Who withdraws more each year
- Which accounts used each year
- Withdrawal patterns over time
- RRIF minimum impact (age 72+)

**Example**: Tax-Optimized strategy shows:
- Balanced withdrawals between spouses
- Person with lower income withdraws more
- TFSA used first (both spouses)
- RRSP used strategically to balance rates

## Technical Details

### Conditional Rendering

```python
with tab3:
    if is_couple_mode:
        # Use couple_projection data
        # Show 6 accounts (person1_*, person2_*)
        # Use couple_withdrawal_strategy
    else:
        # Use account_projection data (single person)
        # Show 3 accounts (rrsp, tfsa, nonreg)
        # Use withdrawal_strategy
```

### Data Sources

**Couple Mode**:
- `couple_projection` dictionary with keys:
  - `person1_age`, `person2_age`
  - `person1_rrsp_balance`, `person1_tfsa_balance`, `person1_nonreg_balance`
  - `person2_rrsp_balance`, `person2_tfsa_balance`, `person2_nonreg_balance`
  - `person1_rrsp_withdrawal`, `person1_tfsa_withdrawal`, `person1_nonreg_withdrawal`
  - `person2_rrsp_withdrawal`, `person2_tfsa_withdrawal`, `person2_nonreg_withdrawal`
  - `person1_total_balance`, `person2_total_balance`

**Single Mode**:
- `tax_efficient`, `rrsp_first`, `proportional` dictionaries with keys:
  - `age`
  - `rrsp_balance`, `tfsa_balance`, `nonreg_balance`
  - `rrsp_withdrawal`, `tfsa_withdrawal`, `nonreg_withdrawal`
  - `total_balance`

### Color Scheme

**Person 1** (darker, 0.7-0.8 opacity):
- RRSP: `rgba(99, 110, 250, 0.7)` (blue)
- TFSA: `rgba(239, 85, 59, 0.7)` (orange)
- Non-Reg: `rgba(0, 204, 150, 0.7)` (green)

**Person 2** (lighter, 0.4 opacity):
- RRSP: `rgba(99, 110, 250, 0.4)` (light blue)
- TFSA: `rgba(239, 85, 59, 0.4)` (light orange)
- Non-Reg: `rgba(0, 204, 150, 0.4)` (light green)

**Rationale**: Opacity difference clearly distinguishes spouses while maintaining color consistency by account type.

## Comparison: Before vs After

| Aspect | Before (Bug) | After (Fixed) |
|--------|-------------|---------------|
| **Couple Mode Display** | Single-person content (wrong) | Couple-specific content |
| **Account Visibility** | 3 accounts only | 6 accounts (both spouses) |
| **Strategy Shown** | 3 single strategies comparison | Selected couple strategy |
| **Spouse Breakdown** | None | Side-by-side metrics |
| **Withdrawals** | N/A | Both spouses' withdrawals |
| **Coordination** | Not visible | Clearly visualized |
| **Strategy Explanation** | Generic | Coordination-focused |
| **Charts** | Single person | Household with both spouses |

## Benefits by User Type

### For Couples with Similar Accounts

**Scenario**: Both spouses have ~$500K in retirement accounts

**Benefits**:
- See how withdrawals balance between equal partners
- Verify both stay below OAS threshold
- Confirm proportional depletion (Balanced strategy)
- Compare final balances for estate equality

### For Couples with Imbalanced Accounts

**Scenario**: Person 1 has $1M, Person 2 has $300K

**Benefits**:
- See how Tax-Optimized withdraws more from higher-balance spouse
- Understand why lower-income spouse might withdraw more (tax optimization)
- Visualize RRSP Meltdown depleting Person 1's large RRSP first
- Plan for survivor scenario (Person 2's accounts preserved)

### For Couples with Age Differences

**Scenario**: Person 1 age 65, Person 2 age 60

**Benefits**:
- See staggered retirement impact on withdrawals
- Understand OAS timing differences (Person 2 waits 5 more years)
- Visualize strategy adjusting to age gap
- Plan for Person 2's longer life expectancy

### For High-Net-Worth Couples

**Scenario**: $2M+ combined retirement accounts

**Benefits**:
- See RRSP Meltdown dramatically reduce RRSP balances early
- Understand OAS clawback risk management (keep both below $86,912)
- Visualize tax minimization through coordination
- Plan legacy (TFSAs preserved = $500K+ tax-free inheritance)

## Future Enhancements

### Potential Additions (Not Currently Implemented)

1. **Strategy Comparison for Couples**
   - Show 4 side-by-side charts (one per couple strategy)
   - Compare final balances across strategies
   - Highlight recommended strategy based on situation

2. **Interactive Strategy Selection**
   - Toggle between strategies in the chart
   - See real-time impact on projections
   - Compare total lifetime taxes

3. **Withdrawal Heatmap**
   - Color-coded year-by-year withdrawals
   - Red = high withdrawal, Green = low withdrawal
   - Identify peak withdrawal years

4. **Account Depletion Timeline**
   - Show age at which each account depletes (if applicable)
   - Flag years with insufficient funds
   - Suggest spending adjustments

5. **Tax Visualization**
   - Show annual tax paid by each spouse
   - Visualize marginal rate balancing
   - Highlight income splitting savings

## Testing

**Manual Testing Checklist**:

✅ Couple mode displays couple-specific content (not single-person)
✅ All 6 accounts shown in chart (Person 1 + Person 2)
✅ Selected strategy name displayed correctly
✅ Final balances shown for both spouses
✅ Withdrawal breakdown shows both spouses
✅ Strategy explanation matches selected strategy
✅ Charts render without errors
✅ RRIF table displays correctly

**Single Mode Regression Testing**:

✅ Single mode still shows 3-strategy comparison
✅ Selected strategy highlighted correctly
✅ Withdrawal breakdown shows correctly
✅ No errors or broken charts

**Automated Testing**:

✅ All 94 tests pass (no regressions)
✅ No Python syntax errors
✅ App compiles successfully

## Summary

The RRSP/TFSA tab now properly supports **couple mode** with:

✅ Dedicated couple-specific visualizations
✅ Visibility into both spouses' accounts
✅ Withdrawal coordination insights
✅ Strategy-specific explanations
✅ Side-by-side final balance comparisons
✅ Clear account depletion patterns

**Impact**: Users in couple mode can now fully understand how their selected withdrawal strategy coordinates withdrawals between both spouses to optimize household outcomes. This was a critical missing feature that is now fully implemented and tested.

---

**Implementation Date**: 2026-03-11
**Lines Modified**: ~200 lines in app.py (Tab 3 section)
**New Features**: 6 (charts, metrics, explanations)
**Tests**: ✅ 94/94 passing
**Status**: Production Ready
