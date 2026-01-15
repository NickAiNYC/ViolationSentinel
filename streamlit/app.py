"""
ViolationSentinel V1 - Streamlit Dashboard
NYC Property Compliance Risk Dashboard for Landlords
"""

import streamlit as st
import pandas as pd
import io
from datetime import datetime
import plotly.express as px

# Page config
st.set_page_config(
    page_title="ViolationSentinel - NYC Property Risk Dashboard",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1E3A8A;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        text-align: center;
        color: #64748B;
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }
    .risk-critical {
        background: #FEE2E2;
        color: #991B1B;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        font-weight: bold;
        border: 2px solid #DC2626;
    }
    .risk-urgent {
        background: #FED7AA;
        color: #9A3412;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        font-weight: bold;
        border: 2px solid #EA580C;
    }
    .risk-normal {
        background: #D1FAE5;
        color: #065F46;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        font-weight: bold;
        border: 2px solid #10B981;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 0.75rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #E5E7EB;
    }
    .alert-box {
        background: #FEF3C7;
        border-left: 4px solid #F59E0B;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'portfolio_df' not in st.session_state:
    st.session_state.portfolio_df = None
if 'user_tier' not in st.session_state:
    st.session_state.user_tier = 'free'

# Helper functions
def calculate_risk_score(row):
    """Calculate risk score from violation data"""
    score = 0
    
    # Class C violations (immediate hazard) = 40 pts each
    if pd.notna(row.get('class_c_count', 0)):
        score += int(row['class_c_count']) * 40
    
    # Heat complaints in last 7 days = 30 pts each
    if pd.notna(row.get('heat_complaints_7d', 0)):
        score += int(row['heat_complaints_7d']) * 30
    
    # Open violations > 90 days = 20 pts each
    if pd.notna(row.get('open_violations_90d', 0)):
        score += int(row['open_violations_90d']) * 20
    
    # 311 complaint spike = 10 pts
    if pd.notna(row.get('complaint_311_spike', 0)):
        score += int(row['complaint_311_spike']) * 10
    
    return min(100, score)

def get_priority(risk_score):
    """Determine priority level from risk score"""
    if risk_score >= 80:
        return "IMMEDIATE"
    elif risk_score >= 50:
        return "URGENT"
    else:
        return "NORMAL"

def get_status_color(risk_score):
    """Get status color based on risk score"""
    if risk_score >= 80:
        return "🔴 RED"
    elif risk_score >= 50:
        return "🟡 YELLOW"
    else:
        return "🟢 GREEN"

def estimate_fine_risk(row):
    """Estimate potential fine exposure"""
    fine_estimate = 0
    
    # Class C violations: $1,000-$5,000 each (use $3,000 avg)
    if pd.notna(row.get('class_c_count', 0)):
        fine_estimate += int(row['class_c_count']) * 3000
    
    # Heat complaints: $250-$500 per day (use $350 avg)
    if pd.notna(row.get('heat_complaints_7d', 0)):
        fine_estimate += int(row['heat_complaints_7d']) * 350
    
    # Old violations: $100-$1,000 each (use $500 avg)
    if pd.notna(row.get('open_violations_90d', 0)):
        fine_estimate += int(row['open_violations_90d']) * 500
    
    return f"${fine_estimate:,}"

# Header
st.markdown("<h1 class='main-header'>🏢 ViolationSentinel</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-header'>NYC Property Compliance Risk Dashboard • Prevent Fines • Protect Your Portfolio</p>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### 📊 Portfolio Upload")
    st.markdown("Upload your building portfolio as CSV")
    st.caption("Required columns: `bbl`, `name`, `units`, `address`")
    
    uploaded_file = st.file_uploader(
        "Choose CSV file",
        type=['csv'],
        help="CSV format: bbl,name,units,address"
    )
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            
            # Validate required columns
            required_cols = ['bbl', 'name', 'units', 'address']
            if not all(col in df.columns for col in required_cols):
                st.error(f"❌ Missing required columns. Need: {', '.join(required_cols)}")
            else:
                # Add sample violation data for demo (in production, fetch from API)
                df['class_c_count'] = [2, 0, 1, 0, 3] if len(df) >= 5 else [0] * len(df)
                df['heat_complaints_7d'] = [1, 0, 2, 0, 0] if len(df) >= 5 else [0] * len(df)
                df['open_violations_90d'] = [3, 1, 2, 0, 4] if len(df) >= 5 else [0] * len(df)
                df['complaint_311_spike'] = [1, 0, 1, 0, 1] if len(df) >= 5 else [0] * len(df)
                
                # Calculate risk metrics
                df['risk_score'] = df.apply(calculate_risk_score, axis=1)
                df['priority'] = df['risk_score'].apply(get_priority)
                df['status'] = df['risk_score'].apply(get_status_color)
                df['fine_risk'] = df.apply(estimate_fine_risk, axis=1)
                
                st.session_state.portfolio_df = df
                st.success(f"✅ Loaded {len(df)} properties")
                
        except Exception as e:
            st.error(f"Error loading file: {str(e)}")
    
    st.markdown("---")
    st.markdown("### 🔑 Account")
    
    # Tier info
    tier = st.session_state.user_tier
    if tier == 'free':
        st.info("**Free Plan**\n- 3 buildings max\n- Daily updates")
        if st.button("🚀 Upgrade to Pro", use_container_width=True):
            st.markdown("### Start Your Free Trial")
            st.markdown("**Pro Plan - $99/month**")
            st.markdown("✓ Unlimited buildings")
            st.markdown("✓ Real-time alerts")
            st.markdown("✓ Priority support")
            
            # Stripe checkout button (stub)
            st.markdown("""
            <a href="https://buy.stripe.com/test_xxxxx" target="_blank">
                <button style="width:100%; padding:10px; background:#6366F1; color:white; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">
                    Start Free Trial →
                </button>
            </a>
            """, unsafe_allow_html=True)
    else:
        st.success(f"**{tier.title()} Plan** ✓")
    
    st.markdown("---")
    st.markdown("### 📥 Export")
    if st.session_state.portfolio_df is not None:
        col1, col2 = st.columns(2)
        with col1:
            # CSV export
            csv = st.session_state.portfolio_df.to_csv(index=False)
            st.download_button(
                label="📄 CSV",
                data=csv,
                file_name=f"portfolio_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col2:
            # PDF export (stub - would use reportlab in production)
            st.download_button(
                label="📑 PDF",
                data="PDF export coming soon",
                file_name=f"portfolio_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True,
                disabled=True
            )

# Main content
if st.session_state.portfolio_df is None:
    # Welcome screen
    st.markdown("### 👋 Welcome to ViolationSentinel")
    st.markdown("""
    Get instant visibility into your NYC property portfolio's compliance risk.
    
    **How it works:**
    1. 📤 Upload your building list (CSV with BBL, name, units, address)
    2. 📊 See real-time risk scores and priority levels
    3. 🚨 Get alerted to Class C violations and heat complaints
    4. 💰 Estimate fine exposure and take action
    
    **Sample CSV format:**
    ```
    bbl,name,units,address
    1000010001,Building A,24,123 Main St Manhattan
    2000020002,Building B,48,456 Oak Ave Brooklyn
    3000030003,Building C,12,789 Elm St Queens
    ```
    """)
    
    # Sample data download
    sample_data = pd.DataFrame({
        'bbl': ['1000010001', '2000020002', '3000030003'],
        'name': ['Building A', 'Building B', 'Building C'],
        'units': [24, 48, 12],
        'address': ['123 Main St Manhattan', '456 Oak Ave Brooklyn', '789 Elm St Queens']
    })
    csv_sample = sample_data.to_csv(index=False)
    st.download_button(
        label="📥 Download Sample CSV",
        data=csv_sample,
        file_name="sample_portfolio.csv",
        mime="text/csv"
    )
    
else:
    df = st.session_state.portfolio_df
    
    # Check tier limits
    if st.session_state.user_tier == 'free' and len(df) > 3:
        st.warning("⚠️ Free plan limited to 3 buildings. Upgrade to Pro for unlimited access.")
        df = df.head(3)
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.metric("Total Buildings", len(df))
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        high_risk = len(df[df['risk_score'] >= 80])
        st.metric("Immediate Action", high_risk, delta=f"{high_risk} critical" if high_risk > 0 else None, delta_color="inverse")
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col3:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        class_c_total = df['class_c_count'].sum()
        st.metric("Class C Violations", int(class_c_total))
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col4:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        # Calculate total fine risk
        total_fines = sum([int(f.replace('$', '').replace(',', '')) for f in df['fine_risk']])
        st.metric("Total Fine Risk", f"${total_fines:,}", delta="Estimated")
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Alert section
    critical_properties = df[df['risk_score'] >= 80]
    if len(critical_properties) > 0:
        st.markdown("<div class='alert-box'>", unsafe_allow_html=True)
        st.markdown(f"### ⚠️ {len(critical_properties)} Properties Need IMMEDIATE Attention")
        for idx, row in critical_properties.iterrows():
            st.markdown(f"**{row['name']}** - Risk Score: {row['risk_score']} - {row['fine_risk']} at risk")
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Top 5 highest risk
    st.markdown("### 🔥 Top 5 Highest Risk Properties")
    top_5 = df.nlargest(5, 'risk_score')[['name', 'address', 'risk_score', 'priority', 'status', 'fine_risk', 'class_c_count', 'heat_complaints_7d']]
    
    # Display as cards
    for idx, row in top_5.iterrows():
        priority_class = "risk-critical" if row['priority'] == "IMMEDIATE" else "risk-urgent" if row['priority'] == "URGENT" else "risk-normal"
        
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.markdown(f"**{row['name']}**")
            st.caption(row['address'])
        with col2:
            st.markdown(f"<div class='{priority_class}'>{row['priority']}</div>", unsafe_allow_html=True)
        with col3:
            st.metric("Risk", row['risk_score'])
        
        # Details
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Class C", int(row['class_c_count']))
        col2.metric("Heat (7d)", int(row['heat_complaints_7d']))
        col3.metric("Fine Risk", row['fine_risk'])
        col4.markdown(f"**Status:** {row['status']}")
        
        st.markdown("---")
    
    # Heatmap visualization
    st.markdown("### 📊 Portfolio Risk Heatmap")
    
    fig = px.scatter(
        df,
        x='units',
        y='risk_score',
        size='class_c_count',
        color='priority',
        hover_data=['name', 'address', 'fine_risk'],
        color_discrete_map={
            'IMMEDIATE': '#DC2626',
            'URGENT': '#F59E0B',
            'NORMAL': '#10B981'
        },
        title="Risk Score vs Building Size"
    )
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)
    
    # Full portfolio table
    st.markdown("### 📋 Complete Portfolio")
    
    # Add filters
    col1, col2, col3 = st.columns(3)
    with col1:
        priority_filter = st.multiselect(
            "Priority",
            options=['IMMEDIATE', 'URGENT', 'NORMAL'],
            default=['IMMEDIATE', 'URGENT', 'NORMAL']
        )
    with col2:
        min_risk = st.slider("Min Risk Score", 0, 100, 0)
    with col3:
        max_risk = st.slider("Max Risk Score", 0, 100, 100)
    
    # Apply filters
    filtered_df = df[
        (df['priority'].isin(priority_filter)) &
        (df['risk_score'] >= min_risk) &
        (df['risk_score'] <= max_risk)
    ]
    
    # Display table
    st.dataframe(
        filtered_df[['name', 'address', 'units', 'risk_score', 'priority', 'status', 
                     'class_c_count', 'heat_complaints_7d', 'open_violations_90d', 'fine_risk']],
        use_container_width=True,
        height=400
    )
    
    st.caption(f"Showing {len(filtered_df)} of {len(df)} properties")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #64748B; padding: 2rem 0;'>
    <p>ViolationSentinel • NYC Property Compliance Intelligence</p>
    <p>Data sources: NYC Open Data (DOB, HPD, 311) • Updated daily at 2 AM EST</p>
</div>
""", unsafe_allow_html=True)
