<p align="center">
  <img src="frontend/public/favicon.svg" width="80" alt="AgriSense Logo" />
</p>

<h1 align="center">🌾 AgriSense — AI Salinity & Crop Stress Forecaster</h1>

<p align="center">
  <strong>Predict soil salinity, crop water stress, irrigation needs & crop health — and turn every forecast into actionable advice for farmers.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React_19-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/Tailwind_CSS_4-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white" alt="Tailwind CSS" />
  <img src="https://img.shields.io/badge/XGBoost-FF6600?style=for-the-badge&logo=xgboost&logoColor=white" alt="XGBoost" />
  <img src="https://img.shields.io/badge/Vite_8-646CFF?style=for-the-badge&logo=vite&logoColor=white" alt="Vite" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
</p>

<p align="center">
  <em>Built for the UNDP Climate Hackathon</em>
</p>

---

## 📋 Table of Contents

- [The Problem](#-the-problem)
- [What It Does](#-what-it-does)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
- [Project Structure](#-project-structure)
- [API Endpoints](#-api-endpoints)
- [Model Performance](#-model-performance)
- [Data Disclosure](#-honest-data-disclosure)
- [Demo Resilience](#-demo-resilience)
- [Accessibility & Design](#-accessibility--design)
- [Scaling Roadmap](#-scaling-roadmap)
- [Environment Variables](#-environment-variables)
- [References](#-references)
- [License](#-license)

---

## 🌍 The Problem

Soil salinisation degrades roughly **1.5 million hectares** of cropland every year. It is invisible until it is expensive — by the time salt stress shows in the crop, the yield is already gone.

Salinity emerges from the *interaction* of irrigation water quality, evaporative demand, rainfall leaching, drainage capacity and the depth of the water table. Salt does not evaporate — water leaves the root zone as vapour and the salt it carried stays behind. Every irrigation adds salt; only water percolating *below* the roots removes it.

> **That is a multi-variable problem a person cannot eyeball, and exactly the kind a model can forecast.**

---

## 🚀 What It Does

| Forecast | Horizon | Turned Into |
|---|---|---|
| 🧂 **Soil Salinity** (ECe, dS/m) | 30 days | Leaching depth in mm, against the crop's salt tolerance |
| 💧 **Crop Water Stress** | Current | Irrigation urgency, deferred when rain is coming |
| 🌊 **Irrigation Need** | Current | A number in mm, including the leaching overhead |
| 🌱 **Crop Health** | Current | Expected yield loss as a percentage |

### 🎮 What-If Simulator

Change the water source, the depth per irrigation, the interval, or the rainfall — and see the **30-day outcome** against carrying on unchanged.

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────────┐
│  React 19 + TS + Tailwind 4 + Vite  (TanStack Query) │
└───────────────────────┬──────────────────────────────┘
                        │ REST /api/*
┌───────────────────────▼──────────────────────────────┐
│                    FastAPI                            │
│  routers → services → repositories → SQLAlchemy       │
│     │           │                                     │
│     │      ┌────▼──────────┐   ┌──────────────────┐  │
│     │      │ 4 XGBoost     │   │ Weather provider │  │
│     │      │ regressors    │   │ ├ Open-Meteo ✓   │  │
│     │      │ + drivers     │   │ └ OpenWeatherMap │  │
│     │      └───────────────┘   └────────┬─────────┘  │
└─────┼───────────────────────────────────┼────────────┘
      ▼                                   ▼
   SQLite (WAL)                  cached in SQLite (TTL)
```

**Routers never touch the database or the models directly.** Routers validate and delegate; services own business logic; repositories own every SQLAlchemy call. That boundary is what makes the Postgres migration a swap rather than a rewrite.

---

## 🛠 Tech Stack

### Backend
| Technology | Purpose |
|---|---|
| **FastAPI** | High-performance async REST API |
| **SQLAlchemy 2.0** | ORM & database layer |
| **SQLite (WAL)** | Lightweight persistent storage |
| **XGBoost** | Gradient-boosted ML models (4 regressors) |
| **Pandas / NumPy** | Data processing & feature engineering |
| **scikit-learn** | Model evaluation & preprocessing |
| **HTTPX** | Async HTTP client for weather APIs |

### Frontend
| Technology | Purpose |
|---|---|
| **React 19** | UI framework |
| **TypeScript** | Type-safe JavaScript |
| **Tailwind CSS 4** | Utility-first styling |
| **Vite 8** | Lightning-fast build tool |
| **TanStack Query** | Server-state management & caching |
| **Recharts** | Data visualization & charts |
| **Framer Motion** | Smooth animations & transitions |
| **Lucide React** | Icon library |
| **React Router 7** | Client-side routing |

### DevOps
| Technology | Purpose |
|---|---|
| **Docker** | Containerised deployment |
| **Docker Compose** | Multi-service orchestration |

---

## ⚡ Getting Started

### Prerequisites

- **Python** 3.10+
- **Node.js** 20+
- **npm** (comes with Node.js)

### Quick Start (Windows)

```powershell
# Clone the repository
git clone https://github.com/nitin270906/Agrisense_app.git
cd Agrisense_app/agrisense-app

# One-click setup (installs dependencies, trains models, seeds data)
.\setup.bat

# Launch both backend + frontend
.\go.bat
```

### Manual Setup

#### 1️⃣ Backend

```bash
cd backend

# Create virtual environment (recommended)
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Generate training data, train models & write artifacts (~2 min)
python -m app.ml.train --regenerate

# Seed demo farms + 150 days of sensor history
python -m app.seed.seed --reset

# Start the API server
python -m uvicorn app.main:app --reload
```

#### 2️⃣ Frontend (separate terminal)

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

#### 3️⃣ Open the App

| Service | URL |
|---|---|
| 🖥 **Frontend** | [http://localhost:5173](http://localhost:5173) |
| 📡 **API Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) |

> **No API key is needed.** Open-Meteo is keyless and publishes FAO-56 Penman-Monteith ET₀ directly — the single most important driver in the water balance.

### 🐳 Docker

```bash
docker compose up
```

One process, one URL (`http://localhost:8000`), and **no CORS class of failure during a live demo**.

### Production Build

```bash
cd frontend && npm run build      # emits frontend/dist
cd ../backend && python -m uvicorn app.main:app --port 8000
```

FastAPI serves the built SPA itself — single origin, zero CORS issues.

---

## 📁 Project Structure

```
agrisense-app/
├── backend/
│   ├── app/
│   │   ├── ml/                    # Machine learning pipeline
│   │   │   ├── physics.py         # FAO-56 water balance, Maas-Hoffman, salt mass balance
│   │   │   ├── crop_profiles.py   # Published agronomic constants with citations
│   │   │   ├── features.py        # Shared feature builder (train + serve)
│   │   │   ├── train.py           # Grouped splits, baselines, metrics
│   │   │   ├── predictor.py       # Inference engine
│   │   │   ├── generate.py        # Physics-based data generator
│   │   │   ├── ingest_csv.py      # Drop-in for real field data
│   │   │   └── artifacts/         # Trained model files (.joblib)
│   │   ├── models/                # SQLAlchemy ORM models
│   │   ├── routers/               # API route handlers
│   │   │   ├── dashboard.py       # Dashboard aggregations
│   │   │   ├── farms.py           # Farm & field CRUD
│   │   │   ├── insights.py        # Predictions & recommendations
│   │   │   └── meta.py            # Model info & health checks
│   │   ├── schemas/               # Pydantic request/response schemas
│   │   ├── services/              # Business logic layer
│   │   │   ├── dashboard.py       # Dashboard computations
│   │   │   ├── prediction.py      # ML prediction service
│   │   │   ├── recommendation.py  # Rules engine for farmer advice
│   │   │   └── simulation.py      # What-if scenario engine
│   │   ├── repositories/          # Database access layer
│   │   ├── weather/               # Weather provider abstraction
│   │   │   ├── open_meteo.py      # Open-Meteo integration (default)
│   │   │   ├── openweather.py     # OpenWeatherMap adapter
│   │   │   └── service.py         # Provider selection & caching
│   │   ├── seed/                  # Demo data seeding
│   │   ├── config.py              # App configuration
│   │   ├── database.py            # DB connection setup
│   │   └── main.py                # FastAPI application entry point
│   ├── tests/                     # Unit tests
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/                 # Route-level page components
│   │   │   ├── DashboardPage      # Farm overview & risk map
│   │   │   ├── FieldDetailPage    # Individual field analysis
│   │   │   ├── FieldComparisonPage# Side-by-side field comparison
│   │   │   ├── SimulatorPage      # What-if scenario simulator
│   │   │   └── ModelPage          # Model transparency & metrics
│   │   ├── components/            # Reusable UI components
│   │   │   ├── charts/            # Gauge, Sparkline, Weather, Stress charts
│   │   │   ├── dashboard/         # KPI row, Risk map, Alerts, Field cards
│   │   │   ├── field/             # Prediction cards, Recommendations
│   │   │   ├── layout/            # App shell & navigation
│   │   │   └── ui/                # Design system primitives
│   │   ├── api/                   # API client & React Query hooks
│   │   ├── lib/                   # Utility functions
│   │   └── types/                 # TypeScript type definitions
│   ├── public/                    # Static assets
│   ├── package.json
│   └── vite.config.ts
├── docs/                          # Additional documentation
│   ├── ARCHITECTURE.md
│   └── DEMO_SCRIPT.md
├── docker-compose.yml
├── setup.bat                      # Windows one-click setup
├── go.bat                         # Windows one-click launch
├── start_demo.bat                 # Demo startup script
└── .env.example                   # Environment variable template
```

> **Why `features.py` is shared:** Train/serve skew — where training computes a rolling sum one way and the API computes it another — is the classic silent failure in a fast ML build. There is exactly one implementation and both paths call it.

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/dashboard` | Aggregated farm dashboard data |
| `GET` | `/api/farms` | List all farms |
| `GET` | `/api/farms/{id}` | Get farm details |
| `GET` | `/api/farms/{id}/fields` | List fields for a farm |
| `GET` | `/api/insights/predict/{field_id}` | Get ML predictions for a field |
| `GET` | `/api/insights/recommend/{field_id}` | Get actionable recommendations |
| `POST` | `/api/insights/simulate` | Run what-if scenario simulation |
| `GET` | `/api/model/info` | Model metadata & performance metrics |
| `GET` | `/api/health` | Health check |

📖 Full interactive docs available at `/docs` (Swagger UI) when the server is running.

---

## 📊 Model Performance

Every model is scored against a **naive baseline** — because a metric without one is marketing. Whole fields are held out, never rows.

| Target | R² | MAE | Baseline | vs Baseline |
|---|---|---|---|---|
| 🧂 30-day salinity change | 0.281 | 0.159 dS/m | assume no change (MAE 0.225) | **29% better** |
| 💧 Crop water stress | 0.846 | 0.022 | predict the mean (MAE 0.084) | **73% better** |
| 🌊 Irrigation need | 0.742 | 8.91 mm | predict the mean (MAE 25.4) | **65% better** |
| 🌱 Crop health | 0.854 | 3.62 | predict the mean (MAE 13.4) | **73% better** |

### Key Design Decisions

<details>
<summary><strong>Why salinity R² is "only" 0.28</strong></summary>

The salinity model originally scored R² 0.98 — and **lost to its baseline**. It was predicting the salinity *level*, and soil ECe moves so slowly that "next week equals today" scored 0.987 on its own. Over 7 days ECe drifts about 0.05 dS/m, which is below the sensor noise floor.

Reframing the target as the **30-day change** put the baseline at "no change" and made the score honest.
</details>

<details>
<summary><strong>Why water stress and irrigation were decoupled</strong></summary>

Both were exactly 87.5% zero, because `Ks = 1` and "no irrigation needed" were triggered by the identical condition. Moving the irrigation trigger to 65% of readily-available water both decoupled them and produced better agronomy — advice that waits until stress begins is advice that arrives too late.
</details>

---

## 📢 Honest Data Disclosure

> **⚠️ The models are trained on physics-simulated data, not field measurements.**

This is stated in the UI on every screen, on a dedicated `/model` page, and at `GET /api/model/info`. It is not buried here.

No public dataset pairs soil-salinity time series with weather at field scale. Three were evaluated and rejected:

| Candidate | Why It Doesn't Fit |
|---|---|
| USDA-ARS USSL ECe (1,889 samples) | Point measurements — no time series, no paired weather |
| Songnen Plain 40-year salinity | Remote-sensing raster (100 m, China), not field records |
| Kaggle smart-farming / crop-NPK | Auth-gated; EC present as a fertility proxy, no ECe target, no temporal dimension |

Training data is generated by an agronomic simulator built from published relationships:

- **FAO-56** (Allen et al., 1998) — reference ET, crop coefficients, TAW/RAW, the Ks water-stress coefficient
- **Maas & Hoffman (1977)** — salt tolerance, `Yr = 100 − b(ECe − a)`, per-crop threshold & slope from FAO-29
- **Root-zone salt mass balance** — leaching fraction, irrigation water EC, rainfall dilution, capillary rise
- **USDA salinity classes** — the 2 / 4 / 8 dS/m bands used throughout the UI

The models learn those relationships. They have **not been validated against measured field data**. `backend/app/ml/ingest_csv.py` is the drop-in path for real data when it becomes available — the feature schema does not change.

---

## 🛡 Demo Resilience

Three things that matter more at a hackathon than in production:

| Feature | How It Works |
|---|---|
| **Weather caching** | Fresh cache → live provider → stale cache → error. Stale responses are flagged in the UI rather than passed off as live. |
| **Graceful model fallback** | Missing model artifacts degrade to the physics simulator — the API boots and works even where training has never run. |
| **Rate limit handling** | Cache grid coarsened to ~11 km (one call per farm, not nine fields), per-location lock, bounded concurrency, and backoff. |

---

## ♿ Accessibility & Design

Colour comes from a validated data-visualisation palette, checked with a CVD simulator in both light and dark modes (worst adjacent pair ΔE 35.9 under deuteranopia).

- 🏷 **Risk states never rely on colour alone** — every one carries an icon and a text label
- 🎨 **Status colours are reserved for risk** and never reused as chart series
- 📊 **No dual-axis charts** — rainfall and ET₀ share an axis (both mm); water stress gets its own chart
- 📱 **Mobile-first** — the intended user is holding a phone at the edge of a field

---

## 🗺 Scaling Roadmap

| Current | Next | Why It's Cheap |
|---|---|---|
| SQLite | Postgres + TimescaleDB | Only the repository layer changes |
| Sync inference | Celery + Redis | The prediction service is already headless |
| Manual re-run | Nightly batch | Same service, called on a schedule |
| Sensor CSV/API | MQTT / LoRaWAN gateway | Ingestion already normalises |
| Point weather | + Sentinel-2 NDVI, SMAP | The feature builder is additive |
| Simulated training | Real field data | `ingest_csv.py`, schema unchanged |
| English | Hindi, Punjabi, Gujarati | Copy is centralised for this |
| — | SMS/WhatsApp alerts | Recommendations are already structured |

---

## ⚙️ Environment Variables

Copy `.env.example` → `.env` and adjust. The app runs with **no `.env` at all** — every value has a working default.

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `AI Salinity & Crop Stress Forecaster` | Application display name |
| `DATABASE_URL` | `sqlite:///./salinity.db` | Database connection string |
| `WEATHER_PROVIDER` | `open_meteo` | `open_meteo` (keyless) or `openweathermap` |
| `OPENWEATHERMAP_API_KEY` | *(empty)* | Required only if using OpenWeatherMap |
| `WEATHER_CACHE_TTL_HOURS` | `3` | Hours before cached weather is considered stale |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Allowed origins (only needed for separate frontend) |

---

## 📚 References

- Allen, R.G. et al. (1998). *Crop evapotranspiration*. FAO Irrigation & Drainage Paper 56.
- Ayers, R.S. & Westcot, D.W. (1985). *Water quality for agriculture*. FAO 29 Rev.1.
- Maas, E.V. & Hoffman, G.J. (1977). *Crop salt tolerance — current assessment*.
- Doorenbos, J. & Kassam, A.H. (1979). *Yield response to water*. FAO 33.
- Weather data: [Open-Meteo](https://open-meteo.com/) (CC-BY 4.0).

---

## 📄 License

This project was built for the **UNDP Climate Hackathon**. Please refer to the repository for license details.

---

<p align="center">
  Made with 💚 for sustainable agriculture
</p>
