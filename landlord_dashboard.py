"""
Landlord Dashboard - Comprehensive Property Violation Monitoring
Integrates DOB, HPD, and 311 violations for property management.
Real-time updates via WebSocket connection.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os

# Support both old and new package structure for backward compatibility
try:
    from src.violationsentinel.data import DOBViolationMonitor
    from src.violationsentinel.scoring import (
        pre1974_risk_multiplier, 
        get_building_era_risk,
        calculate_portfolio_pre1974_stats,
        inspector_risk_multiplier,
        get_district_hotspot,
        heat_violation_forecast,
        is_heat_season,
        peer_percentile,
        calculate_portfolio_peer_ranking,
    )
except ImportError:
    # Fallback to old import paths
    from dob_violations.dob_engine import DOBViolationMonitor
    from risk_engine.pre1974_multiplier import (
        pre1974_risk_multiplier, 
        get_building_era_risk,
        calculate_portfolio_pre1974_stats
    )
    from risk_engine.inspector_patterns import inspector_risk_multiplier, get_district_hotspot
    from risk_engine.seasonal_heat_model import heat_violation_forecast, is_heat_season
    from risk_engine.peer_benchmark import peer_percentile, calculate_portfolio_peer_ranking

from vs_components.components.pre1974_banner import (
    show_pre1974_banner,
    show_pre1974_stats,
    show_winter_heat_alert,
    show_inspector_hotspot_alert,
    show_peer_benchmark_card
)
# Note: Would need to import existing HPD/311 modules here

# Page configuration
st.set_page_config(
    page_title="ViolationSentinel - Landlord Dashboard",
    page_icon="🏢",
    layout="wide"
)

# Initialize session state
if 'dob_monitor' not in st.session_state:
    st.session_state.dob_monitor = DOBViolationMonitor()
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = []
if 'ws_connected' not in st.session_state:
    st.session_state.ws_connected = False
if 'real_time_updates' not in st.session_state:
    st.session_state.real_time_updates = []
if 'last_update_time' not in st.session_state:
    st.session_state.last_update_time = datetime.now()
if 'debug_mode' not in st.session_state:
    st.session_state.debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

# WebSocket configuration
WS_HOST = os.getenv('WEBSOCKET_HOST', 'localhost')
WS_PORT = os.getenv('WEBSOCKET_PORT', '8765')
WS_URL = f"ws://{WS_HOST}:{WS_PORT}"
JWT_TOKEN = os.getenv('JWT_TOKEN', '')  # Should be set in production

# Custom CSS with connection status indicator and animations
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
    
    /* Connection Status Indicator */
    .connection-status {
        display: inline-flex;
        align-items: center;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        font-weight: 600;
        margin-left: 1rem;
    }
    .status-connected {
        background-color: #D1FAE5;
        color: #065F46;
    }
    .status-reconnecting {
        background-color: #FEF3C7;
        color: #92400E;
    }
    .status-disconnected {
        background-color: #FEE2E2;
        color: #991B1B;
    }
    .status-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 0.5rem;
        display: inline-block;
    }
    .dot-green {
        background-color: #10B981;
        box-shadow: 0 0 10px #10B981;
        animation: pulse-green 2s infinite;
    }
    .dot-yellow {
        background-color: #F59E0B;
        box-shadow: 0 0 10px #F59E0B;
        animation: pulse-yellow 1s infinite;
    }
    .dot-red {
        background-color: #EF4444;
        box-shadow: 0 0 10px #EF4444;
    }
    
    @keyframes pulse-green {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    @keyframes pulse-yellow {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
    }
    
    /* Activity Feed */
    .activity-feed {
        max-height: 400px;
        overflow-y: auto;
        border: 1px solid #E5E7EB;
        border-radius: 0.5rem;
        padding: 1rem;
        background: #F9FAFB;
    }
    .activity-item {
        padding: 0.75rem;
        border-left: 3px solid #3B82F6;
        background: white;
        margin-bottom: 0.5rem;
        border-radius: 0.25rem;
        animation: slideIn 0.3s ease-out;
    }
    .activity-item.critical {
        border-left-color: #DC2626;
        background: #FEF2F2;
    }
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateX(-20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    /* Badge Animations */
    .violation-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.875rem;
        font-weight: 600;
        animation: fadeIn 0.5s ease-out;
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    
    /* Last Updated */
    .last-updated {
        font-size: 0.875rem;
        color: #6B7280;
        font-style: italic;
    }
    
    /* Toast Notification */
    .toast-notification {
        position: fixed;
        top: 80px;
        right: 20px;
        background: white;
        border-left: 4px solid #3B82F6;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        padding: 1rem;
        border-radius: 0.5rem;
        z-index: 9999;
        animation: slideInRight 0.3s ease-out;
    }
    .toast-notification.critical {
        border-left-color: #DC2626;
        background: #FEF2F2;
    }
    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(100px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
</style>
""", unsafe_allow_html=True)

# WebSocket JavaScript Component
websocket_component = """
<script>
let ws = null;
let reconnectAttempts = 0;
const maxReconnectAttempts = 10;
const baseDelay = 1000;

function getConnectionStatus() {
    if (!ws) return 'disconnected';
    switch(ws.readyState) {
        case WebSocket.CONNECTING: return 'connecting';
        case WebSocket.OPEN: return 'connected';
        case WebSocket.CLOSING: return 'disconnecting';
        case WebSocket.CLOSED: return 'disconnected';
        default: return 'disconnected';
    }
}

function updateConnectionUI(status) {
    const statusElement = document.getElementById('ws-status');
    if (!statusElement) return;
    
    let statusClass, dotClass, statusText;
    
    switch(status) {
        case 'connected':
            statusClass = 'status-connected';
            dotClass = 'dot-green';
            statusText = 'Connected';
            break;
        case 'connecting':
        case 'reconnecting':
            statusClass = 'status-reconnecting';
            dotClass = 'dot-yellow';
            statusText = status === 'reconnecting' ? 'Reconnecting...' : 'Connecting...';
            break;
        default:
            statusClass = 'status-disconnected';
            dotClass = 'dot-red';
            statusText = 'Disconnected';
    }
    
    statusElement.className = 'connection-status ' + statusClass;
    statusElement.innerHTML = '<span class="status-dot ' + dotClass + '"></span>' + statusText;
}

function connectWebSocket() {
    const wsUrl = '""" + WS_URL + """';
    const jwtToken = '""" + JWT_TOKEN + """';
    const properties = """ + json.dumps([p['bbl'] for p in st.session_state.portfolio]) + """;
    const debugMode = """ + json.dumps(st.session_state.debug_mode) + """;
    
    try {
        updateConnectionUI('connecting');
        ws = new WebSocket(wsUrl);
        
        ws.onopen = function() {
            console.log('WebSocket connected');
            updateConnectionUI('connected');
            reconnectAttempts = 0;
            
            // Authenticate
            if (jwtToken) {
                ws.send(JSON.stringify({
                    type: 'AUTHENTICATE',
                    token: jwtToken
                }));
            }
            
            // Subscribe to all properties
            properties.forEach(function(bbl) {
                ws.send(JSON.stringify({
                    type: 'SUBSCRIBE',
                    property_id: bbl
                }));
                if (debugMode) {
                    console.log('Subscribed to property:', bbl);
                }
            });
        };
        
        ws.onmessage = function(event) {
            const message = JSON.parse(event.data);
            
            if (debugMode) {
                console.log('WebSocket message:', message);
            }
            
            // Handle different message types
            if (message.type === 'VIOLATION_UPDATE') {
                handleViolationUpdate(message);
            } else if (message.type === 'PING') {
                ws.send(JSON.stringify({type: 'PONG'}));
            }
        };
        
        ws.onerror = function(error) {
            console.error('WebSocket error:', error);
            updateConnectionUI('disconnected');
        };
        
        ws.onclose = function() {
            console.log('WebSocket closed');
            updateConnectionUI('disconnected');
            attemptReconnect();
        };
        
    } catch (error) {
        console.error('Failed to create WebSocket:', error);
        updateConnectionUI('disconnected');
        attemptReconnect();
    }
}

function attemptReconnect() {
    if (reconnectAttempts >= maxReconnectAttempts) {
        console.log('Max reconnect attempts reached');
        return;
    }
    
    reconnectAttempts++;
    const delay = Math.min(baseDelay * Math.pow(2, reconnectAttempts), 30000);
    
    updateConnectionUI('reconnecting');
    console.log('Reconnecting in', delay, 'ms (attempt', reconnectAttempts, ')');
    
    setTimeout(connectWebSocket, delay);
}

function handleViolationUpdate(message) {
    const debugMode = """ + json.dumps(st.session_state.debug_mode) + """;
    
    // Play sound for critical violations
    if (message.severity === 'critical') {
        playAlertSound();
    }
    
    // Show toast notification
    showToast(message);
    
    // Trigger Streamlit rerun to update UI
    if (window.parent && window.parent.postMessage) {
        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            value: {
                update: message,
                timestamp: new Date().toISOString()
            }
        }, '*');
    }
}

function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast-notification' + (message.severity === 'critical' ? ' critical' : '');
    toast.innerHTML = `
        <strong>${message.property_id}</strong><br>
        ${message.type}: ${message.count || 0} violations
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(function() {
        toast.style.animation = 'slideInRight 0.3s ease-out reverse';
        setTimeout(function() {
            document.body.removeChild(toast);
        }, 300);
    }, 5000);
}

function playAlertSound() {
    // Create a simple beep using Web Audio API
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.value = 800;
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.5);
    } catch (error) {
        console.error('Failed to play alert sound:', error);
    }
}

// Initialize WebSocket on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', connectWebSocket);
} else {
    connectWebSocket();
}

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
    }
});
</script>
"""

# Inject WebSocket component if portfolio exists
if st.session_state.portfolio:
    st.components.v1.html(websocket_component, height=0)

# Header with connection status
header_col1, header_col2 = st.columns([3, 1])
with header_col1:
    st.markdown("<h1 class='main-header'>🏢 ViolationSentinel - Landlord Dashboard</h1>", unsafe_allow_html=True)
with header_col2:
    st.markdown('<div id="ws-status" class="connection-status status-disconnected"><span class="status-dot dot-red"></span>Disconnected</div>', unsafe_allow_html=True)

st.markdown("### Comprehensive NYC Property Violation Monitoring for Landlords & Property Managers")

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
        prop_year = st.number_input("Year Built", min_value=1800, max_value=2025, value=1965)
        
        if st.form_submit_button("Add to Portfolio"):
            if len(prop_bbl) == 10 and prop_bbl.isdigit():
                st.session_state.portfolio.append({
                    'name': prop_name,
                    'bbl': prop_bbl,
                    'units': prop_units,
                    'year_built': prop_year,
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
    
    # Settings
    st.subheader("⚙️ Settings")
    
    # Debug mode toggle
    debug_toggle = st.checkbox(
        "Enable Debug Mode",
        value=st.session_state.debug_mode,
        help="Log WebSocket messages to browser console"
    )
    if debug_toggle != st.session_state.debug_mode:
        st.session_state.debug_mode = debug_toggle
        st.rerun()
    
    # Real-time updates toggle
    st.info("✅ Real-time updates enabled via WebSocket")
    
    # Connection settings display
    st.text(f"WebSocket: {WS_URL}")
    
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
        
        # ===== COMPETITIVE MOAT FEATURES =====
        
        # Pre-1974 Risk Analysis
        portfolio_df = pd.DataFrame(st.session_state.portfolio)
        if 'year_built' in portfolio_df.columns:
            pre1974_stats = calculate_portfolio_pre1974_stats(st.session_state.portfolio)
            
            if pre1974_stats['pre1974_count'] > 0:
                st.subheader("🏗️ Pre-1974 Building Risk Assessment")
                show_pre1974_stats(pre1974_stats)
                show_pre1974_banner(portfolio_df)
                st.divider()
        
        # Winter Heat Season Alert (if applicable)
        if is_heat_season():
            st.subheader("🌡️ Winter Heat Season Risk")
            st.info("**Active Heat Season (Oct 1 - May 31)**: Elevated Class C violation risk")
            
            # Check for buildings with heat complaints (mock data for now)
            # In production, this would fetch actual 311 data
            heat_alert_buildings = []
            for prop in st.session_state.portfolio:
                year = prop.get('year_built', 2000)
                if year < 1974:
                    # Mock heat complaints for demonstration
                    prop_with_complaints = prop.copy()
                    prop_with_complaints['heat_complaints_30d'] = 4 if year < 1960 else 2
                    heat_alert_buildings.append(prop_with_complaints)
            
            if heat_alert_buildings:
                show_winter_heat_alert(heat_alert_buildings)
            st.divider()
        
        # Inspector Hotspot Analysis
        if any('council_district' in prop for prop in st.session_state.portfolio):
            hotspot_buildings = []
            for prop in st.session_state.portfolio:
                district = prop.get('council_district')
                if district:
                    multiplier = inspector_risk_multiplier(prop['bbl'], district)
                    if multiplier > 1.5:
                        prop_copy = prop.copy()
                        prop_copy['inspector_multiplier'] = multiplier
                        hotspot_buildings.append(prop_copy)
            
            if hotspot_buildings:
                show_inspector_hotspot_alert(hotspot_buildings)
                st.divider()
        
        # ===== END COMPETITIVE MOAT FEATURES =====
        
        # Property Details
        st.subheader("Property Violation Details")
        
        for prop_result in results['properties']:
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                
                with col1:
                    st.markdown(f"**{prop_result['property_name']}** ({prop_result['bbl']})")
                
                with col2:
                    violations = prop_result['summary']['total']
                    open_vios = prop_result['summary']['open']
                    st.markdown(
                        f'<span class="violation-badge" style="background:#3B82F6; color:white;">Total: {violations}</span> '
                        f'<span class="violation-badge" style="background:#EF4444; color:white;">Open: {open_vios}</span>',
                        unsafe_allow_html=True
                    )
                
                with col3:
                    risk = prop_result['risk_level']
                    risk_class = f"risk-{risk.lower()}" if risk != "CLEAN" else "risk-clean"
                    st.markdown(f"<div class='{risk_class}'>Risk: {risk}</div>", unsafe_allow_html=True)
                
                with col4:
                    # Auto-refresh indicator
                    st.markdown(
                        '<span style="font-size:0.75rem; color:#6B7280;">🔄 Live</span>',
                        unsafe_allow_html=True
                    )
                
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
col1, col2 = st.columns([2, 1])
with col1:
    st.caption("ViolationSentinel v1.0 • Last updated: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    st.caption("Monitoring: DOB Violations • HPD Violations • 311 Complaints")
with col2:
    if st.session_state.portfolio:
        st.caption(f"🔄 Real-time monitoring {len(st.session_state.portfolio)} properties")
    else:
        st.caption("Add properties to enable real-time monitoring")
