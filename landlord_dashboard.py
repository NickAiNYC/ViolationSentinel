"""
Landlord Dashboard - Enhanced with AI Risk Predictions
Integrates DOB, HPD, 311 violations with AI-powered risk forecasting.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from functools import lru_cache
import time
from io import BytesIO

from dob_violations.dob_engine import DOBViolationMonitor

# Lazy load AI predictor (only when needed)
_risk_predictor = None

def get_risk_predictor():
    """Lazy load risk predictor for performance."""
    global _risk_predictor
    if _risk_predictor is None:
        try:
            from ai.risk_predictor import RiskPredictor
            _risk_predictor = RiskPredictor()
            # Try to load pre-trained models if available
            try:
                _risk_predictor.load_models("risk_predictor_latest")
            except:
                st.warning("⚠️ Pre-trained AI models not found. Train models using scripts/train_models.py")
        except ImportError:
            st.error("AI Risk Predictor not available. Please install required dependencies.")
            return None
    return _risk_predictor

# Page configuration
st.set_page_config(
    page_title="ViolationSentinel - AI-Powered Dashboard",
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
    .risk-critical { 
        color: white; 
        background-color: #DC2626; 
        padding: 0.5rem; 
        border-radius: 0.25rem; 
        font-weight: bold; 
        text-align: center;
    }
    .risk-high { 
        color: white; 
        background-color: #EA580C; 
        padding: 0.5rem; 
        border-radius: 0.25rem; 
        font-weight: bold; 
        text-align: center;
    }
    .risk-medium { 
        color: white; 
        background-color: #3B82F6; 
        padding: 0.5rem; 
        border-radius: 0.25rem; 
        font-weight: bold; 
        text-align: center;
    }
    .risk-low { 
        color: white; 
        background-color: #059669; 
        padding: 0.5rem; 
        border-radius: 0.25rem; 
        font-weight: bold; 
        text-align: center;
    }
    .risk-minimal { 
        color: white; 
        background-color: #10B981; 
        padding: 0.5rem; 
        border-radius: 0.25rem; 
        font-weight: bold; 
        text-align: center;
    }
    .property-card {
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #E5E7EB;
        margin-bottom: 1rem;
        background: white;
    }
    .metric-card {
        padding: 1rem;
        border-radius: 0.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("<h1 class='main-header'>🏢 ViolationSentinel - AI-Powered Dashboard</h1>", unsafe_allow_html=True)
st.markdown("### Comprehensive NYC Property Violation Monitoring with AI Risk Forecasting")

# Initialize session state
if 'dob_monitor' not in st.session_state:
    st.session_state.dob_monitor = DOBViolationMonitor()
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = []
if 'ai_predictions' not in st.session_state:
    st.session_state.ai_predictions = {}
if 'prediction_cache_time' not in st.session_state:
    st.session_state.prediction_cache_time = {}

@st.cache_data(ttl=3600)  # Cache for 1 hour
def predict_property_risk(property_data: dict) -> dict:
    """
    Predict risk for a property using AI model (cached for 1 hour).
    
    Args:
        property_data: Dictionary with property features
        
    Returns:
        Dictionary with prediction results
    """
    predictor = get_risk_predictor()
    if predictor is None:
        return None
    
    try:
        # Prepare features for prediction
        features = {
            'property_age': property_data.get('property_age', 50),
            'violation_history_count': property_data.get('violation_history_count', 0),
            'days_since_last_violation': property_data.get('days_since_last_violation', 365),
            'neighborhood_risk_score': property_data.get('neighborhood_risk_score', 0.5),
            'total_units': property_data.get('total_units', 10),
            'complaint_frequency': property_data.get('complaint_frequency', 0.1),
            'owner_compliance_score': property_data.get('owner_compliance_score', 0.7),
            'seasonal_factor': property_data.get('seasonal_factor', 0.5),
            'economic_zone_risk': property_data.get('economic_zone_risk', 0.5),
            'flood_zone_risk': property_data.get('flood_zone_risk', 0.3),
            'construction_activity_nearby': property_data.get('construction_activity_nearby', 0)
        }
        
        result = predictor.predict(features)
        return {
            'risk_score': result.risk_score,
            'risk_level': result.risk_level,
            'critical_violation_probability': result.critical_violation_probability,
            'days_until_next_violation': result.days_until_next_violation,
            'recommended_action': result.recommended_action,
            'confidence': result.confidence,
            'feature_importance': result.feature_importance,
            'shap_values': result.shap_values
        }
    except Exception as e:
        st.error(f"Error predicting risk: {str(e)}")
        return None

def generate_risk_pdf_report(portfolio_data: list, predictions: dict) -> bytes:
    """Generate PDF report with risk predictions."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.units import inch
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph("<b>ViolationSentinel AI Risk Report</b>", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 0.3*inch))
        
        # Summary
        summary_text = f"""
        <b>Report Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}<br/>
        <b>Total Properties:</b> {len(portfolio_data)}<br/>
        <b>Properties Analyzed:</b> {len(predictions)}
        """
        elements.append(Paragraph(summary_text, styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
        
        # Risk distribution
        risk_counts = {}
        for pred in predictions.values():
            if pred:
                risk_level = pred.get('risk_level', 'UNKNOWN')
                risk_counts[risk_level] = risk_counts.get(risk_level, 0) + 1
        
        elements.append(Paragraph("<b>Risk Level Distribution:</b>", styles['Heading2']))
        for level, count in risk_counts.items():
            elements.append(Paragraph(f"{level}: {count} properties", styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
        
        # Property details table
        elements.append(Paragraph("<b>Property Risk Details:</b>", styles['Heading2']))
        
        table_data = [['Property', 'Risk Score', 'Risk Level', 'Days to Next Violation', 'Action Required']]
        for prop in portfolio_data:
            pred = predictions.get(prop['bbl'])
            if pred:
                table_data.append([
                    prop['name'][:30],
                    f"{pred['risk_score']:.1f}",
                    pred['risk_level'],
                    f"{pred['days_until_next_violation']:.0f}",
                    'Yes' if pred['risk_level'] in ['CRITICAL', 'HIGH'] else 'Monitor'
                ])
        
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(table)
        
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
    except Exception as e:
        st.error(f"Error generating PDF: {str(e)}")
        return None

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
        prop_age = st.number_input("Building Age (years)", min_value=0, value=50)
        
        if st.form_submit_button("Add to Portfolio"):
            if len(prop_bbl) == 10 and prop_bbl.isdigit():
                st.session_state.portfolio.append({
                    'name': prop_name,
                    'bbl': prop_bbl,
                    'units': prop_units,
                    'property_age': prop_age,
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
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Scan All", type="primary", use_container_width=True):
            st.session_state.scan_results = st.session_state.dob_monitor.check_portfolio(st.session_state.portfolio)
            st.rerun()
    
    with col2:
        if st.button("🤖 AI Predict", use_container_width=True):
            with st.spinner("Running AI predictions..."):
                for prop in st.session_state.portfolio:
                    # Create property data with mock features for now
                    prop_data = {
                        'property_age': prop.get('property_age', 50),
                        'total_units': prop.get('units', 10),
                        'violation_history_count': 5,  # Would come from scan results
                        'days_since_last_violation': 90,
                        'neighborhood_risk_score': 0.5,
                        'complaint_frequency': 0.2,
                        'owner_compliance_score': 0.7,
                        'seasonal_factor': 0.5,
                        'economic_zone_risk': 0.4,
                        'flood_zone_risk': 0.3,
                        'construction_activity_nearby': 0
                    }
                    prediction = predict_property_risk(prop_data)
                    if prediction:
                        st.session_state.ai_predictions[prop['bbl']] = prediction
                        st.session_state.prediction_cache_time[prop['bbl']] = datetime.now()
            st.success("AI predictions complete!")
            st.rerun()

# Main Dashboard
if not st.session_state.portfolio:
    st.info("👈 Add properties to your portfolio using the sidebar to get started.")
    
    # Sample dashboard preview
    with st.expander("📋 See Sample Dashboard Features"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Properties", "0", "Add properties to begin")
        with col2:
            st.metric("AI Risk Score", "0", "Run AI prediction")
        with col3:
            st.metric("Days to Next Violation", "N/A", "AI-powered forecast")
        
        st.info("✨ **New AI Features Available:**")
        st.write("• 🤖 AI-powered risk predictions with confidence scores")
        st.write("• 📈 Days until next violation forecasting")
        st.write("• 🎯 Top risk factors identification (SHAP values)")
        st.write("• 📊 Portfolio risk distribution analysis")
        st.write("• 💰 Prevent vs React cost comparison")
        st.write("• 📄 Exportable AI risk reports (PDF)")
    
else:
    # Portfolio Risk Overview Section (NEW)
    st.header("📊 Portfolio Risk Overview")
    
    # Show AI predictions if available
    if st.session_state.ai_predictions:
        # Calculate portfolio-level metrics
        risk_levels = {}
        total_risk_score = 0
        critical_count = 0
        
        for bbl, pred in st.session_state.ai_predictions.items():
            if pred:
                risk_level = pred['risk_level']
                risk_levels[risk_level] = risk_levels.get(risk_level, 0) + 1
                total_risk_score += pred['risk_score']
                if risk_level == 'CRITICAL':
                    critical_count += 1
        
        avg_risk_score = total_risk_score / len(st.session_state.ai_predictions) if st.session_state.ai_predictions else 0
        
        # Top metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Avg Risk Score", f"{avg_risk_score:.1f}/100", 
                     f"{avg_risk_score - 50:.1f}" if avg_risk_score > 0 else None)
        
        with col2:
            st.metric("Critical Properties", critical_count, 
                     "🚨 Immediate action" if critical_count > 0 else "✅")
        
        with col3:
            high_risk_count = risk_levels.get('HIGH', 0) + risk_levels.get('CRITICAL', 0)
            st.metric("High Risk Properties", high_risk_count,
                     f"{(high_risk_count/len(st.session_state.portfolio)*100):.0f}%")
        
        with col4:
            # Calculate potential savings
            savings = critical_count * 5000 + risk_levels.get('HIGH', 0) * 2000
            st.metric("Potential Cost Avoidance", f"${savings:,}", 
                     "by taking action")
        
        # Pie chart: Risk distribution
        col1, col2 = st.columns(2)
        
        with col1:
            if risk_levels:
                fig_pie = px.pie(
                    names=list(risk_levels.keys()), 
                    values=list(risk_levels.values()),
                    title='Portfolio Risk Distribution',
                    color=list(risk_levels.keys()),
                    color_discrete_map={
                        'CRITICAL': '#DC2626',
                        'HIGH': '#EA580C',
                        'MEDIUM': '#3B82F6',
                        'LOW': '#059669',
                        'MINIMAL': '#10B981'
                    }
                )
                st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Prevent vs React Cost Comparison
            prevent_cost = critical_count * 500 + risk_levels.get('HIGH', 0) * 200  # Inspection costs
            react_cost = critical_count * 5000 + risk_levels.get('HIGH', 0) * 2000  # Violation fines
            
            fig_cost = go.Figure(data=[
                go.Bar(name='Prevent (Proactive)', x=['Cost'], y=[prevent_cost], marker_color='#10B981'),
                go.Bar(name='React (Fines)', x=['Cost'], y=[react_cost], marker_color='#DC2626')
            ])
            fig_cost.update_layout(
                title='Prevent vs React: Cost Analysis',
                yaxis_title='Cost ($)',
                barmode='group'
            )
            st.plotly_chart(fig_cost, use_container_width=True)
        
        st.divider()
        
        # Filters
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            show_only_high_risk = st.checkbox("🔴 Show only HIGH/CRITICAL properties", value=False)
        
        with col2:
            sort_by = st.selectbox("Sort by:", ["Risk Score (High to Low)", "Risk Score (Low to High)", 
                                                  "Days to Next Violation", "Property Name"])
        
        with col3:
            if st.button("📄 Export Risk Report"):
                pdf_data = generate_risk_pdf_report(st.session_state.portfolio, st.session_state.ai_predictions)
                if pdf_data:
                    st.download_button(
                        label="Download PDF Report",
                        data=pdf_data,
                        file_name=f"risk_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf"
                    )
    
    st.divider()
    
    # Property Details with AI Predictions
    st.header("🏢 Property Risk Analysis")
    
    # Prepare property list for display
    property_list = []
    for prop in st.session_state.portfolio:
        pred = st.session_state.ai_predictions.get(prop['bbl'])
        if pred:
            prop_with_pred = prop.copy()
            prop_with_pred.update(pred)
            property_list.append(prop_with_pred)
    
    # Apply filters
    if show_only_high_risk and property_list:
        property_list = [p for p in property_list if p.get('risk_level') in ['HIGH', 'CRITICAL']]
    
    # Apply sorting
    if property_list:
        if sort_by == "Risk Score (High to Low)":
            property_list.sort(key=lambda x: x.get('risk_score', 0), reverse=True)
        elif sort_by == "Risk Score (Low to High)":
            property_list.sort(key=lambda x: x.get('risk_score', 0))
        elif sort_by == "Days to Next Violation":
            property_list.sort(key=lambda x: x.get('days_until_next_violation', 999))
        else:  # Property Name
            property_list.sort(key=lambda x: x.get('name', ''))
    
    # Display each property
    for prop in (property_list if property_list else st.session_state.portfolio):
        pred = st.session_state.ai_predictions.get(prop['bbl'])
        
        with st.container():
            # Property header
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(f"### {prop['name']}")
                st.caption(f"BBL: {prop['bbl']} • {prop['units']} units • Age: {prop.get('property_age', 'N/A')} years")
            
            with col2:
                if pred:
                    st.metric("AI Risk Score", f"{pred['risk_score']:.1f}/100")
            
            with col3:
                if pred:
                    risk_level = pred['risk_level']
                    risk_class = f"risk-{risk_level.lower()}"
                    
                    # Risk badge with icon
                    if risk_level == 'CRITICAL':
                        st.markdown(f"<div class='{risk_class}'>🚨 CRITICAL<br/>IMMEDIATE ACTION</div>", unsafe_allow_html=True)
                    elif risk_level == 'HIGH':
                        st.markdown(f"<div class='{risk_class}'>⚠️ HIGH RISK<br/>Schedule within 7 days</div>", unsafe_allow_html=True)
                    elif risk_level == 'MEDIUM':
                        st.markdown(f"<div class='{risk_class}'>📊 MEDIUM<br/>Monitor closely</div>", unsafe_allow_html=True)
                    elif risk_level == 'LOW':
                        st.markdown(f"<div class='{risk_class}'>✓ LOW<br/>Good compliance</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='risk-minimal'>✅ MINIMAL<br/>Excellent</div>", unsafe_allow_html=True)
            
            # AI Prediction Details
            if pred:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    days = pred['days_until_next_violation']
                    if days < 30:
                        st.metric("⏱️ Days to Next Violation", f"{days:.0f}", 
                                 delta=f"High urgency", delta_color="inverse")
                    else:
                        st.metric("⏱️ Days to Next Violation", f"{days:.0f}")
                
                with col2:
                    prob = pred['critical_violation_probability']
                    st.metric("🎯 Critical Violation Prob", f"{prob*100:.1f}%")
                
                with col3:
                    conf = pred['confidence']
                    st.metric("✓ Confidence", f"{conf*100:.0f}%")
                
                with col4:
                    cache_time = st.session_state.prediction_cache_time.get(prop['bbl'])
                    if cache_time:
                        age = (datetime.now() - cache_time).total_seconds() / 60
                        st.caption(f"🔄 Updated {age:.0f}m ago")
                
                # Top 3 Risk Factors
                if pred.get('feature_importance'):
                    st.markdown("**🎯 Top 3 Risk Factors:**")
                    sorted_features = sorted(pred['feature_importance'].items(), 
                                           key=lambda x: abs(x[1]), reverse=True)[:3]
                    
                    cols = st.columns(3)
                    for idx, (feature, importance) in enumerate(sorted_features):
                        with cols[idx]:
                            # Clean up feature name
                            feature_name = feature.replace('_', ' ').title()
                            st.markdown(f"**{idx+1}. {feature_name}**")
                            st.progress(min(abs(importance), 1.0))
                            st.caption(f"Impact: {importance:.2f}")
                
                # Recommended Actions
                st.markdown("**📋 Recommended Actions:**")
                st.info(pred['recommended_action'])
                
                # SHAP Explanations (Expandable)
                if pred.get('shap_values'):
                    with st.expander("🔍 AI Model Explainability (SHAP Values)"):
                        st.markdown("**Feature Contributions to Risk Prediction:**")
                        st.caption("Positive values increase risk, negative values decrease risk")
                        
                        shap_df = pd.DataFrame([
                            {'Feature': k.replace('_', ' ').title(), 
                             'SHAP Value': v,
                             'Impact': 'Increases Risk' if v > 0 else 'Decreases Risk'}
                            for k, v in pred['shap_values'].items()
                        ]).sort_values('SHAP Value', key=abs, ascending=False)
                        
                        st.dataframe(shap_df, use_container_width=True, hide_index=True)
                        
                        # SHAP bar chart
                        fig_shap = px.bar(shap_df, x='SHAP Value', y='Feature', 
                                         orientation='h',
                                         title='SHAP Feature Contributions',
                                         color='SHAP Value',
                                         color_continuous_scale=['red', 'gray', 'green'])
                        st.plotly_chart(fig_shap, use_container_width=True)
            
            st.divider()
    
    # Risk Score Timeline (if historical data available)
    if st.session_state.ai_predictions:
        st.header("📈 Risk Score Timeline")
        st.caption("Track how risk scores evolve over time (Feature coming soon)")
        
        # Mock timeline data
        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        mock_scores = []
        for prop in st.session_state.portfolio:
            pred = st.session_state.ai_predictions.get(prop['bbl'])
            if pred:
                base_score = pred['risk_score']
                # Generate some variance
                scores = [base_score + np.random.randn() * 5 for _ in range(30)]
                mock_scores.append({
                    'Property': prop['name'],
                    'dates': dates,
                    'scores': scores
                })
        
        if mock_scores:
            fig_timeline = go.Figure()
            for prop_data in mock_scores:
                fig_timeline.add_trace(go.Scatter(
                    x=prop_data['dates'],
                    y=prop_data['scores'],
                    mode='lines',
                    name=prop_data['Property']
                ))
            
            fig_timeline.update_layout(
                title='Risk Score Trends (Last 30 Days)',
                xaxis_title='Date',
                yaxis_title='Risk Score',
                hovermode='x unified'
            )
            st.plotly_chart(fig_timeline, use_container_width=True)
    
    # Traditional Violation Tracking (Keep existing functionality)
    st.divider()
    st.header("📋 Traditional Violation Tracking")
    
    if 'scan_results' in st.session_state:
        results = st.session_state.scan_results
        portfolio_summary = results['portfolio_summary']
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Properties Scanned", len(results['properties']))
        
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
                risk_class = "risk-minimal"
            
            st.markdown(f"<div class='{risk_class}'>Traditional Risk: {risk}</div>", unsafe_allow_html=True)
        
        # Show violation details in expander
        with st.expander("View Detailed Violation Records"):
            for prop_result in results['properties']:
                st.markdown(f"**{prop_result['property_name']}** ({prop_result['bbl']})")
                
                if prop_result['violations']:
                    violations_df = pd.DataFrame(prop_result['violations'])
                    if not violations_df.empty:
                        display_cols = ['violation_number', 'violation_type', 'issue_date', 
                                      'violation_class', 'disposition']
                        available_cols = [col for col in display_cols if col in violations_df.columns]
                        
                        if available_cols:
                            st.dataframe(violations_df[available_cols], use_container_width=True)
                else:
                    st.success("No violations found")
                
                st.divider()
    else:
        st.info("Click 'Scan All' in the sidebar to check for violations.")

# Footer
st.divider()
st.caption("ViolationSentinel AI v2.0 • Last updated: " + datetime.now().strftime('%Y-%m-%d %H:%M'))
st.caption("🤖 AI-Powered Risk Forecasting • 📊 DOB/HPD/311 Monitoring • 🎯 Predictive Analytics")
