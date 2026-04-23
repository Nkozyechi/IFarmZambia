"""
Price Prediction Module.
Uses multiple methods to forecast crop prices for target harvest months:
1. Simple Moving Average (SMA) - 3-month and 6-month windows
2. Weighted Moving Average (WMA)
3. Linear Regression - trend-based prediction using numpy

Data source: Zambia Open Data for Africa - Agriculture Statistics 2011-2025.
"""

import numpy as np
from collections import defaultdict
from models.database import get_price_history, get_crop_by_id

MONTH_NAMES = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]


def predict_price(crop_id, target_months, target_year=2026, province='National', start_year=None, end_year=None):
    """
    Predict crop prices for target harvest months using multiple methods.
    
    Args:
        crop_id: ID of the crop
        target_months: list of month numbers (1-12) for harvest period
        target_year: year to predict for (default 2026)
    
    Returns:
        dict with predictions from each method and a combined forecast.
    """
    records = get_price_history(crop_id, start_year, end_year, province)
    crop = get_crop_by_id(crop_id)
    
    if not records:
        return None

    # Organize data
    monthly_prices = defaultdict(list)  # month -> list of prices across years
    chronological_prices = []  # (year, month, price)
    yearly_month_prices = defaultdict(dict)  # year -> {month: price}

    for r in records:
        monthly_prices[r['month']].append({
            'year': r['year'],
            'price': r['price_per_kg']
        })
        chronological_prices.append((r['year'], r['month'], r['price_per_kg']))
        yearly_month_prices[r['year']][r['month']] = r['price_per_kg']

    predictions = {}
    
    for target_month in target_months:
        month_name = MONTH_NAMES[target_month - 1]
        
        # ── Method 1: Simple Moving Average ──────────────────────────────
        sma_prediction = _simple_moving_average(monthly_prices[target_month])
        
        # ── Method 2: Weighted Moving Average ────────────────────────────
        wma_prediction = _weighted_moving_average(monthly_prices[target_month])
        
        # ── Method 3: Linear Regression ──────────────────────────────────
        lr_prediction = _linear_regression(monthly_prices[target_month], target_year)
        
        # ── Method 4: Seasonal Decomposition + Trend ─────────────────────
        seasonal_prediction = _seasonal_trend_prediction(
            yearly_month_prices, target_month, target_year
        )
        
        # ── Combined Forecast (weighted ensemble) ────────────────────────
        valid_predictions = []
        weights = []
        
        if sma_prediction['predicted_price']:
            valid_predictions.append(sma_prediction['predicted_price'])
            weights.append(0.15)  # Lower weight - simple method
        if wma_prediction['predicted_price']:
            valid_predictions.append(wma_prediction['predicted_price'])
            weights.append(0.25)  # Medium weight
        if lr_prediction['predicted_price']:
            valid_predictions.append(lr_prediction['predicted_price'])
            weights.append(0.35)  # Higher weight - captures trend
        if seasonal_prediction['predicted_price']:
            valid_predictions.append(seasonal_prediction['predicted_price'])
            weights.append(0.25)  # Medium-high weight

        if valid_predictions:
            # Normalize weights
            total_w = sum(weights)
            weights = [w / total_w for w in weights]
            combined_price = round(sum(p * w for p, w in zip(valid_predictions, weights)), 2)
            
            # Confidence interval (based on historical std dev for this month)
            month_historical = [p['price'] for p in monthly_prices[target_month]]
            if len(month_historical) >= 3:
                recent_std = np.std(month_historical[-5:])
                ci_lower = round(combined_price - 1.96 * recent_std, 2)
                ci_upper = round(combined_price + 1.96 * recent_std, 2)
            else:
                ci_lower = round(combined_price * 0.85, 2)
                ci_upper = round(combined_price * 1.15, 2)
        else:
            combined_price = None
            ci_lower = ci_upper = None

        predictions[target_month] = {
            'month_name': month_name,
            'target_year': target_year,
            'methods': {
                'simple_moving_average': sma_prediction,
                'weighted_moving_average': wma_prediction,
                'linear_regression': lr_prediction,
                'seasonal_trend': seasonal_prediction,
            },
            'combined_forecast': {
                'predicted_price': combined_price,
                'confidence_interval': {
                    'lower': max(0, ci_lower) if ci_lower else None,
                    'upper': ci_upper,
                },
                'price_range_str': f"ZMW {max(0, ci_lower):.2f} - {ci_upper:.2f}" if ci_lower else 'N/A',
            },
            'historical_prices_for_month': [
                {'year': p['year'], 'price': p['price']}
                for p in monthly_prices[target_month]
            ],
        }

    # Overall summary
    all_combined = [
        p['combined_forecast']['predicted_price']
        for p in predictions.values()
        if p['combined_forecast']['predicted_price']
    ]
    
    return {
        'crop': crop,
        'target_year': target_year,
        'target_months': [MONTH_NAMES[m - 1] for m in target_months],
        'predictions': predictions,
        'overall_expected_price': round(np.mean(all_combined), 2) if all_combined else None,
        'prediction_methods_used': [
            {
                'name': 'Simple Moving Average (SMA)',
                'description': 'Averages the most recent 3 data points for the same month across years.',
                'weight': '15%'
            },
            {
                'name': 'Weighted Moving Average (WMA)',
                'description': 'More recent years are given higher weights (most recent = highest).',
                'weight': '25%'
            },
            {
                'name': 'Linear Regression',
                'description': 'Fits a trend line to historical same-month prices and extrapolates to the target year.',
                'weight': '35%'
            },
            {
                'name': 'Seasonal Trend Decomposition',
                'description': 'Combines the overall yearly price trend with the seasonal pattern for the target month.',
                'weight': '25%'
            },
        ]
    }


def _simple_moving_average(month_data, window=3):
    """Simple Moving Average using last N years of same-month prices."""
    if not month_data:
        return {'predicted_price': None, 'method': 'SMA', 'window': window}
    
    sorted_data = sorted(month_data, key=lambda x: x['year'])
    recent = sorted_data[-window:]
    prices = [d['price'] for d in recent]
    
    predicted = round(np.mean(prices), 2)
    return {
        'predicted_price': predicted,
        'method': 'Simple Moving Average',
        'window': window,
        'data_points_used': len(recent),
        'years_used': [d['year'] for d in recent],
    }


def _weighted_moving_average(month_data, window=5):
    """Weighted Moving Average - more weight on recent years."""
    if not month_data:
        return {'predicted_price': None, 'method': 'WMA', 'window': window}
    
    sorted_data = sorted(month_data, key=lambda x: x['year'])
    recent = sorted_data[-window:]
    prices = [d['price'] for d in recent]
    
    # Linearly increasing weights
    n = len(prices)
    weights = list(range(1, n + 1))
    total_weight = sum(weights)
    
    weighted_sum = sum(p * w for p, w in zip(prices, weights))
    predicted = round(weighted_sum / total_weight, 2)
    
    return {
        'predicted_price': predicted,
        'method': 'Weighted Moving Average',
        'window': window,
        'data_points_used': n,
        'years_used': [d['year'] for d in recent],
        'weights_applied': [round(w / total_weight, 3) for w in weights],
    }


def _linear_regression(month_data, target_year):
    """Linear regression on same-month prices across years."""
    if not month_data or len(month_data) < 2:
        return {'predicted_price': None, 'method': 'Linear Regression'}
    
    sorted_data = sorted(month_data, key=lambda x: x['year'])
    years = np.array([d['year'] for d in sorted_data], dtype=float)
    prices = np.array([d['price'] for d in sorted_data], dtype=float)
    
    # Fit linear regression: price = slope * year + intercept
    n = len(years)
    x_mean = np.mean(years)
    y_mean = np.mean(prices)
    
    numerator = np.sum((years - x_mean) * (prices - y_mean))
    denominator = np.sum((years - x_mean) ** 2)
    
    if denominator == 0:
        return {'predicted_price': round(y_mean, 2), 'method': 'Linear Regression'}
    
    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    
    # Predict
    predicted = round(slope * target_year + intercept, 2)
    
    # R-squared
    y_pred = slope * years + intercept
    ss_res = np.sum((prices - y_pred) ** 2)
    ss_tot = np.sum((prices - y_mean) ** 2)
    r_squared = round(1 - (ss_res / ss_tot), 4) if ss_tot != 0 else 0
    
    return {
        'predicted_price': max(0, predicted),
        'method': 'Linear Regression',
        'slope': round(slope, 4),
        'intercept': round(intercept, 2),
        'r_squared': r_squared,
        'trend_per_year': round(slope, 2),
        'equation': f"Price = {slope:.4f} × Year + ({intercept:.2f})",
        'data_points_used': n,
    }


def _seasonal_trend_prediction(yearly_month_prices, target_month, target_year):
    """Predict using seasonal decomposition and trend extrapolation."""
    if not yearly_month_prices:
        return {'predicted_price': None, 'method': 'Seasonal Trend'}
    
    # Calculate yearly averages
    yearly_avgs = {}
    for year, months in sorted(yearly_month_prices.items()):
        if months:
            yearly_avgs[year] = np.mean(list(months.values()))
    
    if len(yearly_avgs) < 2:
        return {'predicted_price': None, 'method': 'Seasonal Trend'}
    
    # Trend: linear regression on yearly averages
    years = np.array(list(yearly_avgs.keys()), dtype=float)
    avgs = np.array(list(yearly_avgs.values()), dtype=float)
    
    slope = np.polyfit(years, avgs, 1)[0]
    trend_value = np.polyval(np.polyfit(years, avgs, 1), target_year)
    
    # Seasonal factor for target month
    seasonal_factors = []
    for year, months in yearly_month_prices.items():
        if target_month in months and year in yearly_avgs and yearly_avgs[year] > 0:
            factor = months[target_month] / yearly_avgs[year]
            seasonal_factors.append(factor)
    
    if not seasonal_factors:
        return {'predicted_price': None, 'method': 'Seasonal Trend'}
    
    avg_seasonal_factor = np.mean(seasonal_factors)
    predicted = round(trend_value * avg_seasonal_factor, 2)
    
    return {
        'predicted_price': max(0, predicted),
        'method': 'Seasonal Trend Decomposition',
        'trend_component': round(trend_value, 2),
        'seasonal_factor': round(avg_seasonal_factor, 3),
        'yearly_trend_slope': round(slope, 4),
    }
