"""Open-Meteo provider — the default, and the reason no API key is required.

Beyond being free and keyless, Open-Meteo is the better technical fit: it
publishes FAO-56 Penman-Monteith reference evapotranspiration (`et0_fao_
evapotranspiration`) directly. ET0 is the single most important driver in the
water balance, and computing it ourselves from temperature alone (Hargreaves)
is measurably less accurate.

One request returns up to 92 past days plus 16 forecast days, so history and
forecast arrive together and stay mutually consistent.
"""
from __future__ import annotations

import logging
from datetime import date as Date
from datetime import datetime

import httpx

from app.config import settings
from app.weather.base import KMH_TO_MS, DailyWeather, WeatherProvider, WeatherSeries

logger = logging.getLogger(__name__)

ENDPOINT = "https://api.open-meteo.com/v1/forecast"

DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "precipitation_sum",
    "et0_fao_evapotranspiration",
    "wind_speed_10m_max",
    "relative_humidity_2m_mean",
]

MAX_PAST_DAYS = 92      # API limit for the forecast endpoint
MAX_FORECAST_DAYS = 16


def _num(value: object, fallback: float = 0.0) -> float:
    """Open-Meteo returns null for gaps; coerce to a usable float."""
    if value is None:
        return fallback
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


class OpenMeteoProvider(WeatherProvider):
    name = "open_meteo"

    @property
    def is_configured(self) -> bool:
        return True  # no credential needed — this is the whole point

    async def fetch(
        self, lat: float, lon: float, past_days: int = 92, forecast_days: int = 16
    ) -> WeatherSeries:
        params = {
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "daily": ",".join(DAILY_VARS),
            "timezone": "auto",
            "past_days": min(past_days, MAX_PAST_DAYS),
            "forecast_days": min(forecast_days, MAX_FORECAST_DAYS),
        }

        async with httpx.AsyncClient(timeout=settings.weather_timeout_seconds) as client:
            response = await client.get(ENDPOINT, params=params)
            response.raise_for_status()
            payload = response.json()

        return self._parse(lat, lon, payload)

    def _parse(self, lat: float, lon: float, payload: dict) -> WeatherSeries:
        daily = payload.get("daily") or {}
        dates = daily.get("time") or []
        if not dates:
            raise ValueError("Open-Meteo response contained no daily series")

        today = datetime.now().date()
        days: list[DailyWeather] = []

        for i, iso in enumerate(dates):
            def col(key: str, fallback: float = 0.0) -> float:
                series = daily.get(key) or []
                return _num(series[i] if i < len(series) else None, fallback)

            day = Date.fromisoformat(iso)
            t_max = col("temperature_2m_max")
            t_min = col("temperature_2m_min")
            t_mean = col("temperature_2m_mean", (t_max + t_min) / 2)

            days.append(DailyWeather(
                date=day,
                t_mean_c=t_mean,
                t_max_c=t_max,
                t_min_c=t_min,
                precip_mm=col("precipitation_sum"),
                et0_mm=col("et0_fao_evapotranspiration"),
                humidity_pct=col("relative_humidity_2m_mean", 50.0),
                # API reports km/h; the feature pipeline expects m/s.
                wind_ms=col("wind_speed_10m_max") * KMH_TO_MS,
                is_forecast=day > today,
            ))

        return WeatherSeries(lat=lat, lon=lon, provider=self.name, days=days)
