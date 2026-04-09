# Years in Canada Accumulation - Bug Fix Summary

## Issue Identified

The "Years in Canada" parameter was being treated as a **static value** that didn't increase as projections progressed through future years. This caused incorrect OAS benefit calculations for people who haven't yet accumulated 40 years of Canadian residency.

## The Problem

### Incorrect Behavior (Before Fix) ❌

**Scenario**: Person age 50 with 32 years in Canada (lived since age 18)

**User Input**:
- Current Age: 50
- Years in Canada: 32

**What Should Happen**:
- Age 50: 32 years → 80% OAS (32/40)
- Age 55: 37 years → 92.5% OAS (37/40)
- Age 60: 40 years (capped) → 100% OAS (40/40)
- Age 65+: 40 years → 100% OAS

**What Actually Happened** (Bug):
- Age 50: 32 years → 80% OAS ✅
- Age 55: 32 years → 80% OAS ❌ (should be 92.5%)
- Age 60: 32 years → 80% OAS ❌ (should be 100%)
- Age 65+: 32 years → 80% OAS ❌ (should be 100%)

**Impact**: Person received permanently reduced OAS benefits despite living in Canada continuously, losing **20% of OAS** ($143/month or $1,716/year) for their entire retirement.

## The Fix

### Correct Behavior (After Fix) ✅

Years in Canada now **accumulate** during projections, assuming continued Canadian residency:

```python
# Calculate accumulated years at this age
years_accumulated = min(
    years_in_canada + (age - current_age),  # Add years passed
    40  # Cap at 40 (maximum for full OAS)
)
```

**Example Calculation**:
- User enters 32 years (current accumulated)
- At age 55 (5 years later): 32 + 5 = 37 years → 92.5% OAS ✅
- At age 60 (10 years later): 32 + 10 = 42 → cap at 40 → 100% OAS ✅
- At age 65+: Still 40 (capped) → 100% OAS ✅

## Code Changes

### 1. Single-Person Projection (`cpp_oas.py`)

**File**: `src/calculations/cpp_oas.py` (line 168-176)

```python
# Before (Bug):
oas_monthly = calculate_oas_benefit(age, total_income, years_in_canada)

# After (Fixed):
# Accumulate years in Canada (add years passed since current age, capped at 40)
years_accumulated = min(years_in_canada + (age - current_age), 40)
oas_monthly = calculate_oas_benefit(age, total_income, years_accumulated)
```

### 2. Couple Projection (`cpp_oas.py`)

**File**: `src/calculations/cpp_oas.py` (line 270-296)

```python
# Before (Bug):
person1_oas_monthly = calculate_oas_benefit(
    person1_age,
    person1_total_income,
    person1_oas_params.get('years_in_canada', 40),
    person1_oas_params.get('start_age', 65)
)

# After (Fixed):
# Accumulate years in Canada for Person 1
person1_years_accumulated = min(
    person1_oas_params.get('years_in_canada', 40) + (person1_age - person1_current_age),
    40
)
person1_oas_monthly = calculate_oas_benefit(
    person1_age,
    person1_total_income,
    person1_years_accumulated,
    person1_oas_params.get('start_age', 65)
)

# Similar fix for Person 2...
```

### 3. UI Clarification (`app.py`)

**File**: `app.py` (lines 52, 79)

Added help text to clarify that the value represents **current** accumulated years:

```python
years_in_canada = st.number_input(
    "Years in Canada (after age 18)",
    min_value=0,
    max_value=80,
    value=40,
    key="p1_years_canada",
    help="Current accumulated years. Will increase each projection year if you remain in Canada."  # NEW
)
```

### 4. Documentation Updates

**File**: `src/models/household.py`

```python
years_in_canada: int = 40  # Current accumulated years after age 18 (will increase in projections)
```

**File**: `src/calculations/cpp_oas.py`

Updated docstring for `calculate_oas_benefit()`:
```python
Args:
    years_in_canada: Years of residence in Canada after age 18 (accumulated at this age)
```

## Canadian OAS Rules (Context)

### Qualification Requirements

**Full OAS Benefit**:
- Requires **40 years** of Canadian residence after age 18
- Paid at age 65+ (can defer to 70 for higher amount)
- Full amount in 2026: **$718.33/month**

**Partial OAS Benefit**:
- If less than 40 years: **Prorated** by years/40
- Example: 30 years → 30/40 = 75% of full OAS = $538.75/month

**Years Calculation**:
- Count starts at **age 18** (not birth)
- Must be after age 18 and while living in Canada
- Caps at **40 years** (more years don't increase benefit)

### Examples

| Scenario | Age | Years in Canada | OAS Benefit |
|----------|-----|-----------------|-------------|
| Born in Canada, age 60 | 60 | 42 years | 100% OAS at 65 |
| Immigrated age 28, now 50 | 50 | 22 years | 55% OAS at 65 (if leaves) |
| Immigrated age 28, now 50, stays | 50 | 22 → 37 at 65 | 92.5% OAS at 65 |
| Immigrated age 40, now 60 | 60 | 20 years | 50% OAS at 65 (if leaves) |
| Immigrated age 40, now 60, stays | 60 | 20 → 25 at 65 | 62.5% OAS at 65 |

**Key Point**: Years accumulate while living in Canada, which our fix now correctly models!

## Impact Analysis

### Who Benefits from This Fix

✅ **New immigrants** (< 40 years accumulated) who will reach 40 years by retirement

✅ **Mid-career professionals** (age 40-60) who moved to Canada in their 20s-30s

✅ **Younger Canadians** (under age 58) who haven't reached 40 years yet

✅ **Recent permanent residents** planning long-term retirement in Canada

### Who Is Unaffected

⚪ **Long-term residents** who already have 40+ years (already at maximum)

⚪ **Older retirees** (age 65+) who already qualified for OAS (historical years don't change)

### Financial Impact Example

**Case Study**: Immigrant who arrived in Canada at age 28, now age 50 planning to retire at 65

**Before Fix** (Bug):
- Age 50: 22 years in Canada
- Projection assumes: 22 years forever
- OAS benefit at 65: 22/40 = **55% = $395/month**
- Annual OAS loss: $718.33 * 12 * 0.45 = **$3,878/year**
- 30-year retirement loss: **$116,340**

**After Fix** (Correct):
- Age 50: 22 years in Canada
- By age 65: 22 + 15 = 37 years
- OAS benefit at 65: 37/40 = **92.5% = $664/month**
- Much closer to full OAS! Loss only **$654/year**
- 30-year retirement: Saves **$96,720** vs the bug

## Testing

### New Test Suite

**File**: `tests/test_years_in_canada_accumulation.py`

Created comprehensive test suite with **8 test cases**:

1. ✅ `test_years_accumulate_single_person` - Verifies basic accumulation
2. ✅ `test_partial_years_accumulate_correctly` - Verifies exact calculations
3. ✅ `test_years_capped_at_40` - Verifies 40-year cap
4. ✅ `test_already_40_years_stays_100_percent` - Verifies existing full benefits
5. ✅ `test_couple_both_accumulate_years` - Tests both spouses independently
6. ✅ `test_couple_different_accumulation_rates` - Tests different starting points
7. ✅ `test_zero_years_accumulate_from_zero` - Tests new immigrants
8. ✅ `test_very_old_person_with_few_years` - Tests edge cases

**All 8 tests pass**, verifying correct behavior.

### Full Test Suite

**Total Tests**: 94 tests (86 original + 8 new)
**Status**: ✅ **All 94 tests passing**

## User Experience Changes

### What Users Will Notice

**Before** (Bug):
- Users with < 40 years saw **permanently reduced** OAS projections
- No indication that years should accumulate
- Projections pessimistic for immigrants and younger workers

**After** (Fix):
- Users with < 40 years see **progressively increasing** OAS benefits
- Help text clarifies accumulation behavior
- Projections accurate for all residency scenarios

### What Users Should Do

**If you entered your current years in Canada correctly**:
- ✅ No action needed - projections now correct automatically

**If you entered "40" but actually have fewer years**:
- Update to your **actual current years** (e.g., current_age - 18 if born in Canada)
- Example: Age 50, lived since age 18 → Enter **32 years** (not 40)

### UI Help Text (New)

When hovering over "Years in Canada" field:
> "Current accumulated years. Will increase each projection year if you remain in Canada."

This clarifies that:
1. Enter your **current** accumulated years (not projected future years)
2. System will **automatically add** years as projections progress
3. Assumes **continued Canadian residency** throughout retirement

## Assumptions Made

### Implicit Assumptions in Fix

1. **Continued Residency**: Assumes person stays in Canada through retirement
   - Reasonable for retirement planning tool
   - Most retirement plans assume staying in country

2. **No Partial Years**: Accumulates in whole years
   - Matches CRA's annual assessment model
   - Simplifies calculation without loss of accuracy

3. **40-Year Cap**: Enforces maximum accumulation
   - Matches Canadian OAS rules exactly
   - Additional years beyond 40 don't increase benefits

### What This Fix Does NOT Handle

❌ **Temporary Absences**: Doesn't model leaving Canada temporarily
   - Assumption: Continuous residency during retirement planning

❌ **Historical Gaps**: Doesn't account for past gaps in residency
   - User should enter accurate current accumulated years

❌ **Provincial Variations**: OAS is federal, same across provinces
   - No provincial-specific handling needed

## Migration Notes

### For Existing Users

**Data Migration**: Not required
- Years in Canada is user input (not stored data)
- Users will see correct results on next app launch

**Recalculation**: Automatic
- Projections recalculate with correct accumulation immediately
- No manual intervention needed

### For Developers

**API Changes**: None
- Function signatures unchanged
- Internal calculation improved, external interface same

**Backward Compatibility**: Maintained
- Existing code calling these functions works unchanged
- Tests updated to verify new behavior

## References

### Canadian Government Sources

1. **OAS Eligibility**: [Service Canada - OAS](https://www.canada.ca/en/services/benefits/publicpensions/cpp/old-age-security.html)
2. **Residency Requirements**: [CRA - OAS Residence Requirements](https://www.canada.ca/en/services/benefits/publicpensions/cpp/old-age-security/benefit-amount.html)
3. **Pro-Rated Benefits**: [Service Canada - Partial OAS](https://www.canada.ca/en/services/benefits/publicpensions/cpp/old-age-security/benefit-amount.html#h2.1)

### Key Rules Implemented

✅ 40 years required for full OAS
✅ Prorated for fewer years (years/40 × full amount)
✅ Count starts at age 18
✅ Maximum 40 years count (additional years don't increase benefit)
✅ Years accumulate while living in Canada

## Conclusion

This fix ensures the Ontario Retirement Planner correctly models OAS benefit accumulation for all users, particularly benefiting **immigrants** and **younger Canadians** who haven't yet reached 40 years of residency.

The fix:
- ✅ Aligns with Canadian OAS rules
- ✅ Provides accurate projections
- ✅ Improves financial planning for immigrants
- ✅ Maintains backward compatibility
- ✅ Fully tested (94 tests passing)

**Financial Impact**: Users with partial years will see **significantly higher** OAS projections (up to $96,720 more over 30-year retirement for someone with 22 current years reaching 37 by retirement).

---

**Fix Date**: 2026-03-11
**Issue Type**: Calculation Bug
**Severity**: High (affects OAS accuracy for partial-year residents)
**Status**: ✅ Fixed and Tested
