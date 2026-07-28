"""Domain enums shared by ORM models, Pydantic schemas and the ML layer.

Stored as plain strings in SQLite for portability; validated at the schema edge.
"""
from __future__ import annotations

from enum import Enum


class RiskLevel(str, Enum):
    """Salinity risk bands, aligned to USDA soil salinity classes (dS/m)."""

    LOW = "low"            # ECe < 2   — non-saline
    MODERATE = "moderate"  # 2-4       — slightly saline
    HIGH = "high"          # 4-8       — moderately saline
    CRITICAL = "critical"  # > 8       — strongly saline


class SoilTexture(str, Enum):
    SANDY = "sandy"
    SANDY_LOAM = "sandy_loam"
    LOAM = "loam"
    CLAY_LOAM = "clay_loam"
    CLAY = "clay"


class DrainageClass(str, Enum):
    POOR = "poor"
    MODERATE = "moderate"
    GOOD = "good"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    URGENT = "urgent"
    CRITICAL = "critical"


class RecommendationCategory(str, Enum):
    IRRIGATION = "irrigation"
    LEACHING = "leaching"
    AMENDMENT = "amendment"
    CROP_CHOICE = "crop_choice"
    DRAINAGE = "drainage"
    MONITORING = "monitoring"


class ReadingSource(str, Enum):
    SENSOR = "sensor"
    MANUAL = "manual"
    SIMULATED = "simulated"


class WeatherKind(str, Enum):
    CURRENT = "current"
    FORECAST = "forecast"
    HISTORY = "history"
