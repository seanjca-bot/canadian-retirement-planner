# Canadian Retirement Planner

A comprehensive retirement planning tool for Canadian residents across all provinces. This application helps you plan your retirement by modeling CPP/OAS benefits, RRSP/TFSA accounts, tax implications across different provinces, and various withdrawal strategies.

## Features

- **CPP/OAS Projections**: Calculate Canada Pension Plan and Old Age Security benefits based on your profile
- **RRSP/TFSA Modeling**: Track registered account growth and simulate withdrawal strategies
- **Multi-Province Tax Calculations**: Federal and provincial tax projections for all Canadian provinces, including OAS clawback
- **Monte Carlo Simulation**: Probability-based analysis with market volatility scenarios
- **RRSP Meltdown Strategy**: Optimize RRSP withdrawals to minimize lifetime taxes
- **Province Selection**: Choose your province for accurate tax calculations (ON, BC, AB, SK, MB, QC, NB, NS, PE, NL)

## Installation

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the Streamlit app:
```bash
streamlit run app.py
```

The app will open in your default browser at http://localhost:8501

## Project Structure

```
canadian-retirement-planner/
├── app.py                      # Main Streamlit application
├── src/
│   ├── calculations/
│   │   ├── cpp_oas.py         # CPP/OAS benefit calculations
│   │   ├── rrsp_tfsa.py       # Registered account modeling
│   │   ├── taxes.py           # Federal and provincial tax calculations
│   │   └── monte_carlo.py     # Monte Carlo simulation engine
│   ├── strategies/
│   │   ├── rrsp_meltdown.py   # RRSP meltdown strategy optimizer
│   │   ├── couple_withdrawal.py   # Couple withdrawal strategies
│   │   └── survivor_scenarios.py   # Survivor scenario analysis
│   ├── models/
│   │   └── household.py        # Household modeling
│   └── utils/
│       └── constants.py        # Canadian federal and provincial tax rates
└── tests/                      # Unit tests
```

## Canadian Tax Rates (2026)

The application uses current federal and provincial tax rates for all Canadian provinces, CPP/OAS benefit amounts, and contribution limits. These are defined in `src/utils/constants.py` and should be updated annually.

**Supported Provinces:**
- Ontario (ON)
- British Columbia (BC)
- Alberta (AB)
- Saskatchewan (SK)
- Manitoba (MB)
- Quebec (QC)
- New Brunswick (NB)
- Nova Scotia (NS)
- Prince Edward Island (PE)
- Newfoundland and Labrador (NL)

## Feedback & Feature Requests

We'd love to hear from you! If you have feedback, suggestions, or feature requests, please contact us at:

📧 **canadianretireplan@gmail.com**

Your input helps us improve the Canadian Retirement Planner for all users.

## License

MIT License
