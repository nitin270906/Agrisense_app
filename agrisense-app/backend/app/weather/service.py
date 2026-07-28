"""Weather orchestration: provider selection, SQLite caching, offline fallback.

The fallback ladder is the point of this module:

    fresh cache  ->  live provider  ->  stale cache  ->  error

Serving stale data is a deliberate choice. Yesterday's weather still produces a
useful salinity forecast, whereas a 503 produces an empty dashboard. On a
conference wifi during a live demo, that difference decides whether the product
works. Stale responses are flagged so the UI can say so rather than pretend.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date as Date
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import WeatherSnapshot
from app.weather.base import DailyWeather, WeatherProvider, WeatherSeries
from app.weather.open_meteo import OpenMeteoProvider
from app.weather.openweather import OpenWeatherMapProvider

logger = logging.getLogger(__name__)

# ~11 km grid. Deliberately coarse: daily aggregates (mean temperature, rainfall
# total, ET0) do not vary meaningfully across a single farm, so every plot on a
# farm should share one cached record.
#
# This started at 2 decimals (~1.1 km) and rate-limited immediately. Seeded plots
# are scattered a few hundred metres apart, which was enough to give each its own
# cache key, so a nine-field dashboard fired nine concurrent upstream calls and
# Open-Meteo returned 429 for two of them. Those fields then vanished from the
# dashboard. One decimal collapses a farm to a single call.
GRID_PRECISION = 1

# Ceiling on concurrent upstream calls, independent of how many fields render.
_MAX_CONCURRENT_FETCHES = 3
_fetch_semaphore = asyncio.Semaphore(_MAX_CONCURRENT_FETCHES)

# One lock per grid cell, so simultaneous requests for the same location do not
# each issue a call: the first fetches and caches, the rest find it fresh.
_location_locks: dict[tuple[float, float], asyncio.Lock] = {}
_locks_guard = asyncio.Lock()

RETRY_STATUS = {429, 502, 503, 504}
RETRY_DELAYS = (0.5, 1.5)


def _grid(value: float) -> float:
    return round(value, GRID_PRECISION)


async def _lock_for(lat: float, lon: float) -> asyncio.Lock:
    key = (_grid(lat), _grid(lon))
    async with _locks_guard:
        lock = _location_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            _location_locks[key] = lock
        return lock


async def _fetch_with_retry(provider: WeatherProvider, lat: float, lon: float) -> WeatherSeries:
    """Fetch with bounded concurrency and backoff on transient upstream errors."""
    last_error: Exception | None = None
    for attempt in range(len(RETRY_DELAYS) + 1):
        try:
            async with _fetch_semaphore:
                return await provider.fetch(lat, lon)
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response.status_code not in RETRY_STATUS:
                raise
            if attempt < len(RETRY_DELAYS):
                delay = RETRY_DELAYS[attempt]
                logger.warning(
                    "Weather upstream returned %s; retrying in %.1fs",
                    exc.response.status_code, delay,
                )
                await asyncio.sleep(delay)
        except Exception as exc:
            last_error = exc
            raise
    raise last_error if last_error else RuntimeError("weather fetch failed")


def get_provider(name: str | None = None) -> WeatherProvider:
    """Resolve the configured provider, falling back to the keyless one.

    If OpenWeatherMap is selected but no key is present, silently degrading to
    Open-Meteo is better than failing every weather request — the app stays
    functional and logs the reason.
    """
    chosen = (name or settings.weather_provider or "open_meteo").lower()
    if chosen == "openweathermap":
        provider = OpenWeatherMapProvider()
        if provider.is_configured:
            return provider
        logger.warning("openweathermap selected but no API key set; using open_meteo")
    return OpenMeteoProvider()


def _to_snapshot(lat: float, lon: float, day: DailyWeather, provider: str) -> WeatherSnapshot:
    return WeatherSnapshot(
        lat=_grid(lat),
        lon=_grid(lon),
        ts=datetime.combine(day.date, datetime.min.time()),
        kind="forecast" if day.is_forecast else "history",
        temp_c=day.t_mean_c,
        temp_max_c=day.t_max_c,
        temp_min_c=day.t_min_c,
        precip_mm=day.precip_mm,
        et0_mm=day.et0_mm,
        humidity_pct=day.humidity_pct,
        wind_ms=day.wind_ms,
        provider=provider,
        fetched_at=datetime.now(timezone.utc),
    )


def _from_snapshot(row: WeatherSnapshot) -> DailyWeather:
    return DailyWeather(
        date=row.ts.date(),
        t_mean_c=row.temp_c,
        t_max_c=row.temp_max_c,
        t_min_c=row.temp_min_c,
        precip_mm=row.precip_mm,
        et0_mm=row.et0_mm,
        humidity_pct=row.humidity_pct,
        wind_ms=row.wind_ms,
        is_forecast=row.kind == "forecast",
    )


def _read_cache(db: Session, lat: float, lon: float) -> list[WeatherSnapshot]:
    stmt = (
        select(WeatherSnapshot)
        .where(WeatherSnapshot.lat == _grid(lat), WeatherSnapshot.lon == _grid(lon))
        .order_by(WeatherSnapshot.ts)
    )
    return list(db.scalars(stmt))


def _is_fresh(rows: list[WeatherSnapshot]) -> bool:
    if not rows:
        return False
    newest = max(r.fetched_at for r in rows if r.fetched_at)
    if newest.tzinfo is None:
        newest = newest.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - newest
    return age < timedelta(hours=settings.weather_cache_ttl_hours)


def _write_cache(db: Session, series: WeatherSeries) -> None:
    """Replace this location's cached rows with a freshly fetched series."""
    lat, lon = _grid(series.lat), _grid(series.lon)
    db.query(WeatherSnapshot).filter(
        WeatherSnapshot.lat == lat, WeatherSnapshot.lon == lon
    ).delete(synchronize_session=False)
    db.add_all([_to_snapshot(lat, lon, d, series.provider) for d in series.days])
    db.commit()


def _series_from_cache(
    lat: float, lon: float, rows: list[WeatherSnapshot], *, stale: bool = False
) -> WeatherSeries:
    return WeatherSeries(
        lat=lat, lon=lon,
        provider=rows[0].provider,
        days=[_from_snapshot(r) for r in rows],
        from_cache=True,
        stale=stale,
    )


async def get_weather(
    db: Session, lat: float, lon: float, *, force_refresh: bool = False
) -> WeatherSeries:
    """Weather for a point, cached, with graceful degradation when offline.

    Fresh cache -> live provider -> stale cache -> raise.
    """
    cached = _read_cache(db, lat, lon)
    if cached and _is_fresh(cached) and not force_refresh:
        return _series_from_cache(lat, lon, cached)

    # Serialise per location so a dashboard rendering many plots on one farm
    # produces a single upstream call rather than one per plot.
    lock = await _lock_for(lat, lon)
    async with lock:
        # Another coroutine may have populated the cache while we waited.
        if not force_refresh:
            cached = _read_cache(db, lat, lon)
            if cached and _is_fresh(cached):
                return _series_from_cache(lat, lon, cached)

        provider = get_provider()
        try:
            series = await _fetch_with_retry(provider, lat, lon)
            _write_cache(db, series)
            return series
        except Exception as exc:
            if cached:
                logger.warning(
                    "Weather fetch failed (%s); serving %d cached rows as stale",
                    exc, len(cached),
                )
                return _series_from_cache(lat, lon, cached, stale=True)
            logger.error("Weather fetch failed with no cache to fall back on: %s", exc)
            raise


def weather_to_frame_rows(series: WeatherSeries) -> dict[Date, DailyWeather]:
    """Index a series by date for joining against sensor readings."""
    return {d.date: d for d in series.days}
