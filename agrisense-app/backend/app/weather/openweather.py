"""OpenWeatherMap adapter.

Kept behind the same interface so the provider can be switched by config alone.
Two honest caveats, surfaced here rather than buried:

* OWM does not publish FAO-56 reference evapotranspiration, so ET0 is estimated
  from temperature via Hargreaves-Samani. That is a real accuracy loss on the
  most important driver in the model.
* The free tier's history window is far shorter than Open-Meteo's 92 days, which
  leaves the 30-day rolling features thinly populated.

Open-Meteo remains the default for both reasons.
"""
from __future__ import annotations

import logging
from datetime import date as Date
from datetime import datetime, timedelta

import httpx

from app.config import settings
from app.ml.physics import hargreaves_et0
from app.weather.base import DailyWeather, WeatherProvider, WeatherSeries

logger = logging.getLogger(__name__)

ENDPOINT = "https://api.openweathermap.org/data/2.5/forecast"


class OpenWeatherMapProvider(WeatherProvider):
    name = "openweathermap"

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or settings.openweathermap_api_key

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def fetch(
        self, lat: float, lon: float, past_days: int = 92, forecast_days: int = 16
    ) -> WeatherSeries:
        if not self.is_configured:
            raise RuntimeError("OPENWEATHERMAP_API_KEY is not set")

        params = {"lat": round(lat, 4), "lon": round(lon, 4),
                  "appid": self._api_key, "units": "metric"}

        async with httpx.AsyncClient(timeout=settings.weather_timeout_seconds) as client:
            response = await client.get(ENDPOINT, params=params)
            response.raise_for_status()
            payload = response.json()

        return self._parse(lat, lon, payload)

    def _parse(self, lat: float, lon: float, payload: dict) -> WeatherSeries:
        """Collapse OWM's 3-hourly forecast list into daily aggregates."""
        buckets: dict[Date, dict[str, list[float]]] = {}

        for entry in payload.get("list", []):
            stamp = datetime.fromtimestamp(entry["dt"])
            day = stamp.date()
            main = entry.get("main", {})
            bucket = buckets.setdefault(day, {"t": [], "h": [], "w": [], "p": []})
            bucket["t"].append(float(main.get("temp", 0.0)))
            bucket["h"].append(float(main.get("humidity", 50.0)))
            bucket["w"].append(float(entry.get("wind", {}).get("speed", 0.0)))
            bucket["p"].append(float(entry.get("rain", {}).get("3h", 0.0)))

        today = datetime.now().date()
        days: list[DailyWeather] = []

        for day in sorted(buckets):
            b = buckets[day]
            temps = b["t"] or [0.0]
            t_max, t_min = max(temps), min(temps)
            t_mean = sum(temps) / len(temps)
            doy = day.timetuple().tm_yday

            days.append(DailyWeather(
                date=day,
                t_mean_c=t_mean,
                t_max_c=t_max,
                t_min_c=t_min,
                precip_mm=sum(b["p"]),
                et0_mm=hargreaves_et0(t_mean, t_max, t_min, lat, doy),
                humidity_pct=sum(b["h"]) / len(b["h"]) if b["h"] else 50.0,
                wind_ms=sum(b["w"]) / len(b["w"]) if b["w"] else 0.0,  # OWM metric = m/s
                is_forecast=day > today,
            ))

        if not days:
            raise ValueError("OpenWeatherMap response contained no forecast entries")
        return WeatherSeries(lat=lat, lon=lon, provider=self.name, days=days)
