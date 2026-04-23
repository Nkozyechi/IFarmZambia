# IFarm Zambia: System Design & Architecture Document

## 1. Project Overview
**IFarm Zambia** is a comprehensive Farm Market Analysis and Price Prediction System designed to empower Zambian farmers with data-driven insights. It aggregates historical agricultural data (2011–2025) to forecast crop prices, assess market demand, and provide actionable planting recommendations.

Recent updates have expanded the platform into a fully fledged Progressive Web App (PWA) incorporating peer-to-peer marketplace capabilities, real-time weather forecasting, and a detailed crop agronomy library.

---

## 2. System Architecture
The application follows the **Model-View-Controller (MVC)** architectural pattern, implemented using the Flask web framework in Python:

- **Model (`models/database.py`)**: Handles all data interactions using a lightweight SQLite database (`ifarm.db`). It abstracts SQL queries into Python functions.
- **View (`templates/`, `static/`)**: Comprises Jinja2 HTML templates styled with a modern, glassmorphism CSS design system. Static assets include JavaScript for interactivity and a Service Worker for offline PWA capabilities.
- **Controller (`app.py`, `analysis/`)**: `app.py` serves as the central router, managing HTTP requests, form validations, and session authentication. The heavy lifting of data processing is offloaded to specialized Python modules in the `analysis/` directory.

---

## 3. Directory Structure

```text
IFarmZambia/
│
├── app.py                     # Main Flask application and URL router
├── ifarm.db                   # SQLite database (Users, Crops, Prices, Marketplace)
├── requirements.txt           # Python dependencies
├── Procfile / render.yaml     # Cloud Deployment configurations
│
├── analysis/                  # Core Business Logic & Algorithms
│   ├── decision.py            # Aggregates data to generate planting recommendations & ROI
│   ├── prediction.py          # Forecasting engines (SMA, WMA, Linear Reg, Seasonal)
│   ├── historical.py          # Time-series analysis, volatility, and seasonal indexes
│   ├── demand.py              # Supply-demand balance calculations
│   ├── weather.py             # Open-Meteo API integration for 7-day province forecasts
│   ├── pdf_generator.py       # PDF export engine (ReportLab)
│   └── csv_generator.py       # Flat data export engine
│
├── models/
│   ├── database.py            # Database schema definition and query functions
│   └── __init__.py            
│
├── static/                    # Frontend Assets
│   ├── css/style.css          # Glassmorphism design system & responsive layout
│   ├── data/crop_info.json    # Agronomic dictionary data for the Crop Library
│   ├── js/main.js             # UI interactions (Theme toggles, DOM manipulation)
│   ├── manifest.json          # PWA App Manifest (Installability)
│   └── service-worker.js      # PWA Service Worker (Offline caching)
│
└── templates/                 # Jinja2 HTML Views
    ├── base.html              # Core layout shell & sidebar navigation
    ├── index.html             # Dashboard summary
    ├── analyze.html           # Analysis configuration form (Year sliders, region, inputs)
    ├── report.html            # Final recommendation presentation
    ├── compare.html           # Multi-crop radar chart comparison
    ├── marketplace.html       # Peer-to-peer farmer listing board
    ├── library.html           # Agronomic info cards
    └── login/register.html    # Authentication views
```

---

## 4. Core Features & Capabilities

1. **Intelligent Crop Analysis (`decision.py`)**: 
   - Accepts user parameters: Crop, Planting Month, Harvest Period, Farm Size, Region, Custom Costs, and Target Year Ranges.
   - Calculates custom profitability (Net Profit, Gross Revenue, ROI percentage).
   - Generates a Confidence Score out of 100 with a strict "Recommended", "Caution", or "Not Recommended" verdict.
2. **Multi-Model Price Prediction (`prediction.py`)**:
   - Computes future prices using an ensemble of 4 methods: Simple Moving Average (15% weight), Weighted Moving Average (25%), Linear Regression (35%), and Seasonal Trend Decomposition (25%).
3. **Farmer Marketplace**:
   - An authenticated bulletin board where users can view, add, and delete peer-to-peer crop listings with contact info and expected harvest volumes.
4. **Progressive Web App (PWA)**:
   - Configured with `manifest.json` and a Service Worker, allowing mobile users to "Install" the app to their home screens and cache core CSS/JS for faster loading in low-connectivity areas.
5. **Dynamic Weather Integration (`weather.py`)**:
   - Maps the selected Zambian Province to latitude/longitude coordinates and fetches real-time 7-day weather forecasts via the Open-Meteo API.
6. **Crop Information Library**:
   - Dedicated dashboard showcasing physical agronomic requirements (Maturity days, spacing, soil preference, scientific names).

---

## 5. Database Schema (SQLite)

The system utilizes seven core tables:

1. **`crops`**: Core entities (`id`, `name`, `category`, `growth_period_months`).
2. **`price_records`**: Time-series monthly prices per kg (`year`, `month`, `crop_id`, `price_per_kg`).
3. **`production_records`**: Annual national yields and hectares harvested (`year`, `crop_id`, `area_harvested_ha`, `production_mt`).
4. **`production_costs`**: Baseline ZMW costs per hectare (`seed_cost`, `fertilizer_cost`, `labor_cost`, etc.).
5. **`demand_records`**: Historical market demand index and volume metric (`year`, `month`, `demand_index`).
6. **`users`**: Authentication table for farmers (`id`, `username`, `password_hash`).
7. **`marketplace_listings`**: Active trade listings. Relates to `users` and `crops`. Stores `quantity_kg`, `price_per_kg`, and `location`.

---

## 6. Logic Flow: 'Analyze Crop' Pipeline

1. **Input Phase**: User configures the analysis in `analyze.html` (e.g., Target Crop, Custom Dates 2020-2025, Custom Input Costs). Data is POSTed to `@app.route('/analyze')`.
2. **Data Filtration**: The backend passes the `start_year` and `end_year` to `models/database.py`, restricting the historical dataset.
3. **Algorithmic Processing**:
   - `historical.py` calculates Seasonality Indexes and Volatility (CV) strictly on the filtered dates.
   - `prediction.py` fits Linear Regression and Moving Averages to predict harvest month prices.
   - `demand.py` establishes the current supply-demand balance.
4. **Aggregation**: `decision.py` evaluates all outputs, checks for risks (e.g., High Volatility > 30% or High Supply Risk), and calculates projected Net Profit.
5. **Output**: The combined `report` dictionary is rendered back to `analyze.html` containing charts (via Chart.js) and the final recommendation. User can export the exact state to `pdf_generator.py`.
