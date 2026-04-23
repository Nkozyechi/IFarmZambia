# IFarm Zambia - Farm Market Analysis System

## What Was Built

A complete Flask web application for Zambian farmers to analyze crop market prices, predict future prices, estimate demand, and receive planting recommendations.

**Data Source**: [Zambia Open Data for Africa - Agriculture Statistics 2011-2025](https://zambia.opendataforafrica.org/etqmqgf/agriculture-statistics-2011-2025)

## Project Structure

```
IFarmZambia/
├── app.py                    # Flask entry point (port 5050)
├── requirements.txt          # flask, numpy
├── ifarm.db                  # SQLite database (auto-generated)
├── data/seed_data.py         # Seeds DB with 15 years of data
├── models/database.py        # Database layer
├── analysis/
│   ├── historical.py         # Price trend analysis
│   ├── prediction.py         # 4-method price prediction
│   ├── demand.py             # Demand estimation
│   └── decision.py           # Recommendation engine
├── templates/
│   ├── base.html             # Sidebar layout
│   ├── index.html            # Dashboard
│   ├── analyze.html          # Analysis + charts
│   ├── marketplace.html      # NEW: Trade/Buy/Sell listings
│   └── report.html           # Full decision report
└── static/
    ├── css/style.css          # Dark glassmorphism theme
    ├── js/main.js             # UI interactions
    ├── manifest.json          # NEW: PWA manifest
    └── service-worker.js      # NEW: Offline caching worker
```

## Key Features

| Feature | Description |
|---------|-------------|
| **Dashboard** | Overview of 8 crops with latest prices and trends |
| **Progressive Web App (PWA)** | Installable base app that fetches cached assets for faster/offline loads |
| **Crop Information Library** | Detailed agronomic data (planting times, maturity, spacing) for supported crops |
| **Weather Forecast** | Dynamic 7-day province-specific weather forecast via Open-Meteo API |
| **Farmer Marketplace** | Peer-to-peer buy/sell listing board for users to advertise upcoming harvests |
| **Historical Analysis** | 15 years of price data, seasonal patterns, volatility |
| **Historical Year Targeting** | Select specific custom date ranges (e.g. 2020 - 2025) to isolate recent price volatility for the prediction engines. |
| **Price Prediction** | 4 methods: SMA, WMA, Linear Regression, Seasonal Decomposition |
| **Demand Estimation** | Demand forecasting with supply-demand balance |
| **Decision Report** | Recommendation (Recommended/Caution/Not Recommended) with risk assessment |
| **Profitability Calculator** | ROI, Gross Revenue, and Net Profit estimation based on farm size and input costs |
| **Export/Reporting** | PDF generation of decision reports and CSV export of historical data |
| **Multi-Language Support** | Instant UI translations for Zambian dialects: English, Bemba, Nyanja, Tonga, and Lozi |
| **Profit Calculator** | Input custom costs to project margin models on top of predicted crop yield |
| **Compare Crops** | Compare up to 3 crops head-to-head utilizing a multi-dimensional radar chart |
| **Region Filters** | Drill-down data filters selecting 1 of Zambia's 10 major provinces |
| **User Authentication** | SQLite-backed login/registration system for farmer user models |
| **Deep Exports** | Download flat CSV sheets or formatted, print-ready PDFs of data analyses |
| **Dashboard Sparklines** | At-a-glance historical tracking lines integrated directly into the dashboard |

## Data Coverage

- **8 Crops**: Tomatoes, Maize, Onions, Cabbage, Irish Potatoes, Groundnuts, Soybeans, Wheat
- **15 Years**: 2011–2025
- **~1,368** monthly price records with seasonal patterns
- **~1,368** demand records
- **120** annual production records
- All prices in **Zambian Kwacha (ZMW)**

## How to Run

```bash
cd IFarmZambia
pip install flask numpy
python app.py
# Open http://127.0.0.1:5050
```

## Verification Results

- ✅ Database seeded: 8 crops, 120 production, ~1368 price, ~1368 demand records
- ✅ Flask server starts on port 5050
- ✅ Dashboard loads with all 8 crops, prices, and trends
- ✅ API endpoints return valid JSON data
- ✅ Analysis form works with crop/month selection
- ✅ Decision reports generate with recommendations
