# Ontario Retirement Planner

A comprehensive retirement planning tool for individuals in Ontario, Canada. This application helps you plan your retirement by modeling CPP/OAS benefits, RRSP/TFSA accounts, tax implications, and various withdrawal strategies.

## Features

- **CPP/OAS Projections**: Calculate Canada Pension Plan and Old Age Security benefits based on your profile
- **RRSP/TFSA Modeling**: Track registered account growth and simulate withdrawal strategies
- **Tax Calculations**: Federal and Ontario provincial tax projections, including OAS clawback
- **Monte Carlo Simulation**: Probability-based analysis with market volatility scenarios
- **RRSP Meltdown Strategy**: Optimize RRSP withdrawals to minimize lifetime taxes

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
ontario-retirement-planner/
├── app.py                      # Main Streamlit application
├── src/
│   ├── calculations/
│   │   ├── cpp_oas.py         # CPP/OAS benefit calculations
│   │   ├── rrsp_tfsa.py       # Registered account modeling
│   │   ├── taxes.py           # Tax calculations
│   │   └── monte_carlo.py     # Monte Carlo simulation engine
│   ├── strategies/
│   │   └── rrsp_meltdown.py   # RRSP meltdown strategy optimizer
│   └── utils/
│       └── constants.py        # Canadian tax rates and constants
└── tests/                      # Unit tests
```

## Canadian Tax Rates (2026)

The application uses current federal and Ontario tax rates, CPP/OAS benefit amounts, and contribution limits. These are defined in `src/utils/constants.py` and should be updated annually.

## License

MIT License
