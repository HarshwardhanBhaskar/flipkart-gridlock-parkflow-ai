# 🚦 ParkFlow AI — Parking Congestion Intelligence System

> **Flipkart Gridlock Hackathon 2.0 — Round 2 Prototype Submission**

ParkFlow AI is an end-to-end intelligent traffic management system that combines **machine learning demand prediction** with a **real-time interactive dashboard** to help municipal authorities identify, prioritize, and resolve illegal parking hotspots that cause urban congestion.

---

## 🎯 Problem Statement

Illegal parking in dense urban corridors reduces effective road capacity, creating bottleneck congestion that cascades across entire road networks. Current enforcement is reactive and resource-inefficient — officers patrol randomly instead of being dispatched to the highest-impact locations.

## 💡 Our Solution

### 1. ML Prediction Engine (Phase 1)
A high-performance **ensemble model** combining LightGBM, XGBoost, and CatBoost to predict traffic demand at any location and time:

- **Spatial Feature Engineering** — Geohash decoding to lat/long + K-Means clustering (K=15)
- **Cyclic Temporal Encoding** — Trigonometric hour/day encoding for continuous time patterns
- **Out-of-Fold Target Encoding** — Leakage-free historical baseline demand per location
- **5-Fold Cross-Validation** — Robust ensemble with optimized blending weights

### 2. Interactive Dashboard (Phase 2 Prototype)
A Flask-powered **real-time congestion intelligence dashboard** featuring:

- 🗺️ **Interactive Leaflet Map** — Color-coded enforcement hotspots across Bengaluru with in-place maximize/minimize
- 📊 **Dual Analytics Charts** — City-wide diurnal trends + per-location hourly violation/demand curves
- 🎛️ **What-If Simulation Engine** — Slide to simulate clearing illegally parked vehicles and see real-time economic savings (₹)
- 📋 **Priority Dispatch Panel** — Auto-ranked enforcement zones by Targeted Enforcement Priority (TEP) index
- 💰 **Economic Impact Calculator** — Hourly congestion cost estimation in Indian Rupees (₹)

---

## 🖥️ Screenshots

| Dashboard Overview | Location Inspector |
|---|---|
| Interactive map with violation hotspots | Sliding panel with simulation engine |

---

## 🏗️ Project Structure

```
ml project/
├── data/
│   ├── dataset/              # Train/test CSV files
│   └── parking/              # Parking stats & traffic demand lookup
├── training/
│   └── train_pipeline.py     # Full ML training pipeline (LGB + XGB + CatBoost)
├── prototype/
│   ├── server.py             # Flask backend with REST APIs
│   ├── templates/
│   │   └── index.html        # Dashboard HTML template
│   └── static/
│       ├── app.js            # Frontend JavaScript (map, charts, events)
│       └── style.css         # Custom CSS styling
├── results/
│   └── submission.csv        # Final predictions (41,778 rows)
├── Approach.md               # Detailed methodology document
├── Traffic_Demand_Prediction_Submission.ipynb  # Jupyter Notebook
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

---

## 🚀 How to Run

### Prerequisites
- Python 3.10+
- pip

### 1. Clone the repository
```bash
git clone https://github.com/HarshwardhanBhaskar/flipkart-gridlock-parkflow-ai.git
cd flipkart-gridlock-parkflow-ai
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Dashboard
```bash
cd prototype
python server.py
```

Open your browser and navigate to **http://127.0.0.1:5000/**

### 4. Run the ML Training Pipeline (optional)
```bash
cd training
python train_pipeline.py
```

---

## 🧠 Technical Architecture

```
┌──────────────────────────────────────────────────────┐
│                    ParkFlow AI                        │
├──────────────────┬───────────────────────────────────┤
│  ML Engine       │  Dashboard Prototype              │
│  ─────────       │  ──────────────────               │
│  • LightGBM      │  • Flask REST API                 │
│  • XGBoost       │  • Leaflet.js Interactive Map     │
│  • CatBoost      │  • Chart.js Dual-Axis Analytics   │
│  • 5-Fold CV     │  • What-If Simulation Engine      │
│  • OOF Encoding  │  • Priority Dispatch Rankings     │
├──────────────────┴───────────────────────────────────┤
│  Data Layer                                          │
│  • Geohash Spatial Clustering                        │
│  • Rank-based Spatiotemporal Mapping                 │
│  • Bottleneck Engine (CDI, TEP, Economic Loss)       │
└──────────────────────────────────────────────────────┘
```

---

## 📊 Key Metrics

| Metric | Description |
|--------|-------------|
| **CDI** (Congestion Drag Index) | Demand ÷ Remaining Capacity — measures bottleneck severity |
| **TEP** (Targeted Enforcement Priority) | Violations × CDI — ranks locations for dispatch |
| **Economic Loss (₹)** | Estimated hourly cost of congestion to commuters |

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| ML Models | LightGBM, XGBoost, CatBoost |
| Backend | Flask (Python) |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Mapping | Leaflet.js + CARTO tiles |
| Charts | Chart.js |
| Data | Pandas, NumPy, Scikit-learn |

---

## 👨‍💻 Team

**Harshwardhan's Team** — Flipkart Gridlock Hackathon 2.0

---

## 📄 License

This project was developed as part of the Flipkart Gridlock Hackathon 2.0.
