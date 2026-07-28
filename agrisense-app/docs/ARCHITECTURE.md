# Architecture

## Layering

```
routers/       HTTP shape only — validate, delegate, serialise
   ↓
services/      business logic — prediction, recommendation, simulation, dashboard
   ↓
repositories/  every SQLAlchemy call lives here
   ↓
SQLite (WAL)
```

Routers never touch the database or the models directly. That boundary is the
whole reason "SQLite now, Postgres later" is a real claim rather than an
aspiration: swapping the backend means rewriting `repositories/core.py` and
nothing above it.

Two subsystems hang off the service layer:

- **`ml/`** — the physics simulator, the shared feature builder, and the four
  trained regressors behind a singleton loader.
- **`weather/`** — a provider interface with two implementations, a SQLite cache,
  and an offline fallback ladder.

## Request flow: a prediction

```
POST /api/fields/2/predict
  → routers/insights.py         resolve field, 404 if absent
  → services/prediction.py      load 120d of readings (repositories)
                                fetch weather (weather/service.py, cached)
                                join onto a daily index
  → ml/features.py              build the feature matrix   ← SHARED WITH TRAINING
  → ml/predictor.py             4 regressors, clamp to physical ranges
                                salinity delta + today's EC → forecast level
  → services/recommendation.py  deterministic rules over the forecast
  → repositories/core.py        persist prediction + replace recommendations
```

### Why `features.py` is shared

Train/serve skew is the classic silent failure in a fast ML build: the training
script computes a 7-day rainfall sum one way, the API computes it another, and
the model quietly receives inputs it never saw. Nothing errors; the predictions
are just wrong.

The defence is structural. There is exactly one `build_features`, imported by
both `train.py` and `predictor.py`. Serving passes a ~120-day window and takes
the final row; training passes the whole corpus. Every rolling aggregate is
computed by identical code on both sides.

## The ML pipeline

```
physics.py          FAO-56 water balance · Maas-Hoffman · salt mass balance
   ↓
generate.py         400 virtual fields × ~200 days, sampled irrigation regimes
   ↓
features.py         42 features (shared)
   ↓
train.py            GroupShuffleSplit by field · baselines · metrics.json
   ↓
artifacts/*.joblib  loaded once at startup by predictor.py
```

### Three decisions that shaped the numbers

**Whole fields are held out, never rows.** Consecutive days within a field are
near-identical. A random row split lets the model see 5 May while predicting
6 May, producing an R² that measures nothing. Splitting on `field_id` answers the
real question: how well does this work on a farm never seen before?

**Every target is scored against a naive baseline.** The first salinity model
scored R² 0.98 predicting the *level* — and lost to "next week equals today",
which scores 0.987 on its own because soil ECe moves slowly. Over 7 days it
drifts ~0.05 dS/m, below the sensor noise floor. Reframing the target as the
**30-day change** put the baseline at "no change" and made the metric meaningful.

**Categorical inputs are encoded as physical constants, not one-hot.** Wheat
enters the model as "salt threshold 6.0 dS/m, root depth 1.5 m, depletion
fraction 0.55" rather than an opaque indicator. The model learns the agronomic
relationship, and a crop it has never seen still yields sensible predictions
because it is described in the same vocabulary.

## Weather subsystem

```
fresh cache  →  live provider  →  stale cache  →  error
```

Serving stale data is deliberate. Yesterday's weather still produces a useful
salinity forecast; a 503 produces an empty dashboard. Stale responses are flagged
so the UI can say so rather than pretend.

**The rate limit was a real bug, not a hypothetical.** Nine plots rendering
concurrently fired nine upstream calls, Open-Meteo returned 429 for two, and
those fields silently vanished from the dashboard — masked by the per-field
try/except that exists so one bad field cannot blank the page. Three fixes:

1. **Coarsened the cache grid to ~11 km.** Daily aggregates do not vary across
   one farm, so a farm is now one call rather than nine. This was the big win.
2. **A per-location asyncio lock**, so simultaneous requests for the same grid
   cell wait on one fetch instead of racing.
3. **Bounded concurrency plus backoff** on 429/5xx.

## Failure modes and what happens

| Failure | Behaviour |
|---|---|
| Model artifacts missing | Falls back to the physics simulator; API boots normally |
| Weather provider down | Serves stale cache, flagged in the UI |
| Weather down *and* cache empty | 503 on that field only; dashboard renders the rest |
| One field errors during aggregation | Logged and skipped; other fields still render |
| Unknown crop string | Falls back to wheat rather than raising |
| Field with <3 readings | Physics fallback with reduced confidence |
| Frontend not built | API serves a JSON index pointing at `/docs` |

## Frontend

Server state is TanStack Query only — there is no client store, because nothing
here is genuinely client-global except the selected farm, which lives in the URL.

Colour discipline is enforced by structure rather than convention:

- **Status colours are reserved for risk** and never used as a chart series, so a
  risk colour can never impersonate data.
- **Risk states carry an icon and a label**, never colour alone. The palette puts
  amber below 3:1 contrast on light surfaces by design; icon+label is the
  documented mitigation, and it also survives a washed-out projector.
- **No dual-axis charts.** Rainfall and ET0 share an axis because both are
  millimetres — a genuine comparison. Water stress is a unitless index, so it
  gets its own chart instead of a second y-scale.

Palette validated with a CVD simulator in both modes; worst adjacent pair
ΔE 35.9 under deuteranopia, well clear of the ≥12 target.

## Deployment

Vite builds to `frontend/dist`; FastAPI mounts it with an SPA history fallback
registered last so it never shadows `/api` or `/docs`. One process, one URL, and
no CORS class of failure during a live demo. `docker compose up` reproduces it.
