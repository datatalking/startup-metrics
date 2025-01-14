from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Tuple

import plotly.graph_objects as go
import streamlit as st


@dataclass
class Scenario:
    name: str
    revenue_multiplier: float
    expense_multiplier: float
    customer_growth_multiplier: float
    color: str


class GrowthModel(str, Enum):
    FIXED = "Fixed"
    LINEAR = "Linear"
    EXPONENTIAL = "Exponential"


class CustomerType(str, Enum):
    B2B = "B2B"
    B2C = "B2C"


@dataclass
class CustomerMetrics:
    total: int
    new: int
    cac: float
    churn_rate: float
    type: CustomerType


def calculate_runway(cash_balance: float, monthly_burn: float) -> float:
    """Calculate runway in months"""
    if not isinstance(cash_balance, (int, float)) or not isinstance(
        monthly_burn, (int, float)
    ):
        raise ValueError("Cash balance and monthly burn must be numeric values")
    return 0 if monthly_burn <= 0 else cash_balance / monthly_burn


def calculate_burn_rate(revenues: float, expenses: float) -> float:
    """Calculate monthly burn rate"""
    if not isinstance(revenues, (int, float)) or not isinstance(expenses, (int, float)):
        raise ValueError("Revenues and expenses must be numeric values")
    return expenses - revenues


def calculate_mom_growth(current: float, previous: float) -> float:
    """Calculate Month-over-Month growth rate"""
    return 0 if previous == 0 else ((current - previous) / previous) * 100


def calculate_ltv_cac_ratio(ltv: float, cac: float) -> float:
    """Calculate LTV/CAC ratio"""
    return 0 if cac == 0 else ltv / cac


@st.cache_data
def generate_runway_projection(cash_balance, burn_rate, runway_months):
    months = range(int(runway_months) + 1)
    projected_cash = [cash_balance - (burn_rate * month) for month in months]
    dates = [
        (datetime.now() + timedelta(days=30 * month)).strftime("%Y-%m")
        for month in months
    ]
    return dates, projected_cash


def calculate_revenue_projection(
    initial_revenue: float,
    months: int,
    model: GrowthModel,
    linear_coefficient: float = 0,
    exponential_base: float = 0,
) -> List[float]:
    """Calculate revenue projection based on selected model"""
    revenues = []

    for month in range(months + 1):
        if model == GrowthModel.FIXED:
            revenue = initial_revenue
        elif model == GrowthModel.LINEAR:
            # Revenue increases by percentage of initial revenue each month
            monthly_increase = initial_revenue * (linear_coefficient / 100)
            revenue = initial_revenue + (monthly_increase * month)
        else:  # EXPONENTIAL
            # Revenue grows by exponential_base% each month
            revenue = initial_revenue * ((1 + exponential_base / 100) ** month)

        revenues.append(max(0, revenue))  # Ensure revenue doesn't go negative

    return revenues


def calculate_customer_projection(
    b2b_metrics: CustomerMetrics,
    b2c_metrics: CustomerMetrics,
    months: int,
    model: GrowthModel,
    linear_growth: int = 0,
    exponential_growth: float = 0,
) -> dict[str, List[int]]:
    """Calculate customer growth projection for B2B and B2C separately"""
    projections = {}

    for metrics in [b2b_metrics, b2c_metrics]:
        customers = []
        current_customers = metrics.total

        for month in range(months + 1):
            customers.append(current_customers)

            if model == GrowthModel.FIXED:
                current_customers += metrics.new
            elif model == GrowthModel.LINEAR:
                current_customers += metrics.new + (linear_growth * month)
            else:  # EXPONENTIAL
                growth_rate = exponential_growth / 100
                current_customers = int(metrics.total * ((1 + growth_rate) ** month))

        projections[metrics.type] = customers

    return projections


@st.cache_data
def generate_scenario_projections(
    cash_balance: float,
    monthly_revenue: float,
    monthly_expenses: float,
    months: int,
    scenarios: List[Scenario],
    revenue_model: GrowthModel,
    linear_coefficient: float = 0,
    exponential_base: float = 0,
) -> List[Tuple[str, List[str], List[float], str]]:
    """Generate cash projections for multiple scenarios"""
    projections = []

    for scenario in scenarios:
        adjusted_initial_revenue = monthly_revenue * scenario.revenue_multiplier
        adjusted_expenses = monthly_expenses * scenario.expense_multiplier

        # Calculate revenue progression for all months
        revenues = calculate_revenue_projection(
            adjusted_initial_revenue,
            months,
            revenue_model,
            linear_coefficient * scenario.revenue_multiplier,
            exponential_base * scenario.revenue_multiplier,
        )

        dates = [
            (datetime.now() + timedelta(days=30 * month)).strftime("%Y-%m")
            for month in range(months + 1)
        ]

        projected_cash = []
        current_cash = cash_balance

        for month in range(months + 1):
            projected_cash.append(current_cash)
            monthly_burn = calculate_burn_rate(
                revenues[month], adjusted_expenses * (1.02**month)
            )  # 2% expense growth
            current_cash -= monthly_burn

        projections.append((scenario.name, dates, projected_cash, scenario.color))

    return projections


def create_ltv_cac_gauge(ltv_cac_ratio: float, target: float = 3.0) -> go.Figure:
    """Create a gauge chart for LTV/CAC ratio that respects theme settings"""

    # Get current theme
    is_dark_theme = st.get_option("theme.base") == "dark"

    # Define colors based on theme
    colors = {
        "low": "#FF4B4B",  # Bright red (same for both themes)
        "medium": "#FFA500",  # Orange (same for both themes)
        "good": "#00CC96",  # Emerald green (same for both themes)
        "background": "#1F2937" if is_dark_theme else "#F8F9FA",  # Background
        "text": "#F9FAFB" if is_dark_theme else "#2C3E50",  # Text color
    }

    # Create the gauge chart
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=ltv_cac_ratio,
            delta={"reference": target, "position": "bottom"},
            domain={"x": [0, 1], "y": [0, 0.9]},
            gauge={
                "axis": {
                    "range": [None, 5],
                    "tickwidth": 2,
                    "tickcolor": colors["text"],
                    "ticktext": ["0", "1", "2", "3", "4", "5"],
                    "tickvals": [0, 1, 2, 3, 4, 5],
                    "tickfont": {"size": 14, "color": colors["text"]},
                },
                "bar": {"color": colors["text"]},  # Use theme color for the bar
                "bgcolor": colors["background"],
                "borderwidth": 2,
                "bordercolor": colors["text"],
                "steps": [
                    {"range": [0, 1], "color": colors["low"], "line": {"width": 0}},
                    {"range": [1, 2], "color": colors["medium"], "line": {"width": 0}},
                    {"range": [2, 3], "color": colors["good"], "line": {"width": 0}},
                    {"range": [3, 5], "color": colors["medium"], "line": {"width": 0}},
                ],
                "threshold": {
                    "line": {"color": colors["text"], "width": 4},
                    "thickness": 0.8,
                    "value": target,
                },
            },
            title={
                "text": f"LTV/CAC Ratio<br><span style='font-size:0.9em;color:{colors['text']}'>Target: {target}</span>",
                "font": {
                    "size": 20,
                    "color": colors["text"],
                    "family": "Arial, sans-serif",
                },
                "align": "center",
            },
            number={
                "font": {
                    "size": 40,
                    "color": colors["text"],
                    "family": "Arial, sans-serif",
                },
                "prefix": "",
                "suffix": "",
                "valueformat": ".2f",
            },
        )
    )

    # Update layout with theme-aware colors
    fig.update_layout(
        height=350,
        margin=dict(l=30, r=30, t=90, b=30),
        paper_bgcolor=colors["background"],
        plot_bgcolor=colors["background"],
        font={"color": colors["text"], "family": "Arial, sans-serif"},
    )

    return fig


def calculate_customer_flow(
    initial_customers: int,
    new_customers: int,
    churn_rate: float,
    months: int,
    growth_model: GrowthModel,
    linear_growth: float = 0,  # Now represents percentage
    exponential_growth: float = 0,
) -> tuple[list[int], list[int], list[int]]:
    """Calculate monthly customer flow: new, churned, and total customers"""
    new_per_month = []
    churned_per_month = []
    total_customers = []

    current_total = initial_customers
    current_new = new_customers

    for month in range(months + 1):
        # Calculate new customers based on growth model
        if growth_model == GrowthModel.FIXED:
            new_this_month = new_customers
        elif growth_model == GrowthModel.LINEAR:
            # Calculate increase based on percentage of initial new customers
            new_this_month = int(new_customers * (1 + (linear_growth / 100) * month))
        else:  # EXPONENTIAL
            growth_rate = exponential_growth / 100
            new_this_month = int(new_customers * ((1 + growth_rate) ** month))

        # Calculate churn
        churned_this_month = int(current_total * (churn_rate / 100))

        # Update total
        current_total = current_total + new_this_month - churned_this_month
        current_total = max(0, current_total)  # Ensure non-negative

        # Store values
        new_per_month.append(new_this_month)
        churned_per_month.append(churned_this_month)
        total_customers.append(current_total)

    return new_per_month, churned_per_month, total_customers


def calculate_lifetime_from_churn(churn_rate: float) -> float:
    """Calculate expected lifetime in months from monthly churn rate"""
    return 1 / (churn_rate / 100) if churn_rate > 0 else float("inf")


def main():
    st.set_page_config(page_title="Startup Metrics Dashboard", layout="wide")

    st.title("🚀 Startup Metrics Dashboard")

    # Tabs for different metric categories
    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "💰 Financials",
            "📈 Growth Metrics",
            "👥 Customer Metrics",
            "❓ Help & Definitions",
        ]
    )

    # Organize sidebar with expanders for better organization
    with st.sidebar:
        st.title("Dashboard Settings")

        # 1. Financial Inputs
        with st.expander("💰 Financial Inputs", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                cash_balance = st.number_input(
                    "Cash Balance (€)",
                    min_value=0.0,
                    value=100000.0,
                    step=1000.0,
                    format="%0.2f",
                    help="Current cash balance in bank",
                )
            with col2:
                monthly_expenses = st.number_input(
                    "Monthly Expenses (€)",
                    min_value=0.0,
                    value=20000.0,
                    step=1000.0,
                    format="%0.2f",
                    help="Total monthly expenses",
                )

        # 2. Customer Metrics (moved up)
        with st.expander("👥 Customer Metrics", expanded=True):
            st.subheader("B2B Customers")
            col1, col2 = st.columns(2)
            with col1:
                b2b_total = st.number_input(
                    "Total B2B Customers",
                    min_value=0,
                    value=20,
                    help="Current total number of B2B customers",
                )
                b2b_new = st.number_input(
                    "New B2B Customers",
                    min_value=0,
                    value=5,
                    help="New B2B customers this month",
                )
            with col2:
                b2b_cac = st.number_input(
                    "B2B CAC (€)",
                    min_value=0.0,
                    value=500.0,
                    format="%0.2f",
                    help="B2B Customer Acquisition Cost",
                )
                b2b_churn_rate = st.number_input(
                    "B2B Monthly Churn Rate (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=2.0,
                    format="%0.1f",
                    help="Percentage of B2B customers that churn each month",
                )

            st.subheader("B2C Customers")
            col1, col2 = st.columns(2)
            with col1:
                b2c_total = st.number_input(
                    "Total B2C Customers",
                    min_value=0,
                    value=80,
                    help="Current total number of B2C customers",
                )
                b2c_new = st.number_input(
                    "New B2C Customers",
                    min_value=0,
                    value=15,
                    help="New B2C customers this month",
                )
            with col2:
                b2c_cac = st.number_input(
                    "B2C CAC (€)",
                    min_value=0.0,
                    value=50.0,
                    format="%0.2f",
                    help="B2C Customer Acquisition Cost",
                )
                b2c_churn_rate = st.number_input(
                    "B2C Monthly Churn Rate (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=5.0,
                    format="%0.1f",
                    help="Percentage of B2C customers that churn each month",
                )

        # 3. Revenue Model
        with st.expander("📈 Revenue Model", expanded=True):
            revenue_growth_model = st.selectbox(
                "Revenue Growth Model",
                options=[model.value for model in GrowthModel],
                help="Select how revenue grows over time",
            )

            # Current and Previous Revenue
            col1, col2 = st.columns(2)
            with col1:
                monthly_revenue = st.number_input(
                    "Current Revenue (€)",
                    min_value=0.0,
                    value=10000.0,
                    step=1000.0,
                    format="%0.2f",
                )
            with col2:
                previous_month_revenue = st.number_input(
                    "Previous Revenue (€)",
                    min_value=0.0,
                    value=8000.0,
                    step=1000.0,
                    format="%0.2f",
                )

            # Growth Parameters based on selected model
            if revenue_growth_model == GrowthModel.LINEAR:
                revenue_linear_coefficient = st.slider(
                    "Monthly Revenue Increase (%)",
                    min_value=0.0,
                    max_value=200.0,
                    value=10.0,
                    step=1.0,
                    help="Percentage by which revenue increases each month",
                )
                revenue_exponential_base = 0

                monthly_increase = monthly_revenue * (revenue_linear_coefficient / 100)
                st.caption(
                    f"""
                    Revenue will increase by {revenue_linear_coefficient}% (€{monthly_increase:,.2f}) each month
                    """
                )

            elif revenue_growth_model == GrowthModel.EXPONENTIAL:
                revenue_exponential_base = st.slider(
                    "Monthly Revenue Growth Rate (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=10.0,
                    step=1.0,
                    help="Percentage by which revenue grows each month",
                )
                revenue_linear_coefficient = 0

                st.caption(
                    f"Revenue will grow by {revenue_exponential_base}% each month"
                )
            else:
                st.caption("Revenue will remain constant at the initial value")
                revenue_linear_coefficient = 0
                revenue_exponential_base = 0

        # 4. Customer Acquisition Model
        with st.expander("👥 Customer Acquisition Model", expanded=True):
            # B2B Growth Model
            st.subheader("B2B Customer Growth")
            b2b_growth_model = st.selectbox(
                "B2B Growth Model",
                options=[model.value for model in GrowthModel],
                help="Select how B2B customer acquisition grows over time",
                key="b2b_growth",
            )

            if b2b_growth_model == GrowthModel.LINEAR:
                b2b_linear_growth = st.slider(
                    "Monthly B2B Growth Rate (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=10.0,
                    step=1.0,
                    help="Percentage by which B2B customer acquisition increases each month",
                )
                b2b_exponential_growth = 0

                monthly_increase = int(b2b_new * (b2b_linear_growth / 100))
                st.caption(
                    f"B2B acquisition will increase by {b2b_linear_growth}% ({monthly_increase} customers) each month"
                )

            elif b2b_growth_model == GrowthModel.EXPONENTIAL:
                b2b_exponential_growth = st.slider(
                    "Monthly B2B Growth Rate (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=3.0,
                    step=0.5,
                    help="Percentage by which B2B acquisition grows each month",
                )
                b2b_linear_growth = 0

                st.caption(
                    f"B2B acquisition will grow by {b2b_exponential_growth}% each month"
                )
            else:
                st.caption("B2B acquisition will remain constant")
                b2b_linear_growth = 0
                b2b_exponential_growth = 0

            # B2C Growth Model
            st.subheader("B2C Customer Growth")
            b2c_growth_model = st.selectbox(
                "B2C Growth Model",
                options=[model.value for model in GrowthModel],
                help="Select how B2C customer acquisition grows over time",
                key="b2c_growth",
            )

            if b2c_growth_model == GrowthModel.LINEAR:
                b2c_linear_growth = st.slider(
                    "Monthly B2C Growth Rate (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=15.0,
                    step=1.0,
                    help="Percentage by which B2C customer acquisition increases each month",
                )
                b2c_exponential_growth = 0

                monthly_increase = int(b2c_new * (b2c_linear_growth / 100))
                st.caption(
                    f"B2C acquisition will increase by {b2c_linear_growth}% ({monthly_increase} customers) each month"
                )

            elif b2c_growth_model == GrowthModel.EXPONENTIAL:
                b2c_exponential_growth = st.slider(
                    "Monthly B2C Growth Rate (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=5.0,
                    step=0.5,
                    help="Percentage by which B2C acquisition grows each month",
                )
                b2c_linear_growth = 0

                st.caption(
                    f"B2C acquisition will grow by {b2c_exponential_growth}% each month"
                )
            else:
                st.caption("B2C acquisition will remain constant")
                b2c_linear_growth = 0
                b2c_exponential_growth = 0

        # 5. Scenario Analysis
        with st.expander("🔄 Scenario Analysis", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                show_scenarios = st.toggle(
                    "Enable Scenario Analysis",
                    value=False,
                    help="Analyze different business scenarios to understand potential outcomes and plan accordingly.",
                )
            with col2:
                projection_months = st.slider(
                    "Projection Period (months)",
                    min_value=3,
                    max_value=36,
                    value=12,
                    step=3,
                    help="Number of months to project into the future",
                )

            # Define scenarios
            scenarios = [
                Scenario("Best Case", 1.2, 0.9, 1.15, "green"),
                Scenario("Normal Case", 1.0, 1.0, 1.10, "blue"),
                Scenario("Worst Case", 0.8, 1.1, 1.05, "red"),
            ]

    # In main() function, before calculations
    if cash_balance < 0 or monthly_revenue < 0 or monthly_expenses < 0:
        st.error("Financial values cannot be negative")
        return

    if b2b_total < 0 or b2b_new > b2b_total or b2c_total < 0 or b2c_new > b2c_total:
        st.error("Invalid customer metrics")
        return

    # Store initial values
    initial_b2b_total = b2b_total
    initial_b2c_total = b2c_total

    # Calculate metrics
    burn_rate = calculate_burn_rate(monthly_revenue, monthly_expenses)
    runway_months = calculate_runway(cash_balance, burn_rate)
    mom_growth = calculate_mom_growth(monthly_revenue, previous_month_revenue)

    # Customer metrics calculations
    b2b_metrics = CustomerMetrics(
        b2b_total, b2b_new, b2b_cac, b2b_churn_rate, CustomerType.B2B
    )
    b2c_metrics = CustomerMetrics(
        b2c_total, b2c_new, b2c_cac, b2c_churn_rate, CustomerType.B2C
    )

    total_customers = b2b_total + b2c_total
    new_customers = b2b_new + b2c_new

    # Weighted average calculations
    weighted_cac = (
        (b2b_cac * b2b_total + b2c_cac * b2c_total) / total_customers
        if total_customers > 0
        else 0
    )
    weighted_churn = (
        (b2b_churn_rate * b2b_total + b2c_churn_rate * b2c_total) / total_customers
        if total_customers > 0
        else 0
    )
    average_lifetime = calculate_lifetime_from_churn(weighted_churn)

    arpu = monthly_revenue / total_customers if total_customers > 0 else 0
    ltv = arpu * average_lifetime
    ltv_cac_ratio = calculate_ltv_cac_ratio(ltv, weighted_cac)
    conversion_rate = (
        (new_customers / total_customers * 100) if total_customers > 0 else 0
    )

    with tab1:
        # Financial Metrics
        if show_scenarios:
            # Show metrics for each scenario
            st.subheader("Scenario Analysis")

            # Calculate metrics for each scenario
            for i, scenario in enumerate(scenarios):
                adjusted_revenue = monthly_revenue * scenario.revenue_multiplier
                adjusted_expenses = monthly_expenses * scenario.expense_multiplier
                scenario_burn_rate = calculate_burn_rate(
                    adjusted_revenue, adjusted_expenses
                )
                scenario_runway = calculate_runway(cash_balance, scenario_burn_rate)

                # Add divider before scenarios (except the first one)
                if i > 0:
                    st.divider()

                # Create a container with scenario color
                with st.container():
                    st.markdown(
                        f"#### {scenario.name}"
                    )  # The emoji is now part of the name
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(
                            "Monthly Burn Rate",
                            f"€{scenario_burn_rate:,.2f}",
                            delta=f"€{scenario_burn_rate - burn_rate:,.2f}",
                        )
                    with col2:
                        st.metric(
                            "Runway",
                            f"{scenario_runway:.1f} months",
                            delta=f"{scenario_runway - runway_months:.1f} months",
                        )
                    with col3:
                        st.metric(
                            "Monthly Revenue",
                            f"€{adjusted_revenue:,.2f}",
                            delta=f"€{adjusted_revenue - monthly_revenue:,.2f}",
                        )
        else:
            # Original single scenario metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Monthly Burn Rate", f"€{burn_rate:,.2f}")
            with col2:
                st.metric("Runway", f"{runway_months:.1f} months")
            with col3:
                st.metric("Monthly Revenue", f"€{monthly_revenue:,.2f}")

        # Modified Runway projection chart
        st.subheader("Cash Projection Analysis")

        if show_scenarios:
            scenario_projections = generate_scenario_projections(
                cash_balance,
                monthly_revenue,
                monthly_expenses,
                projection_months,
                scenarios,
                GrowthModel(revenue_growth_model),
                revenue_linear_coefficient,
                revenue_exponential_base,
            )

            fig = go.Figure()

            for name, dates, projected_cash, color in scenario_projections:
                fig.add_trace(
                    go.Scatter(
                        x=dates,
                        y=projected_cash,
                        mode="lines",
                        name=name,
                        line=dict(color=color),
                        hovertemplate="Date: %{x}<br>Cash: €%{y:,.2f}<extra></extra>",
                    )
                )

            fig.add_hline(
                y=0, line_dash="dash", line_color="gray", annotation_text="Zero Cash"
            )

            fig.update_layout(
                title=f"Scenario Analysis - {projection_months} Month Cash Projection",
                xaxis_title="Date",
                yaxis_title="Cash Balance (€)",
                showlegend=True,
                legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
                hovermode="x unified",
            )
        else:
            # Original single projection chart code
            dates, projected_cash = generate_runway_projection(
                cash_balance, burn_rate, runway_months
            )

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=projected_cash,
                    mode="lines+markers",
                    name="Projected Cash",
                )
            )

            fig.add_hline(y=0, line_dash="dash", line_color="red")
            fig.update_layout(
                title="Cash Runway Projection",
                xaxis_title="Date",
                yaxis_title="Cash Balance (€)",
                showlegend=True,
            )

        st.plotly_chart(fig, use_container_width=True)

        if show_scenarios:
            # Update info box to include revenue model information
            revenue_model_info = {
                GrowthModel.FIXED: "Fixed monthly revenue",
                GrowthModel.LINEAR: f"Revenue increases by €{revenue_linear_coefficient:,.2f} per month",
                GrowthModel.EXPONENTIAL: f"Revenue grows by {revenue_exponential_base}% per month",
            }

            st.info(
                f"""
            **Revenue Growth Model**: {revenue_growth_model}
            {f"- Monthly increase: €{revenue_linear_coefficient:,.2f}" if revenue_growth_model == GrowthModel.LINEAR else ""}
            {f"- Monthly growth rate: {revenue_exponential_base}%" if revenue_growth_model == GrowthModel.EXPONENTIAL else ""}

            **Customer Growth Model**: {b2b_growth_model}
            {f"- Monthly increase: {b2b_linear_growth} customers" if b2b_growth_model == GrowthModel.LINEAR else ""}
            {f"- Monthly growth rate: {b2b_exponential_growth}%" if b2b_growth_model == GrowthModel.EXPONENTIAL else ""}

            **Scenario Assumptions:**
            - Best Case: 20% higher revenue, 10% lower expenses, 15% monthly growth
            - Normal Case: Base case with 10% monthly growth
            - Worst Case: 20% lower revenue, 10% higher expenses, 5% monthly growth
            """
            )

    with tab2:
        # Growth Metrics
        col1, col2 = st.columns(2)
        with col1:
            st.metric("MoM Growth", f"{mom_growth:.1f}%")
        with col2:
            st.metric("New Customers", new_customers)

        # Revenue Growth Visualization
        st.subheader("Revenue Growth Visualization")

        # Generate dates for x-axis
        projection_dates = [
            (datetime.now() + timedelta(days=30 * month)).strftime("%Y-%m")
            for month in range(projection_months + 1)
        ]

        if show_scenarios:
            # Create revenue projections for each scenario
            fig_growth = go.Figure()

            for scenario in scenarios:
                adjusted_revenue = monthly_revenue * scenario.revenue_multiplier
                scenario_projection = calculate_revenue_projection(
                    adjusted_revenue,
                    projection_months,
                    GrowthModel(revenue_growth_model),
                    revenue_linear_coefficient * scenario.revenue_multiplier,
                    revenue_exponential_base * scenario.revenue_multiplier,
                )

                fig_growth.add_trace(
                    go.Scatter(
                        x=projection_dates,
                        y=scenario_projection,
                        mode="lines",
                        name=f"{scenario.name}",
                        line=dict(color=scenario.color),
                        hovertemplate="Date: %{x}<br>Revenue: €%{y:,.2f}<extra></extra>",
                    )
                )
        else:
            # Original single projection visualization
            fig_growth = go.Figure()
            revenue_projection = calculate_revenue_projection(
                monthly_revenue,
                projection_months,
                GrowthModel(revenue_growth_model),
                revenue_linear_coefficient,
                revenue_exponential_base,
            )

            fig_growth.add_trace(
                go.Scatter(
                    x=projection_dates,
                    y=revenue_projection,
                    mode="lines+markers",
                    name="Projected Revenue",
                    hovertemplate="Date: %{x}<br>Revenue: €%{y:,.2f}<extra></extra>",
                )
            )

        fig_growth.update_layout(
            title="Revenue Growth Projection",
            xaxis_title="Month",
            yaxis_title="Revenue (€)",
            showlegend=True,
            hovermode="x unified",
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        )
        st.plotly_chart(fig_growth, use_container_width=True)

        # Customer Growth Projection
        st.subheader("Customer Growth Projection")

        # Generate dates for x-axis
        projection_dates = [
            (datetime.now() + timedelta(days=30 * month)).strftime("%Y-%m")
            for month in range(projection_months + 1)
        ]

        # B2B Customer Flow
        st.subheader("B2B Customer Flow")
        b2b_new, b2b_churned, b2b_total = calculate_customer_flow(
            initial_b2b_total,
            b2b_new,
            b2b_churn_rate,
            projection_months,
            GrowthModel(b2b_growth_model),
            b2b_linear_growth,
            b2b_exponential_growth,
        )

        fig_b2b = go.Figure()
        fig_b2b.add_trace(
            go.Scatter(
                x=projection_dates,
                y=b2b_total,
                mode="lines",
                name="Total B2B",
                line=dict(color="blue", width=3),
                hovertemplate="Date: %{x}<br>Total: %{y:,.0f}<extra></extra>",
            )
        )
        fig_b2b.add_trace(
            go.Bar(
                x=projection_dates,
                y=b2b_new,
                name="New B2B",
                marker_color="green",
                hovertemplate="Date: %{x}<br>New: %{y:,.0f}<extra></extra>",
            )
        )
        fig_b2b.add_trace(
            go.Bar(
                x=projection_dates,
                y=[-x for x in b2b_churned],  # Negative values for churned
                name="Churned B2B",
                marker_color="red",
                hovertemplate="Date: %{x}<br>Churned: %{y:,.0f}<extra></extra>",
            )
        )

        fig_b2b.update_layout(
            title="B2B Customer Flow",
            xaxis_title="Month",
            yaxis_title="Number of Customers",
            barmode="relative",
            hovermode="x unified",
        )
        st.plotly_chart(fig_b2b, use_container_width=True)

        # B2C Customer Flow
        st.subheader("B2C Customer Flow")
        b2c_new, b2c_churned, b2c_total = calculate_customer_flow(
            b2c_total,
            b2c_new,
            b2c_churn_rate,
            projection_months,
            GrowthModel(b2c_growth_model),
            b2c_linear_growth,
            b2c_exponential_growth,
        )

        fig_b2c = go.Figure()
        fig_b2c.add_trace(
            go.Scatter(
                x=projection_dates,
                y=b2c_total,
                mode="lines",
                name="Total B2C",
                line=dict(color="blue", width=3),
                hovertemplate="Date: %{x}<br>Total: %{y:,.0f}<extra></extra>",
            )
        )
        fig_b2c.add_trace(
            go.Bar(
                x=projection_dates,
                y=b2c_new,
                name="New B2C",
                marker_color="green",
                hovertemplate="Date: %{x}<br>New: %{y:,.0f}<extra></extra>",
            )
        )
        fig_b2c.add_trace(
            go.Bar(
                x=projection_dates,
                y=[-x for x in b2c_churned],  # Negative values for churned
                name="Churned B2C",
                marker_color="red",
                hovertemplate="Date: %{x}<br>Churned: %{y:,.0f}<extra></extra>",
            )
        )

        fig_b2c.update_layout(
            title="B2C Customer Flow",
            xaxis_title="Month",
            yaxis_title="Number of Customers",
            barmode="relative",
            hovermode="x unified",
        )
        st.plotly_chart(fig_b2c, use_container_width=True)

        if show_scenarios:
            st.info(
                """
            **Customer Growth Assumptions:**
            - Growth follows the selected revenue model
            - Best Case: 15% higher customer growth
            - Normal Case: Base growth rate
            - Worst Case: 5% lower customer growth
            """
            )

    with tab3:
        # Customer Metrics Overview
        st.subheader("Customer Metrics Overview")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("ARPU", f"€{arpu:,.2f}")
        with col2:
            st.metric("LTV", f"€{ltv:,.2f}")
        with col3:
            st.metric("CAC", f"€{weighted_cac:,.2f}")
        with col4:
            st.metric("LTV/CAC Ratio", f"{ltv_cac_ratio:.2f}")

        # LTV/CAC Analysis
        st.subheader("LTV/CAC Analysis")
        col1, col2 = st.columns([2, 1])
        with col1:
            gauge_fig = create_ltv_cac_gauge(ltv_cac_ratio)
            st.plotly_chart(gauge_fig, use_container_width=True)
        with col2:
            st.markdown(
                """
            ### Understanding LTV/CAC
            The LTV to CAC ratio measures the relationship between:
            - **LTV**: Lifetime Value of a customer
            - **CAC**: Customer Acquisition Cost
            """
            )

        # B2B Metrics
        st.subheader("B2B Metrics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("B2B Customers", initial_b2b_total)
        with col2:
            st.metric("B2B CAC", f"€{b2b_cac:,.2f}")
        with col3:
            st.metric("B2B Churn Rate", f"{b2b_churn_rate}%")

        # B2C Metrics
        st.subheader("B2C Metrics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("B2C Customers", initial_b2c_total)
        with col2:
            st.metric("B2C CAC", f"€{b2c_cac:,.2f}")
        with col3:
            st.metric("B2C Churn Rate", f"{b2c_churn_rate}%")

    with tab4:
        st.markdown(
            """
        <h3 style='font-size: 1.5em;'>📚 Metrics Guide</h3>
        """,
            unsafe_allow_html=True,
        )

        # Financial Metrics Section
        st.markdown(
            """
        <h4 style='font-size: 1.2em; margin-top: 1em;'>💰 Financial Metrics</h4>
        """,
            unsafe_allow_html=True,
        )

        with st.expander("Monthly Burn Rate"):
            st.markdown(
                """
            - **What it is:** The amount of money you're losing (or gaining) each month
            - **How it's calculated:** Monthly Expenses - Monthly Revenue
            - **Why it matters:** Shows how quickly you're using your cash
            """
            )

        with st.expander("Runway"):
            st.markdown(
                """
            - **What it is:** How long your cash will last at the current burn rate
            - **How it's calculated:** Cash Balance ÷ Monthly Burn Rate
            - **Why it matters:** Tells you how many months you can operate before needing more funding
            """
            )

        # Growth Metrics Section
        st.markdown(
            """
        <h4 style='font-size: 1.2em; margin-top: 1em;'>📈 Growth Metrics</h4>
        """,
            unsafe_allow_html=True,
        )

        with st.expander("Month-over-Month (MoM) Growth"):
            st.markdown(
                """
            - **What it is:** How much your revenue grew compared to last month
            - **How it's calculated:** ((Current Revenue - Previous Revenue) ÷ Previous Revenue) × 100
            - **Why it matters:** Shows if your business is growing and how fast
            """
            )

        with st.expander("Growth Models"):
            st.markdown(
                """
            **Fixed Growth**
            - Growth stays the same each month
            - Predictable but may not reflect reality

            **Linear Growth**
            - Growth increases by a fixed percentage each month
            - Good for steady, predictable growth

            **Exponential Growth**
            - Growth compounds, growing faster over time
            - Typical for successful startups
            """
            )

        # Customer Metrics Section
        st.markdown(
            """
        <h4 style='font-size: 1.2em; margin-top: 1em;'>👥 Customer Metrics</h4>
        """,
            unsafe_allow_html=True,
        )

        with st.expander("ARPU (Average Revenue Per User)"):
            st.markdown(
                """
            - **What it is:** How much revenue you get from each customer
            - **How it's calculated:** Monthly Revenue ÷ Total Customers
            - **Why it matters:** Shows how valuable each customer is
            """
            )

        with st.expander("LTV (Lifetime Value)"):
            st.markdown(
                """
            - **What it is:** How much revenue you expect from a customer over their entire relationship
            - **How it's calculated:** ARPU × Average Customer Lifetime
            - **Why it matters:** Shows how much you can spend to acquire customers
            """
            )

        with st.expander("CAC (Customer Acquisition Cost)"):
            st.markdown(
                """
            - **What it is:** How much you spend to get a new customer
            - **How it's calculated:** Total Acquisition Costs ÷ New Customers
            - **Why it matters:** Helps ensure you're not spending too much to acquire customers
            """
            )

        with st.expander("LTV/CAC Ratio"):
            st.markdown(
                """
            - **What it is:** Relationship between customer value and acquisition cost
            - **How it's calculated:** LTV ÷ CAC
            - **Target ranges:**
                • 🔴 Below 1: Losing money on each customer
                • 🟠 1-2: Need to improve efficiency
                • 🟢 2-3: Healthy business model
                • 🔵 Above 3: Potential to scale faster
            """
            )

        with st.expander("Churn Rate"):
            st.markdown(
                """
            - **What it is:** Percentage of customers you lose each month
            - **How it's calculated:** (Lost Customers ÷ Total Customers) × 100
            - **Why it matters:** Shows how well you retain customers
            - **Typical ranges:**
                • 🟢 < 2%: Excellent retention
                • 🟠 2-5%: Normal range
                • 🔴 > 5%: Needs attention
            """
            )

        # Scenario Analysis Section
        st.markdown(
            """
        <h4 style='font-size: 1.2em; margin-top: 1em;'>🔄 Scenario Analysis</h4>
        """,
            unsafe_allow_html=True,
        )

        with st.expander("Best Case Scenario (🟢)"):
            st.markdown(
                """
            - Revenue grows faster than expected (+20%)
            - Expenses are lower than planned (-10%)
            - Customer growth is strong (+15%)
            - Churn rates decrease
            """
            )

        with st.expander("Normal Case Scenario (🟠)"):
            st.markdown(
                """
            - Things go according to plan
            - Moderate growth and expenses
            - Expected customer acquisition
            - Stable churn rates
            """
            )

        with st.expander("Worst Case Scenario (🔴)"):
            st.markdown(
                """
            - Revenue is lower than expected (-20%)
            - Expenses are higher than planned (+10%)
            - Growth is slower (+5%)
            - Higher churn rates
            """
            )


if __name__ == "__main__":
    main()
