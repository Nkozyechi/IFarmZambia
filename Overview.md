# IFarm Zambia - Project Overview Document

## 1. Executive Summary
**IFarm Zambia** is a comprehensive, data-driven Farm Market Analysis and Price Prediction System designed specifically to empower farmers in Zambia with actionable insights for their planting decisions. 

It is a modern web application built using Python (Flask) on the backend, a lightweight SQLite database, and HTML/CSS/JS on the frontend utilizing a sleek "glassmorphism" design system. The platform aggregates historical agricultural records (2011–2025) across 8 major Zambian crops to forecast prices, assess market demand, and provide intelligent planting recommendations.

---

## 2. Core Modules & Functionality

### 📊 Intelligent Market Analysis & Prediction 
At its core, the app helps farmers decide *what* to plant and *when* to harvest to maximize their profit.
- It analyzes 15 years of Zambian agricultural data across crops like Maize, Soybeans, Cassava, and Mixed Beans.
- When a farmer asks to analyze a crop, the system runs an ensemble of **4 specialized forecasting algorithms**:
  1. Simple Moving Averages (15% weight)
  2. Weighted Moving Averages (25% weight)
  3. Linear Regression (35% weight)
  4. Seasonal Trend Decomposition (25% weight)
- These methods predict the future price of that crop during their expected harvest month and calculate national demand versus production to estimate supply risks.

### 🧮 Profitability & ROI Calculator
Instead of just giving a price, the app creates a full **Decision Report**.
- Farmers can input their farm size (in hectares) and their expected costs for seeds, fertilizer, chemicals, and labor (in ZMW).
- The app calculates exactly how much Gross Revenue and Net Profit they stand to make, generating a precise ROI percentage based on the predicted prices.
- It ultimately gives a strict confidence rating: **Recommended**, **Caution**, or **Not Recommended** based on market volatility and profit margins.

### 🌍 Provincial Tracking & Live Weather
- Farmers can filter their analysis by any of Zambia's 10 provinces (e.g., Lusaka, Copperbelt, Southern). 
- The app dynamically hooks into the Open-Meteo API to pull down an accurate 7-day weather forecast (Rainfall, Max/Min Temps) specific to the selected province to assist with immediate planting logistics.

### 🛒 Peer-to-Peer Farmer Marketplace
- Users can securely register accounts and log in.
- The platform contains a live, authenticated bulletin board where farmers can post listings to sell their crops or advertise upcoming harvests directly to buyers. Listings display quantity in kg, price per kg, province location, and contact information.

### 📚 Crop Agronomy Library 
- A dedicated dashboard section serving as a digital encyclopedia for the supported crops, outlining scientific names, optimal soil types, exact maturity periods (in days), and recommended planting windows.

### 📱 Progressive Web App (PWA) & Localization
- **Offline & Installable**: The app is built as a PWA with a custom `manifest.json` and a Service Worker module. This means farmers can "Install" the website directly to their mobile home screens like a native app, and it caches core assets so it loads extremely fast even on 3G rural networks or when offline.
- **Zambian Dialects**: It features built-in UI localization. With a click of a button, the entire app immediately translates into **Bemba, Nyanja, Tonga, or Lozi**, making the tool highly accessible to local communities.
- **Data Export**: Every analysis report can be instantly downloaded as a clean, formatted **PDF** or exported to **CSV** for offline record-keeping.

---

## 3. Technology Stack

- **Backend Framework**: Python (Flask)
- **Database**: SQLite3 (`ifarm.db`) mapped via native Python functions (No ORM for maximum performance).
- **Data Science / Math**: `numpy` for Array generation and prediction logic handling.
- **Frontend Views**: Jinja2 HTML Templating.
- **Styling**: Vanilla CSS3 (Custom Glassmorphism framework with responsive breakpoints).
- **Interactivity**: Vanilla JavaScript & Chart.js for data visualization.
- **Authentication**: `Flask-Login` and `Werkzeug` secure password hashing.
- **PDF Generation**: `FPDF2` programmatic layout generator.

---

## 4. Local Setup & Execution

### Prerequisites
- Python 3.8+ installed on your machine.

### Installation
1. Navigate to the project directory:
   `cd IFarmZambia`
2. Install the required dependencies:
   `pip install -r requirements.txt`
3. The database is pre-seeded with 15 years of data. Run the application:
   `python app.py`
4. Open a web browser and navigate to:
   `http://127.0.0.1:5050`
