"""
Canadian Retirement Planner - Streamlit Application

A comprehensive retirement planning tool for Canadian residents across all provinces.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

from src.calculations.cpp_oas import calculate_cpp_benefit, calculate_oas_benefit, project_cpp_oas_income, project_couple_cpp_oas_income
from src.calculations.rrsp_tfsa import project_registered_accounts, project_all_accounts, calculate_rrif_minimum_table, project_couple_accounts
from src.calculations.taxes import calculate_total_tax, project_lifetime_taxes, calculate_household_tax
from src.calculations.monte_carlo import run_monte_carlo_simulation, calculate_safe_withdrawal_rate, compare_strategies
from src.strategies.rrsp_meltdown import compare_meltdown_vs_traditional, simulate_meltdown_strategy
from src.strategies.survivor_scenarios import project_survivor_scenario, analyze_survivor_scenarios
from src.models.household import Person, Household

# Page configuration
st.set_page_config(
    page_title="Canadian Retirement Planner",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title
st.title("🏦 Canadian Retirement Planner")
st.markdown("Plan your retirement with CPP/OAS projections, provincial tax optimization, and Monte Carlo simulations")

# Sidebar - User Inputs
st.sidebar.header("Your Information")

# Province Selection
province = st.sidebar.selectbox(
    "Province/Territory",
    options=[
        'Ontario',
        'British Columbia',
        'Alberta',
        'Saskatchewan',
        'Manitoba',
        'Quebec',
        'New Brunswick',
        'Nova Scotia',
        'Prince Edward Island',
        'Newfoundland and Labrador'
    ],
    index=0,  # Default to Ontario
    help="Select your province for accurate tax calculations"
)

st.sidebar.markdown("---")

# Planning Mode Toggle
planning_mode = st.sidebar.radio(
    "Planning Mode",
    options=['Single', 'Couple'],
    index=0,
    help="Switch between individual and couple retirement planning"
)

is_couple_mode = (planning_mode == 'Couple')

st.sidebar.markdown("---")

# Personal Information - Person 1
with st.sidebar.expander("👤 Person 1 Details", expanded=True):
    current_age = st.number_input("Current Age", min_value=18, max_value=100, value=55, key="p1_age")
    retirement_age = st.number_input("Planned Retirement Age", min_value=current_age, max_value=75, value=65, key="p1_ret_age")
    years_in_canada = st.number_input(
        "Years in Canada (after age 18)",
        min_value=0,
        max_value=80,
        value=40,
        key="p1_years_canada",
        help="Current accumulated years. Will increase each projection year if you remain in Canada."
    )

# Financial Information - Person 1
with st.sidebar.expander("💰 Person 1 Finances", expanded=True):
    rrsp_balance = st.number_input("Current RRSP Balance ($)", min_value=0, value=500000, step=10000, key="p1_rrsp")
    tfsa_balance = st.number_input("Current TFSA Balance ($)", min_value=0, value=100000, step=10000, key="p1_tfsa")
    nonreg_balance = st.number_input("Non-Registered Savings ($)", min_value=0, value=200000, step=10000, key="p1_nonreg")
    st.caption("💡 Non-registered: Taxable investment accounts (capital gains tax applies)")
    annual_income = st.number_input("Current Annual Income ($)", min_value=0, value=80000, step=5000, key="p1_income")
    annual_savings = st.number_input("Annual Savings/Contributions ($)", min_value=0, value=20000, step=1000, key="p1_savings")

# CPP/OAS Information - Person 1
with st.sidebar.expander("🇨🇦 Person 1 CPP/OAS", expanded=True):
    cpp_start_age = st.slider("CPP Start Age", min_value=60, max_value=70, value=65, key="p1_cpp_start")
    cpp_contribution_years = st.number_input("Years of CPP Contributions", min_value=0, max_value=47, value=35, key="p1_cpp_years")
    cpp_earnings_ratio = st.slider("Average Earnings (% of YMPE)", min_value=0, max_value=100, value=80, key="p1_cpp_ratio") / 100
    st.markdown("---")
    oas_start_age = st.slider("OAS Start Age", min_value=65, max_value=70, value=65, key="p1_oas_start")
    st.caption("💡 Deferring OAS increases benefits by 0.6% per month (7.2% per year)")

# Person 2 Inputs (only shown in couple mode)
if is_couple_mode:
    st.sidebar.markdown("---")

    with st.sidebar.expander("👥 Person 2 (Spouse) Details", expanded=True):
        person2_age = st.number_input("Current Age", min_value=18, max_value=100, value=53, key="p2_age")
        person2_retirement_age = st.number_input("Planned Retirement Age", min_value=person2_age, max_value=75, value=65, key="p2_ret_age")
        person2_years_in_canada = st.number_input(
            "Years in Canada (after age 18)",
            min_value=0,
            max_value=80,
            value=40,
            key="p2_years_canada",
            help="Current accumulated years. Will increase each projection year if you remain in Canada."
        )

    with st.sidebar.expander("💰 Person 2 Finances", expanded=True):
        person2_rrsp_balance = st.number_input("Current RRSP Balance ($)", min_value=0, value=300000, step=10000, key="p2_rrsp")
        person2_tfsa_balance = st.number_input("Current TFSA Balance ($)", min_value=0, value=80000, step=10000, key="p2_tfsa")
        person2_nonreg_balance = st.number_input("Non-Registered Savings ($)", min_value=0, value=100000, step=10000, key="p2_nonreg")
        person2_annual_income = st.number_input("Current Annual Income ($)", min_value=0, value=70000, step=5000, key="p2_income")
        person2_annual_savings = st.number_input("Annual Savings/Contributions ($)", min_value=0, value=15000, step=1000, key="p2_savings")

    with st.sidebar.expander("🇨🇦 Person 2 CPP/OAS", expanded=True):
        person2_cpp_start_age = st.slider("CPP Start Age", min_value=60, max_value=70, value=65, key="p2_cpp_start")
        person2_cpp_contribution_years = st.number_input("Years of CPP Contributions", min_value=0, max_value=47, value=35, key="p2_cpp_years")
        person2_cpp_earnings_ratio = st.slider("Average Earnings (% of YMPE)", min_value=0, max_value=100, value=75, key="p2_cpp_ratio") / 100
        st.markdown("---")
        person2_oas_start_age = st.slider("OAS Start Age", min_value=65, max_value=70, value=65, key="p2_oas_start")

    st.sidebar.markdown("---")

    # Household Settings
    with st.sidebar.expander("🏠 Household Settings", expanded=True):
        household_annual_spending = st.number_input(
            "Household Annual Spending ($)",
            min_value=0,
            value=80000,
            step=5000,
            help="Combined household spending needs in retirement"
        )
        apply_income_splitting = st.checkbox(
            "Apply Income Splitting (65+)",
            value=True,
            help="Automatically optimize pension income splitting when both 65+"
        )
        survivor_spending_ratio = st.slider(
            "Survivor Spending (% of couple spending)",
            min_value=50,
            max_value=100,
            value=70,
            help="Expected spending reduction when one spouse passes"
        ) / 100

        couple_withdrawal_strategy = st.selectbox(
            "Couple Withdrawal Strategy",
            options=['tax_optimized', 'oas_clawback_aware', 'balanced', 'rrsp_meltdown'],
            format_func=lambda x: {
                'tax_optimized': '🟢 Tax-Optimized (Minimize household tax)',
                'oas_clawback_aware': '🟡 OAS-Aware (Keep both below threshold)',
                'balanced': '🔵 Balanced (Proportional from both)',
                'rrsp_meltdown': '🔥 RRSP Meltdown (Minimize lifetime taxes & maximize legacy)'
            }[x],
            index=0,
            help="Strategy for coordinating withdrawals between spouses"
        )

# Retirement Spending (Single Mode)
if not is_couple_mode:
    with st.sidebar.expander("💳 Retirement Spending", expanded=True):
        annual_spending = st.number_input("Annual Retirement Spending ($)", min_value=0, value=60000, step=5000)
        st.markdown("---")
        withdrawal_strategy = st.selectbox(
            "Withdrawal Strategy",
            options=['tax_efficient', 'rrsp_first', 'proportional'],
            format_func=lambda x: {
                'tax_efficient': '🟢 Tax-Efficient (TFSA → Non-Reg → RRSP)',
                'rrsp_first': '🔥 RRSP Meltdown (RRSP → Non-Reg → TFSA)',
                'proportional': '🟡 Proportional (All accounts equally)'
            }[x],
            index=0
        )
        if withdrawal_strategy == 'tax_efficient':
            st.caption("💡 Minimizes taxes by using tax-free accounts first")
        elif withdrawal_strategy == 'rrsp_first':
            st.caption("💡 RRSP Meltdown: Reduces RRSP early to minimize lifetime taxes and maximize legacy value")
        else:
            st.caption("💡 Withdraws proportionally from all accounts")
else:
    # Use couple-specific values for single-person calculations when needed
    annual_spending = household_annual_spending
    withdrawal_strategy = 'tax_efficient'  # Default for backward compatibility

# Investment Assumptions
with st.sidebar.expander("📈 Investment Assumptions", expanded=False):
    expected_return = st.slider("Expected Annual Return (%)", min_value=0.0, max_value=15.0, value=6.0, step=0.5) / 100
    return_std_dev = st.slider("Return Std Deviation (%)", min_value=0.0, max_value=30.0, value=12.0, step=1.0) / 100
    inflation_rate = st.slider("Annual Inflation (%)", min_value=0.0, max_value=10.0, value=2.0, step=0.1) / 100
    st.caption("💡 Inflation adjusts your spending needs over time to maintain purchasing power")

# Main content tabs
if is_couple_mode:
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview",
        "🎯 CPP/OAS",
        "💼 RRSP/TFSA",
        "👥 Couple Strategy",
        "🎲 Monte Carlo"
    ])
else:
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview",
        "🎯 CPP/OAS",
        "💼 RRSP/TFSA",
        "🎲 Monte Carlo",
        "🔥 RRSP Meltdown"
    ])

# Tab 1: Overview
with tab1:
    st.header("Retirement Overview")

    if is_couple_mode:
        # Couple Mode Overview
        # Calculate CPP/OAS for both spouses
        person1_cpp_monthly = calculate_cpp_benefit(cpp_start_age, cpp_contribution_years, cpp_earnings_ratio)
        person1_cpp_annual = person1_cpp_monthly * 12
        person1_oas_monthly = calculate_oas_benefit(oas_start_age, 50000, years_in_canada, oas_start_age)
        person1_oas_annual = person1_oas_monthly * 12

        person2_cpp_monthly = calculate_cpp_benefit(person2_cpp_start_age, person2_cpp_contribution_years, person2_cpp_earnings_ratio)
        person2_cpp_annual = person2_cpp_monthly * 12
        person2_oas_monthly = calculate_oas_benefit(person2_oas_start_age, 50000, person2_years_in_canada, person2_oas_start_age)
        person2_oas_annual = person2_oas_monthly * 12

        # Household metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            household_cpp = person1_cpp_annual + person2_cpp_annual
            st.metric("Household CPP (Annual)", f"${household_cpp:,.0f}")

        with col2:
            household_oas = person1_oas_annual + person2_oas_annual
            st.metric("Household OAS (Annual)", f"${household_oas:,.0f}")

        with col3:
            total_accounts = rrsp_balance + tfsa_balance + nonreg_balance + person2_rrsp_balance + person2_tfsa_balance + person2_nonreg_balance
            st.metric("Total Household Savings", f"${total_accounts:,.0f}")

        with col4:
            age_diff = abs(current_age - person2_age)
            st.metric("Age Difference", f"{age_diff} years")

        # Individual breakdown
        st.markdown("---")
        st.subheader("Individual Breakdown")

        col_p1, col_p2 = st.columns(2)

        with col_p1:
            st.markdown("#### 👤 Person 1")
            st.metric("Age", current_age)
            person1_total = rrsp_balance + tfsa_balance + nonreg_balance
            st.metric("Total Savings", f"${person1_total:,.0f}")
            st.metric("CPP (Annual)", f"${person1_cpp_annual:,.0f}")
            st.metric("OAS (Annual)", f"${person1_oas_annual:,.0f}")
            st.metric("Years to Retirement", retirement_age - current_age)

        with col_p2:
            st.markdown("#### 👥 Person 2 (Spouse)")
            st.metric("Age", person2_age)
            person2_total = person2_rrsp_balance + person2_tfsa_balance + person2_nonreg_balance
            st.metric("Total Savings", f"${person2_total:,.0f}")
            st.metric("CPP (Annual)", f"${person2_cpp_annual:,.0f}")
            st.metric("OAS (Annual)", f"${person2_oas_annual:,.0f}")
            st.metric("Years to Retirement", person2_retirement_age - person2_age)

    else:
        # Single Mode Overview (existing code)
        col1, col2, col3, col4 = st.columns(4)

        # Calculate CPP benefit
        cpp_monthly = calculate_cpp_benefit(cpp_start_age, cpp_contribution_years, cpp_earnings_ratio)
        cpp_annual = cpp_monthly * 12

        with col1:
            st.metric("CPP (Annual)", f"${cpp_annual:,.0f}", f"${cpp_monthly:,.0f}/mo")

        # Estimate OAS (at OAS start age, assuming no clawback)
        oas_monthly = calculate_oas_benefit(oas_start_age, 50000, years_in_canada, oas_start_age)  # Rough estimate
        oas_annual = oas_monthly * 12

        with col2:
            st.metric("OAS (Annual)", f"${oas_annual:,.0f}", f"${oas_monthly:,.0f}/mo")

        with col3:
            total_accounts = rrsp_balance + tfsa_balance + nonreg_balance
            st.metric("Total Savings", f"${total_accounts:,.0f}")

        with col4:
            years_to_retirement = retirement_age - current_age
            st.metric("Years to Retirement", f"{years_to_retirement}")

    st.markdown("---")

    # Projection
    if is_couple_mode:
        st.subheader("Household Portfolio Projection")

        projection_years = max(95 - current_age, 95 - person2_age)

        # Create functions to get CPP/OAS for each person by year
        def person1_cpp_oas_func(year):
            age = current_age + year
            cpp = person1_cpp_annual if age >= cpp_start_age else 0
            oas = person1_oas_annual if age >= oas_start_age else 0
            return cpp, oas

        def person2_cpp_oas_func(year):
            age = person2_age + year
            cpp = person2_cpp_annual if age >= person2_cpp_start_age else 0
            oas = person2_oas_annual if age >= person2_oas_start_age else 0
            return cpp, oas

        # Project couple accounts
        couple_projection = project_couple_accounts(
            current_age,
            person2_age,
            retirement_age,
            person2_retirement_age,
            projection_years,
            rrsp_balance,
            tfsa_balance,
            nonreg_balance,
            person2_rrsp_balance,
            person2_tfsa_balance,
            person2_nonreg_balance,
            annual_savings,
            person2_annual_savings,
            household_annual_spending,
            person1_cpp_oas_func,
            person2_cpp_oas_func,
            couple_withdrawal_strategy,
            investment_returns=[expected_return] * projection_years,
            inflation_rate=inflation_rate,
            province=province,
        )

        # Plot household portfolio as stacked area
        fig = go.Figure()

        # Person 1 accounts
        fig.add_trace(go.Scatter(
            x=couple_projection['person1_age'],
            y=couple_projection['person1_rrsp_balance'],
            name='Person 1 RRSP',
            stackgroup='one',
            fillcolor='rgba(99, 110, 250, 0.7)',
            line=dict(width=0.5, color='rgb(99, 110, 250)')
        ))
        fig.add_trace(go.Scatter(
            x=couple_projection['person1_age'],
            y=couple_projection['person1_tfsa_balance'],
            name='Person 1 TFSA',
            stackgroup='one',
            fillcolor='rgba(239, 85, 59, 0.7)',
            line=dict(width=0.5, color='rgb(239, 85, 59)')
        ))
        fig.add_trace(go.Scatter(
            x=couple_projection['person1_age'],
            y=couple_projection['person1_nonreg_balance'],
            name='Person 1 Non-Reg',
            stackgroup='one',
            fillcolor='rgba(0, 204, 150, 0.7)',
            line=dict(width=0.5, color='rgb(0, 204, 150)')
        ))

        # Person 2 accounts (lighter shades)
        fig.add_trace(go.Scatter(
            x=couple_projection['person1_age'],
            y=couple_projection['person2_rrsp_balance'],
            name='Person 2 RRSP',
            stackgroup='one',
            fillcolor='rgba(99, 110, 250, 0.4)',
            line=dict(width=0.5, color='rgb(99, 110, 250)')
        ))
        fig.add_trace(go.Scatter(
            x=couple_projection['person1_age'],
            y=couple_projection['person2_tfsa_balance'],
            name='Person 2 TFSA',
            stackgroup='one',
            fillcolor='rgba(239, 85, 59, 0.4)',
            line=dict(width=0.5, color='rgb(239, 85, 59)')
        ))
        fig.add_trace(go.Scatter(
            x=couple_projection['person1_age'],
            y=couple_projection['person2_nonreg_balance'],
            name='Person 2 Non-Reg',
            stackgroup='one',
            fillcolor='rgba(0, 204, 150, 0.4)',
            line=dict(width=0.5, color='rgb(0, 204, 150)')
        ))

        strategy_display = {
            'tax_optimized': 'Tax-Optimized',
            'oas_clawback_aware': 'OAS-Aware',
            'balanced': 'Balanced'
        }

        fig.update_layout(
            title=f'Household Portfolio Over Time ({strategy_display.get(couple_withdrawal_strategy, couple_withdrawal_strategy)} Strategy)',
            xaxis_title='Person 1 Age',
            yaxis_title='Balance ($)',
            hovermode='x unified',
            showlegend=True
        )
        st.plotly_chart(fig, width="stretch")

        # Show key metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            final_balance = couple_projection['household_total_balance'][-1]
            st.metric("Final Household Balance (Age 95)", f"${final_balance:,.0f}")
        with col2:
            total_splitting_savings = sum(couple_projection['income_splitting_savings'])
            st.metric("Lifetime Income Splitting Savings", f"${total_splitting_savings:,.0f}")
        with col3:
            total_household_tax = sum(couple_projection['household_tax'])
            st.metric("Lifetime Household Tax", f"${total_household_tax:,.0f}")

    else:
        # Single Mode Projection (existing code)
        st.subheader("Retirement Income Projection")

        projection_years = 95 - current_age

        # Project all accounts with selected withdrawal strategy
        account_projection = project_all_accounts(
            current_age,
            retirement_age,
            projection_years,
            rrsp_balance,
            tfsa_balance,
            nonreg_balance,
            annual_savings,
            withdrawal_strategy=withdrawal_strategy,
            annual_withdrawal_amount=annual_spending,
            investment_returns=[expected_return] * projection_years,
            inflation_rate=inflation_rate,
        )

        # Create projection dataframe
        df_proj = pd.DataFrame({
            'Age': account_projection['age'],
            'RRSP Balance': account_projection['rrsp_balance'],
            'TFSA Balance': account_projection['tfsa_balance'],
            'Non-Registered Balance': account_projection['nonreg_balance'],
            'Total Balance': account_projection['total_balance'],
        })

        # Plot portfolio balance as stacked area
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_proj['Age'],
            y=df_proj['RRSP Balance'],
            name='RRSP',
            stackgroup='one',
            fillcolor='rgba(99, 110, 250, 0.7)',
            line=dict(width=0.5, color='rgb(99, 110, 250)')
        ))
        fig.add_trace(go.Scatter(
            x=df_proj['Age'],
            y=df_proj['TFSA Balance'],
            name='TFSA',
            stackgroup='one',
            fillcolor='rgba(239, 85, 59, 0.7)',
            line=dict(width=0.5, color='rgb(239, 85, 59)')
        ))
        fig.add_trace(go.Scatter(
            x=df_proj['Age'],
            y=df_proj['Non-Registered Balance'],
            name='Non-Registered',
            stackgroup='one',
            fillcolor='rgba(0, 204, 150, 0.7)',
            line=dict(width=0.5, color='rgb(0, 204, 150)')
        ))
        strategy_names = {
            'tax_efficient': 'Tax-Efficient',
            'rrsp_first': 'RRSP First',
            'proportional': 'Proportional'
        }
        fig.update_layout(
            title=f'Portfolio Balance Over Time ({strategy_names.get(withdrawal_strategy, withdrawal_strategy)} Strategy)',
            xaxis_title='Age',
            yaxis_title='Balance ($)',
            hovermode='x unified',
            showlegend=True
        )
        st.plotly_chart(fig, width="stretch")

# Tab 2: CPP/OAS Details
with tab2:
    st.header("CPP and OAS Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("CPP Benefits by Start Age")
        cpp_ages = list(range(60, 71))
        cpp_benefits = [calculate_cpp_benefit(age, cpp_contribution_years, cpp_earnings_ratio) * 12
                       for age in cpp_ages]

        df_cpp = pd.DataFrame({
            'Start Age': cpp_ages,
            'Annual Benefit': cpp_benefits
        })

        fig_cpp = px.bar(df_cpp, x='Start Age', y='Annual Benefit',
                        title='CPP Annual Benefit by Start Age')
        fig_cpp.update_yaxes(title='Annual Benefit ($)')
        st.plotly_chart(fig_cpp, width="stretch")

        st.dataframe(df_cpp.style.format({'Annual Benefit': '${:,.0f}'}), width="stretch")

    with col2:
        st.subheader("OAS Clawback Analysis")
        income_levels = np.arange(50000, 160000, 5000)
        oas_benefits = [calculate_oas_benefit(oas_start_age, income, years_in_canada, oas_start_age) * 12
                       for income in income_levels]

        df_oas = pd.DataFrame({
            'Income': income_levels,
            'OAS Benefit': oas_benefits
        })

        fig_oas = go.Figure()
        fig_oas.add_trace(go.Scatter(x=df_oas['Income'], y=df_oas['OAS Benefit'],
                                     mode='lines', name='OAS Benefit'))
        fig_oas.add_vline(x=86912, line_dash="dash", line_color="red",
                         annotation_text="Clawback Starts")

        # Show deferral bonus in title
        deferral_bonus = (oas_start_age - 65) * 7.2 if oas_start_age > 65 else 0
        title_text = f'OAS Benefit vs Income (Start Age {oas_start_age}'
        if deferral_bonus > 0:
            title_text += f', +{deferral_bonus:.1f}% bonus)'
        else:
            title_text += ')'

        fig_oas.update_layout(title=title_text,
                            xaxis_title='Annual Income ($)',
                            yaxis_title='Annual OAS Benefit ($)')
        st.plotly_chart(fig_oas, width="stretch")

    # OAS Deferral Comparison
    st.markdown("---")
    st.subheader("OAS Benefits by Start Age")
    st.markdown("Deferring OAS increases your benefit by 0.6% per month (7.2% per year), up to 36% at age 70.")

    col3, col4 = st.columns([2, 1])

    with col3:
        oas_ages = list(range(65, 71))
        oas_start_benefits = [calculate_oas_benefit(age, 50000, years_in_canada, age) * 12
                             for age in oas_ages]

        df_oas_start = pd.DataFrame({
            'Start Age': oas_ages,
            'Annual Benefit': oas_start_benefits,
            'Bonus %': [(age - 65) * 7.2 for age in oas_ages]
        })

        fig_oas_start = px.bar(df_oas_start, x='Start Age', y='Annual Benefit',
                              title='OAS Annual Benefit by Start Age (assuming $50k income)',
                              text='Bonus %')
        fig_oas_start.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig_oas_start.update_yaxes(title='Annual Benefit ($)')
        st.plotly_chart(fig_oas_start, width="stretch")

    with col4:
        st.dataframe(df_oas_start.style.format({
            'Annual Benefit': '${:,.0f}',
            'Bonus %': '{:.1f}%'
        }), width="stretch")

        st.info("💡 **Tip**: If you have significant RRSP/investment income, deferring OAS can help avoid or reduce clawback.")

# Tab 3: All Account Withdrawal Strategies
with tab3:
    if is_couple_mode:
        st.header("Couple Account Balances & Withdrawal Strategy")

        st.markdown(f"""
        **Selected Strategy**: {couple_withdrawal_strategy.replace('_', ' ').title()}

        This shows how your selected withdrawal strategy affects both spouses' account balances over time.
        """)

        # Show account balances for both spouses
        st.subheader("Household Account Projections")

        # Create combined chart showing all 6 accounts (3 per person)
        fig_couple_accounts = go.Figure()

        # Person 1 accounts
        fig_couple_accounts.add_trace(go.Scatter(
            x=couple_projection['person1_age'],
            y=couple_projection['person1_rrsp_balance'],
            name='Person 1 RRSP',
            stackgroup='one',
            fillcolor='rgba(99, 110, 250, 0.7)'
        ))
        fig_couple_accounts.add_trace(go.Scatter(
            x=couple_projection['person1_age'],
            y=couple_projection['person1_tfsa_balance'],
            name='Person 1 TFSA',
            stackgroup='one',
            fillcolor='rgba(239, 85, 59, 0.7)'
        ))
        fig_couple_accounts.add_trace(go.Scatter(
            x=couple_projection['person1_age'],
            y=couple_projection['person1_nonreg_balance'],
            name='Person 1 Non-Reg',
            stackgroup='one',
            fillcolor='rgba(0, 204, 150, 0.7)'
        ))

        # Person 2 accounts
        fig_couple_accounts.add_trace(go.Scatter(
            x=couple_projection['person2_age'],
            y=couple_projection['person2_rrsp_balance'],
            name='Person 2 RRSP',
            stackgroup='two',
            fillcolor='rgba(99, 110, 250, 0.4)'
        ))
        fig_couple_accounts.add_trace(go.Scatter(
            x=couple_projection['person2_age'],
            y=couple_projection['person2_tfsa_balance'],
            name='Person 2 TFSA',
            stackgroup='two',
            fillcolor='rgba(239, 85, 59, 0.4)'
        ))
        fig_couple_accounts.add_trace(go.Scatter(
            x=couple_projection['person2_age'],
            y=couple_projection['person2_nonreg_balance'],
            name='Person 2 Non-Reg',
            stackgroup='two',
            fillcolor='rgba(0, 204, 150, 0.4)'
        ))

        fig_couple_accounts.update_layout(
            xaxis_title='Person 1 Age',
            yaxis_title='Balance ($)',
            hovermode='x unified',
            title=f'Household Accounts ({couple_withdrawal_strategy.replace("_", " ").title()} Strategy)'
        )
        st.plotly_chart(fig_couple_accounts, width="stretch")

        # Side-by-side account breakdown
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("👤 Person 1 Final Balances (Age 95)")
            final_idx = -1
            st.metric("RRSP", f"${couple_projection['person1_rrsp_balance'][final_idx]:,.0f}")
            st.metric("TFSA", f"${couple_projection['person1_tfsa_balance'][final_idx]:,.0f}")
            st.metric("Non-Reg", f"${couple_projection['person1_nonreg_balance'][final_idx]:,.0f}")
            st.metric("Total", f"${couple_projection['person1_total_balance'][final_idx]:,.0f}",
                     delta=None, delta_color="normal")

        with col2:
            st.subheader("👤 Person 2 Final Balances (Age 95)")
            st.metric("RRSP", f"${couple_projection['person2_rrsp_balance'][final_idx]:,.0f}")
            st.metric("TFSA", f"${couple_projection['person2_tfsa_balance'][final_idx]:,.0f}")
            st.metric("Non-Reg", f"${couple_projection['person2_nonreg_balance'][final_idx]:,.0f}")
            st.metric("Total", f"${couple_projection['person2_total_balance'][final_idx]:,.0f}",
                     delta=None, delta_color="normal")

        # Withdrawal breakdown for both spouses
        st.markdown("---")
        st.subheader("Annual Withdrawal Breakdown by Spouse")

        fig_couple_withdrawals = go.Figure()

        # Person 1 withdrawals
        fig_couple_withdrawals.add_trace(go.Bar(
            x=couple_projection['person1_age'],
            y=couple_projection['person1_rrsp_withdrawal'],
            name='Person 1 RRSP',
            marker_color='rgba(99, 110, 250, 0.8)'
        ))
        fig_couple_withdrawals.add_trace(go.Bar(
            x=couple_projection['person1_age'],
            y=couple_projection['person1_tfsa_withdrawal'],
            name='Person 1 TFSA',
            marker_color='rgba(239, 85, 59, 0.8)'
        ))
        fig_couple_withdrawals.add_trace(go.Bar(
            x=couple_projection['person1_age'],
            y=couple_projection['person1_nonreg_withdrawal'],
            name='Person 1 Non-Reg',
            marker_color='rgba(0, 204, 150, 0.8)'
        ))

        # Person 2 withdrawals
        fig_couple_withdrawals.add_trace(go.Bar(
            x=couple_projection['person2_age'],
            y=couple_projection['person2_rrsp_withdrawal'],
            name='Person 2 RRSP',
            marker_color='rgba(99, 110, 250, 0.4)'
        ))
        fig_couple_withdrawals.add_trace(go.Bar(
            x=couple_projection['person2_age'],
            y=couple_projection['person2_tfsa_withdrawal'],
            name='Person 2 TFSA',
            marker_color='rgba(239, 85, 59, 0.4)'
        ))
        fig_couple_withdrawals.add_trace(go.Bar(
            x=couple_projection['person2_age'],
            y=couple_projection['person2_nonreg_withdrawal'],
            name='Person 2 Non-Reg',
            marker_color='rgba(0, 204, 150, 0.4)'
        ))

        fig_couple_withdrawals.update_layout(
            barmode='stack',
            xaxis_title='Person 1 Age',
            yaxis_title='Withdrawal ($)',
            hovermode='x unified',
            title='Annual Withdrawals by Account Type and Spouse'
        )
        st.plotly_chart(fig_couple_withdrawals, width="stretch")

        # Strategy explanation
        st.markdown("---")
        st.subheader("About Your Selected Strategy")

        strategy_explanations = {
            'tax_optimized': """
            **🟢 Tax-Optimized Strategy**: Minimizes household tax by coordinating withdrawals to equalize
            marginal tax rates between spouses. Withdraws more from the lower-income spouse to keep both
            in lower tax brackets.
            """,
            'oas_clawback_aware': """
            **🟡 OAS-Clawback-Aware Strategy**: Keeps both spouses below the OAS clawback threshold
            ($86,912) when possible to preserve dual OAS benefits. Prioritizes TFSA withdrawals (don't
            affect OAS) and balances taxable withdrawals between spouses.
            """,
            'balanced': """
            **🔵 Balanced Strategy**: Withdraws proportionally from both spouses' accounts based on their
            relative account sizes. Maintains the ratio of assets between spouses throughout retirement.
            """,
            'rrsp_meltdown': """
            **🔥 RRSP Meltdown Strategy**: Prioritizes RRSP withdrawals from both spouses to minimize
            lifetime taxes. Depletes RRSPs early (before mandatory RRIF withdrawals), preserves TFSAs
            for tax-free growth, and balances withdrawals by income levels to minimize household tax.
            """
        }

        st.markdown(strategy_explanations.get(couple_withdrawal_strategy, "Strategy description not available."))

        # RRIF table
        st.subheader("RRIF Minimum Withdrawal Rates (Age 72+)")
        rrif_table = calculate_rrif_minimum_table(65, 95)
        df_rrif = pd.DataFrame(list(rrif_table.items()), columns=['Age', 'Minimum Rate (%)'])
        df_rrif['Minimum Rate (%)'] = df_rrif['Minimum Rate (%)'] * 100

        col1, col2 = st.columns([1, 2])
        with col1:
            st.dataframe(df_rrif.style.format({'Minimum Rate (%)': '{:.2f}%'}), height=400)
        with col2:
            st.info("""
            💡 **RRIF Conversion**: RRSP automatically converts to RRIF at age 72.
            Minimum withdrawals are mandatory and fully taxable. The RRSP Meltdown
            strategy reduces your RRSP before age 72 to minimize these mandatory
            withdrawals and reduce lifetime taxes.
            """)

    else:
        # Single mode content (existing code)
        st.header("Withdrawal Strategies (RRSP/TFSA/Non-Registered)")

        st.subheader("Tax-Efficient Withdrawal Order")
        st.markdown("""
        **Optimal tax-efficient withdrawal strategy:**
        1. 🟢 **TFSA first** - Tax-free withdrawals
        2. 🟡 **Non-Registered second** - Only 50% of capital gains taxable
        3. 🔴 **RRSP last** - 100% taxable as income
        """)

    # Calculate all three strategies
    tax_efficient = project_all_accounts(
        current_age, retirement_age, projection_years,
        rrsp_balance, tfsa_balance, nonreg_balance, annual_savings,
        withdrawal_strategy='tax_efficient',
        annual_withdrawal_amount=annual_spending,
        investment_returns=[expected_return] * projection_years,
        inflation_rate=inflation_rate,
    )

    rrsp_first = project_all_accounts(
        current_age, retirement_age, projection_years,
        rrsp_balance, tfsa_balance, nonreg_balance, annual_savings,
        withdrawal_strategy='rrsp_first',
        annual_withdrawal_amount=annual_spending,
        investment_returns=[expected_return] * projection_years,
        inflation_rate=inflation_rate,
    )

    proportional = project_all_accounts(
        current_age, retirement_age, projection_years,
        rrsp_balance, tfsa_balance, nonreg_balance, annual_savings,
        withdrawal_strategy='proportional',
        annual_withdrawal_amount=annual_spending,
        investment_returns=[expected_return] * projection_years,
        inflation_rate=inflation_rate,
    )

    # Compare strategies
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("🟢 Tax-Efficient")
        st.caption("TFSA → Non-Reg → RRSP")
        fig_te = go.Figure()
        fig_te.add_trace(go.Scatter(x=tax_efficient['age'], y=tax_efficient['rrsp_balance'],
                                    name='RRSP', stackgroup='one', fillcolor='rgba(99, 110, 250, 0.7)'))
        fig_te.add_trace(go.Scatter(x=tax_efficient['age'], y=tax_efficient['tfsa_balance'],
                                    name='TFSA', stackgroup='one', fillcolor='rgba(239, 85, 59, 0.7)'))
        fig_te.add_trace(go.Scatter(x=tax_efficient['age'], y=tax_efficient['nonreg_balance'],
                                    name='Non-Reg', stackgroup='one', fillcolor='rgba(0, 204, 150, 0.7)'))
        fig_te.update_layout(xaxis_title='Age', yaxis_title='Balance ($)', hovermode='x unified', showlegend=False)
        st.plotly_chart(fig_te, width="stretch")

    with col2:
        st.subheader("🔴 RRSP First")
        st.caption("RRSP → Non-Reg → TFSA")
        fig_rrsp = go.Figure()
        fig_rrsp.add_trace(go.Scatter(x=rrsp_first['age'], y=rrsp_first['rrsp_balance'],
                                       name='RRSP', stackgroup='one', fillcolor='rgba(99, 110, 250, 0.7)'))
        fig_rrsp.add_trace(go.Scatter(x=rrsp_first['age'], y=rrsp_first['tfsa_balance'],
                                       name='TFSA', stackgroup='one', fillcolor='rgba(239, 85, 59, 0.7)'))
        fig_rrsp.add_trace(go.Scatter(x=rrsp_first['age'], y=rrsp_first['nonreg_balance'],
                                       name='Non-Reg', stackgroup='one', fillcolor='rgba(0, 204, 150, 0.7)'))
        fig_rrsp.update_layout(xaxis_title='Age', yaxis_title='Balance ($)', hovermode='x unified', showlegend=False)
        st.plotly_chart(fig_rrsp, width="stretch")

    with col3:
        st.subheader("🟡 Proportional")
        st.caption("All accounts equally")
        fig_prop = go.Figure()
        fig_prop.add_trace(go.Scatter(x=proportional['age'], y=proportional['rrsp_balance'],
                                      name='RRSP', stackgroup='one', fillcolor='rgba(99, 110, 250, 0.7)'))
        fig_prop.add_trace(go.Scatter(x=proportional['age'], y=proportional['tfsa_balance'],
                                      name='TFSA', stackgroup='one', fillcolor='rgba(239, 85, 59, 0.7)'))
        fig_prop.add_trace(go.Scatter(x=proportional['age'], y=proportional['nonreg_balance'],
                                      name='Non-Reg', stackgroup='one', fillcolor='rgba(0, 204, 150, 0.7)'))
        fig_prop.update_layout(xaxis_title='Age', yaxis_title='Balance ($)', hovermode='x unified')
        st.plotly_chart(fig_prop, width="stretch")

    # Withdrawal breakdown for selected strategy
    st.markdown("---")
    strategy_display = {
        'tax_efficient': ('🟢 Tax-Efficient', tax_efficient),
        'rrsp_first': ('🔴 RRSP First', rrsp_first),
        'proportional': ('🟡 Proportional', proportional)
    }
    selected_name, selected_data = strategy_display[withdrawal_strategy]

    st.subheader(f"Your Strategy: {selected_name}")

    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Final Portfolio Balance (Age 95)",
                 f"${selected_data['total_balance'][-1]:,.0f}")
    with col_b:
        total_withdrawn = sum(selected_data['total_withdrawal'])
        st.metric("Total Withdrawn Over Retirement",
                 f"${total_withdrawn:,.0f}")

    st.subheader("Annual Withdrawal Breakdown")
    fig_withdrawals = go.Figure()
    fig_withdrawals.add_trace(go.Bar(x=selected_data['age'], y=selected_data['tfsa_withdrawal'],
                                     name='TFSA (Tax-Free)', marker_color='rgb(0, 204, 150)'))
    fig_withdrawals.add_trace(go.Bar(x=selected_data['age'], y=selected_data['nonreg_withdrawal'],
                                     name='Non-Reg (50% Taxable)', marker_color='rgb(255, 193, 7)'))
    fig_withdrawals.add_trace(go.Bar(x=selected_data['age'], y=selected_data['rrsp_withdrawal'],
                                     name='RRSP (100% Taxable)', marker_color='rgb(239, 85, 59)'))
    fig_withdrawals.update_layout(barmode='stack', xaxis_title='Age', yaxis_title='Withdrawal ($)',
                                 hovermode='x unified', title='Source of Annual Income by Account Type')
    st.plotly_chart(fig_withdrawals, width="stretch")

    # RRIF Minimum Withdrawal Table
    st.subheader("RRIF Minimum Withdrawal Rates")
    rrif_table = calculate_rrif_minimum_table(65, 95)
    df_rrif = pd.DataFrame(list(rrif_table.items()), columns=['Age', 'Minimum Rate (%)'])
    df_rrif['Minimum Rate (%)'] = df_rrif['Minimum Rate (%)'] * 100

    col1, col2 = st.columns([1, 2])
    with col1:
        st.dataframe(df_rrif.style.format({'Minimum Rate (%)': '{:.2f}%'}), height=400)

# Tab 4: Couple Strategy (couple mode) or Monte Carlo (single mode)
with tab4:
    if is_couple_mode:
        st.header("Couple Withdrawal Strategy Optimization")

        st.markdown("""
        Optimize your household withdrawals considering:
        - Combined tax minimization through income splitting
        - Dual OAS clawback management (keep both below $86,912 threshold)
        - Age difference implications
        - RRIF minimum withdrawals for both spouses
        """)

        # Show income splitting information
        if current_age >= 65 and person2_age >= 65:
            st.success("✅ Both spouses are 65+ - Income splitting is available!")
            total_splitting = sum(couple_projection['income_splitting_savings'])
            if total_splitting > 0:
                st.metric("Lifetime Income Splitting Savings", f"${total_splitting:,.0f}")
        elif current_age >= 65 or person2_age >= 65:
            younger_age = min(current_age, person2_age)
            years_until_splitting = 65 - younger_age
            st.info(f"ℹ️ Income splitting will be available in {years_until_splitting} years when both spouses reach 65")
        else:
            st.info(f"ℹ️ Income splitting will be available when both spouses reach age 65")

        # OAS clawback analysis
        st.subheader("OAS Clawback Management")

        st.markdown(f"""
        **Key Insight:** Each person can earn up to **${86912:,.0f}** before OAS clawback begins.
        As a couple, you can maintain up to **${86912 * 2:,.0f}** in combined income without losing OAS benefits.
        """)

        # Show withdrawal breakdown
        st.subheader("Annual Withdrawal Strategy")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Person 1 Withdrawals (Sample Year: Age 70)")
            if len(couple_projection['person1_age']) > (70 - current_age):
                year_idx = 70 - current_age
                st.metric("RRSP", f"${couple_projection['person1_rrsp_withdrawal'][year_idx]:,.0f}")
                st.metric("TFSA", f"${couple_projection['person1_tfsa_withdrawal'][year_idx]:,.0f}")
                st.metric("Non-Reg", f"${couple_projection['person1_nonreg_withdrawal'][year_idx]:,.0f}")

        with col2:
            st.markdown("#### Person 2 Withdrawals (Sample Year: Age 70)")
            if len(couple_projection['person2_age']) > 0 and person2_age <= 70:
                year_idx = 70 - person2_age
                if year_idx >= 0 and year_idx < len(couple_projection['person2_rrsp_withdrawal']):
                    st.metric("RRSP", f"${couple_projection['person2_rrsp_withdrawal'][year_idx]:,.0f}")
                    st.metric("TFSA", f"${couple_projection['person2_tfsa_withdrawal'][year_idx]:,.0f}")
                    st.metric("Non-Reg", f"${couple_projection['person2_nonreg_withdrawal'][year_idx]:,.0f}")

        # Tax over time
        st.subheader("Household Tax Over Time")

        fig_tax = go.Figure()
        fig_tax.add_trace(go.Scatter(
            x=couple_projection['person1_age'],
            y=couple_projection['household_tax'],
            name='Annual Household Tax',
            mode='lines',
            line=dict(color='rgb(239, 85, 59)', width=2)
        ))
        fig_tax.update_layout(
            xaxis_title='Person 1 Age',
            yaxis_title='Annual Tax ($)',
            hovermode='x unified'
        )
        st.plotly_chart(fig_tax, width="stretch")

        # Income splitting savings over time
        if apply_income_splitting:
            st.subheader("Income Splitting Savings Over Time")

            fig_splitting = go.Figure()
            fig_splitting.add_trace(go.Bar(
                x=couple_projection['person1_age'],
                y=couple_projection['income_splitting_savings'],
                name='Annual Savings from Income Splitting',
                marker_color='rgb(0, 204, 150)'
            ))
            fig_splitting.update_layout(
                xaxis_title='Person 1 Age',
                yaxis_title='Annual Savings ($)',
                hovermode='x unified'
            )
            st.plotly_chart(fig_splitting, width="stretch")

        # Survivor Scenarios Analysis
        st.markdown("---")
        st.subheader("💔 Survivor Scenario Analysis")

        st.markdown("""
        Plan for financial security if one spouse passes away. This analysis shows:
        - CPP survivor benefits
        - Asset transfers and tax implications
        - Portfolio sustainability for the survivor
        """)

        col1, col2 = st.columns(2)

        with col1:
            deceased_spouse = st.selectbox(
                "Which spouse passes first?",
                options=['Person 1', 'Person 2'],
                help="Analyze financial impact based on who passes first"
            )

        with col2:
            death_age_input = st.slider(
                "Age at death",
                min_value=max(current_age, person2_age),
                max_value=90,
                value=80,
                help="Age at which spouse passes away"
            )

        if st.button("Analyze Survivor Scenario", type="secondary"):
            with st.spinner("Analyzing survivor scenario..."):
                # Determine which person dies and which survives
                if deceased_spouse == 'Person 1':
                    death_age = death_age_input
                    year_idx = death_age - current_age

                    if year_idx < len(couple_projection['person1_age']):
                        deceased_params = {
                            'rrsp_balance_at_death': couple_projection['person1_rrsp_balance'][year_idx],
                            'tfsa_balance_at_death': couple_projection['person1_tfsa_balance'][year_idx],
                            'nonreg_balance_at_death': couple_projection['person1_nonreg_balance'][year_idx],
                            'age_at_death': death_age,
                            'name': 'Person 1',
                        }

                        survivor_age_at_death = person2_age + year_idx
                        survivor_params_dict = {
                            'current_age': survivor_age_at_death,
                            'rrsp_balance': couple_projection['person2_rrsp_balance'][year_idx],
                            'tfsa_balance': couple_projection['person2_tfsa_balance'][year_idx],
                            'nonreg_balance': couple_projection['person2_nonreg_balance'][year_idx],
                            'years_in_canada': person2_years_in_canada,
                            'oas_start_age': person2_oas_start_age,
                            'name': 'Person 2',
                        }

                        deceased_cpp_monthly = couple_projection['person1_cpp_annual'][year_idx] / 12
                        deceased_oas_monthly = couple_projection['person1_oas_annual'][year_idx] / 12
                        survivor_cpp_monthly = couple_projection['person2_cpp_annual'][year_idx] / 12
                        survivor_oas_monthly = couple_projection['person2_oas_annual'][year_idx] / 12
                    else:
                        st.error("Death age is beyond projection range")
                        deceased_params = None
                else:  # Person 2 dies
                    death_age = death_age_input
                    year_idx = death_age - person2_age

                    if year_idx < len(couple_projection['person2_age']):
                        deceased_params = {
                            'rrsp_balance_at_death': couple_projection['person2_rrsp_balance'][year_idx],
                            'tfsa_balance_at_death': couple_projection['person2_tfsa_balance'][year_idx],
                            'nonreg_balance_at_death': couple_projection['person2_nonreg_balance'][year_idx],
                            'age_at_death': death_age,
                            'name': 'Person 2',
                        }

                        survivor_age_at_death = current_age + year_idx
                        survivor_params_dict = {
                            'current_age': survivor_age_at_death,
                            'rrsp_balance': couple_projection['person1_rrsp_balance'][year_idx],
                            'tfsa_balance': couple_projection['person1_tfsa_balance'][year_idx],
                            'nonreg_balance': couple_projection['person1_nonreg_balance'][year_idx],
                            'years_in_canada': years_in_canada,
                            'oas_start_age': oas_start_age,
                            'name': 'Person 1',
                        }

                        deceased_cpp_monthly = couple_projection['person2_cpp_annual'][year_idx] / 12
                        deceased_oas_monthly = couple_projection['person2_oas_annual'][year_idx] / 12
                        survivor_cpp_monthly = couple_projection['person1_cpp_annual'][year_idx] / 12
                        survivor_oas_monthly = couple_projection['person1_oas_annual'][year_idx] / 12
                    else:
                        st.error("Death age is beyond projection range")
                        deceased_params = None

                if deceased_params:
                    survivor_result = project_survivor_scenario(
                        deceased_params,
                        survivor_params_dict,
                        death_age,
                        95 - survivor_age_at_death,
                        household_annual_spending * survivor_spending_ratio,
                        deceased_cpp_monthly,
                        deceased_oas_monthly,
                        survivor_cpp_monthly,
                        survivor_oas_monthly,
                        investment_return=expected_return,
                        inflation_rate=inflation_rate,
                        province=province,
                    )

                    # Display results
                    st.success(f"✅ Survivor scenario analyzed for {survivor_params_dict['name']}")

                    # Key metrics
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        assets_transferred = survivor_result['death_summary']['assets_transferred']
                        st.metric("Assets Transferred", f"${assets_transferred:,.0f}")

                    with col2:
                        death_taxes = survivor_result['death_summary']['death_taxes']
                        st.metric("Estate Taxes", f"${death_taxes:,.0f}", delta_color="inverse")

                    with col3:
                        cpp_survivor_benefit = survivor_result['income_changes']['cpp_survivor_benefit_added']
                        st.metric("CPP Survivor Benefit", f"${cpp_survivor_benefit:,.0f}/yr")

                    with col4:
                        final_balance = survivor_result['portfolio_sustainability']['final_balance_at_age_95']
                        st.metric("Final Balance (Age 95)", f"${final_balance:,.0f}")

                    # Portfolio sustainability
                    if survivor_result['portfolio_sustainability']['portfolio_sustainable']:
                        st.success(f"✅ Portfolio sustainable: ${final_balance:,.0f} remaining at age 95")
                    else:
                        depletion_age = survivor_result['portfolio_sustainability']['depletion_age']
                        st.error(f"⚠️ Portfolio depleted at age {depletion_age}. Consider adjusting strategy.")

                    # Survivor portfolio projection chart
                    st.subheader("Survivor Portfolio Projection")

                    proj = survivor_result['projections']
                    fig_survivor = go.Figure()

                    fig_survivor.add_trace(go.Scatter(
                        x=proj['survivor_age'],
                        y=proj['survivor_rrsp_balance'],
                        name='RRSP',
                        stackgroup='one',
                        fillcolor='rgba(99, 110, 250, 0.7)',
                        line=dict(width=0.5, color='rgb(99, 110, 250)')
                    ))
                    fig_survivor.add_trace(go.Scatter(
                        x=proj['survivor_age'],
                        y=proj['survivor_tfsa_balance'],
                        name='TFSA',
                        stackgroup='one',
                        fillcolor='rgba(239, 85, 59, 0.7)',
                        line=dict(width=0.5, color='rgb(239, 85, 59)')
                    ))
                    fig_survivor.add_trace(go.Scatter(
                        x=proj['survivor_age'],
                        y=proj['survivor_nonreg_balance'],
                        name='Non-Reg',
                        stackgroup='one',
                        fillcolor='rgba(0, 204, 150, 0.7)',
                        line=dict(width=0.5, color='rgb(0, 204, 150)')
                    ))

                    fig_survivor.add_vline(
                        x=death_age,
                        line_dash="dash",
                        line_color="red",
                        annotation_text=f"{deceased_params['name']} passes at {death_age}"
                    )

                    fig_survivor.update_layout(
                        title=f"Survivor ({survivor_params_dict['name']}) Portfolio After Spouse's Death",
                        xaxis_title='Survivor Age',
                        yaxis_title='Balance ($)',
                        hovermode='x unified'
                    )
                    st.plotly_chart(fig_survivor, width="stretch")

                    # Income comparison
                    st.subheader("Income Changes After Death")

                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("**Before Death (Couple)**")
                        st.metric("Household CPP", f"${(deceased_cpp_monthly + survivor_cpp_monthly) * 12:,.0f}")
                        st.metric("Household OAS", f"${(deceased_oas_monthly + survivor_oas_monthly) * 12:,.0f}")

                    with col2:
                        st.markdown("**After Death (Survivor)**")
                        st.metric("Survivor CPP", f"${survivor_result['income_changes']['cpp_after_death']:,.0f}")
                        st.metric("Survivor OAS", f"${survivor_result['income_changes']['oas_after_death']:,.0f}")
                        st.caption(f"+ ${cpp_survivor_benefit:,.0f} survivor benefit included")

    else:
        # Single mode: Monte Carlo Simulation
        st.header("Monte Carlo Simulation")
        st.markdown("Analyze retirement success probability with market volatility")

    num_simulations = st.slider("Number of Simulations", min_value=100, max_value=5000, value=1000, step=100)

    if st.button("Run Monte Carlo Simulation", type="primary"):
        with st.spinner("Running simulation..."):
            # Prepare withdrawal schedule
            withdrawals = []
            for year in range(projection_years):
                age = current_age + year
                if age >= retirement_age:
                    withdrawals.append(annual_spending * (1.02 ** (year - (retirement_age - current_age))))
                else:
                    withdrawals.append(0)

            # Run simulation
            initial_portfolio = rrsp_balance + tfsa_balance
            mc_results = run_monte_carlo_simulation(
                initial_portfolio,
                withdrawals,
                num_simulations,
                mean_return=expected_return,
                std_dev=return_std_dev,
                random_seed=42
            )

            # Display results
            col1, col2, col3 = st.columns(3)

            with col1:
                success_color = "green" if mc_results['success_rate'] >= 0.9 else "orange" if mc_results['success_rate'] >= 0.75 else "red"
                st.metric("Success Rate", f"{mc_results['success_rate']*100:.1f}%")

            with col2:
                st.metric("Median Final Balance", f"${mc_results['final_stats']['median']:,.0f}")

            with col3:
                st.metric("Mean Final Balance", f"${mc_results['final_stats']['mean']:,.0f}")

            # Plot percentile bands
            ages = list(range(current_age, current_age + projection_years))

            fig_mc = go.Figure()

            # Add percentile bands
            fig_mc.add_trace(go.Scatter(
                x=ages, y=mc_results['percentiles']['p90'],
                name='90th Percentile',
                line=dict(color='rgba(0,176,246,0.2)'),
                mode='lines'
            ))
            fig_mc.add_trace(go.Scatter(
                x=ages, y=mc_results['percentiles']['p75'],
                name='75th Percentile',
                line=dict(color='rgba(0,176,246,0.4)'),
                fill='tonexty',
                mode='lines'
            ))
            fig_mc.add_trace(go.Scatter(
                x=ages, y=mc_results['percentiles']['p50'],
                name='Median',
                line=dict(color='rgb(0,100,200)', width=3),
                fill='tonexty',
                mode='lines'
            ))
            fig_mc.add_trace(go.Scatter(
                x=ages, y=mc_results['percentiles']['p25'],
                name='25th Percentile',
                line=dict(color='rgba(231,107,243,0.4)'),
                fill='tonexty',
                mode='lines'
            ))
            fig_mc.add_trace(go.Scatter(
                x=ages, y=mc_results['percentiles']['p10'],
                name='10th Percentile',
                line=dict(color='rgba(231,107,243,0.2)'),
                fill='tonexty',
                mode='lines'
            ))

            fig_mc.update_layout(
                title=f'Monte Carlo Simulation ({num_simulations} runs)',
                xaxis_title='Age',
                yaxis_title='Portfolio Balance ($)',
                hovermode='x unified'
            )
            st.plotly_chart(fig_mc, width="stretch")

            # Safe withdrawal rate
            st.subheader("Safe Withdrawal Rate Analysis")
            retirement_years = 95 - retirement_age
            swr_result = calculate_safe_withdrawal_rate(
                initial_portfolio,
                retirement_years,
                target_success_rate=0.95,
                num_simulations=500,
                mean_return=expected_return,
                std_dev=return_std_dev
            )

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Safe Withdrawal Rate (95% success)",
                         f"{swr_result['safe_withdrawal_rate']*100:.2f}%")
            with col2:
                st.metric("First Year Withdrawal",
                         f"${swr_result['first_year_withdrawal']:,.0f}")

# Tab 5
with tab5:
    if is_couple_mode:
        # Couple mode: Monte Carlo Simulation
        st.header("Monte Carlo Simulation")
        st.markdown("Analyze retirement success probability with market volatility")

        num_simulations = st.slider("Number of Simulations", min_value=100, max_value=5000, value=1000, step=100, key="couple_mc_sims")

        if st.button("Run Monte Carlo Simulation", type="primary", key="couple_mc_run"):
            with st.spinner("Running simulation..."):
                # Prepare withdrawal schedule for household
                withdrawals = []
                for year in range(projection_years):
                    age = current_age + year
                    if age >= retirement_age:
                        withdrawals.append(annual_spending * (1.02 ** (year - (retirement_age - current_age))))
                    else:
                        withdrawals.append(0)

                # Run simulation on total household portfolio
                initial_portfolio = rrsp_balance + tfsa_balance + person2_rrsp_balance + person2_tfsa_balance
                mc_results = run_monte_carlo_simulation(
                    initial_portfolio,
                    withdrawals,
                    num_simulations,
                    mean_return=expected_return,
                    std_dev=return_std_dev,
                    random_seed=42
                )

                # Display results
                col1, col2, col3 = st.columns(3)

                with col1:
                    success_color = "green" if mc_results['success_rate'] >= 0.9 else "orange" if mc_results['success_rate'] >= 0.75 else "red"
                    st.metric("Success Rate", f"{mc_results['success_rate']*100:.1f}%")

                with col2:
                    st.metric("Median Final Balance", f"${mc_results['final_stats']['median']:,.0f}")

                with col3:
                    st.metric("Mean Final Balance", f"${mc_results['final_stats']['mean']:,.0f}")

                # Plot percentile bands
                ages = list(range(current_age, current_age + projection_years))

                fig_mc = go.Figure()

                # Add percentile bands
                fig_mc.add_trace(go.Scatter(
                    x=ages, y=mc_results['percentiles']['p90'],
                    name='90th Percentile',
                    line=dict(color='rgba(0,176,246,0.2)'),
                    mode='lines'
                ))
                fig_mc.add_trace(go.Scatter(
                    x=ages, y=mc_results['percentiles']['p75'],
                    name='75th Percentile',
                    line=dict(color='rgba(0,176,246,0.4)'),
                    fill='tonexty',
                    mode='lines'
                ))
                fig_mc.add_trace(go.Scatter(
                    x=ages, y=mc_results['percentiles']['p50'],
                    name='Median',
                    line=dict(color='rgb(0,100,200)', width=3),
                    fill='tonexty',
                    mode='lines'
                ))
                fig_mc.add_trace(go.Scatter(
                    x=ages, y=mc_results['percentiles']['p25'],
                    name='25th Percentile',
                    line=dict(color='rgba(231,107,243,0.4)'),
                    fill='tonexty',
                    mode='lines'
                ))
                fig_mc.add_trace(go.Scatter(
                    x=ages, y=mc_results['percentiles']['p10'],
                    name='10th Percentile',
                    line=dict(color='rgba(231,107,243,0.2)'),
                    fill='tonexty',
                    mode='lines'
                ))

                fig_mc.update_layout(
                    title=f'Monte Carlo Simulation ({num_simulations} runs)',
                    xaxis_title='Age',
                    yaxis_title='Portfolio Balance ($)',
                    hovermode='x unified'
                )
                st.plotly_chart(fig_mc, width="stretch")

                # Safe withdrawal rate
                st.subheader("Safe Withdrawal Rate Analysis")
                retirement_years = 95 - retirement_age
                swr_result = calculate_safe_withdrawal_rate(
                    initial_portfolio,
                    retirement_years,
                    target_success_rate=0.95,
                    num_simulations=500,
                    mean_return=expected_return,
                    std_dev=return_std_dev
                )

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Safe Withdrawal Rate (95% success)",
                             f"{swr_result['safe_withdrawal_rate']*100:.2f}%")
                with col2:
                    st.metric("First Year Withdrawal",
                             f"${swr_result['first_year_withdrawal']:,.0f}")

    else:
        # Single mode: RRSP Meltdown Strategy
        st.header("RRSP Meltdown Strategy")
        st.markdown("""
        The RRSP meltdown strategy involves strategically withdrawing from your RRSP before age 65
        to minimize lifetime taxes and OAS clawback.
        """)

        if st.button("Compare Meltdown vs Traditional Strategy", type="primary"):
            with st.spinner("Analyzing strategies..."):
                comparison = compare_meltdown_vs_traditional(
                    current_age,
                    retirement_age,
                    rrsp_balance,
                    tfsa_balance,
                    annual_income if current_age < retirement_age else 0,
                    cpp_monthly,
                    years_in_canada,
                    expected_return,
                    annual_spending,
                    oas_start_age,
                    province
                )

                # Display comparison metrics
                st.subheader("Lifetime Comparison")

                col1, col2, col3 = st.columns(3)

                with col1:
                    tax_savings = comparison['comparison']['tax_savings']
                    st.metric("Tax Savings", f"${tax_savings:,.0f}")

                with col2:
                    oas_advantage = comparison['comparison']['oas_advantage']
                    st.metric("Additional OAS Received", f"${oas_advantage:,.0f}")

                with col3:
                    total_advantage = comparison['comparison']['total_financial_advantage']
                    st.metric("Total Financial Advantage", f"${total_advantage:,.0f}")

                # Plot comparison
                meltdown_data = comparison['meltdown_strategy']
                traditional_data = comparison['traditional_strategy']

                # Tax comparison chart
                fig_tax = go.Figure()
                fig_tax.add_trace(go.Bar(x=meltdown_data['age'], y=meltdown_data['total_tax'],
                                        name='Meltdown Strategy'))
                fig_tax.add_trace(go.Bar(x=traditional_data['age'], y=traditional_data['total_tax'],
                                        name='Traditional Strategy'))
                fig_tax.update_layout(title='Annual Taxes Paid',
                                    xaxis_title='Age',
                                    yaxis_title='Taxes ($)',
                                    barmode='group')
                st.plotly_chart(fig_tax, width="stretch")

                # OAS comparison chart
                fig_oas = go.Figure()
                fig_oas.add_trace(go.Scatter(x=meltdown_data['age'], y=meltdown_data['oas_income'],
                                            name='Meltdown Strategy', mode='lines'))
                fig_oas.add_trace(go.Scatter(x=traditional_data['age'], y=traditional_data['oas_income'],
                                            name='Traditional Strategy', mode='lines'))
                fig_oas.update_layout(title='Annual OAS Benefits',
                                    xaxis_title='Age',
                                    yaxis_title='OAS Income ($)',
                                    hovermode='x unified')
                st.plotly_chart(fig_oas, width="stretch")

                # RRSP balance comparison
                fig_rrsp = go.Figure()
                fig_rrsp.add_trace(go.Scatter(x=meltdown_data['age'], y=meltdown_data['rrsp_balance'],
                                             name='Meltdown Strategy', mode='lines'))
                fig_rrsp.add_trace(go.Scatter(x=traditional_data['age'], y=traditional_data['rrsp_balance'],
                                             name='Traditional Strategy', mode='lines'))
                fig_rrsp.update_layout(title='RRSP Balance Over Time',
                                     xaxis_title='Age',
                                     yaxis_title='RRSP Balance ($)',
                                     hovermode='x unified')
                st.plotly_chart(fig_rrsp, width="stretch")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p><small>This tool provides estimates based on 2026 tax rates and benefit amounts.
    Consult with a qualified financial advisor for personalized advice.</small></p>
</div>
""", unsafe_allow_html=True)
