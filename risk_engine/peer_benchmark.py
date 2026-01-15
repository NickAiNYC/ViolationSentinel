"""
Peer Benchmarking - Landlord Competitive Intelligence

"Your building vs. 1,247 similar Brooklyn properties"
Anonymized benchmarking creates instant credibility and urgency.

This feature converts leads by showing landlords where they stand vs. peers.
"""

from typing import Dict, List, Optional
import statistics


def peer_percentile(
    address: str, 
    risk_score: float, 
    building_data: Optional[Dict] = None,
    similar_buildings: Optional[List[Dict]] = None
) -> Dict:
    """
    Calculate peer percentile for a building's risk score.
    
    Shows landlord: "Your building is riskier than 73% of similar properties"
    
    Args:
        address: Building address (for display)
        risk_score: Building's calculated risk score
        building_data: Dict with 'units', 'year_built', 'borough' for matching
        similar_buildings: Optional pre-filtered list of similar buildings
        
    Returns:
        Dictionary with peer benchmark data
        
    Example:
        >>> peer_percentile("123 Main St", 75.3, {'units': 24, 'year_built': 1965})
        {'percentile': 73, 'vs_peers': 'Top 27% riskiest', ...}
    """
    # If no similar buildings provided, generate mock data for now
    # In production, this would query actual database of monitored properties
    if similar_buildings is None:
        similar_buildings = _generate_similar_building_scores(building_data or {})
    
    if not similar_buildings:
        return {
            'address': address,
            'risk_score': risk_score,
            'vs_peers': 'Insufficient peer data',
            'percentile': None,
            'similar_count': 0
        }
    
    # Calculate percentile
    peer_scores = [b.get('risk_score', 50) for b in similar_buildings if 'risk_score' in b]
    
    if not peer_scores:
        return {
            'address': address,
            'risk_score': risk_score,
            'vs_peers': 'Insufficient peer data',
            'percentile': None,
            'similar_count': 0
        }
    
    # Percentile calculation
    below_count = sum(1 for score in peer_scores if score < risk_score)
    percentile = (below_count / len(peer_scores)) * 100
    
    # Stats
    neighborhood_avg = statistics.mean(peer_scores)
    neighborhood_median = statistics.median(peer_scores)
    
    # Determine comparison message
    if percentile >= 90:
        comparison = f"Top {100-percentile:.0f}% riskiest"
        urgency = "CRITICAL"
    elif percentile >= 75:
        comparison = f"Top {100-percentile:.0f}% riskiest"
        urgency = "HIGH"
    elif percentile >= 50:
        comparison = "Above average risk"
        urgency = "MODERATE"
    elif percentile >= 25:
        comparison = "Below average risk"
        urgency = "LOW"
    else:
        comparison = f"Bottom {percentile:.0f}% risk"
        urgency = "LOW"
    
    # Match criteria for transparency
    match_criteria = _get_match_criteria(building_data or {})
    
    return {
        'address': address,
        'risk_score': round(risk_score, 1),
        'vs_peers': comparison,
        'percentile': round(percentile, 0),
        'urgency': urgency,
        'neighborhood_avg': round(neighborhood_avg, 1),
        'neighborhood_median': round(neighborhood_median, 1),
        'similar_count': len(similar_buildings),
        'match_criteria': match_criteria,
        'action': _get_peer_action(percentile, risk_score, neighborhood_avg)
    }


def get_similar_properties(building_data: Dict, all_buildings: Optional[List[Dict]] = None) -> List[Dict]:
    """
    Find similar properties for benchmarking.
    
    Matching criteria (in priority order):
    1. Same borough
    2. Similar unit count (±30%)
    3. Similar construction era (±10 years)
    4. Similar building type
    
    Args:
        building_data: Dict with 'units', 'year_built', 'borough', 'bbl'
        all_buildings: Database of all monitored buildings
        
    Returns:
        List of similar building dictionaries
    """
    if all_buildings is None:
        # In production, query database
        # For now, return mock similar buildings
        return _generate_similar_buildings(building_data)
    
    target_units = building_data.get('units', 0)
    target_year = building_data.get('year_built', 2000)
    target_borough = building_data.get('borough', '').lower()
    target_bbl = building_data.get('bbl', '')
    
    similar = []
    
    for building in all_buildings:
        # Don't match with self
        if building.get('bbl') == target_bbl:
            continue
        
        # Borough match (required)
        if building.get('borough', '').lower() != target_borough:
            continue
        
        # Unit count similarity (±30%)
        building_units = building.get('units', 0)
        if building_units > 0 and target_units > 0:
            unit_ratio = building_units / target_units
            if unit_ratio < 0.7 or unit_ratio > 1.3:
                continue
        
        # Year similarity (±15 years)
        building_year = building.get('year_built')
        if building_year and target_year:
            year_diff = abs(building_year - target_year)
            if year_diff > 15:
                continue
        
        similar.append(building)
    
    return similar


def calculate_portfolio_peer_ranking(portfolio: List[Dict], market_data: Optional[List[Dict]] = None) -> Dict:
    """
    Calculate how an entire portfolio ranks against market.
    
    Args:
        portfolio: List of buildings in portfolio
        market_data: Optional market comparison data
        
    Returns:
        Portfolio benchmark summary
    """
    if not portfolio:
        return {
            'portfolio_size': 0,
            'average_risk': 0,
            'portfolio_percentile': None
        }
    
    # Calculate portfolio average risk
    portfolio_scores = [b.get('risk_score', 50) for b in portfolio if 'risk_score' in b]
    
    if not portfolio_scores:
        avg_risk = 50  # Default
    else:
        avg_risk = statistics.mean(portfolio_scores)
    
    # Get market comparison
    if market_data:
        market_scores = [b.get('risk_score', 50) for b in market_data if 'risk_score' in b]
        if market_scores:
            market_avg = statistics.mean(market_scores)
            below_count = sum(1 for score in market_scores if score < avg_risk)
            percentile = (below_count / len(market_scores)) * 100
        else:
            market_avg = 50
            percentile = None
    else:
        market_avg = 50
        percentile = None
    
    # High-risk building count
    high_risk_count = sum(1 for b in portfolio if b.get('risk_score', 0) >= 70)
    
    return {
        'portfolio_size': len(portfolio),
        'average_risk': round(avg_risk, 1),
        'market_average': round(market_avg, 1),
        'portfolio_percentile': round(percentile, 0) if percentile else None,
        'high_risk_buildings': high_risk_count,
        'high_risk_percentage': round(high_risk_count / len(portfolio) * 100, 1) if portfolio else 0,
        'performance': 'Above Market Average' if avg_risk > market_avg else 'Below Market Average',
        'recommendation': _get_portfolio_recommendation(avg_risk, high_risk_count, len(portfolio))
    }


def _generate_similar_building_scores(building_data: Dict) -> List[Dict]:
    """
    Generate mock similar building scores for demonstration.
    In production, this queries actual database.
    """
    import random
    
    # Generate 50-200 similar buildings with realistic score distribution
    count = random.randint(80, 200)
    scores = []
    
    # Normal distribution around 55 with some variance
    for _ in range(count):
        score = random.gauss(55, 18)
        score = max(10, min(95, score))  # Clamp to 10-95
        scores.append({'risk_score': score})
    
    return scores


def _generate_similar_buildings(building_data: Dict) -> List[Dict]:
    """Generate mock similar buildings with full data."""
    import random
    
    base_units = building_data.get('units', 24)
    base_year = building_data.get('year_built', 1965)
    borough = building_data.get('borough', 'Brooklyn')
    
    count = random.randint(80, 200)
    similar = []
    
    for i in range(count):
        # Vary units by ±25%
        units = int(base_units * random.uniform(0.75, 1.25))
        # Vary year by ±12 years
        year = base_year + random.randint(-12, 12)
        # Risk score with some correlation to year
        base_risk = 70 if year < 1960 else 60 if year < 1974 else 45
        risk_score = base_risk + random.gauss(0, 12)
        risk_score = max(10, min(95, risk_score))
        
        similar.append({
            'units': units,
            'year_built': year,
            'borough': borough,
            'risk_score': risk_score
        })
    
    return similar


def _get_match_criteria(building_data: Dict) -> str:
    """Generate human-readable match criteria."""
    criteria = []
    
    if 'borough' in building_data:
        criteria.append(f"{building_data['borough']} properties")
    
    if 'units' in building_data:
        units = building_data['units']
        criteria.append(f"{int(units*0.7)}-{int(units*1.3)} units")
    
    if 'year_built' in building_data:
        year = building_data['year_built']
        criteria.append(f"built {year-15} to {year+15}")
    
    return "Matched on: " + ", ".join(criteria) if criteria else "General market comparison"


def _get_peer_action(percentile: float, risk_score: float, avg_score: float) -> str:
    """Get action item based on peer comparison."""
    if percentile >= 75:
        diff = risk_score - avg_score
        return f"Your score {risk_score:.0f} is {diff:.0f} points above neighborhood average. Immediate review recommended."
    elif percentile >= 50:
        return f"Your score {risk_score:.0f} is above average. Consider preventive measures."
    else:
        return f"Your score {risk_score:.0f} is below neighborhood average. Continue current maintenance."


def _get_portfolio_recommendation(avg_risk: float, high_risk_count: int, total: int) -> str:
    """Get portfolio recommendation."""
    if high_risk_count > total * 0.3:
        return f"⚠️  {high_risk_count} buildings need immediate attention. Portfolio-wide review recommended."
    elif avg_risk > 65:
        return "Portfolio risk is elevated. Focus on preventive maintenance."
    else:
        return "Portfolio health is acceptable. Continue monitoring."
