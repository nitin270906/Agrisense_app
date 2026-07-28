"""Application settings, loaded from environment with demo-safe defaults."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = BACKEND_DIR / "app" / "ml" / "artifacts"
FRONTEND_DIST = BACKEND_DIR.parent / "frontend" / "dist"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AGRISENSE — AI Salinity & Crop Stress Forecaster"
    api_prefix: str = "/api"

    database_url: str = f"sqlite:///{BACKEND_DIR / 'salinity.db'}"

    weather_provider: str = "open_meteo"
    openweathermap_api_key: str = ""
    weather_cache_ttl_hours: int = 3
    weather_timeout_seconds: float = 12.0

    # localhost:8000 covers demo mode (FastAPI serves the built bundle).
    # localhost:5173 covers Vite dev server. Both are same-machine, no secret.
    cors_origins: str = (
        "http://localhost:8000,http://127.0.0.1:8000,"
        "http://localhost:5173,http://127.0.0.1:5173"
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
