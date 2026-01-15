"""
Pre-1974 Warning Banner Component

Reusable Streamlit component for displaying pre-1974 building warnings.
Core competitive moat UI element.
"""

import streamlit as st
import pandas as pd
from typing import List, Dict


def show_pre1974_banner(buildings_df: pd.DataFrame) -> None:
    """
    Display prominent warning banner for pre-1974 buildings.
    
    Args:
        buildings_df: DataFrame with 'year_built' column
    """
    if 'year_built' not in buildings_df.columns:
        return
    
    # Filter pre-1974 buildings
    pre1974_buildings = buildings_df[buildings_df['year_built'] < 1974]
    pre1960_buildings = buildings_df[buildings_df['year_built'] < 1960]
    
    if len(pre1974_buildings) > 0:
        # Critical warning for pre-1960
        if len(pre1960_buildings) > 0:
            st.error(f"🚨 **CRITICAL: {len(pre1960_buildings)} PRE-1960 BUILDINGS DETECTED**")
            st.error("""
            **3.8x HIGHER VIOLATION RISK**
            - Lead paint hazard (pre-1960 construction)
            - Heat complaints 4.2x higher than modern buildings  
            - Class C violation risk elevated in winter season
            - **URGENT**: Heat system inspection recommended before October 1
            """)
        
        # Elevated warning for 1960-1973
        pre60_to_74 = len(pre1974_buildings) - len(pre1960_buildings)
        if pre60_to_74 > 0:
            st.warning(f"⚠️  **{pre60_to_74} RENT-STABILIZED ERA BUILDINGS (1960-1973)**")
            st.warning("""
            **2.5x HIGHER VIOLATION RISK**
            - Built before modern building codes
            - Aging HVAC systems (primary complaint driver)
            - Potential rent stabilization complexity
            """)
        
        # Show details
        with st.expander(f"📋 View {len(pre1974_buildings)} Pre-1974 Buildings"):
            display_cols = ['address', 'year_built', 'risk_score'] if 'address' in buildings_df.columns else ['year_built']
            if 'name' in buildings_df.columns:
                display_cols = ['name'] + display_cols
            
            available_cols = [col for col in display_cols if col in buildings_df.columns]
            
            if available_cols:
                st.dataframe(
                    pre1974_buildings[available_cols].sort_values('year_built'),
                    use_container_width=True
                )


def show_pre1974_stats(portfolio_stats: Dict) -> None:
    """
    Display pre-1974 portfolio statistics.
    
    Args:
        portfolio_stats: Dictionary from calculate_portfolio_pre1974_stats()
    """
    if not portfolio_stats or portfolio_stats.get('total_buildings', 0) == 0:
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Pre-1974 Buildings", 
            portfolio_stats['pre1974_count'],
            f"{portfolio_stats['pre1974_percentage']:.0f}% of portfolio"
        )
    
    with col2:
        st.metric(
            "Pre-1960 (Critical)",
            portfolio_stats['pre1960_count'],
            "3.8x risk" if portfolio_stats['pre1960_count'] > 0 else None
        )
    
    with col3:
        st.metric(
            "Avg Risk Multiplier",
            f"{portfolio_stats['average_multiplier']}x"
        )
    
    with col4:
        risk_level = portfolio_stats['portfolio_risk_level']
        color = "🔴" if risk_level == "CRITICAL" else "🟡" if risk_level == "ELEVATED" else "🟢"
        st.metric(
            "Portfolio Risk",
            f"{color} {risk_level}"
        )


def show_winter_heat_alert(buildings_with_heat_complaints: List[Dict]) -> None:
    """
    Display winter heat season alert for buildings with recent complaints.
    
    Args:
        buildings_with_heat_complaints: List of buildings with heat_complaints_30d > 0
    """
    if not buildings_with_heat_complaints:
        return
    
    critical_count = sum(1 for b in buildings_with_heat_complaints if b.get('heat_complaints_30d', 0) >= 3)
    
    if critical_count > 0:
        st.error(f"🌡️ **WINTER HEAT ALERT: {critical_count} Buildings with Multiple Heat Complaints**")
        st.error("""
        **87% correlation: 311 heat complaint → HPD Class C violation within 14 days**
        - Jan-Mar = Peak season (62% of $10K+ fines)
        - Action required: HVAC inspection within 7 days
        """)
        
        with st.expander("View Buildings with Heat Complaints"):
            for building in buildings_with_heat_complaints:
                if building.get('heat_complaints_30d', 0) >= 3:
                    st.write(f"🚨 **{building.get('name', 'Unknown')}**: {building['heat_complaints_30d']} complaints (30 days)")


def show_inspector_hotspot_alert(buildings_in_hotspots: List[Dict]) -> None:
    """
    Display inspector hotspot alert for buildings in high-enforcement zones.
    
    Args:
        buildings_in_hotspots: List of buildings with inspector_multiplier > 1.5
    """
    if not buildings_in_hotspots:
        return
    
    st.warning(f"🔍 **{len(buildings_in_hotspots)} Buildings in HPD Inspector Hotspots**")
    st.warning("""
    **Faster 311 complaint → HPD inspection conversion (7-14 days vs. 30+ citywide)**
    - High-priority enforcement zones
    - Increased inspector presence
    - Recommendation: Proactive compliance review
    """)
    
    with st.expander("View Hotspot Buildings"):
        for building in buildings_in_hotspots:
            district = building.get('council_district', 'Unknown')
            mult = building.get('inspector_multiplier', 1.0)
            st.write(f"⚠️  **{building.get('name', 'Unknown')}** ({district}): {mult}x enforcement")


def show_peer_benchmark_card(peer_data: Dict) -> None:
    """
    Display peer benchmarking card.
    
    Args:
        peer_data: Dictionary from peer_percentile()
    """
    if not peer_data or peer_data.get('percentile') is None:
        return
    
    percentile = peer_data['percentile']
    urgency = peer_data.get('urgency', 'LOW')
    
    # Color based on urgency
    if urgency in ['CRITICAL', 'HIGH']:
        st.error(f"📊 **Peer Benchmark: {peer_data['vs_peers']}**")
    elif urgency == 'MODERATE':
        st.warning(f"📊 **Peer Benchmark: {peer_data['vs_peers']}**")
    else:
        st.info(f"📊 **Peer Benchmark: {peer_data['vs_peers']}**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Your Risk Score", peer_data['risk_score'])
    
    with col2:
        st.metric("Neighborhood Average", peer_data['neighborhood_avg'])
    
    with col3:
        st.metric("Similar Buildings", peer_data['similar_count'])
    
    st.caption(peer_data.get('match_criteria', ''))
    
    if peer_data.get('action'):
        st.write(f"**Action:** {peer_data['action']}")
