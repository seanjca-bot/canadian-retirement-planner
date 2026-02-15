"""
Ontario Retirement Planner - Streamlit Application

A comprehensive retirement planning tool for Ontario residents.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

from src.calculations.cpp_oas import calculate_cpp_benefit, calculate_oas_benefit, project_cpp_oas_income
from src.calculations.rrsp_tfsa import project_registered_accounts, project_all_accounts, calculate_rrif_minimum_table
from src.calculations.taxes import calculate_total_tax, project_lifetime_taxes
from src.calculations.monte_carlo import run_monte_carlo_simulation, calculate_safe_withdrawal_rate, compare_strategies
from src.strategies.rrsp_meltdown import compare_meltdown_vs_traditional, simulate_meltdown_strategy

# Page configuration
st.set_page_config(
    page_title="Ontario Retirement Planner",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title
st.title("🏦 Ontario Retirement Planner")
st.markdown("Plan your retirement with CPP/OAS projections, tax optimization, and Monte Carlo simulations")

# Sidebar - User Inputs
st.sidebar.header("Your Information")

# Personal Information
with st.sidebar.expander("📋 Personal Details", expanded=True):
    current_age = st.number_input("Current Age", min_value=18, max_value=100, value=55)
    retirement_age = st.number_input("Planned Retirement Age", min_value=current_age, max_value=75, value=65)
    years_in_canada = st.number_input("Years in Canada (after age 18)", min_value=0, max_value=80, value=40)

# Financial Information
with st.sidebar.expander("💰 Current Finances", expanded=True):
    rrsp_balance = st.number_input("Current RRSP Balance ($)", min_value=0, value=500000, step=10000)
    tfsa_balance = st.number_input("Current TFSA Balance ($)", min_value=0, value=100000, step=10000)
    nonreg_balance = st.number_input("Non-Registered Savings ($)", min_value=0, value=200000, step=10000)
    st.caption("💡 Non-registered: Taxable investment accounts (capital gains tax applies)")
    annual_income = st.number_input("Current Annual Income ($)", min_value=0, value=80000, step=5000)
    annual_savings = st.number_input("Annual Savings/Contributions ($)", min_value=0, value=20000, step=1000)

# CPP/OAS Information
with st.sidebar.expander("🇨🇦 CPP/OAS Details", expanded=True):
    cpp_start_age = st.slider("CPP Start Age", min_value=60, max_value=70, value=65)
    cpp_contribution_years = st.number_input("Years of CPP Contributions", min_value=0, max_value=47, value=35)
    cpp_earnings_ratio = st.slider("Average Earnings (% of YMPE)", min_value=0, max_value=100, value=80) / 100
    st.markdown("---")
    oas_start_age = st.slider("OAS Start Age", min_value=65, max_value=70, value=65)
    st.caption("💡 Deferring OAS increases benefits by 0.6% per month (7.2% per year)")

# Retirement Spending
with st.sidebar.expander("💳 Retirement Spending", expanded=True):
    annual_spending = st.number_input("Annual Retirement Spending ($)", min_value=0, value=60000, step=5000)
    st.markdown("---")
    withdrawal_strategy = st.selectbox(
        "Withdrawal Strategy",
        options=['tax_efficient', 'rrsp_first', 'proportional'],
        format_func=lambda x: {
            'tax_efficient': '🟢 Tax-Efficient (TFSA → Non-Reg → RRSP)',
            'rrsp_first': '🔴 RRSP First (RRSP → Non-Reg → TFSA)',
            'proportional': '🟡 Proportional (All accounts equally)'
        }[x],
        index=0
    )
    if withdrawal_strategy == 'tax_efficient':
        st.caption("💡 Minimizes taxes by using tax-free accounts first")
    elif withdrawal_strategy == 'rrsp_first':
        st.caption("💡 Reduces RRSP balance early, preserves TFSA for emergencies")
    else:
        st.caption("💡 Withdraws proportionally from all accounts")

# Investment Assumptions
with st.sidebar.expander("📈 Investment Assumptions", expanded=False):
    expected_return = st.slider("Expected Annual Return (%)", min_value=0.0, max_value=15.0, value=6.0, step=0.5) / 100
    return_std_dev = st.slider("Return Std Deviation (%)", min_value=0.0, max_value=30.0, value=12.0, step=1.0) / 100

# Main content tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Overview", "🎯 CPP/OAS", "💼 RRSP/TFSA", "🎲 Monte Carlo", "🔥 RRSP Meltdown"])

# Tab 1: Overview
with tab1:
    st.header("Retirement Overview")

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

    # Simple projection
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
        title=f'Portfolio Balance Over Time ({strategy_names[withdrawal_strategy]} Strategy)',
        xaxis_title='Age',
        yaxis_title='Balance ($)',
        hovermode='x unified',
        showlegend=True
    )
    st.plotly_chart(fig, use_container_width=True)

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
        st.plotly_chart(fig_cpp, use_container_width=True)

        st.dataframe(df_cpp.style.format({'Annual Benefit': '${:,.0f}'}), use_container_width=True)

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
        st.plotly_chart(fig_oas, use_container_width=True)

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
        st.plotly_chart(fig_oas_start, use_container_width=True)

    with col4:
        st.dataframe(df_oas_start.style.format({
            'Annual Benefit': '${:,.0f}',
            'Bonus %': '{:.1f}%'
        }), use_container_width=True)

        st.info("💡 **Tip**: If you have significant RRSP/investment income, deferring OAS can help avoid or reduce clawback.")

# Tab 3: All Account Withdrawal Strategies
with tab3:
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
        annual_withdrawal_amount=annual_spending
    )

    rrsp_first = project_all_accounts(
        current_age, retirement_age, projection_years,
        rrsp_balance, tfsa_balance, nonreg_balance, annual_savings,
        withdrawal_strategy='rrsp_first',
        annual_withdrawal_amount=annual_spending
    )

    proportional = project_all_accounts(
        current_age, retirement_age, projection_years,
        rrsp_balance, tfsa_balance, nonreg_balance, annual_savings,
        withdrawal_strategy='proportional',
        annual_withdrawal_amount=annual_spending
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
        st.plotly_chart(fig_te, use_container_width=True)

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
        st.plotly_chart(fig_rrsp, use_container_width=True)

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
        st.plotly_chart(fig_prop, use_container_width=True)

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
    st.plotly_chart(fig_withdrawals, use_container_width=True)

    # RRIF Minimum Withdrawal Table
    st.subheader("RRIF Minimum Withdrawal Rates")
    rrif_table = calculate_rrif_minimum_table(65, 95)
    df_rrif = pd.DataFrame(list(rrif_table.items()), columns=['Age', 'Minimum Rate (%)'])
    df_rrif['Minimum Rate (%)'] = df_rrif['Minimum Rate (%)'] * 100

    col1, col2 = st.columns([1, 2])
    with col1:
        st.dataframe(df_rrif.style.format({'Minimum Rate (%)': '{:.2f}%'}), height=400)

# Tab 4: Monte Carlo Simulation
with tab4:
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
            st.plotly_chart(fig_mc, use_container_width=True)

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

# Tab 5: RRSP Meltdown Strategy
with tab5:
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
                oas_start_age
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
            st.plotly_chart(fig_tax, use_container_width=True)

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
            st.plotly_chart(fig_oas, use_container_width=True)

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
            st.plotly_chart(fig_rrsp, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p><small>This tool provides estimates based on 2026 tax rates and benefit amounts.
    Consult with a qualified financial advisor for personalized advice.</small></p>
</div>
""", unsafe_allow_html=True)
