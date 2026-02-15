# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ontario Retirement Planner is a comprehensive financial planning tool for retirement planning in Ontario, Canada. It's a Python-based Streamlit web application that models:
- CPP (Canada Pension Plan) and OAS (Old Age Security) benefits
- RRSP/TFSA account growth and withdrawal strategies
- Federal and Ontario tax calculations with senior credits
- Monte Carlo simulations for retirement success probability
- RRSP meltdown strategy optimization to minimize lifetime taxes

## Commands

### Running the Application
```bash
streamlit run app.py
```
The app will be available at http://localhost:8501

### Development Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running Tests
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_calculations.py

# Run with coverage
pytest --cov=src tests/
```

### Code Quality
```bash
# Format code
black src/ tests/ app.py

# Type checking
mypy src/

# Linting
pylint src/
```

## Architecture

### Core Calculation Modules (`src/calculations/`)

**cpp_oas.py**: CPP and OAS benefit calculations
- `calculate_cpp_benefit()`: Calculates CPP based on start age (60-70), contribution years, and earnings ratio
- `calculate_oas_benefit()`: Calculates OAS with clawback based on income and residency
- Key consideration: OAS clawback starts at $86,912 income (2026), eliminated at $142,609

**rrsp_tfsa.py**: Registered account modeling
- `RRSPAccount` and `TFSAAccount` classes track balances over time
- Automatic RRSP-to-RRIF conversion at age 71
- RRIF minimum withdrawal rates from government table
- `project_registered_accounts()`: Simulates accounts with different withdrawal strategies

**taxes.py**: Federal and Ontario tax calculations
- Progressive tax brackets for both jurisdictions
- Senior-specific credits: Basic Personal Amount, Age Amount, Pension Income Amount
- Age Amount credit phases out starting at $42,335 income
- `calculate_total_tax()`: Combined federal + provincial tax with all credits

**monte_carlo.py**: Probability-based retirement analysis
- Generates return scenarios using normal distribution (mean 6%, std dev 12%)
- `run_monte_carlo_simulation()`: Tests portfolio sustainability over thousands of scenarios
- `calculate_safe_withdrawal_rate()`: Binary search for withdrawal rate with target success probability

### Strategy Modules (`src/strategies/`)

**rrsp_meltdown.py**: RRSP meltdown strategy optimizer
- Strategy: Withdraw RRSP before age 65 to stay below OAS clawback threshold
- Compares lifetime taxes and OAS benefits between strategies
- Key insight: Strategic early withdrawals can save $50,000+ in lifetime taxes for high-income retirees

### Constants (`src/utils/constants.py`)

All Canadian tax rates, benefit amounts, and contribution limits for 2026:
- Federal/Ontario tax brackets
- CPP maximum ($1,364.60/month at 65)
- OAS maximum ($718.33/month at 65, +10% at 75)
- RRSP/TFSA limits
- RRIF minimum withdrawal rates table

**Important**: Update these values annually when CRA releases new tax year information.

## Key Architectural Decisions

### Separation of Calculations and UI
All financial calculations are in `src/` modules, completely independent of Streamlit. This allows:
- Unit testing of calculations without UI
- Potential future use in CLI, API, or other interfaces
- Clear separation of concerns

### Strategy Pattern for Withdrawals
RRSP/TFSA projection supports multiple withdrawal strategies:
- `'minimum'`: RRIF minimum withdrawals only
- `'fixed'`: Fixed dollar amount (inflation-adjusted)
- `'percentage'`: Percentage of portfolio (e.g., 4% rule)

New strategies can be added by extending the `withdrawal_strategy` parameter logic.

### OAS Clawback as Central Concern
The RRSP meltdown strategy is built around the OAS clawback threshold ($86,912 in 2026). This is a critical optimization point because:
1. OAS clawback is 15% on income above threshold
2. Combined with marginal tax rate, effective rate can exceed 50%
3. Strategic RRSP withdrawals before 65 can preserve OAS benefits

### Monte Carlo Return Generation
Uses normal distribution for returns, which is a simplification. Real markets have:
- Fat tails (more extreme events)
- Serial correlation (momentum/mean reversion)
- This is suitable for planning purposes but should be disclosed to users

## Development Guidelines

### Adding New Tax Years
When updating for a new tax year:
1. Update `src/utils/constants.py` with new rates
2. Update references to tax year in comments and documentation
3. Test edge cases: OAS clawback threshold, RRIF rates

### Adding New Features
For new calculation features:
1. Add calculation logic to appropriate `src/calculations/` module
2. Write unit tests in `tests/`
3. Add UI in new tab or section in `app.py`
4. Update README.md with feature description

### Tax Calculation Accuracy
Tax calculations include:
- Progressive brackets (federal + Ontario)
- Basic Personal Amount credit
- Age Amount credit (65+, income-tested)
- Pension Income Amount credit ($2,000 federal, $1,605 Ontario)

Missing features to consider adding:
- Dividend tax credit
- Capital gains (50% inclusion rate)
- Spousal income splitting
- GIS (Guaranteed Income Supplement) for low-income seniors

### Performance Considerations
Monte Carlo simulations are computationally intensive:
- Default to 1,000 simulations (reasonable for web app)
- Allow user to adjust (100-5,000)
- Consider caching results for same inputs
- For production, consider running simulations async/background

## Common Development Tasks

### Adding a New Withdrawal Strategy
1. Add strategy logic in `project_registered_accounts()` in `rrsp_tfsa.py`
2. Add to strategy comparison in app.py Tab 3
3. Document strategy rationale and use cases

### Updating CPP/OAS Rates
Government announces rates in October-November for next year:
1. Update constants in `constants.py`
2. Check for formula changes (rare but happens)
3. Test with edge cases (maximum benefits, clawback thresholds)

### Adding Charts/Visualizations
Use Plotly for interactive charts (already imported in app.py):
- `plotly.graph_objects` for custom charts
- `plotly.express` for quick standard charts
- Keep consistent color scheme across tabs
