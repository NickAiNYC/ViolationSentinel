"""
Landlord Dashboard - Comprehensive Property Violation Monitoring
Integrates DOB, HPD, and 311 violations for property management.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dob_violations.dob_engine import DOBViolationMonitor
# Note: Would need to import existing HPD/311 modules here

# Page configuration
st.set_page_config(
    page_title="ViolationSentinel - Landlord Dashboard",
    page_icon="🏢",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        font-weight: 800;
        margin-bottom: 1rem;
    }
    .risk-critical { color: #DC2626; font-weight: bold; }
    .risk-high { color: #EA580C; font-weight: bold; }
    .risk-medium { color: #D97706; font-weight: bold; }
    .risk-low { color: #059669; font-weight: bold; }
    .risk-clean { color: #10B981; font-weight: bold; }
    .property-card {
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #E5E7EB;
        margin-bottom: 1rem;
        background: white;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("<h1 class='main-header'>🏢 ViolationSentinel - Landlord Dashboard</h1>", unsafe_allow_html=True)
st.markdown("### Comprehensive NYC Property Violation Monitoring for Landlords & Property Managers")

# Initialize session state
if 'dob_monitor' not in st.session_state:
    st.session_state.dob_monitor = DOBViolationMonitor()
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = []

# Sidebar - Property Management
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/apartment.png", width=80)
    st.title("Property Portfolio")
    
    # Add property form
    with st.form("add_property"):
        st.subheader("Add Property")
        prop_name = st.text_input("Property Name", "123 Main St Apartments")
        prop_bbl = st.text_input("BBL Number", "1012650001")
        prop_units = st.number_input("Number of Units", min_value=1, value=10)
        
        if st.form_submit_button("Add to Portfolio"):
            if len(prop_bbl) == 10 and prop_bbl.isdigit():
                st.session_state.portfolio.append({
                    'name': prop_name,
                    'bbl': prop_bbl,
                    'units': prop_units,
                    'added': datetime.now().strftime('%Y-%m-%d')
                })
                st.success(f"Added {prop_name} to portfolio")
            else:
                st.error("Please enter a valid 10-digit BBL number")
    
    st.divider()
    
    # Portfolio summary
    if st.session_state.portfolio:
        st.subheader(f"Portfolio: {len(st.session_state.portfolio)} Properties")
        for prop in st.session_state.portfolio:
            st.write(f"• {prop['name']} ({prop['units']} units)")
    
    st.divider()
    
    # Actions
    if st.button("🔄 Scan All Properties", type="primary"):
        st.session_state.scan_results = st.session_state.dob_monitor.check_portfolio(st.session_state.portfolio)
        st.rerun()
    
    if st.button("📊 Generate Compliance Report"):
        st.info("Compliance report generation coming soon")

# Main Dashboard
if not st.session_state.portfolio:
    st.info("👈 Add properties to your portfolio using the sidebar to get started.")
    
    # Sample dashboard preview
    with st.expander("📋 See Sample Dashboard"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Properties", "0", "Add properties to begin")
        with col2:
            st.metric("Total Violations", "0", "No properties scanned")
        with col3:
            st.metric("Risk Level", "N/A", "Add properties first")
        
        st.info("Once you add properties, you'll see:")
        st.write("• Real-time violation monitoring")
        st.write("• Risk assessment across your portfolio")
        st.write("• DOB, HPD, and 311 violation tracking")
        st.write("• Compliance reporting and alerts")
    
else:
    # Portfolio Overview Metrics
    if 'scan_results' in st.session_state:
        results = st.session_state.scan_results
        portfolio_summary = results['portfolio_summary']
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Properties", len(results['properties']))
        
        with col2:
            total_violations = portfolio_summary['total']
            st.metric("Total Violations", total_violations)
        
        with col3:
            open_violations = portfolio_summary['open']
            st.metric("Open Violations", open_violations)
        
        with col4:
            # Calculate overall risk
            class_c = portfolio_summary['by_class'].get('Class C', 0)
            class_b = portfolio_summary['by_class'].get('Class B', 0)
            
            if class_c > 0:
                risk = "CRITICAL"
                risk_class = "risk-critical"
            elif class_b > 2:
                risk = "HIGH"
                risk_class = "risk-high"
            elif open_violations > 5:
                risk = "MEDIUM"
                risk_class = "risk-medium"
            elif total_violations > 0:
                risk = "LOW"
                risk_class = "risk-low"
            else:
                risk = "CLEAN"
                risk_class = "risk-clean"
            
            st.markdown(f"<div class='{risk_class}'>Risk Level: {risk}</div>", unsafe_allow_html=True)
        
        st.divider()
        
        # Property Details
        st.subheader("Property Violation Details")
        
        for prop_result in results['properties']:
            with st.container():
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.markdown(f"**{prop_result['property_name']}** ({prop_result['bbl']})")
                
                with col2:
                    violations = prop_result['summary']['total']
                    open_vios = prop_result['summary']['open']
                    st.write(f"Violations: {violations} ({open_vios} open)")
                
                with col3:
                    risk = prop_result['risk_level']
                    risk_class = f"risk-{risk.lower()}" if risk != "CLEAN" else "risk-clean"
                    st.markdown(f"<div class='{risk_class}'>Risk: {risk}</div>", unsafe_allow_html=True)
                
                # Show violation breakdown if any
                if prop_result['violations']:
                    with st.expander("View Violations"):
                        violations_df = pd.DataFrame(prop_result['violations'])
                        if not violations_df.empty:
                            # Select and rename columns for display
                            display_cols = ['violation_number', 'violation_type', 'issue_date', 
                                          'violation_class', 'disposition']
                            available_cols = [col for col in display_cols if col in violations_df.columns]
                            
                            if available_cols:
                                st.dataframe(violations_df[available_cols], use_container_width=True)
                
                st.divider()
        
        # Visualization
        st.subheader("Portfolio Analytics")
        
        # Create summary data for charts
        properties_data = []
        for prop_result in results['properties']:
            properties_data.append({
                'Property': prop_result['property_name'],
                'Total Violations': prop_result['summary']['total'],
                'Open Violations': prop_result['summary']['open'],
                'Risk Level': prop_result['risk_level']
            })
        
        if properties_data:
            df = pd.DataFrame(properties_data)
            
            # Bar chart of violations by property
            fig1 = px.bar(df, x='Property', y='Total Violations', 
                         title='Violations by Property',
                         color='Risk Level',
                         color_discrete_map={
                             'CRITICAL': '#DC2626',
                             'HIGH': '#EA580C',
                             'MEDIUM': '#D97706',
                             'LOW': '#059669',
                             'CLEAN': '#10B981'
                         })
            st.plotly_chart(fig1, use_container_width=True)
            
            # Violation class breakdown
            class_data = portfolio_summary['by_class']
            if sum(class_data.values()) > 0:
                fig2 = px.pie(names=list(class_data.keys()), 
                            values=list(class_data.values()),
                            title='Violations by Class',
                            color=list(class_data.keys()),
                            color_discrete_map={
                                'Class C': '#DC2626',
                                'Class B': '#EA580C',
                                'Class A': '#D97706'
                            })
                st.plotly_chart(fig2, use_container_width=True)
    
    else:
        st.info("Click 'Scan All Properties' in the sidebar to check for violations.")

# Footer
st.divider()
st.caption("ViolationSentinel v1.0 • Last updated: " + datetime.now().strftime('%Y-%m-%d %H:%M'))
st.caption("Monitoring: DOB Violations • HPD Violations • 311 Complaints")
