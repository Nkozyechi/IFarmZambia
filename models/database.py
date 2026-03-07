"""
Database module for IFarm Zambia - Farm Market Analysis System.
Uses SQLite to store historical agriculture data sourced from
Zambia Open Data for Africa (Agriculture Statistics 2011-2025).
"""

import sqlite3
import os


def get_db_path():
    """Return the configured SQLite path for local and hosted deployments."""
    return os.environ.get(
        'IFARM_DB_PATH',
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ifarm.db'),
    )


def ensure_db_directory():
    """Create the parent directory for the database file when needed."""
    db_directory = os.path.dirname(get_db_path())
    if db_directory:
        os.makedirs(db_directory, exist_ok=True)


def get_db():
    """Get a database connection."""
    ensure_db_directory()
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database schema."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS crops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL,
            growth_period_months INTEGER NOT NULL,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS price_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crop_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            price_per_kg REAL NOT NULL,
            price_per_50kg_bag REAL,
            province TEXT DEFAULT 'National',
            source TEXT DEFAULT 'Zambia Open Data for Africa',
            FOREIGN KEY (crop_id) REFERENCES crops(id)
        );

        CREATE TABLE IF NOT EXISTS production_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crop_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            area_planted_ha REAL,
            area_harvested_ha REAL,
            production_mt REAL,
            yield_mt_per_ha REAL,
            province TEXT DEFAULT 'National',
            source TEXT DEFAULT 'Zambia Open Data for Africa',
            FOREIGN KEY (crop_id) REFERENCES crops(id)
        );

        CREATE TABLE IF NOT EXISTS production_costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crop_id INTEGER NOT NULL UNIQUE,
            seed_cost_per_ha REAL NOT NULL,
            fertilizer_cost_per_ha REAL NOT NULL,
            chemical_cost_per_ha REAL NOT NULL,
            labor_cost_per_ha REAL NOT NULL,
            other_costs_per_ha REAL NOT NULL,
            FOREIGN KEY (crop_id) REFERENCES crops(id)
        );

        CREATE TABLE IF NOT EXISTS demand_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crop_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            demand_index REAL NOT NULL,
            market_volume_mt REAL,
            province TEXT DEFAULT 'National',
            FOREIGN KEY (crop_id) REFERENCES crops(id)
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    conn.commit()
    conn.close()


def get_crop_list():
    """Return all crops."""
    conn = get_db()
    crops = conn.execute('SELECT * FROM crops ORDER BY name').fetchall()
    conn.close()
    return [dict(c) for c in crops]


def get_crop_by_id(crop_id):
    """Return a single crop by ID."""
    conn = get_db()
    crop = conn.execute('SELECT * FROM crops WHERE id = ?', (crop_id,)).fetchone()
    conn.close()
    return dict(crop) if crop else None


def get_crop_by_name(name):
    """Return a single crop by name."""
    conn = get_db()
    crop = conn.execute('SELECT * FROM crops WHERE LOWER(name) = LOWER(?)', (name,)).fetchone()
    conn.close()
    return dict(crop) if crop else None


def get_price_history(crop_id, start_year=None, end_year=None, province='National'):
    """Return price history for a crop."""
    conn = get_db()
    query = 'SELECT * FROM price_records WHERE crop_id = ? AND province = ?'
    params = [crop_id, province]
    if start_year:
        query += ' AND year >= ?'
        params.append(start_year)
    if end_year:
        query += ' AND year <= ?'
        params.append(end_year)
    query += ' ORDER BY year, month'
    records = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in records]


def get_production_history(crop_id, start_year=None, end_year=None, province='National'):
    """Return production history for a crop."""
    conn = get_db()
    query = 'SELECT * FROM production_records WHERE crop_id = ? AND province = ?'
    params = [crop_id, province]
    if start_year:
        query += ' AND year >= ?'
        params.append(start_year)
    if end_year:
        query += ' AND year <= ?'
        params.append(end_year)
    query += ' ORDER BY year'
    records = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in records]


def get_demand_history(crop_id, start_year=None, end_year=None, province='National'):
    """Return demand records for a crop."""
    conn = get_db()
    query = 'SELECT * FROM demand_records WHERE crop_id = ? AND province = ?'
    params = [crop_id, province]
    if start_year:
        query += ' AND year >= ?'
        params.append(start_year)
    if end_year:
        query += ' AND year <= ?'
        params.append(end_year)
    query += ' ORDER BY year, month'
    records = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in records]


def get_production_costs(crop_id):
    """Return average production costs per hectare for a crop."""
    conn = get_db()
    costs = conn.execute('SELECT * FROM production_costs WHERE crop_id = ?', (crop_id,)).fetchone()
    conn.close()
    return dict(costs) if costs else None


def get_user_by_username(username):
    """Retrieve a user by their username."""
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return dict(user) if user else None


def get_user_by_id(user_id):
    """Retrieve a user by ID."""
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None


def create_user(username, password_hash):
    """Create a new user in the database."""
    conn = get_db()
    try:
        conn.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, password_hash))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()
