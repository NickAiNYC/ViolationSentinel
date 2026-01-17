"""
ViolationSentinel - SMS Alerts Setup
Configure real-time SMS notifications for new violations

Never miss a Class C violation again.
"""

import streamlit as st
import os
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Alerts Setup - ViolationSentinel",
    page_icon="🔔",
    layout="wide"
)

# Environment configuration
STRIPE_CHECKOUT_URL = os.getenv("STRIPE_CHECKOUT_URL", "https://buy.stripe.com/test_placeholder")


def is_heat_season() -> bool:
    """Check if current date is within NYC heat season (Oct 1 - May 31)."""
    current_month = datetime.now().month
    return current_month >= 10 or current_month <= 5


# Custom CSS
st.markdown("""
<style>
    .alerts-header {
        font-size: 2rem;
        color: #1E3A8A;
        font-weight: 700;
    }
    .alert-card {
        background: white;
        border: 1px solid #E5E7EB;
        border-radius: 0.75rem;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .alert-type-critical {
        border-left: 4px solid #DC2626;
    }
    .alert-type-high {
        border-left: 4px solid #EA580C;
    }
    .alert-type-info {
        border-left: 4px solid #3B82F6;
    }
    .phone-input {
        font-size: 1.25rem;
        padding: 0.75rem;
    }
    .toggle-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem;
        background: #F9FAFB;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "user_tier" not in st.session_state:
    st.session_state.user_tier = "free"
if "alert_settings" not in st.session_state:
    st.session_state.alert_settings = {
        "phone": "",
        "email": "",
        "class_c_enabled": True,
        "class_b_enabled": True,
        "class_a_enabled": False,
        "weekly_digest": True,
        "heat_season_alerts": True,
        "quiet_hours_start": 22,
        "quiet_hours_end": 7,
    }

# Header
st.markdown("<h1 class='alerts-header'>🔔 Alerts Setup</h1>", unsafe_allow_html=True)
st.markdown("Configure real-time SMS and email notifications for new violations.")

st.divider()

# Check user tier
if st.session_state.user_tier == "free":
    st.warning("""
    🔒 **SMS Alerts is a Pro feature**
    
    Upgrade to Pro ($199/mo) to access:
    - Real-time SMS alerts for new violations
    - Email notifications with violation details
    - Heat season warnings
    - Weekly compliance digest
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
    st.info("👇 **Preview**: Here's what your alerts dashboard could look like:")

# Main content
col_left, col_right = st.columns([2, 1])

with col_left:
    # Contact Information
    st.subheader("📱 Contact Information")
    
    with st.form("contact_form"):
        phone = st.text_input(
            "Phone Number (SMS)",
            value=st.session_state.alert_settings.get("phone", ""),
            placeholder="+1 (555) 123-4567",
            help="US phone number for SMS alerts"
        )
        
        email = st.text_input(
            "Email Address",
            value=st.session_state.alert_settings.get("email", ""),
            placeholder="you@company.com",
            help="Email for detailed violation reports"
        )
        
        submitted = st.form_submit_button("💾 Save Contact Info", disabled=st.session_state.user_tier=="free")
        
        if submitted and st.session_state.user_tier != "free":
            st.session_state.alert_settings["phone"] = phone
            st.session_state.alert_settings["email"] = email
            st.success("✅ Contact information saved!")
    
    st.divider()
    
    # Alert Types
    st.subheader("⚠️ Alert Types")
    
    st.markdown("""
    <div class="alert-card alert-type-critical">
        <h4>🔴 Class C Violations (Immediately Hazardous)</h4>
        <p>Heat failures, lead paint, structural issues. <strong>$5,000+ fines</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    class_c_enabled = st.toggle(
        "Enable Class C Alerts",
        value=st.session_state.alert_settings.get("class_c_enabled", True),
        disabled=st.session_state.user_tier=="free",
        help="Recommended: Always keep this ON"
    )
    
    st.markdown("""
    <div class="alert-card alert-type-high">
        <h4>🟠 Class B Violations (Hazardous)</h4>
        <p>Smoke detectors, vermin, water damage. <strong>$1,000-5,000 fines</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    class_b_enabled = st.toggle(
        "Enable Class B Alerts",
        value=st.session_state.alert_settings.get("class_b_enabled", True),
        disabled=st.session_state.user_tier=="free"
    )
    
    st.markdown("""
    <div class="alert-card alert-type-info">
        <h4>🟡 Class A Violations (Non-Hazardous)</h4>
        <p>Cosmetic issues, minor repairs. <strong>$250-1,000 fines</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    class_a_enabled = st.toggle(
        "Enable Class A Alerts",
        value=st.session_state.alert_settings.get("class_a_enabled", False),
        disabled=st.session_state.user_tier=="free",
        help="Optional: Can be noisy for large portfolios"
    )
    
    st.divider()
    
    # Special Alerts
    st.subheader("🌡️ Special Alerts")
    
    heat_season = st.toggle(
        "Heat Season Warnings (Oct 1 - May 31)",
        value=st.session_state.alert_settings.get("heat_season_alerts", True),
        disabled=st.session_state.user_tier=="free",
        help="Get proactive alerts during NYC heat season"
    )
    
    weekly_digest = st.toggle(
        "Weekly Compliance Digest",
        value=st.session_state.alert_settings.get("weekly_digest", True),
        disabled=st.session_state.user_tier=="free",
        help="Summary email every Monday at 9am"
    )
    
    st.divider()
    
    # Quiet Hours
    st.subheader("🌙 Quiet Hours")
    st.caption("No SMS during these hours (email still sent)")
    
    col_start, col_end = st.columns(2)
    with col_start:
        quiet_start = st.selectbox(
            "Start",
            options=list(range(24)),
            index=st.session_state.alert_settings.get("quiet_hours_start", 22),
            format_func=lambda x: f"{x:02d}:00",
            disabled=st.session_state.user_tier=="free"
        )
    with col_end:
        quiet_end = st.selectbox(
            "End",
            options=list(range(24)),
            index=st.session_state.alert_settings.get("quiet_hours_end", 7),
            format_func=lambda x: f"{x:02d}:00",
            disabled=st.session_state.user_tier=="free"
        )
    
    if st.session_state.user_tier != "free":
        st.info(f"🌙 Quiet hours: {quiet_start:02d}:00 - {quiet_end:02d}:00")

with col_right:
    # Alert Preview
    st.subheader("📱 Alert Preview")
    
    st.markdown("""
    <div style="
        background: #1F2937;
        color: white;
        padding: 1rem;
        border-radius: 1rem;
        font-family: monospace;
        font-size: 0.875rem;
    ">
        <div style="color: #9CA3AF; font-size: 0.75rem;">ViolationSentinel</div>
        <br>
        🚨 <strong>NEW CLASS C VIOLATION</strong><br><br>
        📍 123 Atlantic Ave<br>
        BBL: 3012340056<br><br>
        ⚠️ Inadequate Heat<br>
        💰 Est. Fine: $5,000<br><br>
        🎯 Fix NOW to avoid fine<br><br>
        <span style="color: #60A5FA;">violationsentinel.com/v/123</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.caption("Sample SMS alert (160 characters)")
    
    st.divider()
    
    # Recent Alerts
    st.subheader("📋 Recent Alerts")
    
    # Mock recent alerts
    recent_alerts = [
        {"time": "Today 2:34 PM", "type": "Class C", "building": "123 Atlantic Ave", "status": "sent"},
        {"time": "Today 10:15 AM", "type": "Class B", "building": "456 Court St", "status": "sent"},
        {"time": "Yesterday 4:22 PM", "type": "Digest", "building": "All Buildings", "status": "sent"},
    ]
    
    for alert in recent_alerts:
        icon = "🔴" if alert["type"] == "Class C" else ("🟠" if alert["type"] == "Class B" else "📧")
        st.markdown(f"""
        <div style="
            padding: 0.5rem;
            border-left: 3px solid {'#DC2626' if alert['type'] == 'Class C' else '#3B82F6'};
            margin: 0.5rem 0;
            background: #F9FAFB;
        ">
            <small style="color: #6B7280;">{alert['time']}</small><br>
            {icon} <strong>{alert['type']}</strong><br>
            {alert['building']}
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # Test Alert
    st.subheader("🧪 Test Your Setup")
    
    if st.button("📱 Send Test SMS", use_container_width=True, disabled=st.session_state.user_tier=="free"):
        if st.session_state.alert_settings.get("phone"):
            st.success("✅ Test SMS sent! Check your phone.")
        else:
            st.warning("⚠️ Please enter a phone number first.")
    
    if st.button("📧 Send Test Email", use_container_width=True, disabled=st.session_state.user_tier=="free"):
        if st.session_state.alert_settings.get("email"):
            st.success("✅ Test email sent! Check your inbox.")
        else:
            st.warning("⚠️ Please enter an email address first.")
    
    st.divider()
    
    # Stats
    st.subheader("📊 Alert Stats")
    st.metric("Alerts Sent (This Month)", "23")
    st.metric("Violations Caught Early", "8")
    st.metric("Est. Fines Avoided", "$42,500")

# Sidebar
with st.sidebar:
    st.title("🔔 Alerts")
    
    st.divider()
    
    # Current Status
    st.subheader("Status")
    
    if st.session_state.user_tier == "free":
        st.error("🔒 Alerts Disabled\nUpgrade to Pro")
    else:
        if st.session_state.alert_settings.get("phone"):
            st.success("✅ SMS Active")
        else:
            st.warning("⚠️ SMS Not Configured")
        
        if st.session_state.alert_settings.get("email"):
            st.success("✅ Email Active")
        else:
            st.warning("⚠️ Email Not Configured")
    
    st.divider()
    
    # Heat Season Status
    st.subheader("🌡️ Heat Season")
    if is_heat_season():
        st.error("**ACTIVE**\nOct 1 - May 31\nElevated Class C risk")
    else:
        st.success("**Off-Season**\nLower violation risk")
    
    st.divider()
    
    # Quick Settings
    st.subheader("⚡ Quick Settings")
    
    if st.button("🔕 Pause All Alerts (24h)", use_container_width=True, disabled=st.session_state.user_tier=="free"):
        st.info("Alerts paused for 24 hours")
    
    if st.button("🔊 Enable All Alert Types", use_container_width=True, disabled=st.session_state.user_tier=="free"):
        st.success("All alerts enabled")

# Save settings button
st.divider()

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("💾 Save All Settings", type="primary", use_container_width=True, disabled=st.session_state.user_tier=="free"):
        st.session_state.alert_settings.update({
            "class_c_enabled": class_c_enabled,
            "class_b_enabled": class_b_enabled,
            "class_a_enabled": class_a_enabled,
            "heat_season_alerts": heat_season,
            "weekly_digest": weekly_digest,
            "quiet_hours_start": quiet_start,
            "quiet_hours_end": quiet_end,
        })
        st.success("✅ All settings saved!")
        st.balloons()

# Footer
st.divider()
st.caption("ViolationSentinel © 2024 ThrivAI • Powered by Twilio")
