"""Weather provider interface and normalised data transfer objects.

Providers differ in field names, units and which variables they expose at all.
Everything above this layer works only with `DailyWeather`, so swapping
Open-Meteo for OpenWeatherMap (or adding a satellite source later) touches one
file and nothing else.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date as Date


@dataclass(frozen=True)
class DailyWeather:
    """One day of weather, normalised to the units the ML pipeline expects.

    Units are stated explicitly because a silent unit mismatch is the easiest
    way to poison a model: Open-Meteo reports wind in km/h while the feature
    builder assumes m/s, which would inflate every wind feature by 3.6x.
    """

    date: Date
    t_mean_c: float
    t_max_c: float
    t_min_c: float
    precip_mm: float
    et0_mm: float          # FAO-56 reference evapotranspiration
    humidity_pct: float
    wind_ms: float         # metres per second
    is_forecast: bool = False

    def to_dict(self) -> dict:
        return {
            "date": self.date.isoformat(),
            "t_mean_c": round(self.t_mean_c, 1),
            "t_max_c": round(self.t_max_c, 1),
            "t_min_c": round(self.t_min_c, 1),
            "precip_mm": round(self.precip_mm, 1),
            "et0_mm": round(self.et0_mm, 2),
            "humidity_pct": round(self.humidity_pct, 0),
            "wind_ms": round(self.wind_ms, 1),
            "is_forecast": self.is_forecast,
        }


@dataclass
class WeatherSeries:
    """A contiguous daily series spanning past and forecast days."""

    lat: float
    lon: float
    provider: str
    days: list[DailyWeather] = field(default_factory=list)
    from_cache: bool = False
    stale: bool = False

    @property
    def history(self) -> list[DailyWeather]:
        return [d for d in self.days if not d.is_forecast]

    @property
    def forecast(self) -> list[DailyWeather]:
        return [d for d in self.days if d.is_forecast]

    @property
    def current(self) -> DailyWeather | None:
        past = self.history
        return past[-1] if past else (self.days[0] if self.days else None)


class WeatherProvider(ABC):
    """Fetches a normalised daily weather series for a location."""

    name: str = "base"

    @abstractmethod
    async def fetch(
        self, lat: float, lon: float, past_days: int = 92, forecast_days: int = 16
    ) -> WeatherSeries:
        """Return past + forecast days for a point. Raises on transport failure."""

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """False when a required credential is absent."""


KMH_TO_MS = 1.0 / 3.6
