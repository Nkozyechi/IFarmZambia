"""
IFarm Zambia - Farm Market Analysis & Price Prediction System
Flask web application entry point.

Data source: Zambia Open Data for Africa - Agriculture Statistics 2011-2025
https://zambia.opendataforafrica.org/etqmqgf/agriculture-statistics-2011-2025
"""

import os
import json
import sqlite3
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from models.database import get_db, get_db_path, get_crop_list, get_crop_by_id, get_price_history
from models.database import get_user_by_id, get_user_by_username, create_user
from models.database import get_marketplace_listings, add_marketplace_listing, delete_marketplace_listing
from analysis.historical import analyze_price_history
from analysis.prediction import predict_price
from analysis.demand import analyze_demand
from analysis.decision import generate_decision_report
from analysis.weather import get_weather_forecast
from data.seed_data import seed_database

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.environ.get('SECRET_KEY', 'ifarm-zambia-local-dev'))

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

@login_manager.user_loader
def load_user(user_id):
    user_data = get_user_by_id(user_id)
    if user_data:
        return User(id=user_data['id'], username=user_data['username'], password_hash=user_data['password_hash'])
    return None

MONTH_NAMES = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]

CUSTOM_COST_FIELDS = (
    ('seed', 'seed_cost'),
    ('fertilizer', 'fertilizer_cost'),
    ('chemicals', 'chemical_cost'),
    ('labor', 'labor_cost'),
)

PROVINCES = [
    'National', 'Central', 'Copperbelt', 'Eastern', 'Luapula', 
    'Lusaka', 'Muchinga', 'North-Western', 'Northern', 'Southern', 'Western'
]

def ensure_db():
    """Ensure database exists and is populated."""
    if not os.path.exists(get_db_path()):
        seed_database()


def build_harvest_months(harvest_start, harvest_end):
    """Build a contiguous harvest month window, including year wrap-around."""
    if harvest_start <= harvest_end:
        return list(range(harvest_start, harvest_end + 1))
    return list(range(harvest_start, 13)) + list(range(1, harvest_end + 1))


def empty_custom_costs():
    """Return an empty custom-cost payload for template defaults."""
    return {key: '' for key, _ in CUSTOM_COST_FIELDS}

# Load Translations Dictionary
try:
    with open('static/data/translations.json', 'r', encoding='utf-8') as f:
        TRANSLATIONS = json.load(f)
except FileNotFoundError:
    TRANSLATIONS = {'en': {}}

# Custom fields for per-hectare cost overrides
def parse_custom_costs(values):
    """Extract optional per-hectare custom costs from form or query params."""
    use_custom_costs = str(values.get('use_custom_costs', '')).lower() in {'1', 'true', 'on', 'yes'}
    selected_costs = empty_custom_costs()
    parsed_costs = {}

    for key, field_name in CUSTOM_COST_FIELDS:
        raw_value = values.get(field_name, '')
        raw_value = raw_value.strip() if isinstance(raw_value, str) else raw_value

        if raw_value in (None, ''):
            if use_custom_costs:
                parsed_costs[key] = 0.0
                selected_costs[key] = 0.0
            continue

        try:
            numeric_value = max(float(raw_value), 0.0)
        except (TypeError, ValueError):
            numeric_value = 0.0

        selected_costs[key] = numeric_value if use_custom_costs else raw_value
        if use_custom_costs:
            parsed_costs[key] = numeric_value

    return use_custom_costs, (parsed_costs if use_custom_costs else None), selected_costs


# ── Localization ─────────────────────────────────────────────────────────────

@app.route('/set_language/<lang_code>')
def set_language(lang_code):
    """Set the user's preferred language in the session."""
    if lang_code in TRANSLATIONS:
        session['lang'] = lang_code
    return redirect(request.referrer or url_for('index'))

@app.context_processor
def inject_translations():
    """Inject the translation function `t` into all Jinja templates."""
    def t(key):
        lang = session.get('lang', 'en')
        return TRANSLATIONS.get(lang, {}).get(key, TRANSLATIONS.get('en', {}).get(key, key))
    
    return dict(t=t, current_lang=session.get('lang', 'en'))

# ── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Home page - landing page for new users, dashboard for logged in."""
    ensure_db()
    
    if not current_user.is_authenticated:
        return render_template('landing.html')
        
    crops = get_crop_list()
    
    # Get latest price for each crop
    crop_summaries = []
    for crop in crops:
        prices = get_price_history(crop['id'])
        if prices:
            latest = prices[-1]
            # Get previous month for comparison
            prev = prices[-2] if len(prices) >= 2 else None
            change = 0
            if prev:
                change = round(((latest['price_per_kg'] - prev['price_per_kg']) / prev['price_per_kg']) * 100, 1)
            
            crop_summaries.append({
                **crop,
                'latest_price': latest['price_per_kg'],
                'latest_month': MONTH_NAMES[latest['month'] - 1],
                'latest_year': latest['year'],
                'price_change': change,
                'trend': 'up' if change > 0 else 'down' if change < 0 else 'stable',
                'sparkline': [p['price_per_kg'] for p in prices[-12:]] if len(prices) >= 12 else [p['price_per_kg'] for p in prices]
            })
        else:
            crop_summaries.append({**crop, 'latest_price': 0, 'price_change': 0, 'trend': 'stable', 'sparkline': []})

    return render_template('index.html', crops=crop_summaries, months=MONTH_NAMES)


@app.route('/landing')
def landing():
    """Explicit landing page view."""
    return render_template('landing.html')


@app.route('/analyze', methods=['GET', 'POST'])
def analyze():
    """Crop analysis page."""
    ensure_db()
    crops = get_crop_list()
    
    if request.method == 'POST':
        crop_id = int(request.form.get('crop_id', 1))
        planting_month = int(request.form.get('planting_month', 2))
        harvest_start = int(request.form.get('harvest_start', 4))
        harvest_end = int(request.form.get('harvest_end', 5))
        farm_size_ha = float(request.form.get('farm_size_ha', 1.0))
        province = request.form.get('province', 'National')
        
        start_year = request.form.get('start_year')
        start_year = int(start_year) if start_year else None
        end_year = request.form.get('end_year')
        end_year = int(end_year) if end_year else None

        has_irrigation = request.form.get('has_irrigation') == '1'
        use_custom_costs, custom_costs, selected_custom_costs = parse_custom_costs(request.form)

        # Build harvest months list
        harvest_months = build_harvest_months(harvest_start, harvest_end)
        
        # Run analysis
        report = generate_decision_report(
            crop_id,
            planting_month,
            harvest_months,
            target_year=2026,
            farm_size_ha=farm_size_ha,
            custom_costs=custom_costs,
            province=province,
            start_year=start_year,
            end_year=end_year,
            has_irrigation=has_irrigation,
        )
        historical = analyze_price_history(crop_id, start_year=start_year, end_year=end_year, province=province)
        prediction = predict_price(crop_id, harvest_months, target_year=2026, province=province, start_year=start_year, end_year=end_year)
        demand = analyze_demand(crop_id, harvest_months, target_year=2026, province=province, start_year=start_year, end_year=end_year)
        weather = get_weather_forecast(province)
        
        return render_template(
            'analyze.html',
            crops=crops,
            months=MONTH_NAMES,
            report=report,
            historical=historical,
            prediction=prediction,
            demand=demand,
            weather=weather,
            selected_crop=crop_id,
            selected_planting=planting_month,
            selected_harvest_start=harvest_start,
            selected_harvest_end=harvest_end,
            selected_farm_size=farm_size_ha,
            selected_province=province,
            selected_use_custom_costs=use_custom_costs,
            selected_custom_costs=selected_custom_costs,
            selected_has_irrigation=has_irrigation,
            selected_start_year=start_year,
            selected_end_year=end_year,
            provinces=PROVINCES
        )
    
    return render_template(
        'analyze.html',
        crops=crops,
        months=MONTH_NAMES,
        provinces=PROVINCES,
        report=None,
        selected_use_custom_costs=False,
        selected_custom_costs=empty_custom_costs(),
        selected_has_irrigation=False,
    )


@app.route('/report/<int:crop_id>/<int:planting_month>/<int:harvest_start>/<int:harvest_end>/<float:farm_size_ha>/<string:province>')
@login_required
def report(crop_id, planting_month, harvest_start, harvest_end, farm_size_ha, province):
    """Full decision report page."""
    ensure_db()
    use_custom_costs, custom_costs, selected_custom_costs = parse_custom_costs(request.args)
    has_irrigation = request.args.get('has_irrigation') == '1'
    harvest_months = build_harvest_months(harvest_start, harvest_end)
    
    start_year = request.args.get('start_year', type=int)
    end_year = request.args.get('end_year', type=int)

    report_data = generate_decision_report(
        crop_id,
        planting_month,
        harvest_months,
        target_year=2026,
        farm_size_ha=farm_size_ha,
        custom_costs=custom_costs,
        province=province,
        start_year=start_year,
        end_year=end_year,
        has_irrigation=has_irrigation,
    )
    
    if not report_data:
        return redirect(url_for('analyze'))
    
    return render_template('report.html', report=report_data, months=MONTH_NAMES, 
                           crop_id=crop_id, planting_month=planting_month, 
                           harvest_start=harvest_start, harvest_end=harvest_end,
                           farm_size_ha=farm_size_ha, province=province,
                           selected_use_custom_costs=use_custom_costs,
                           selected_custom_costs=selected_custom_costs,
                           selected_has_irrigation=has_irrigation,
                           selected_start_year=start_year,
                           selected_end_year=end_year)


@app.route('/report/<int:crop_id>/<int:planting_month>/<int:harvest_start>/<int:harvest_end>/<float:farm_size_ha>/<string:province>/pdf')
@login_required
def report_pdf(crop_id, planting_month, harvest_start, harvest_end, farm_size_ha, province):
    """Download full decision report as PDF."""
    ensure_db()
    _, custom_costs, _ = parse_custom_costs(request.args)
    has_irrigation = request.args.get('has_irrigation') == '1'
    harvest_months = build_harvest_months(harvest_start, harvest_end)
    
    start_year = request.args.get('start_year', type=int)
    end_year = request.args.get('end_year', type=int)

    report_data = generate_decision_report(
        crop_id,
        planting_month,
        harvest_months,
        target_year=2026,
        farm_size_ha=farm_size_ha,
        custom_costs=custom_costs,
        province=province,
        start_year=start_year,
        end_year=end_year,
        has_irrigation=has_irrigation,
    )
    
    if not report_data:
        return redirect(url_for('analyze'))
    
    from analysis.pdf_generator import generate_report_pdf
    from flask import make_response
    
    pdf_bytes = generate_report_pdf(report_data)
    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=IFarm_Zambia_Report_{report_data["crop"]["name"].replace(" ", "_")}.pdf'
    
    return response


@app.route('/report/<int:crop_id>/<int:planting_month>/<int:harvest_start>/<int:harvest_end>/<float:farm_size_ha>/<string:province>/csv')
@login_required
def report_csv(crop_id, planting_month, harvest_start, harvest_end, farm_size_ha, province):
    """Download historical data as CSV."""
    ensure_db()
    
    start_year = request.args.get('start_year', type=int)
    end_year = request.args.get('end_year', type=int)

    historical = analyze_price_history(crop_id, start_year=start_year, end_year=end_year, province=province)
    if not historical:
        return redirect(url_for('analyze'))
        
    from analysis.csv_generator import generate_history_csv
    from flask import make_response
    
    csv_data = generate_history_csv(historical)
    response = make_response(csv_data)
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=IFarm_Zambia_History_{historical["crop"]["name"].replace(" ", "_")}.csv'
    
    return response



@app.route('/compare', methods=['GET', 'POST'])
@login_required
def compare():
    """Side-by-side crop comparison."""
    ensure_db()
    crops = get_crop_list()
    
    if request.method == 'POST':
        crop1_id = int(request.form.get('crop1_id', 0))
        crop2_id = int(request.form.get('crop2_id', 0))
        crop3_id = request.form.get('crop3_id')
        crop3_id = int(crop3_id) if crop3_id else 0
        
        planting_month = int(request.form.get('planting_month', 2))
        harvest_start = int(request.form.get('harvest_start', 4))
        harvest_end = int(request.form.get('harvest_end', 5))
        farm_size_ha = float(request.form.get('farm_size_ha', 1.0))
        province = request.form.get('province', 'National')
        
        harvest_months = build_harvest_months(harvest_start, harvest_end)
        
        selected_crop_ids = [cid for cid in [crop1_id, crop2_id, crop3_id] if cid > 0]
        
        reports = []
        for cid in selected_crop_ids:
            rep = generate_decision_report(cid, planting_month, harvest_months, target_year=2026, farm_size_ha=farm_size_ha, province=province)
            if rep:
                reports.append(rep)
                
        return render_template('compare.html', crops=crops, months=MONTH_NAMES, reports=reports,
                               selected_crop1=crop1_id, selected_crop2=crop2_id, selected_crop3=crop3_id,
                               selected_planting=planting_month, selected_harvest_start=harvest_start,
                               selected_harvest_end=harvest_end, selected_farm_size=farm_size_ha,
                               selected_province=province, provinces=PROVINCES)

    return render_template('compare.html', crops=crops, months=MONTH_NAMES, reports=None, provinces=PROVINCES)


@app.route('/marketplace', methods=['GET'])
def marketplace():
    """Marketplace view showing all listings."""
    ensure_db()
    listings = get_marketplace_listings()
    crops = get_crop_list()
    return render_template('marketplace.html', listings=listings, crops=crops, provinces=PROVINCES)


@app.route('/marketplace/add', methods=['POST'])
@login_required
def marketplace_add():
    ensure_db()
    try:
        crop_id = int(request.form.get('crop_id', 1))
        quantity_kg = float(request.form.get('quantity_kg', 1.0))
        price_per_kg = float(request.form.get('price_per_kg', 1.0))
        location = request.form.get('location', '')
        contact_info = request.form.get('contact_info', '')
        description = request.form.get('description', '')
        
        if add_marketplace_listing(current_user.id, crop_id, quantity_kg, price_per_kg, location, contact_info, description):
            flash('Your harvest was listed on the marketplace successfully!', 'success')
        else:
            flash('An error occurred while listing your harvest.', 'danger')
    except (ValueError, TypeError):
        flash('Invalid inputs provided for the listing.', 'danger')
        
    return redirect(url_for('marketplace'))


@app.route('/marketplace/delete/<int:listing_id>', methods=['POST'])
@login_required
def marketplace_delete(listing_id):
    ensure_db()
    if delete_marketplace_listing(listing_id, current_user.id):
        flash('Listing removed successfully.', 'info')
    else:
        flash('Error removing listing. You might not have permission, or it was already removed.', 'danger')
    return redirect(url_for('marketplace'))


@app.route('/library')
def crop_library():
    """Crop Information Library view."""
    ensure_db()
    try:
        json_path = os.path.join(os.path.dirname(__file__), 'static', 'data', 'crop_info.json')
        with open(json_path, 'r') as f:
            crop_info = json.load(f)
    except Exception as e:
        print(f"Error loading crop library data: {e}")
        crop_info = []
        
    return render_template('library.html', crop_info=crop_info)

# ── API Routes ───────────────────────────────────────────────────────────────

@app.route('/api/price-history/<int:crop_id>')
def api_price_history(crop_id):
    """Return price history data as JSON for charts."""
    prices = get_price_history(crop_id)
    return jsonify({
        'crop': get_crop_by_id(crop_id),
        'prices': prices,
    })


@app.route('/api/analysis/<int:crop_id>')
def api_analysis(crop_id):
    """Return full analysis as JSON."""
    historical = analyze_price_history(crop_id)
    return jsonify(historical)


@app.route('/api/crops')
def api_crops():
    """Return list of crops."""
    return jsonify(get_crop_list())


@app.route('/import-data')
def import_data():
    """Page to fetch and import data from Zambia Open Data API."""
    ensure_db()
    return render_template('import_data.html')


@app.route('/api/import-data', methods=['POST'])
def api_import_data():
    """
    Receive data fetched by the browser from the Zambia Open Data API
    and import it into the local database.
    """
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({'success': False, 'error': 'No data received'})

        raw_data = payload.get('raw_data', {})
        records = payload.get('records', [])

        details = []
        details.append(f"Received payload with {len(records)} records")
        details.append(f"Raw data keys: {list(raw_data.keys()) if isinstance(raw_data, dict) else 'array'}")

        if not records and isinstance(raw_data, dict):
            # Try to extract records from various API response formats
            for key in ['data', 'DataPoints', 'value', 'results', 'rows']:
                if key in raw_data and isinstance(raw_data[key], list):
                    records = raw_data[key]
                    details.append(f"Extracted {len(records)} records from '{key}' field")
                    break

        if not records and isinstance(raw_data, list):
            records = raw_data
            details.append(f"Raw data is an array with {len(records)} items")

        if not records:
            return jsonify({
                'success': False,
                'error': 'Could not find data records in the API response',
                'details': details,
                'raw_structure': str(type(raw_data)),
                'raw_preview': json.dumps(raw_data)[:1000] if raw_data else 'empty'
            })

        # Store raw API data to a JSON file for reference
        raw_file = os.path.join(os.path.dirname(__file__), 'data', 'api_raw_data.json')
        with open(raw_file, 'w') as f:
            json.dump(raw_data, f, indent=2)
        details.append(f"Raw API data saved to data/api_raw_data.json")

        # Process and import records into the database
        conn = get_db()
        cursor = conn.cursor()

        # Create a table for raw API data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_raw_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                indicator_id TEXT,
                indicator_name TEXT,
                region_id TEXT,
                region_name TEXT,
                time_period TEXT,
                value REAL,
                unit TEXT,
                raw_json TEXT
            )
        ''')

        # Clear old API records
        cursor.execute('DELETE FROM api_raw_records')

        imported = 0
        skipped = 0

        for rec in records:
            try:
                # Adapt to different API response formats
                if isinstance(rec, dict):
                    indicator_id = str(rec.get('IndicatorId', rec.get('indicatorId', rec.get('indicator', ''))))
                    indicator_name = str(rec.get('IndicatorName', rec.get('indicatorName', rec.get('Indicator', ''))))
                    region_id = str(rec.get('RegionId', rec.get('regionId', rec.get('region', ''))))
                    region_name = str(rec.get('RegionName', rec.get('regionName', rec.get('Region', ''))))
                    time_period = str(rec.get('TimePeriod', rec.get('timePeriod', rec.get('Time', rec.get('year', '')))))
                    value_raw = rec.get('Value', rec.get('value', None))
                    unit = str(rec.get('Unit', rec.get('unit', rec.get('Scale', ''))))
                elif isinstance(rec, list):
                    indicator_id = str(rec[0]) if len(rec) > 0 else ''
                    indicator_name = str(rec[1]) if len(rec) > 1 else ''
                    region_id = ''
                    region_name = str(rec[2]) if len(rec) > 2 else ''
                    time_period = str(rec[3]) if len(rec) > 3 else ''
                    value_raw = rec[4] if len(rec) > 4 else None
                    unit = str(rec[5]) if len(rec) > 5 else ''
                else:
                    skipped += 1
                    continue

                # Parse value
                value = None
                if value_raw is not None:
                    try:
                        value = float(value_raw)
                    except (ValueError, TypeError):
                        value = None

                cursor.execute('''
                    INSERT INTO api_raw_records 
                    (indicator_id, indicator_name, region_id, region_name, time_period, value, unit, raw_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (indicator_id, indicator_name, region_id, region_name, 
                      time_period, value, unit, json.dumps(rec)))

                imported += 1

            except Exception as e:
                skipped += 1
                details.append(f"Skipped record: {str(e)[:100]}")

        conn.commit()
        conn.close()

        details.append(f"Successfully imported {imported} records, skipped {skipped}")

        return jsonify({
            'success': True,
            'message': f'Imported {imported} records from API ({skipped} skipped)',
            'details': details,
            'imported': imported,
            'skipped': skipped,
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        })


# ── Main ─────────────────────────────────────────────────────────────────────

# ── Authentication Routes ────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user_data = get_user_by_username(username)
        if user_data and check_password_hash(user_data['password_hash'], password):
            user = User(id=user_data['id'], username=user_data['username'], password_hash=user_data['password_hash'])
            login_user(user)
            flash('Logged in successfully.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))
            
        hashed_password = generate_password_hash(password)
        if create_user(username, hashed_password):
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Username already exists. Please pick a different one.', 'danger')
            
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


if __name__ == '__main__':
    ensure_db()
    from models.database import init_db
    init_db()  # Ensures new tables like marketplace_listings are created
    port = int(os.environ.get('PORT', '5050'))
    debug = os.environ.get('FLASK_DEBUG', '').lower() in {'1', 'true', 'yes', 'on'}
    app.run(host='0.0.0.0', port=port, debug=debug)
