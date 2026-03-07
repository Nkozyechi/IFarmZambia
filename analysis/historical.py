"""
Historical Price Analysis Module.
Analyzes past price data to identify trends, seasonal patterns, and volatility.
Data source: Zambia Open Data for Africa - Agriculture Statistics 2011-2025.
"""

from models.database import get_price_history, get_crop_by_id
import numpy as np
from collections import defaultdict

MONTH_NAMES = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]


def analyze_price_history(crop_id, start_year=None, end_year=None, province='National'):
    """
    Perform comprehensive historical price analysis for a crop.
    
    Returns:
        dict with monthly_averages, yearly_averages, seasonal_pattern,
        price_volatility, year_over_year_changes, and summary statistics.
    """
    records = get_price_history(crop_id, start_year, end_year, province)
    if not records:
        return None

    crop = get_crop_by_id(crop_id)

    # Group prices by month and by year
    monthly_prices = defaultdict(list)
    yearly_prices = defaultdict(list)
    all_prices = []

    for r in records:
        monthly_prices[r['month']].append(r['price_per_kg'])
        yearly_prices[r['year']].append(r['price_per_kg'])
        all_prices.append(r['price_per_kg'])

    # Monthly averages (seasonal pattern)
    monthly_avg = {}
    for month in range(1, 13):
        if month in monthly_prices:
            prices = monthly_prices[month]
            monthly_avg[month] = {
                'month_name': MONTH_NAMES[month - 1],
                'avg_price': round(np.mean(prices), 2),
                'min_price': round(min(prices), 2),
                'max_price': round(max(prices), 2),
                'std_dev': round(np.std(prices), 2),
                'sample_count': len(prices)
            }

    # Yearly averages
    yearly_avg = {}
    sorted_years = sorted(yearly_prices.keys())
    for year in sorted_years:
        prices = yearly_prices[year]
        yearly_avg[year] = {
            'avg_price': round(np.mean(prices), 2),
            'min_price': round(min(prices), 2),
            'max_price': round(max(prices), 2),
        }

    # Year-over-year changes
    yoy_changes = {}
    for i in range(1, len(sorted_years)):
        prev_year = sorted_years[i - 1]
        curr_year = sorted_years[i]
        prev_avg = yearly_avg[prev_year]['avg_price']
        curr_avg = yearly_avg[curr_year]['avg_price']
        change_pct = round(((curr_avg - prev_avg) / prev_avg) * 100, 1)
        yoy_changes[curr_year] = {
            'previous_avg': prev_avg,
            'current_avg': curr_avg,
            'change_pct': change_pct,
            'direction': 'up' if change_pct > 0 else 'down' if change_pct < 0 else 'stable'
        }

    # Seasonal pattern analysis
    overall_avg = np.mean(all_prices)
    seasonal_indices = {}
    for month in range(1, 13):
        if month in monthly_avg:
            index = round((monthly_avg[month]['avg_price'] / overall_avg) * 100, 1)
            seasonal_indices[month] = {
                'month_name': MONTH_NAMES[month - 1],
                'index': index,
                'classification': _classify_season(index)
            }

    # Identify best and worst months
    if seasonal_indices:
        best_month = max(seasonal_indices.items(), key=lambda x: x[1]['index'])
        worst_month = min(seasonal_indices.items(), key=lambda x: x[1]['index'])
    else:
        best_month = worst_month = (1, {'month_name': 'N/A', 'index': 100})

    # Price volatility (coefficient of variation)
    cv = round((np.std(all_prices) / np.mean(all_prices)) * 100, 1) if all_prices else 0

    # Price trend (overall direction)
    if len(sorted_years) >= 2:
        first_avg = yearly_avg[sorted_years[0]]['avg_price']
        last_avg = yearly_avg[sorted_years[-1]]['avg_price']
        total_change = round(((last_avg - first_avg) / first_avg) * 100, 1)
        annual_growth = round(total_change / (sorted_years[-1] - sorted_years[0]), 1)
    else:
        total_change = 0
        annual_growth = 0

    return {
        'crop': crop,
        'period': {
            'start_year': sorted_years[0] if sorted_years else None,
            'end_year': sorted_years[-1] if sorted_years else None,
            'total_records': len(records)
        },
        'summary': {
            'overall_avg_price': round(overall_avg, 2),
            'overall_min_price': round(min(all_prices), 2),
            'overall_max_price': round(max(all_prices), 2),
            'price_volatility_cv': cv,
            'volatility_level': _classify_volatility(cv),
            'total_price_change_pct': total_change,
            'avg_annual_growth_pct': annual_growth,
            'trend': 'increasing' if annual_growth > 2 else 'decreasing' if annual_growth < -2 else 'stable',
        },
        'monthly_averages': monthly_avg,
        'yearly_averages': yearly_avg,
        'seasonal_indices': seasonal_indices,
        'year_over_year_changes': yoy_changes,
        'best_selling_month': {
            'month': best_month[0],
            'name': best_month[1]['month_name'],
            'index': best_month[1]['index']
        },
        'worst_selling_month': {
            'month': worst_month[0],
            'name': worst_month[1]['month_name'],
            'index': worst_month[1]['index']
        },
        'raw_data': records
    }


def get_price_for_months(crop_id, months, start_year=None, end_year=None, province='National'):
    """Get historical prices for specific months across all years."""
    records = get_price_history(crop_id, start_year, end_year, province)
    filtered = [r for r in records if r['month'] in months]

    by_year = defaultdict(list)
    for r in filtered:
        by_year[r['year']].append(r['price_per_kg'])

    result = {}
    for year in sorted(by_year.keys()):
        prices = by_year[year]
        result[year] = {
            'avg_price': round(np.mean(prices), 2),
            'min_price': round(min(prices), 2),
            'max_price': round(max(prices), 2),
        }
    return result


def _classify_season(index):
    """Classify seasonal index."""
    if index >= 115:
        return 'Peak Season (High Prices)'
    elif index >= 105:
        return 'Above Average'
    elif index >= 95:
        return 'Normal'
    elif index >= 85:
        return 'Below Average'
    else:
        return 'Low Season (Low Prices)'


def _classify_volatility(cv):
    """Classify price volatility."""
    if cv >= 40:
        return 'Very High'
    elif cv >= 25:
        return 'High'
    elif cv >= 15:
        return 'Moderate'
    else:
        return 'Low'
