import json
import urllib.request
import urllib.error
from datetime import datetime

# Approximate central coordinates for Zambian provinces
PROVINCE_COORDINATES = {
    'National': {'lat': -13.1339, 'lon': 27.8493},
    'Central': {'lat': -14.2831, 'lon': 28.5306},
    'Copperbelt': {'lat': -13.0000, 'lon': 27.5000},
    'Eastern': {'lat': -13.6288, 'lon': 31.9701},
    'Luapula': {'lat': -11.2185, 'lon': 29.1738},
    'Lusaka': {'lat': -15.4167, 'lon': 28.2833},
    'Muchinga': {'lat': -10.5186, 'lon': 32.1287},
    'North-Western': {'lat': -12.8719, 'lon': 25.0483},
    'Northern': {'lat': -10.0203, 'lon': 30.6548},
    'Southern': {'lat': -16.5000, 'lon': 27.0000},
    'Western': {'lat': -15.5000, 'lon': 23.5000}
}

def get_weather_forecast(province):
    """
    Fetches a 7-day weather forecast for the given province using Open-Meteo.
    Uses urllib to avoid requiring the 'requests' package.
    """
    coords = PROVINCE_COORDINATES.get(province, PROVINCE_COORDINATES['National'])
    
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={coords['lat']}&longitude={coords['lon']}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
        f"&timezone=Africa%2FLusaka"
    )
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (IFarmZambia)'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            
            # Format the data for the template
            forecast = []
            daily = data.get('daily', {})
            times = daily.get('time', [])
            temp_max = daily.get('temperature_2m_max', [])
            temp_min = daily.get('temperature_2m_min', [])
            precip = daily.get('precipitation_sum', [])
            
            for i in range(len(times)):
                date_obj = datetime.strptime(times[i], '%Y-%m-%d')
                day_name = date_obj.strftime('%A')
                
                forecast.append({
                    'date': times[i],
                    'day': day_name,
                    'temp_max': temp_max[i] if i < len(temp_max) else 0,
                    'temp_min': temp_min[i] if i < len(temp_min) else 0,
                    'precipitation': precip[i] if i < len(precip) else 0
                })
                
            return {
                'province': province,
                'forecast': forecast
            }
            
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return None
