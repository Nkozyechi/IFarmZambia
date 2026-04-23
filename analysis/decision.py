"""
Decision Support Module.
Generates comprehensive planting decision reports by combining:
- Historical price analysis
- Price predictions
- Market demand estimates
- Risk assessment

Data source: Zambia Open Data for Africa - Agriculture Statistics 2011-2025.
"""

from analysis.historical import analyze_price_history, get_price_for_months
from analysis.prediction import predict_price
from analysis.demand import analyze_demand
from models.database import get_crop_by_id, get_production_costs, get_production_history

MONTH_NAMES = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]


def generate_decision_report(crop_id, planting_month, harvest_months, target_year=2026, farm_size_ha=1.0, custom_costs=None, province='National', start_year=None, end_year=None, has_irrigation=False):
    """
    Generate a comprehensive decision report for planting decisions.
    
    Args:
        crop_id: ID of the crop
        planting_month: month number when planting occurs (1-12)
        harvest_months: list of month numbers for expected harvest
        target_year: year to predict for
        farm_size_ha: size of the farm in hectares for profitability calc
        custom_costs: dict of custom costs replacing the generic DB costs
        has_irrigation: boolean if the farm has an irrigation system
    
    Returns:
        Complete decision report dict.
    """
    crop = get_crop_by_id(crop_id)
    if not crop:
        return None

    # Run all analysis modules
    historical = analyze_price_history(crop_id, start_year=start_year, end_year=end_year, province=province)
    price_prediction = predict_price(crop_id, harvest_months, target_year, province=province, start_year=start_year, end_year=end_year)
    demand_analysis = analyze_demand(crop_id, harvest_months, target_year, province=province, start_year=start_year, end_year=end_year)

    if not historical or not price_prediction or not demand_analysis:
        return None

    # ── Extract key metrics ──────────────────────────────────────────
    
    # Price during harvest
    harvest_prices = {}
    for m in harvest_months:
        if m in price_prediction['predictions']:
            pred = price_prediction['predictions'][m]
            harvest_prices[m] = {
                'month_name': MONTH_NAMES[m - 1],
                'predicted_price': pred['combined_forecast']['predicted_price'],
                'price_range': pred['combined_forecast']['price_range_str'],
                'ci_lower': pred['combined_forecast']['confidence_interval']['lower'],
                'ci_upper': pred['combined_forecast']['confidence_interval']['upper'],
            }

    # Average expected price
    predicted_prices = [
        hp['predicted_price'] for hp in harvest_prices.values()
        if hp['predicted_price']
    ]
    avg_expected_price = round(sum(predicted_prices) / len(predicted_prices), 2) if predicted_prices else 0

    # Best month to sell
    if harvest_prices:
        best_month = max(
            harvest_prices.items(),
            key=lambda x: x[1]['predicted_price'] if x[1]['predicted_price'] else 0
        )
    else:
        best_month = None

    # Demand during harvest
    harvest_demand = {}
    for m in harvest_months:
        if m in demand_analysis['forecasts']:
            f = demand_analysis['forecasts'][m]
            harvest_demand[m] = {
                'month_name': MONTH_NAMES[m - 1],
                'demand_index': f.get('forecast_demand_index', 50),
                'demand_level': f.get('demand_level', 'Unknown'),
                'volume_mt': f.get('forecast_volume_mt', 0),
            }

    avg_demand = round(
        sum(hd['demand_index'] for hd in harvest_demand.values()) / len(harvest_demand), 1
    ) if harvest_demand else 50

    # ── Profitability Calculation ────────────────────────────────────
    prod_history = get_production_history(crop_id, province=province)
    latest_yield_mt_per_ha = prod_history[-1]['yield_mt_per_ha'] if prod_history else 0
    
    # ── Irrigation Logic: Yield Bonus ────────────────────────────────
    # Zambia Dry Season: May (5) to October (10)
    is_dry_season = 5 <= planting_month <= 10
    irrigation_yield_factor = 1.0
    
    if has_irrigation:
        if is_dry_season:
            irrigation_yield_factor = 1.25  # 25% boost in dry season
        else:
            irrigation_yield_factor = 1.10  # 10% stability boost in rainy season
    elif is_dry_season:
        # Rain-fed farming in dry season carries a penalty/risk
        irrigation_yield_factor = 0.80  # 20% penalty for dry season without irrigation
        
    latest_yield_mt_per_ha *= irrigation_yield_factor
    total_yield_kg = latest_yield_mt_per_ha * 1000 * farm_size_ha
    
    production_costs = get_production_costs(crop_id)
    default_breakdown = {
        'seed': 0,
        'fertilizer': 0,
        'chemicals': 0,
        'labor': 0,
        'other': 0,
    }

    if production_costs:
        default_breakdown = {
            'seed': production_costs['seed_cost_per_ha'],
            'fertilizer': production_costs['fertilizer_cost_per_ha'],
            'chemicals': production_costs['chemical_cost_per_ha'],
            'labor': production_costs['labor_cost_per_ha'],
            'other': production_costs['other_costs_per_ha']
        }

    # ── Irrigation Logic: Operational Cost ───────────────────────────
    if has_irrigation:
        # Add 500 ZMW/ha for irrigation maintenance, fuel, and labor
        default_breakdown['other'] += 500.0

    uses_custom_costs = bool(custom_costs)
    if uses_custom_costs:
        breakdown = {
            **default_breakdown,
            'seed': custom_costs.get('seed', default_breakdown['seed']),
            'fertilizer': custom_costs.get('fertilizer', default_breakdown['fertilizer']),
            'chemicals': custom_costs.get('chemicals', default_breakdown['chemicals']),
            'labor': custom_costs.get('labor', default_breakdown['labor']),
        }
    else:
        breakdown = default_breakdown

    cost_per_ha = sum(breakdown.values())
    cost_source_label = (
        'Custom inputs' + (' (incl. irrigation ops)' if has_irrigation else '')
        if uses_custom_costs else
        'Database averages' + (' (incl. irrigation ops)' if has_irrigation else '')
    )

    total_cost = cost_per_ha * farm_size_ha
    projected_revenue = total_yield_kg * avg_expected_price
    projected_profit = projected_revenue - total_cost
    roi_pct = round((projected_profit / total_cost * 100), 1) if total_cost > 0 else 0
    
    profitability = {
        'farm_size_ha': farm_size_ha,
        'cost_per_ha': cost_per_ha,
        'total_cost': total_cost,
        'breakdown': breakdown,
        'yield_mt_per_ha': round(latest_yield_mt_per_ha, 3),
        'total_yield_kg': total_yield_kg,
        'projected_revenue': projected_revenue,
        'projected_profit': projected_profit,
        'roi_pct': roi_pct,
        'is_profitable': projected_profit > 0,
        'uses_custom_costs': uses_custom_costs,
        'has_irrigation': has_irrigation,
        'cost_source': 'custom' if uses_custom_costs else 'database_average',
        'cost_source_label': cost_source_label,
    }

    # ── Risk Assessment ──────────────────────────────────────────────
    risks = _assess_risks(
        historical, price_prediction, demand_analysis,
        harvest_months, harvest_prices, avg_demand,
        planting_month=planting_month, has_irrigation=has_irrigation
    )
    
    # ── Final Recommendation ─────────────────────────────────────────
    recommendation = _generate_recommendation(
        crop, avg_expected_price, avg_demand, risks,
        historical, planting_month, harvest_months,
        has_irrigation=has_irrigation
    )

    # ── Seasonal comparison ──────────────────────────────────────────
    # Compare harvest months vs best selling months
    seasonal = historical.get('seasonal_indices', {})
    harvest_seasonal_avg = 0
    if seasonal:
        harvest_indices = [
            seasonal[m]['index'] for m in harvest_months if m in seasonal
        ]
        if harvest_indices:
            harvest_seasonal_avg = round(sum(harvest_indices) / len(harvest_indices), 1)

    return {
        'crop': crop,
        'scenario': {
            'planting_month': MONTH_NAMES[planting_month - 1],
            'harvest_months': [MONTH_NAMES[m - 1] for m in harvest_months],
            'target_year': target_year,
            'growth_period': f"{crop['growth_period_months']} months",
            'province': province,
        },
        'price_analysis': {
            'historical_summary': historical['summary'],
            'harvest_predictions': harvest_prices,
            'avg_expected_price': avg_expected_price,
            'best_selling_month': {
                'month': best_month[1]['month_name'] if best_month else 'N/A',
                'price': best_month[1]['predicted_price'] if best_month else 0,
            },
            'price_per_50kg_bag': round(avg_expected_price * 50, 2),
        },
        'demand_analysis': {
            'harvest_demand': harvest_demand,
            'avg_demand_index': avg_demand,
            'demand_level': _classify_demand_level(avg_demand),
            'demand_trend': demand_analysis['demand_trend']['direction'],
            'supply_demand': demand_analysis['supply_demand_balance'],
        },
        'profitability': profitability,
        'risk_assessment': risks,
        'recommendation': recommendation,
        'seasonal_timing': {
            'harvest_seasonal_index': harvest_seasonal_avg,
            'best_selling_month': historical['best_selling_month'],
            'worst_selling_month': historical['worst_selling_month'],
            'is_optimal_timing': harvest_seasonal_avg >= 95,
        },
        'prediction_methods': price_prediction.get('prediction_methods_used', []),
        'data_coverage': {
            'years_analyzed': f"{historical['period']['start_year']}-{historical['period']['end_year']}",
            'total_price_records': historical['period']['total_records'],
            'source': 'Zambia Open Data for Africa - Agriculture Statistics 2011-2025',
        },
    }


def _assess_risks(historical, prediction, demand, harvest_months, harvest_prices, avg_demand, planting_month=None, has_irrigation=False):
    """Identify and assess risks for the planting decision."""
    risks = []

    # 1. Price volatility risk
    volatility = historical['summary']['price_volatility_cv']
    if volatility >= 30:
        risks.append({
            'type': 'Price Volatility',
            'severity': 'High',
            'description': f'Price volatility is high (CV={volatility}%). Prices can fluctuate significantly, making revenue uncertain.',
            'mitigation': 'Consider contract farming or forward selling to lock in prices.'
        })
    elif volatility >= 20:
        risks.append({
            'type': 'Price Volatility',
            'severity': 'Medium',
            'description': f'Moderate price volatility (CV={volatility}%). Some price fluctuation is expected.',
            'mitigation': 'Monitor market prices regularly and plan flexible selling windows.'
        })

    # 2. Seasonal surplus risk
    seasonal = historical.get('seasonal_indices', {})
    for m in harvest_months:
        if m in seasonal and seasonal[m]['index'] < 90:
            risks.append({
                'type': 'Seasonal Surplus',
                'severity': 'Medium' if seasonal[m]['index'] >= 80 else 'High',
                'description': f'{MONTH_NAMES[m-1]} typically has below-average prices (seasonal index: {seasonal[m]["index"]}), indicating market surplus during this period.',
                'mitigation': 'Consider storage to sell later when prices recover, or target early/late harvest.'
            })

    # 3. Low demand risk
    if avg_demand < 55:
        risks.append({
            'type': 'Low Market Demand',
            'severity': 'High',
            'description': f'Expected demand is low (index: {avg_demand}) during harvest months.',
            'mitigation': 'Explore value-added processing or alternative markets.'
        })
    elif avg_demand < 70:
        risks.append({
            'type': 'Moderate Demand',
            'severity': 'Low',
            'description': f'Demand is moderate (index: {avg_demand}). Competition may be significant.',
            'mitigation': 'Focus on quality to differentiate from competitors.'
        })

    # 4. Supply-demand imbalance
    sd = demand.get('supply_demand_balance', {})
    if sd.get('supply_risk') in ['High', 'Medium']:
        risks.append({
            'type': 'Supply-Demand Imbalance',
            'severity': sd['supply_risk'],
            'description': sd.get('balance_assessment', 'Potential market imbalance detected.'),
            'mitigation': 'Diversify crops or adjust planting area to reduce exposure.'
        })

    # 5. Price decline trend
    trend = historical['summary'].get('trend', 'stable')
    if trend == 'decreasing':
        risks.append({
            'type': 'Declining Price Trend',
            'severity': 'Medium',
            'description': 'Historical data shows a declining price trend for this crop.',
            'mitigation': 'Consider switching to higher-value crops or reducing planted area.'
        })

    # 6. Rainfall Dependency / Dry Season Risk
    if planting_month:
        is_dry_season = 5 <= planting_month <= 10
        if is_dry_season and not has_irrigation:
            risks.append({
                'type': 'Dry Season Rainfall Risk',
                'severity': 'High',
                'description': f'Planting in {MONTH_NAMES[planting_month-1]} occurs during the dry season without irrigation. High risk of crop failure or significantly reduced yields.',
                'mitigation': 'Install an irrigation system or delay planting until the rainy season (November).'
            })
        elif has_irrigation:
            risks.append({
                'type': 'Irrigation Advantage',
                'severity': 'Low', # Negative risk / Positive factor
                'description': 'Farm irrigation system significantly mitigates rainfall dependency and enables dry-season production.',
                'mitigation': 'Maintain irrigation equipment regularly to ensure consistent water supply.'
            })

    # Overall risk level
    high_risks = sum(1 for r in risks if r['severity'] == 'High')
    medium_risks = sum(1 for r in risks if r['severity'] == 'Medium')
    
    if high_risks >= 2:
        overall_risk = 'High'
    elif high_risks >= 1 or medium_risks >= 2:
        overall_risk = 'Medium'
    elif medium_risks >= 1:
        overall_risk = 'Low-Medium'
    else:
        overall_risk = 'Low'

    return {
        'individual_risks': risks,
        'risk_count': len(risks),
        'high_risk_count': high_risks,
        'medium_risk_count': medium_risks,
        'overall_risk_level': overall_risk,
    }


def _generate_recommendation(crop, avg_price, avg_demand, risks, historical, planting_month, harvest_months, has_irrigation=False):
    """Generate a final planting recommendation."""
    score = 50  # Start at neutral

    # Price factors
    if avg_price > 0:
        # Compare with historical average
        hist_avg = historical['summary']['overall_avg_price']
        if avg_price > hist_avg * 1.15:
            score += 15
            price_outlook = 'Favorable - predicted prices are above historical average'
        elif avg_price > hist_avg * 0.95:
            score += 5
            price_outlook = 'Neutral - predicted prices are near historical average'
        else:
            score -= 10
            price_outlook = 'Unfavorable - predicted prices are below historical average'
    else:
        price_outlook = 'Insufficient data for price outlook'

    # Demand factors
    if avg_demand >= 75:
        score += 15
        demand_outlook = 'Strong demand expected during harvest period'
    elif avg_demand >= 60:
        score += 5
        demand_outlook = 'Moderate demand expected during harvest period'
    else:
        score -= 10
        demand_outlook = 'Weak demand expected during harvest period'

    # Trend factors
    trend = historical['summary'].get('trend', 'stable')
    if trend == 'increasing':
        score += 10
    elif trend == 'decreasing':
        score -= 10

    # Risk factors
    score -= risks['high_risk_count'] * 10
    score -= risks['medium_risk_count'] * 5
    
    # Irrigation Bonus
    if has_irrigation:
        score += 10  # Baseline bonus for stability
        if 5 <= planting_month <= 10:
            score += 5  # Extra bonus for enabling dry-season farming

    # Seasonal timing
    seasonal = historical.get('seasonal_indices', {})
    harvest_indices = [seasonal[m]['index'] for m in harvest_months if m in seasonal]
    if harvest_indices:
        avg_seasonal = sum(harvest_indices) / len(harvest_indices)
        if avg_seasonal >= 110:
            score += 10
        elif avg_seasonal < 85:
            score -= 10

    # Clamp score
    score = max(0, min(100, score))

    # Generate recommendation
    if score >= 70:
        verdict = 'RECOMMENDED'
        confidence = 'High'
        summary = f'Planting {crop["name"]} in {MONTH_NAMES[planting_month-1]} is likely to be profitable. {price_outlook}. {demand_outlook}.'
        if has_irrigation:
            summary += ' Irrigation provides a significant competitive advantage.'
        color = 'green'
    elif score >= 45:
        verdict = 'PROCEED WITH CAUTION'
        confidence = 'Moderate'
        summary = f'Planting {crop["name"]} in {MONTH_NAMES[planting_month-1]} may be moderately profitable but carries some risks. {price_outlook}. {demand_outlook}. Consider risk mitigation strategies.'
        color = 'yellow'
    else:
        verdict = 'NOT RECOMMENDED'
        confidence = 'Low'
        summary = f'Planting {crop["name"]} in {MONTH_NAMES[planting_month-1]} is unlikely to be highly profitable based on current analysis. {price_outlook}. {demand_outlook}. Consider alternative crops or timing.'
        color = 'red'

    return {
        'verdict': verdict,
        'confidence': confidence,
        'score': score,
        'color': color,
        'summary': summary,
        'price_outlook': price_outlook,
        'demand_outlook': demand_outlook,
        'key_factors': [
            f'Historical price trend: {trend}',
            f'Price volatility: {historical["summary"]["volatility_level"]}',
            f'Expected demand: {_classify_demand_level(avg_demand)}',
            f'Risk level: {risks["overall_risk_level"]}',
            f'Irrigation status: {"Enabled" if has_irrigation else "None"}',
        ],
    }


def _classify_demand_level(index):
    if index >= 80:
        return 'High'
    elif index >= 65:
        return 'Moderate-High'
    elif index >= 50:
        return 'Moderate'
    elif index >= 35:
        return 'Low-Moderate'
    else:
        return 'Low'
