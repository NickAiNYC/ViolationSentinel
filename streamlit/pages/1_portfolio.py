"""
ViolationSentinel - Portfolio Dashboard
Multi-building violation monitoring for property managers

Track all your buildings in one place with real-time risk scores.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os

# Page configuration
st.set_page_config(
    page_title="Portfolio Dashboard - ViolationSentinel",
    page_icon="📊",
    layout="wide"
)

# Environment configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
STRIPE_CHECKOUT_URL = os.getenv("STRIPE_CHECKOUT_URL", "https://buy.stripe.com/test_placeholder")

# Custom CSS
st.markdown("""
<style>
    .portfolio-header {
        font-size: 2rem;
        color: #1E3A8A;
        font-weight: 700;
    }
    .risk-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-weight: 600;
        font-size: 0.875rem;
    }
    .risk-critical { background: #FEE2E2; color: #991B1B; }
    .risk-high { background: #FFEDD5; color: #9A3412; }
    .risk-medium { background: #FEF3C7; color: #92400E; }
    .risk-low { background: #D1FAE5; color: #065F46; }
    .building-card {
        background: white;
        border: 1px solid #E5E7EB;
        border-radius: 0.75rem;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .stat-highlight {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.75rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state from main app
if "portfolio" not in st.session_state:
    st.session_state.portfolio = []
if "user_tier" not in st.session_state:
    st.session_state.user_tier = "free"


def get_risk_level(risk_score: float) -> tuple:
    """Get risk level label and CSS class from score."""
    if risk_score >= 0.8:
        return "CRITICAL", "risk-critical"
    elif risk_score >= 0.6:
        return "HIGH", "risk-high"
    elif risk_score >= 0.4:
        return "MEDIUM", "risk-medium"
    else:
        return "LOW", "risk-low"


def generate_mock_portfolio_data() -> list:
    """Generate realistic mock portfolio data for demonstration."""
    return [
        {
            "bbl": "3012340056",
            "address": "123 Atlantic Ave, Brooklyn",
            "units": 24,
            "year_built": 1962,
            "risk_score": 0.87,
            "exposure": 34500,
            "open_violations": 5,
            "class_c": 2,
            "class_b": 2,
            "class_a": 1,
            "last_scan": datetime.now() - timedelta(hours=2),
        },
        {
            "bbl": "3023450067",
            "address": "456 Court St, Brooklyn",
            "units": 18,
            "year_built": 1955,
            "risk_score": 0.72,
            "exposure": 22000,
            "open_violations": 3,
            "class_c": 1,
            "class_b": 1,
            "class_a": 1,
            "last_scan": datetime.now() - timedelta(hours=4),
        },
        {
            "bbl": "3034560078",
            "address": "789 Smith St, Brooklyn",
            "units": 32,
            "year_built": 1978,
            "risk_score": 0.45,
            "exposure": 8500,
            "open_violations": 2,
            "class_c": 0,
            "class_b": 1,
            "class_a": 1,
            "last_scan": datetime.now() - timedelta(hours=6),
        },
        {
            "bbl": "3045670089",
            "address": "321 Bergen St, Brooklyn",
            "units": 12,
            "year_built": 1985,
            "risk_score": 0.28,
            "exposure": 3500,
            "open_violations": 1,
            "class_c": 0,
            "class_b": 0,
            "class_a": 1,
            "last_scan": datetime.now() - timedelta(hours=8),
        },
    ]


# Header
st.markdown("<h1 class='portfolio-header'>📊 Portfolio Dashboard</h1>", unsafe_allow_html=True)
st.markdown("Track all your buildings in one place with real-time risk monitoring.")

st.divider()

# Check user tier
if st.session_state.user_tier == "free":
    st.warning("""
    🔒 **Portfolio Dashboard is a Pro feature**
    
    Upgrade to Pro ($199/mo) to access:
    - Multi-building portfolio view
    - Aggregated risk analytics
    - Trend analysis over time
    - Export compliance reports
    """)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(f"""
            <a href="{STRIPE_CHECKOUT_URL}" target="_blank" style="
                background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
                color: white;
                padding: 0.75rem 1.5rem;
                border-radius: 0.5rem;
                text-decoration: none;
                font-weight: bold;
                display: inline-block;
            ">
                🔓 Upgrade to Pro: $199/mo
            </a>
        """, unsafe_allow_html=True)
    
    st.divider()
    st.info("👇 **Preview**: Here's what your portfolio dashboard could look like:")

# Get portfolio data (use mock data for demo)
portfolio_data = generate_mock_portfolio_data()

if not portfolio_data:
    st.info("No buildings in your portfolio yet. Add buildings from the main dashboard.")
else:
    # Portfolio Summary Metrics
    total_buildings = len(portfolio_data)
    total_units = sum(p["units"] for p in portfolio_data)
    total_exposure = sum(p["exposure"] for p in portfolio_data)
    total_violations = sum(p["open_violations"] for p in portfolio_data)
    total_class_c = sum(p["class_c"] for p in portfolio_data)
    avg_risk = sum(p["risk_score"] for p in portfolio_data) / total_buildings
    
    # Summary Cards
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("🏢 Buildings", total_buildings)
    
    with col2:
        st.metric("🏠 Total Units", total_units)
    
    with col3:
        st.metric("💰 Total Exposure", f"${total_exposure:,.0f}")
    
    with col4:
        st.metric("⚠️ Open Violations", total_violations, delta=f"{total_class_c} Class C", delta_color="inverse")
    
    with col5:
        risk_level, _ = get_risk_level(avg_risk)
        st.metric("📊 Avg Risk", f"{avg_risk:.0%}", delta=risk_level, delta_color="inverse" if risk_level in ["CRITICAL", "HIGH"] else "normal")
    
    st.divider()
    
    # Two column layout for charts and table
    chart_col, table_col = st.columns([1, 1])
    
    with chart_col:
        st.subheader("📈 Risk Distribution")
        
        # Create DataFrame for visualization
        df = pd.DataFrame(portfolio_data)
        
        # Risk score bar chart
        fig = px.bar(
            df,
            x="address",
            y="risk_score",
            color="risk_score",
            color_continuous_scale=["#10B981", "#D97706", "#EA580C", "#DC2626"],
            labels={"risk_score": "Risk Score", "address": "Building"},
            title="Risk Score by Building"
        )
        fig.update_layout(showlegend=False, xaxis_tickangle=-45)
        fig.add_hline(y=0.6, line_dash="dash", line_color="red", annotation_text="High Risk Threshold")
        st.plotly_chart(fig, use_container_width=True)
        
        # Exposure pie chart
        fig2 = px.pie(
            df,
            values="exposure",
            names="address",
            title="Fine Exposure Distribution",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    with table_col:
        st.subheader("🏢 Building Details")
        
        # Building cards
        for building in sorted(portfolio_data, key=lambda x: x["risk_score"], reverse=True):
            risk_level, risk_class = get_risk_level(building["risk_score"])
            
            with st.container():
                st.markdown(f"""
                <div class="building-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong>{building['address']}</strong><br>
                            <small>BBL: {building['bbl']} • {building['units']} units • Built {building['year_built']}</small>
                        </div>
                        <span class="risk-badge {risk_class}">{risk_level}</span>
                    </div>
                    <hr style="margin: 0.5rem 0;">
                    <div style="display: flex; justify-content: space-between;">
                        <span>💰 ${building['exposure']:,}</span>
                        <span>⚠️ {building['open_violations']} violations</span>
                        <span>🔴 {building['class_c']} Class C</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        # Actions
        st.subheader("🎯 Quick Actions")
        
        if st.button("🔄 Refresh All Buildings", use_container_width=True):
            st.info("Scanning all buildings... This would trigger API calls in production.")
        
        if st.button("📄 Export Compliance Report", use_container_width=True):
            if st.session_state.user_tier == "free":
                st.warning("🔒 Export is a Pro feature. Upgrade to access.")
            else:
                st.success("Report generated! Check your email.")
    
    st.divider()
    
    # Violation Trend (mock data)
    st.subheader("📉 Violation Trend (Last 30 Days)")
    
    # Generate mock trend data
    dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
    trend_data = pd.DataFrame({
        'date': dates,
        'total_violations': [15 + i % 5 - 2 for i in range(30)],
        'class_c': [3 + i % 2 for i in range(30)],
    })
    
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=trend_data['date'],
        y=trend_data['total_violations'],
        mode='lines+markers',
        name='Total Violations',
        line=dict(color='#3B82F6', width=2)
    ))
    fig3.add_trace(go.Scatter(
        x=trend_data['date'],
        y=trend_data['class_c'],
        mode='lines+markers',
        name='Class C (Critical)',
        line=dict(color='#DC2626', width=2)
    ))
    fig3.update_layout(
        title="Open Violations Over Time",
        xaxis_title="Date",
        yaxis_title="Count",
        hovermode="x unified"
    )
    st.plotly_chart(fig3, use_container_width=True)
    
    # Pre-1974 Building Analysis
    st.subheader("🏗️ Pre-1974 Risk Analysis")
    
    pre1974_buildings = [b for b in portfolio_data if b["year_built"] < 1974]
    post1974_buildings = [b for b in portfolio_data if b["year_built"] >= 1974]
    
    col1, col2 = st.columns(2)
    
    with col1:
        pre1974_pct = (len(pre1974_buildings) / len(portfolio_data) * 100) if portfolio_data else 0
        st.metric(
            "Pre-1974 Buildings",
            len(pre1974_buildings),
            delta=f"{pre1974_pct:.0f}% of portfolio"
        )
        if pre1974_buildings:
            avg_pre1974_risk = sum(b["risk_score"] for b in pre1974_buildings) / len(pre1974_buildings)
            st.warning(f"⚠️ Avg Risk Score: {avg_pre1974_risk:.0%} (2.5x baseline risk)")
    
    with col2:
        post1974_pct = (len(post1974_buildings) / len(portfolio_data) * 100) if portfolio_data else 0
        st.metric(
            "Modern Buildings (1974+)",
            len(post1974_buildings),
            delta=f"{post1974_pct:.0f}% of portfolio"
        )
        if post1974_buildings:
            avg_post1974_risk = sum(b["risk_score"] for b in post1974_buildings) / len(post1974_buildings)
            st.success(f"✅ Avg Risk Score: {avg_post1974_risk:.0%} (baseline risk)")

# Sidebar
with st.sidebar:
    st.title("📊 Portfolio")
    
    st.divider()
    
    st.subheader("Quick Stats")
    if portfolio_data:
        highest_risk = max(portfolio_data, key=lambda x: x["risk_score"])
        st.error(f"🔴 Highest Risk:\n{highest_risk['address']}\n({highest_risk['risk_score']:.0%})")
        
        most_exposure = max(portfolio_data, key=lambda x: x["exposure"])
        st.warning(f"💰 Most Exposure:\n{most_exposure['address']}\n(${most_exposure['exposure']:,})")
    
    st.divider()
    
    st.subheader("Heat Season Alert")
    current_month = datetime.now().month
    if current_month >= 10 or current_month <= 5:
        st.error("🌡️ **ACTIVE**\nOct 1 - May 31\nClass C heat violations at peak")
    else:
        st.success("✅ Off-season\nLower violation risk")
    
    st.divider()
    
    st.subheader("Export Options")
    st.button("📄 PDF Report", use_container_width=True, disabled=st.session_state.user_tier=="free")
    st.button("📊 Excel Export", use_container_width=True, disabled=st.session_state.user_tier=="free")
    st.button("🔗 Share Dashboard", use_container_width=True, disabled=st.session_state.user_tier=="free")
    
    if st.session_state.user_tier == "free":
        st.caption("🔒 Export features require Pro")

# Footer
st.divider()
st.caption("ViolationSentinel © 2024 ThrivAI • Portfolio Dashboard")
