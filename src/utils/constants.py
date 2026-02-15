"""
Canadian and Ontario-specific constants for retirement planning (2026 tax year).
These values should be updated annually based on CRA and Service Canada announcements.
"""

# CPP Constants (2026)
CPP_MAX_MONTHLY_2026 = 1364.60  # Maximum CPP at age 65
CPP_YMPE_2026 = 68500  # Year's Maximum Pensionable Earnings
CPP_BASIC_EXEMPTION = 3500
CPP_CONTRIBUTION_RATE = 0.0595  # Employee rate
CPP_EARLY_PENALTY_PER_MONTH = 0.006  # 0.6% per month before 65
CPP_LATE_BONUS_PER_MONTH = 0.007  # 0.7% per month after 65
CPP_MIN_AGE = 60
CPP_STANDARD_AGE = 65
CPP_MAX_AGE = 70

# OAS Constants (2026)
OAS_MAX_MONTHLY_2026 = 718.33  # Maximum OAS at age 65
OAS_AGE_75_INCREASE = 1.10  # 10% increase at age 75
OAS_MIN_AGE = 65
OAS_CLAWBACK_THRESHOLD = 86912  # Income threshold for clawback
OAS_CLAWBACK_RATE = 0.15  # 15% clawback rate
OAS_CLAWBACK_ELIMINATION = 142609  # Income at which OAS is fully clawed back

# RRSP/RRIF Constants (2026)
RRSP_CONTRIBUTION_LIMIT_2026 = 31560
RRSP_CONTRIBUTION_RATE = 0.18  # 18% of previous year's income
RRIF_CONVERSION_AGE = 71  # Must convert by end of year you turn 71
RRIF_MIN_WITHDRAWAL_RATES = {
    # Age: Minimum withdrawal percentage
    65: 0.0400,
    66: 0.0417,
    67: 0.0435,
    68: 0.0455,
    69: 0.0476,
    70: 0.0500,
    71: 0.0528,
    72: 0.0540,
    73: 0.0553,
    74: 0.0567,
    75: 0.0582,
    76: 0.0598,
    77: 0.0617,
    78: 0.0636,
    79: 0.0658,
    80: 0.0682,
    81: 0.0708,
    82: 0.0738,
    83: 0.0771,
    84: 0.0808,
    85: 0.0851,
    86: 0.0899,
    87: 0.0955,
    88: 0.1021,
    89: 0.1099,
    90: 0.1192,
    91: 0.1306,
    92: 0.1449,
    93: 0.1634,
    94: 0.1879,
    95: 0.2000,  # 20% for 95+
}

# TFSA Constants (2026)
TFSA_ANNUAL_LIMIT_2026 = 7000
TFSA_CUMULATIVE_LIMIT_2026 = 102000  # Total contribution room since 2009

# Federal Tax Brackets (2026)
FEDERAL_TAX_BRACKETS = [
    (55867, 0.15),      # 15% on first $55,867
    (111733, 0.205),    # 20.5% on next $55,866
    (173205, 0.26),     # 26% on next $61,472
    (246752, 0.29),     # 29% on next $73,547
    (float('inf'), 0.33)  # 33% on income over $246,752
]

# Ontario Tax Brackets (2026)
ONTARIO_TAX_BRACKETS = [
    (51446, 0.0505),    # 5.05% on first $51,446
    (102894, 0.0915),   # 9.15% on next $51,448
    (150000, 0.1116),   # 11.16% on next $47,106
    (220000, 0.1216),   # 12.16% on next $70,000
    (float('inf'), 0.1316)  # 13.16% on income over $220,000
]

# Federal Basic Personal Amount (2026)
FEDERAL_BASIC_PERSONAL_AMOUNT = 15705

# Ontario Basic Personal Amount (2026)
ONTARIO_BASIC_PERSONAL_AMOUNT = 11865

# Age Amount Tax Credit (Federal)
AGE_AMOUNT_CREDIT = 8396  # For seniors 65+
AGE_AMOUNT_THRESHOLD = 42335  # Income threshold for reduction
AGE_AMOUNT_REDUCTION_RATE = 0.15  # 15% reduction rate

# Pension Income Amount (Federal)
PENSION_INCOME_AMOUNT = 2000  # Eligible pension income credit

# Non-Registered Account Tax Treatment
CAPITAL_GAINS_INCLUSION_RATE = 0.50  # 50% of capital gains are taxable
DIVIDEND_GROSS_UP_RATE = 1.38  # Eligible dividend gross-up
DIVIDEND_TAX_CREDIT_FEDERAL = 0.150198  # Federal dividend tax credit rate
DIVIDEND_TAX_CREDIT_ONTARIO = 0.10  # Ontario dividend tax credit rate

# Investment Return Assumptions
EXPECTED_RETURN_MEAN = 0.06  # 6% average annual return
EXPECTED_RETURN_STD_DEV = 0.12  # 12% standard deviation
INFLATION_RATE = 0.02  # 2% average inflation

# Life Expectancy
LIFE_EXPECTANCY_MALE = 82
LIFE_EXPECTANCY_FEMALE = 86
LIFE_EXPECTANCY_PLANNING = 95  # Conservative planning age
