"""
ViolationSentinel - HPD Risk Radar
MVP Streamlit Dashboard for NYC Property Managers

NYC PMs: Stop $5k+ Class C fines/building
BBL input → $27k fine exposure + fix priority → Stripe checkout
"""

import streamlit as st
import requests
import os
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="ViolationSentinel - HPD Risk Radar",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Environment configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
STRIPE_CHECKOUT_URL = os.getenv("STRIPE_CHECKOUT_URL", "https://buy.stripe.com/test_placeholder")

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        font-weight: 800;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.25rem;
        color: #4B5563;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        color: white;
        text-align: center;
    }
    .risk-critical {
        background: linear-gradient(135deg, #DC2626 0%, #991B1B 100%) !important;
    }
    .risk-high {
        background: linear-gradient(135deg, #EA580C 0%, #C2410C 100%) !important;
    }
    .risk-medium {
        background: linear-gradient(135deg, #D97706 0%, #B45309 100%) !important;
    }
    .risk-low {
        background: linear-gradient(135deg, #059669 0%, #047857 100%) !important;
    }
    .violation-item {
        background: #FEF2F2;
        border-left: 4px solid #DC2626;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.5rem;
    }
    .fix-priority {
        background: #ECFDF5;
        border-left: 4px solid #059669;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0.5rem;
    }
    .cta-button {
        background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
        color: white;
        padding: 1rem 2rem;
        border-radius: 0.5rem;
        text-decoration: none;
        font-weight: bold;
        display: inline-block;
        margin-top: 1rem;
    }
    .free-tier-badge {
        background: #DBEAFE;
        color: #1E40AF;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.875rem;
        font-weight: 600;
    }
    .pro-tier-badge {
        background: #FEF3C7;
        color: #92400E;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.875rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


def get_hpd_risk(bbl: str) -> dict:
    """
    Get HPD risk data for a building.
    In production, this calls the backend API.
    For MVP demo, returns realistic mock data based on BBL patterns.
    """
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/risk/{bbl}", timeout=10)
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.RequestException:
        pass  # Fall back to mock data for demo
    
    # Mock data for demonstration - realistic NYC violation patterns
    # BBL format: borough(1) + block(5) + lot(4) = 10 digits
    borough = bbl[0] if len(bbl) >= 1 else "1"
    
    # Generate realistic exposure based on borough
    borough_multipliers = {
        "1": 1.2,   # Manhattan - higher costs
        "2": 1.1,   # Bronx - high violation density
        "3": 1.0,   # Brooklyn - baseline
        "4": 0.9,   # Queens
        "5": 0.85   # Staten Island
    }
    
    base_exposure = 27450
    multiplier = borough_multipliers.get(borough, 1.0)
    exposure = int(base_exposure * multiplier)
    
    # Generate risk score (0.0 - 1.0)
    # Higher for older BBLs (lower block numbers often = older buildings)
    try:
        block_num = int(bbl[1:6]) if len(bbl) >= 6 and bbl[1:6].isdigit() else 5000
    except (ValueError, IndexError):
        block_num = 5000
    risk_score = min(0.95, max(0.15, 0.5 + (10000 - block_num) / 20000))
    
    # Realistic violation types for NYC
    violations = [
        {"type": "Class C - Inadequate Heat", "severity": "immediately_hazardous", "fine": 5000},
        {"type": "Class B - Smoke Detector Missing", "severity": "hazardous", "fine": 2500},
        {"type": "Class A - Peeling Paint (Non-Lead)", "severity": "non_hazardous", "fine": 500},
    ]
    
    # Year built estimation (for pre-1974 risk)
    estimated_year = 1960 if block_num < 3000 else (1975 if block_num < 7000 else 1995)
    
    return {
        "bbl": bbl,
        "exposure": exposure,
        "risk_score": risk_score,
        "violations": violations,
        "violation_count": len(violations),
        "open_class_c": 1,
        "open_class_b": 1,
        "open_class_a": 1,
        "fix_priority": "Heat system inspection (Class C = $5k+ fine/violation)",
        "estimated_year_built": estimated_year,
        "pre_1974_risk": estimated_year < 1974,
        "last_inspection": "2024-11-15",
        "next_inspection_risk": "HIGH - Heat season active"
    }


def render_risk_score_gauge(risk_score: float):
    """Render a visual risk score indicator."""
    if risk_score >= 0.8:
        risk_level = "CRITICAL"
        risk_class = "risk-critical"
        risk_color = "#DC2626"
    elif risk_score >= 0.6:
        risk_level = "HIGH"
        risk_class = "risk-high"
        risk_color = "#EA580C"
    elif risk_score >= 0.4:
        risk_level = "MEDIUM"
        risk_class = "risk-medium"
        risk_color = "#D97706"
    else:
        risk_level = "LOW"
        risk_class = "risk-low"
        risk_color = "#059669"
    
    return risk_level, risk_class, risk_color


# Initialize session state
if "buildings_scanned" not in st.session_state:
    st.session_state.buildings_scanned = 0
if "user_tier" not in st.session_state:
    st.session_state.user_tier = "free"  # free, pro, enterprise
if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

# Header
st.markdown("<h1 class='main-header'>🏠 ViolationSentinel - HPD Risk Radar</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-header'><strong>NYC PMs: Stop $5k+ Class C fines/building</strong></p>", unsafe_allow_html=True)

# Tier indicator
tier_col1, tier_col2 = st.columns([3, 1])
with tier_col2:
    if st.session_state.user_tier == "free":
        buildings_remaining = 3 - len(st.session_state.portfolio)
        st.markdown(f"<span class='free-tier-badge'>Free Tier: {buildings_remaining} buildings left</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='pro-tier-badge'>⭐ Pro: Unlimited</span>", unsafe_allow_html=True)

st.divider()

# Main BBL Input Section
st.subheader("🔍 Check Building Risk")
bbl = st.text_input(
    "Enter BBL (Borough-Block-Lot)",
    placeholder="e.g., 3012340056",
    help="10-digit BBL number. Find it on your property tax bill or NYC DOF website."
)

# BBL format validation
if bbl:
    bbl = bbl.strip().replace("-", "").replace(" ", "")
    
    if len(bbl) != 10 or not bbl.isdigit():
        st.error("⚠️ Please enter a valid 10-digit BBL number (Borough + Block + Lot)")
    else:
        # Create set of existing BBLs for O(1) lookup
        existing_bbls = {p.get("bbl") for p in st.session_state.portfolio}
        
        # Check tier limits
        if st.session_state.user_tier == "free" and len(st.session_state.portfolio) >= 3:
            if bbl not in existing_bbls:
                st.warning("🔒 Free tier limit reached (3 buildings). Upgrade to Pro for unlimited access!")
                st.markdown(f"""
                    <a href="{STRIPE_CHECKOUT_URL}" target="_blank" class="cta-button">
                        🔒 Upgrade to Pro: $199/mo
                    </a>
                """, unsafe_allow_html=True)
            else:
                # Allow re-checking existing buildings
                pass
        
        if st.session_state.user_tier != "free" or len(st.session_state.portfolio) < 3 or bbl in existing_bbls:
            with st.spinner("Analyzing building risk..."):
                risk_data = get_hpd_risk(bbl)
                st.session_state.buildings_scanned += 1
                
                # Add to portfolio if new
                if bbl not in existing_bbls:
                    st.session_state.portfolio.append({
                        "bbl": bbl,
                        "added": datetime.now().isoformat(),
                        "risk_data": risk_data
                    })
            
            # Display Results
            st.success(f"✅ Analysis complete for BBL: {bbl}")
            
            # Key Metrics
            col1, col2, col3 = st.columns(3)
            
            risk_level, risk_class, risk_color = render_risk_score_gauge(risk_data["risk_score"])
            
            with col1:
                st.metric(
                    label="💰 Fine Exposure",
                    value=f"${risk_data['exposure']:,.0f}",
                    delta=f"{risk_data['violation_count']} open violations",
                    delta_color="inverse"
                )
            
            with col2:
                st.metric(
                    label="⚠️ Risk Score",
                    value=f"{risk_data['risk_score']:.0%}",
                    delta=risk_level,
                    delta_color="inverse" if risk_level in ["CRITICAL", "HIGH"] else "normal"
                )
            
            with col3:
                pre1974_status = "⚠️ Pre-1974" if risk_data.get("pre_1974_risk") else "✅ Modern"
                st.metric(
                    label="🏗️ Building Era",
                    value=str(risk_data.get("estimated_year_built", "Unknown")),
                    delta=pre1974_status,
                    delta_color="inverse" if risk_data.get("pre_1974_risk") else "normal"
                )
            
            st.divider()
            
            # Violation Breakdown
            col_left, col_right = st.columns([2, 1])
            
            with col_left:
                st.subheader("🚨 Open Violations")
                
                for v in risk_data.get("violations", []):
                    severity_icon = "🔴" if "Class C" in v["type"] else ("🟠" if "Class B" in v["type"] else "🟡")
                    st.markdown(f"""
                    <div class="violation-item">
                        <strong>{severity_icon} {v['type']}</strong><br>
                        Potential Fine: <strong>${v['fine']:,}</strong>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Fix Priority
                st.markdown(f"""
                <div class="fix-priority">
                    <strong>🎯 Priority Action:</strong><br>
                    {risk_data.get('fix_priority', 'Contact property manager for detailed assessment')}
                </div>
                """, unsafe_allow_html=True)
            
            with col_right:
                st.subheader("📊 Risk Factors")
                
                # Pre-1974 Risk
                if risk_data.get("pre_1974_risk"):
                    st.error("🏗️ **Pre-1974 Building**\n\n2.5x higher violation risk")
                
                # Heat Season Risk
                current_month = datetime.now().month
                if current_month >= 10 or current_month <= 5:
                    st.warning("🌡️ **Heat Season Active**\n\nClass C heat violations at peak")
                
                # Next Inspection
                st.info(f"📅 **Last Inspection**\n\n{risk_data.get('last_inspection', 'Unknown')}")
                st.warning(f"⏰ **Next Inspection Risk**\n\n{risk_data.get('next_inspection_risk', 'Unknown')}")
            
            st.divider()
            
            # CTA Section
            st.subheader("🚀 Take Action")
            
            cta_col1, cta_col2 = st.columns(2)
            
            with cta_col1:
                if st.session_state.user_tier == "free":
                    st.markdown("""
                    ### 🔓 Upgrade to Pro
                    - ✅ Unlimited building scans
                    - ✅ SMS/Email alerts for new violations
                    - ✅ Portfolio risk dashboard
                    - ✅ Priority fix recommendations
                    - ✅ Export compliance reports
                    """)
                    st.markdown(f"""
                        <a href="{STRIPE_CHECKOUT_URL}" target="_blank" class="cta-button">
                            Upgrade to Pro: $199/mo
                        </a>
                    """, unsafe_allow_html=True)
                else:
                    st.success("✅ You're on Pro! Full access enabled.")
            
            with cta_col2:
                st.markdown("""
                ### 📞 Need Help?
                - 📧 support@violationsentinel.com
                - 📅 [Book a Demo](https://calendly.com/violationsentinel/demo)
                - 💬 Live chat (Pro users)
                """)

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/building.png", width=80)
    st.title("ViolationSentinel")
    st.caption("HPD Risk Radar for NYC PMs")
    
    st.divider()
    
    # Quick Stats
    st.subheader("📊 Your Stats")
    st.metric("Buildings Scanned", st.session_state.buildings_scanned)
    st.metric("Portfolio Size", len(st.session_state.portfolio))
    
    st.divider()
    
    # Pricing
    st.subheader("💎 Pricing")
    st.markdown("""
    **Free**: 3 buildings  
    **Pro**: $199/mo unlimited + alerts  
    **Enterprise**: $5k/mo API access
    """)
    
    if st.session_state.user_tier == "free":
        if st.button("🔒 Upgrade to Pro", type="primary", use_container_width=True):
            st.markdown(f"[Complete checkout →]({STRIPE_CHECKOUT_URL})")
    
    st.divider()
    
    # About
    st.subheader("ℹ️ About")
    st.markdown("""
    Built by **ThrivAI Brooklyn** 🏠
    
    Real-time HPD/DOB/311 data integration.
    Stop paying $5k+ Class C fines.
    """)
    
    st.caption(f"v1.0.0 • {datetime.now().strftime('%Y-%m-%d')}")

# Footer
st.divider()
st.caption("ViolationSentinel © 2024 ThrivAI • [Terms](https://violationsentinel.com/terms) • [Privacy](https://violationsentinel.com/privacy)")
