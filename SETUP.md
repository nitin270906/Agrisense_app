# SaltWatch — Hackathon Transfer & Setup Guide

**Goal:** Take this project folder, put it on any clean Windows laptop, run two scripts,
and have the full application live at `http://localhost:8000` in under 10 minutes.

---

## 1. Architecture in One Paragraph

The app is two processes that share one origin during the demo:

| Layer | Technology | Port |
|---|---|---|
| Backend API + ML | Python / FastAPI / XGBoost | 8000 |
| Frontend (served by backend) | Pre-built React / Vite bundle | 8000 (same) |
| Database | SQLite (single file, no server) | — |
| Weather | Open-Meteo API (free, no key) | — |

**During the demo, you only open one terminal and one browser tab.**
FastAPI serves the built React bundle from `frontend/dist/` so there is
no second process, no CORS issue, and no second URL to remember.

---

## 2. What to Copy / What to Exclude

### Must include — the app will not work without these

```
gaurav_work/
├── backend/
│   ├── app/                        ← all Python source code
│   ├── requirements.txt            ← Python dependency list
│   ├── Dockerfile                  ← optional (not needed for demo)
│   ├── salinity.db                 ← ★ CRITICAL: 150 days of seeded demo data
│   ├── salinity.db-wal             ← copy along with salinity.db
│   └── salinity.db-shm             ← copy along with salinity.db
├── frontend/
│   ├── src/                        ← React source (needed if rebuilding)
│   ├── dist/                       ← ★ CRITICAL: pre-built UI — backend serves this
│   ├── package.json
│   ├── package-lock.json           ← ensures exact package versions on reinstall
│   ├── vite.config.ts
│   ├── tsconfig*.json
│   └── index.html
├── .env.example                    ← template; no secrets; see Section 5
├── setup.bat                       ← ★ first-time setup script
├── start_demo.bat                  ← ★ one-click demo launcher
└── SETUP.md                        ← this file
```

### Exclude — do not copy, not needed, or must be regenerated

```
backend/.venv/                      ← Python env — recreated by setup.bat
backend/__pycache__/                ← Python bytecode — auto-generated
backend/app/**/__pycache__/         ← same
backend/.pytest_cache/              ← test cache — irrelevant for demo
backend/app/ml/data/training.parquet← 50k-row training dataset — not needed at runtime
frontend/node_modules/              ← npm packages — reinstalled by setup.bat
.claude/                            ← Claude Code IDE config — irrelevant
```

### The ML model files are intentionally included

```
backend/app/ml/artifacts/
├── target_salinity_delta_30d.joblib   ← salinity prediction model
├── target_water_stress.joblib         ← water stress model
├── target_irrigation_mm.joblib        ← irrigation model
├── target_health.joblib               ← crop health model
├── target_*_q10.joblib                ← p10 quantile models (×4)
├── target_*_q90.joblib                ← p90 quantile models (×4)
└── metrics.json                       ← R², MAE, feature importances
```

These are committed to the repo intentionally — they are the trained ML artifacts and
must be present. Without them the backend falls back to physics-only mode (still works,
but model confidence and prediction intervals won't appear).

---

## 3. Software Prerequisites (Install on New Laptop)

### A. Python 3.11 or newer

1. Go to **https://www.python.org/downloads/**
2. Download the latest Python 3.11.x or 3.12.x Windows installer
3. Run the installer — **tick "Add Python to PATH"** before clicking Install
4. Verify: open Command Prompt → `python --version` → should show `Python 3.11.x`

> **Why not Python 3.10?** The code uses modern type annotations. 3.11+ is required.
> Python 3.13 also works fine.

### B. Node.js 20 LTS

> **Only needed if `frontend/dist/` was not copied (Section 2).**
> If `dist/index.html` exists in the project folder, skip Node entirely for the demo.

1. Go to **https://nodejs.org/en/download**
2. Download the **LTS** (Long Term Support) Windows installer (not "Current")
3. Run the installer with default settings
4. Verify: open Command Prompt → `node --version` → should show `v20.x.x`

### C. Nothing else

No Docker. No Redis. No PostgreSQL. No global npm packages. No VS Code extensions.
Everything else is installed into the project's own virtual environment by `setup.bat`.

---

## 4. How to Transfer the Project

### Option A — USB drive / folder copy (recommended for zero-internet scenarios)

1. On the **source laptop**, zip the project **excluding** the paths listed in Section 2:

   ```
   Right-click gaurav_work → Send to → Compressed (zipped) folder
   ```
   
   Then manually delete from the zip (or use 7-Zip with exclusion):
   - `backend/.venv/`
   - `backend/app/ml/data/`
   - `frontend/node_modules/`
   - All `__pycache__/` folders
   - `.claude/`

   **Include** `salinity.db`, `salinity.db-wal`, `salinity.db-shm` and `frontend/dist/`.

2. Copy the zip to the new laptop via USB.

3. Extract to a path with **no spaces and no special characters**, e.g.:
   ```
   C:\Projects\gaurav_work\
   ```
   Avoid paths like `C:\Users\My Name\Desktop\hackathon folder\` — spaces in paths
   cause subtle failures in some Python virtualenv commands on Windows.

### Option B — Git (if the repo is pushed to GitHub/GitLab)

```
git clone https://github.com/your-org/gaurav_work.git
```

**After cloning you MUST manually add:**
- `backend/salinity.db` (copy from the source machine — git ignores `.db` files)
- `frontend/dist/` (copy from the source machine — git ignores `dist/`)

Without these two additions the app starts but shows no data and serves no UI.

---

## 5. Environment Variables (.env)

**Short answer: you don't need a `.env` file.** Every setting has a production-safe
default. The app runs identically with or without one.

The defaults at startup are:
- Database: `backend/salinity.db` (relative, always correct)
- Weather: Open-Meteo (free, no key, works offline from cache)
- Weather cache TTL: 3 hours
- CORS: covers `localhost:8000` and `localhost:5173`

If you want to customise, copy `.env.example` to `.env` (in the project root, next to
`setup.bat`) and edit it. **Do not commit `.env` to git** — the `.gitignore` already
excludes it.

### Demo-day tip: extend the weather cache TTL

If the venue has unreliable internet, add this to `.env`:

```
WEATHER_CACHE_TTL_HOURS=72
```

This tells the app to reuse cached weather data for up to 3 days before trying to
refresh. The app already fails gracefully (shows a "stale weather" notice instead of
erroring), but extending the TTL avoids even that notice if the cache is warm.

**How to warm the cache before the demo:** Run the app on the source machine the night
before, open every field's detail page, and copy `salinity.db` fresh. The DB now contains
weather data for all 9 field locations.

---

## 6. Step-by-Step Setup on the New Laptop

Open **Command Prompt** (not PowerShell — `.bat` files run in cmd). Navigate to the
project folder, then run:

### Step 1 — First-time setup (run once)

```cmd
setup.bat
```

This script does the following automatically:
1. Checks Python and Node are installed
2. Creates `backend/.venv/` (Python virtual environment)
3. Installs all Python packages from `requirements.txt`
4. Checks for `salinity.db` — seeds fresh data if missing
5. Checks for `frontend/dist/` — builds the UI if missing

Watch for `[ERROR]` lines. If any appear, the error message tells you exactly what to do.

### Step 2 — Start the demo

```cmd
start_demo.bat
```

This:
1. Activates the Python virtual environment
2. Starts the FastAPI server on port 8000
3. Opens `http://localhost:8000` in your default browser after a 2-second delay

### Step 3 — Verify it works

Open `http://localhost:8000` in Chrome. You should see:
- The SaltWatch dashboard with warm cream background and gold accents
- 9 fields across 3 farms (Punjab, Haryana, Gujarat)
- KPI tiles showing salinity, health, and irrigation data
- No red error banners

---

## 7. What Each URL Does

| URL | What you see |
|---|---|
| `http://localhost:8000` | Main dashboard (demo entry point) |
| `http://localhost:8000/fields/1` | Field detail: salinity trend, recommendations |
| `http://localhost:8000/fields/1/simulate` | What-if simulator (irrigation scenarios) |
| `http://localhost:8000/model` | ML model metrics and feature importances |
| `http://localhost:8000/docs` | Interactive API explorer (FastAPI auto-docs) |
| `http://localhost:8000/api/health` | JSON health check — `{"status":"ok","model_loaded":true}` |

---

## 8. Verification Checklist (Run Before the Demo)

Go through this list with the app running. Every item must pass.

### Backend health

```
http://localhost:8000/api/health
```

Expected response:
```json
{"status": "ok", "model_loaded": true, "model_version": "1.0.0"}
```

- `"status": "ok"` — server is up
- `"model_loaded": true` — ML models loaded from `.joblib` files
- If `"model_loaded": false` — models will fall back to physics (still works, note the difference)

### Dashboard loads

- [ ] Dashboard opens at `http://localhost:8000`
- [ ] Shows "9 fields" and "39 ha monitored" in subtitle
- [ ] 4 KPI tiles render with numbers (not blank)
- [ ] Field grid shows at least 6 field cards
- [ ] Risk badges appear (Critical, High, Moderate, Low)
- [ ] Left sidebar shows "SaltWatch" with gold icon (desktop width)

### Field detail works

Click on "Coastal Block 1" (should be the top field — Critical risk):
- [ ] 4 prediction tiles load (Salinity, Water Stress, Irrigation, Health)
- [ ] Salinity trend chart shows historical data + forecast
- [ ] Recommendations list shows at least 2 items
- [ ] "Simulate" button is clickable and opens the simulator page

### ML predictions work

- [ ] Salinity tile shows an EC value in dS/m (e.g., "12.2 dS/m")
- [ ] Prediction interval appears if models loaded (e.g., "11.8–12.6 dS/m 80% interval")
- [ ] Crop health shows a number out of 100
- [ ] "Re-run" button triggers a fresh prediction (watch the tile values update)

### Simulator works

- [ ] Sliders respond when dragged
- [ ] "Run simulation" returns a result
- [ ] Outcome deltas are shown (+/– values)

### Model page works

- [ ] R² values are visible for all 4 targets
- [ ] Feature importance bars are rendered
- [ ] "Simulated data" disclaimer is visible

### Weather

- [ ] Field detail page shows a weather chart
- [ ] If "stale weather" banner appears — that is fine and expected (internet issue),
      the forecast still works from cache

### Offline check (simulate venue wifi failure)

- Disable wifi / unplug ethernet
- Reload `http://localhost:8000`
- [ ] Dashboard still loads (database is local)
- [ ] Field detail still loads
- [ ] A "stale weather" notice may appear — acceptable
- [ ] All ML predictions still run
- Re-enable internet before the demo

---

## 9. Troubleshooting

### "python is not recognized"

Python is not in PATH. During install, the "Add Python to PATH" checkbox was not ticked.

**Fix A (reinstall):** Uninstall Python, reinstall with "Add to PATH" ticked.

**Fix B (no reinstall):** Find where Python is installed (usually
`C:\Users\<you>\AppData\Local\Programs\Python\Python311\`) and add it to your system
PATH manually via System Properties → Advanced → Environment Variables.

---

### "node is not recognized"

Node.js is not installed or not in PATH. See Section 3B.

---

### setup.bat fails at "pip install -r requirements.txt"

**Cause A: No internet.** `pip` needs to download packages.
Fix: Connect to internet and re-run `setup.bat`.

**Cause B: xgboost wheel fails.**
XGBoost occasionally has build issues on older Windows machines.

Fix:
```cmd
pip install xgboost --pre --extra-index-url https://pypi.org/simple/
```
or pin to a specific version:
```cmd
pip install xgboost==2.1.1
```

**Cause C: Microsoft C++ build tools missing.**
Some packages (e.g., numpy) require Visual C++ redistributables.

Fix: Download **Microsoft Visual C++ Redistributable** (latest, x64) from Microsoft's site.

---

### "Error: salinity.db not found" at startup

The database file was not included in the transfer. Run:

```cmd
cd backend
.venv\Scripts\activate
python -m app.seed.seed
```

This takes ~30 seconds and creates a fresh database with 9 fields, 3 farms, and 150 days
of sensor history.

---

### Browser opens but shows a blank page or "Cannot GET /"

The `frontend/dist/` folder is missing. The backend has nothing to serve.

**Fix:** Build the frontend (Node.js must be installed):
```cmd
cd frontend
npm ci
npm run build
```

Then restart the backend. The `dist/` folder will be detected automatically.

---

### Dashboard shows 0 fields or "No farms found"

Database exists but is empty (either empty seed or wrong file copied).

**Fix:** Reseed from scratch:
```cmd
cd backend
.venv\Scripts\activate
python -m app.seed.seed --reset
```

---

### Port 8000 is already in use

Something else is occupying port 8000 (another Python process, another server).

**Fix A:** Kill the existing process:
```cmd
netstat -ano | findstr :8000
taskkill /PID <the-pid-from-above> /F
```

**Fix B:** Use a different port:
```cmd
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```
Then open `http://localhost:8080` (not 8000).

---

### Weather shows "stale" or charts are empty

Not a bug — this is the designed offline fallback. The app fetched weather when you last
ran it and is now serving from cache.

If you want fresh weather: connect to internet and click "Re-run forecast" on the dashboard.

---

### "model_loaded: false" in health check

The `.joblib` model files are missing from `backend/app/ml/artifacts/`.

**Verify they exist:**
```cmd
dir backend\app\ml\artifacts\*.joblib
```

Should list 12 files (4 point models + 8 quantile models).

**If missing:** They need to be re-trained (takes ~3 minutes):
```cmd
cd backend
.venv\Scripts\activate
python -m app.ml.train
```

The app works in physics-fallback mode until then — all API endpoints respond, predictions
run, but the `model_loaded` flag is false and confidence scores are approximate.

---

### Inter font not loading (text looks different)

The Inter font is loaded from Google Fonts CDN. With no internet it falls back to
`system-ui` (Segoe UI on Windows). This is cosmetic only — every feature still works.
The app is designed to fall back gracefully.

---

### Python version error (`match` statement / union types)

The code uses Python 3.10+ syntax. Check your version:
```cmd
python --version
```

If it shows Python 3.8 or 3.9, upgrade. Download Python 3.11+ from python.org.

---

## 10. Demo Tips

1. **Use Chrome or Edge, not Firefox.** The backdrop-blur CSS used in the navbar
   sometimes renders with artefacts in Firefox on some GPU drivers.

2. **Start the server 5 minutes before the demo.** The first request after startup
   triggers weather fetching, model loading, and prediction generation. Give it time.

3. **Open these tabs in advance** (before judges arrive):
   - `http://localhost:8000` — dashboard
   - `http://localhost:8000/fields/1` — Coastal Block 1 (Critical risk, most dramatic)
   - `http://localhost:8000/fields/4` — Village Plot 7 (fast salinity rise)
   - `http://localhost:8000/model` — model metrics page

4. **The "Re-run forecast" button** refreshes all 9 predictions live. Good to show during
   the demo — judges can watch risk badges update.

5. **The Simulator** (`/fields/1/simulate`) is the strongest demo moment. Show a farmer
   scenario: "what happens if I apply 80mm leaching irrigation today?" — the model
   responds in under a second.

6. **If internet drops:** The app still works fully from its SQLite cache. Keep going.

---

## 11. Quick Reference Commands

All commands assume you are in the project root (`gaurav_work/`) unless noted.

```cmd
REM ── First-time setup ─────────────────────────────────────────────────────
setup.bat

REM ── Start demo (normal) ──────────────────────────────────────────────────
start_demo.bat

REM ── Start demo (manual, if .bat won't run) ───────────────────────────────
cd backend
.venv\Scripts\activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

REM ── Reseed database (if empty or missing) ────────────────────────────────
cd backend && .venv\Scripts\activate
python -m app.seed.seed

REM ── Reseed and wipe existing data ────────────────────────────────────────
python -m app.seed.seed --reset

REM ── Retrain ML models ────────────────────────────────────────────────────
python -m app.ml.train

REM ── Rebuild frontend ─────────────────────────────────────────────────────
cd frontend
npm ci
npm run build

REM ── Health check ─────────────────────────────────────────────────────────
curl http://localhost:8000/api/health
```

---

## 12. Dependency Inventory

### Python packages (from requirements.txt)

| Package | Version | Purpose |
|---|---|---|
| fastapi | ≥0.115 | HTTP framework |
| uvicorn[standard] | ≥0.30 | ASGI server (websockets, httptools) |
| sqlalchemy | ≥2.0 | ORM + SQLite driver |
| pydantic | ≥2.9 | Request/response validation |
| pydantic-settings | ≥2.5 | .env loading |
| httpx | ≥0.27 | Async HTTP client (weather API) |
| pandas | ≥2.2 | Feature engineering DataFrames |
| numpy | ≥1.26 | Numerical operations |
| scikit-learn | ≥1.5 | GroupShuffleSplit, baseline metrics |
| xgboost | ≥2.1 | ML models (4 regressors + 8 quantile) |
| joblib | ≥1.4 | Model serialisation |
| python-dateutil | ≥2.9 | Date arithmetic |

### npm packages (from package.json)

| Package | Version | Purpose |
|---|---|---|
| react + react-dom | 19 | UI framework |
| react-router-dom | 7 | Client-side routing |
| @tanstack/react-query | 5 | Server-state caching |
| recharts | 3 | Charts (salinity trend, weather, stress) |
| framer-motion | 12 | Entrance animations, KPI tiles |
| lucide-react | 1 | Icons |
| tailwindcss | 4 | Utility CSS |
| @tailwindcss/vite | 4 | Tailwind Vite plugin |
| vite | 8 | Bundler + dev server |
| typescript | 6 | Type checking |

### External services

| Service | Required? | API Key? | Offline behaviour |
|---|---|---|---|
| Open-Meteo | For fresh weather | None | Serves cached data from SQLite |
| Google Fonts | For Inter font | None | Falls back to system-ui (Segoe UI) |

**No other external services. No Firebase. No Supabase. No paid APIs.**

---

*Generated for UNDP Climate Hackathon — July 2026*
