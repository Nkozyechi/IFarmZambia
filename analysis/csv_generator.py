"""
CSV Generator module for IFarm Zambia.
Converts decision reports and related historical data into downloadable CSV files.
"""

import csv
import io

def generate_report_csv(report_data):
    """
    Generate a CSV string containing the summary of the report
    and the historical price data for the crop.
    
    Args:
        report_data (dict): The complete decision report dictionary.
        
    Returns:
        str: The CSV content as a string.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # ── Report Summary Section ───────────────────────────────────────────────
    writer.writerow(["IFarm Zambia - Decision Report"])
    writer.writerow(["Crop", report_data['crop']['name']])
    writer.writerow(["Region/Province", report_data.get('scenario', {}).get('province', 'National')])
    harvest_months = ", ".join(report_data['scenario']['harvest_months'])
    writer.writerow(["Target Harvest Period", f"{harvest_months} {report_data['scenario']['target_year']}"])
    writer.writerow([])
    
    writer.writerow(["Overall Recommendation", report_data['recommendation']['verdict']])
    writer.writerow(["Confidence Score", f"{report_data['recommendation']['score']}/100"])
    writer.writerow([])
    
    writer.writerow(["Key Metrics"])
    writer.writerow(["Expected Price (ZMW/kg)", round(report_data['price_analysis']['avg_expected_price'], 2)])
    writer.writerow(["Demand Index", report_data['demand_analysis']['avg_demand_index']])
    writer.writerow(["Risk Level", report_data['risk_assessment']['overall_risk_level']])
    writer.writerow([])
    
    if 'profitability' in report_data:
        prof = report_data['profitability']
        writer.writerow(["Profitability Forecast"])
        writer.writerow(["Farm Size (ha)", prof['farm_size_ha']])
        writer.writerow(["Gross Revenue (ZMW)", round(prof['projected_revenue'], 2)])
        writer.writerow(["Total Cost (ZMW)", round(prof['total_cost'], 2)])
        writer.writerow(["Net Profit (ZMW)", round(prof['projected_profit'], 2)])
        writer.writerow(["ROI (%)", prof['roi_pct']])
    
    writer.writerow([])
    return output.getvalue()

def generate_history_csv(historical_data):
    """
    Generate a CSV of historical prices.
    
    Args:
        historical_data (dict): Result of analyze_price_history()
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(["IFarm Zambia - Historical Dataset"])
    crop_name = historical_data['crop']['name'] if 'crop' in historical_data else "Unknown"
    writer.writerow(["Crop", crop_name])
    writer.writerow([])
    
    # Header
    writer.writerow(["Year", "Month", "Price per kg (ZMW)", "Price per 50kg bag (ZMW)"])
    
    for row in historical_data.get('raw_data', []):
        writer.writerow([
            row.get('year'), 
            row.get('month'), 
            row.get('price_per_kg'), 
            row.get('price_per_50kg_bag')
        ])
        
    return output.getvalue()
