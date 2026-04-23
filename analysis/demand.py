"""
Market Demand Estimation Module.
Analyzes demand trends and forecasts expected demand during harvest periods.
Data source: Zambia Open Data for Africa - Agriculture Statistics 2011-2025.
"""

import numpy as np
from collections import defaultdict
from models.database import get_demand_history, get_production_history, get_crop_by_id

MONTH_NAMES = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]


def analyze_demand(crop_id, target_months, target_year=2026, province='National', start_year=None, end_year=None):
    """
    Analyze market demand trends and forecast demand for harvest months.
    
    Args:
        crop_id: ID of the crop
        target_months: list of harvest month numbers (1-12)
        target_year: year to forecast for
    
    Returns:
        dict with demand analysis, trends, and forecasts.
    """
    demand_records = get_demand_history(crop_id, start_year, end_year, province)
    production_records = get_production_history(crop_id, start_year, end_year, province)
    crop = get_crop_by_id(crop_id)
    
    if not demand_records:
        return None

    # ── Organize demand data ─────────────────────────────────────────
    monthly_demand = defaultdict(list)
    yearly_demand = defaultdict(list)
    
    for r in demand_records:
        monthly_demand[r['month']].append({
            'year': r['year'],
            'demand_index': r['demand_index'],
            'volume': r['market_volume_mt']
        })
        yearly_demand[r['year']].append(r['demand_index'])

    # ── Seasonal demand pattern ──────────────────────────────────────
    seasonal_pattern = {}
    for month in range(1, 13):
        if month in monthly_demand:
            indices = [d['demand_index'] for d in monthly_demand[month]]
            volumes = [d['volume'] for d in monthly_demand[month] if d['volume']]
            seasonal_pattern[month] = {
                'month_name': MONTH_NAMES[month - 1],
                'avg_demand_index': round(np.mean(indices), 1),
                'min_demand': round(min(indices), 1),
                'max_demand': round(max(indices), 1),
                'avg_volume': round(np.mean(volumes), 1) if volumes else 0,
                'demand_level': _classify_demand(np.mean(indices)),
            }

    # ── Yearly demand trend ──────────────────────────────────────────
    yearly_avg_demand = {}
    for year in sorted(yearly_demand.keys()):
        indices = yearly_demand[year]
        yearly_avg_demand[year] = round(np.mean(indices), 1)

    # Demand growth trend
    years = sorted(yearly_avg_demand.keys())
    if len(years) >= 2:
        y_vals = np.array([yearly_avg_demand[y] for y in years], dtype=float)
        x_vals = np.array(years, dtype=float)
        coeffs = np.polyfit(x_vals, y_vals, 1)
        demand_trend_slope = round(coeffs[0], 3)
        demand_growing = demand_trend_slope > 0.5
    else:
        demand_trend_slope = 0
        demand_growing = False

    # ── Production trend (supply side) ───────────────────────────────
    production_trend = {}
    if production_records:
        for pr in production_records:
            production_trend[pr['year']] = {
                'production_mt': pr['production_mt'],
                'area_harvested_ha': pr['area_harvested_ha'],
                'yield_mt_per_ha': pr['yield_mt_per_ha'],
            }

    # ── Demand forecast for target months ────────────────────────────
    forecasts = {}
    for target_month in target_months:
        month_name = MONTH_NAMES[target_month - 1]
        month_data = monthly_demand.get(target_month, [])
        
        if not month_data:
            forecasts[target_month] = {
                'month_name': month_name,
                'forecast': None,
            }
            continue

        # Weighted moving average of demand indices
        sorted_data = sorted(month_data, key=lambda x: x['year'])
        recent = sorted_data[-5:]
        
        weights = list(range(1, len(recent) + 1))
        total_w = sum(weights)
        
        demand_indices = [d['demand_index'] for d in recent]
        forecast_index = round(
            sum(d * w for d, w in zip(demand_indices, weights)) / total_w, 1
        )
        
        # Apply trend adjustment
        if len(years) >= 3:
            years_ahead = target_year - years[-1]
            trend_adjustment = demand_trend_slope * years_ahead
            forecast_index = round(min(100, forecast_index + trend_adjustment), 1)

        # Volume forecast
        volumes = [d['volume'] for d in recent if d['volume']]
        if volumes:
            vol_weights = list(range(1, len(volumes) + 1))
            vol_total_w = sum(vol_weights)
            forecast_volume = round(
                sum(v * w for v, w in zip(volumes, vol_weights)) / vol_total_w, 1
            )
        else:
            forecast_volume = 0

        forecasts[target_month] = {
            'month_name': month_name,
            'forecast_demand_index': forecast_index,
            'demand_level': _classify_demand(forecast_index),
            'forecast_volume_mt': forecast_volume,
            'historical': [
                {'year': d['year'], 'demand_index': d['demand_index']}
                for d in sorted_data
            ],
            'trend': 'Growing' if demand_growing else 'Stable/Declining',
        }

    # ── Supply-Demand Balance ────────────────────────────────────────
    supply_demand = _analyze_supply_demand_balance(
        production_records, forecasts, target_months, target_year
    )

    return {
        'crop': crop,
        'target_year': target_year,
        'target_months': [MONTH_NAMES[m - 1] for m in target_months],
        'seasonal_pattern': seasonal_pattern,
        'yearly_avg_demand': yearly_avg_demand,
        'demand_trend': {
            'slope': demand_trend_slope,
            'direction': 'Growing' if demand_growing else 'Stable/Declining',
            'annual_change': f"{demand_trend_slope:+.1f} index points/year",
        },
        'forecasts': forecasts,
        'production_trend': production_trend,
        'supply_demand_balance': supply_demand,
    }


def _analyze_supply_demand_balance(production_records, forecasts, target_months, target_year):
    """Assess supply-demand balance for the target period."""
    if not production_records:
        return {'status': 'Insufficient data'}

    # Production trend (linear extrapolation)
    sorted_prod = sorted(production_records, key=lambda x: x['year'])
    if len(sorted_prod) >= 3:
        years = np.array([p['year'] for p in sorted_prod], dtype=float)
        production = np.array([p['production_mt'] for p in sorted_prod], dtype=float)
        coeffs = np.polyfit(years, production, 1)
        projected_production = round(np.polyval(coeffs, target_year), 0)
        prod_growth = round(coeffs[0], 0)
    else:
        projected_production = sorted_prod[-1]['production_mt'] if sorted_prod else 0
        prod_growth = 0

    # Average forecast demand
    avg_forecast_demand = np.mean([
        f.get('forecast_demand_index', 50)
        for f in forecasts.values()
        if isinstance(f, dict) and f.get('forecast_demand_index')
    ]) if forecasts else 50

    # Determine balance
    if avg_forecast_demand >= 80:
        if prod_growth > 0:
            balance = 'Favorable - High demand with growing supply'
            risk = 'Low'
        else:
            balance = 'Potential Shortage - High demand, supply not keeping up'
            risk = 'Medium'
    elif avg_forecast_demand >= 60:
        balance = 'Balanced - Moderate demand, adequate supply expected'
        risk = 'Low'
    else:
        if prod_growth > 0:
            balance = 'Potential Surplus - Low demand with growing supply'
            risk = 'High'
        else:
            balance = 'Low Market Activity - Consider alternative crops'
            risk = 'Medium'

    return {
        'projected_production_mt': projected_production,
        'production_growth_mt_per_year': prod_growth,
        'avg_forecast_demand_index': round(avg_forecast_demand, 1),
        'balance_assessment': balance,
        'supply_risk': risk,
    }


def _classify_demand(index):
    """Classify demand level based on index."""
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
