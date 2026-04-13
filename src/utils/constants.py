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

# Provincial Tax Brackets (2026)
PROVINCIAL_TAX_BRACKETS = {
    'Ontario': [
        (51446, 0.0505),    # 5.05% on first $51,446
        (102894, 0.0915),   # 9.15% on next $51,448
        (150000, 0.1116),   # 11.16% on next $47,106
        (220000, 0.1216),   # 12.16% on next $70,000
        (float('inf'), 0.1316)  # 13.16% on income over $220,000
    ],
    'British Columbia': [
        (47937, 0.0506),    # 5.06% on first $47,937
        (95875, 0.0770),    # 7.70% on next $47,938
        (110076, 0.1050),   # 10.50% on next $14,201
        (133664, 0.1229),   # 12.29% on next $23,588
        (181232, 0.1470),   # 14.70% on next $47,568
        (252752, 0.1680),   # 16.80% on next $71,520
        (float('inf'), 0.2050)  # 20.50% on income over $252,752
    ],
    'Alberta': [
        (148269, 0.10),     # 10% on first $148,269
        (177922, 0.12),     # 12% on next $29,653
        (237230, 0.13),     # 13% on next $59,308
        (355845, 0.14),     # 14% on next $118,615
        (float('inf'), 0.15)  # 15% on income over $355,845
    ],
    'Saskatchewan': [
        (52057, 0.1050),    # 10.50% on first $52,057
        (148734, 0.1250),   # 12.50% on next $96,677
        (float('inf'), 0.1450)  # 14.50% on income over $148,734
    ],
    'Manitoba': [
        (47000, 0.1080),    # 10.80% on first $47,000
        (100000, 0.1275),   # 12.75% on next $53,000
        (float('inf'), 0.1740)  # 17.40% on income over $100,000
    ],
    'Quebec': [
        (51780, 0.14),      # 14% on first $51,780
        (103545, 0.19),     # 19% on next $51,765
        (126000, 0.24),     # 24% on next $22,455
        (float('inf'), 0.2575)  # 25.75% on income over $126,000
    ],
    'New Brunswick': [
        (49958, 0.0968),    # 9.68% on first $49,958
        (99916, 0.1482),    # 14.82% on next $49,958
        (185064, 0.1652),   # 16.52% on next $85,148
        (float('inf'), 0.1784)  # 17.84% on income over $185,064
    ],
    'Nova Scotia': [
        (29590, 0.0879),    # 8.79% on first $29,590
        (59180, 0.1495),    # 14.95% on next $29,590
        (93000, 0.1667),    # 16.67% on next $33,820
        (150000, 0.1750),   # 17.50% on next $57,000
        (float('inf'), 0.21)  # 21% on income over $150,000
    ],
    'Prince Edward Island': [
        (32656, 0.0980),    # 9.80% on first $32,656
        (64313, 0.1380),    # 13.80% on next $31,657
        (105000, 0.1670),   # 16.70% on next $40,687
        (float('inf'), 0.1870)  # 18.70% on income over $105,000
    ],
    'Newfoundland and Labrador': [
        (43198, 0.0870),    # 8.70% on first $43,198
        (86395, 0.1450),    # 14.50% on next $43,197
        (154244, 0.1580),   # 15.80% on next $67,849
        (215943, 0.1730),   # 17.30% on next $61,699
        (float('inf'), 0.2130)  # 21.30% on income over $215,943
    ],
}

# For backward compatibility
ONTARIO_TAX_BRACKETS = PROVINCIAL_TAX_BRACKETS['Ontario']

# Federal Basic Personal Amount (2026)
FEDERAL_BASIC_PERSONAL_AMOUNT = 15705

# Provincial Basic Personal Amount (2026)
PROVINCIAL_BASIC_PERSONAL_AMOUNT = {
    'Ontario': 11865,
    'British Columbia': 12580,
    'Alberta': 21885,
    'Saskatchewan': 17661,
    'Manitoba': 15780,
    'Quebec': 18056,
    'New Brunswick': 13044,
    'Nova Scotia': 8481,
    'Prince Edward Island': 13500,
    'Newfoundland and Labrador': 10382,
}

# For backward compatibility
ONTARIO_BASIC_PERSONAL_AMOUNT = PROVINCIAL_BASIC_PERSONAL_AMOUNT['Ontario']

# Provincial Age Amount (2026) - for seniors 65+
PROVINCIAL_AGE_AMOUNT = {
    'Ontario': 5537,
    'British Columbia': 5140,
    'Alberta': 5649,
    'Saskatchewan': 5463,
    'Manitoba': 4740,
    'Quebec': 3308,
    'New Brunswick': 5514,
    'Nova Scotia': 5377,
    'Prince Edward Island': 4544,
    'Newfoundland and Labrador': 5077,
}

# Provincial Pension Income Amount (2026)
PROVINCIAL_PENSION_INCOME_AMOUNT = {
    'Ontario': 1605,
    'British Columbia': 1000,
    'Alberta': 1425,
    'Saskatchewan': 1000,
    'Manitoba': 1000,
    'Quebec': 2975,
    'New Brunswick': 1000,
    'Nova Scotia': 1365,
    'Prince Edward Island': 1000,
    'Newfoundland and Labrador': 1000,
}

# Default province
DEFAULT_PROVINCE = 'Ontario'

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
