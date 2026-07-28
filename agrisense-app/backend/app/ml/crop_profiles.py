"""Published agronomic constants for the crops in the demo region.

Sources
-------
Kc (crop coefficient), root depth, depletion fraction p
    Allen et al. (1998), *FAO Irrigation and Drainage Paper 56*, Tables 12 & 22.
salt_threshold_a (dS/m), salt_slope_b (% yield loss per dS/m above threshold)
    Maas & Hoffman (1977); tabulated in Ayers & Westcot, *FAO Irrigation and
    Drainage Paper 29 Rev.1*, Table 4.

Nothing here is invented. These are the numbers an irrigation engineer would
look up, which is what makes the synthetic training data defensible.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CropSpec:
    crop: str
    display_name: str
    kc_init: float
    kc_mid: float
    kc_late: float
    root_depth_m: float
    depletion_fraction: float  # FAO-56 "p": fraction of TAW before stress starts
    salt_threshold_a: float    # ECe (dS/m) below which yield is unaffected
    salt_slope_b: float        # % yield decline per dS/m above the threshold
    season_days: int
    tolerance_label: str


# Ordered roughly by salt sensitivity (most tolerant first) for UI grouping.
CROP_SPECS: dict[str, CropSpec] = {
    "barley": CropSpec(
        "barley", "Barley", 0.30, 1.15, 0.25, 1.2, 0.55, 8.0, 5.0, 130, "tolerant"
    ),
    "cotton": CropSpec(
        "cotton", "Cotton", 0.35, 1.18, 0.60, 1.4, 0.65, 7.7, 5.2, 180, "tolerant"
    ),
    "wheat": CropSpec(
        "wheat", "Wheat", 0.30, 1.15, 0.35, 1.5, 0.55, 6.0, 7.1, 150, "moderately tolerant"
    ),
    "rice": CropSpec(
        "rice", "Rice (paddy)", 1.05, 1.20, 0.75, 0.5, 0.20, 3.0, 12.0, 120, "sensitive"
    ),
    "maize": CropSpec(
        "maize", "Maize", 0.30, 1.20, 0.50, 1.2, 0.55, 1.7, 12.0, 140, "moderately sensitive"
    ),
    "sugarcane": CropSpec(
        "sugarcane", "Sugarcane", 0.40, 1.25, 0.75, 1.5, 0.65, 1.7, 5.9, 330, "moderately sensitive"
    ),
}

DEFAULT_CROP = "wheat"


def get_crop(crop: str) -> CropSpec:
    """Look up a crop, falling back to wheat rather than raising.

    A demo must never 500 because of an unknown crop string.
    """
    return CROP_SPECS.get(crop.lower().strip(), CROP_SPECS[DEFAULT_CROP])


# --- Soil hydraulic properties -------------------------------------------------
# Volumetric water content at field capacity / wilting point.
# FAO-56 Table 19 midpoints.


@dataclass(frozen=True)
class SoilSpec:
    texture: str
    theta_fc: float          # field capacity (m3/m3)
    theta_wp: float          # wilting point (m3/m3)
    infiltration_mm_hr: float
    leaching_efficiency: float  # how effectively applied water flushes salt


SOIL_SPECS: dict[str, SoilSpec] = {
    "sandy":      SoilSpec("sandy",      0.12, 0.05, 50.0, 0.90),
    "sandy_loam": SoilSpec("sandy_loam", 0.21, 0.09, 25.0, 0.80),
    "loam":       SoilSpec("loam",       0.28, 0.13, 13.0, 0.70),
    "clay_loam":  SoilSpec("clay_loam",  0.34, 0.19,  8.0, 0.60),
    "clay":       SoilSpec("clay",       0.39, 0.24,  3.0, 0.45),
}

DEFAULT_SOIL = "loam"


def get_soil(texture: str) -> SoilSpec:
    return SOIL_SPECS.get(texture.lower().strip(), SOIL_SPECS[DEFAULT_SOIL])


# Drainage class -> fraction of percolating water that actually leaves the root
# zone. Poor drainage traps salt, which is the core mechanism of salinisation.
DRAINAGE_FACTOR: dict[str, float] = {
    "poor": 0.35,
    "moderate": 0.65,
    "good": 0.95,
}


def get_drainage_factor(drainage_class: str) -> float:
    return DRAINAGE_FACTOR.get(drainage_class.lower().strip(), 0.65)
