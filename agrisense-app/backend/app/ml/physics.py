"""Agronomic process model: FAO-56 water balance + salt mass balance.

This module is the ground truth the XGBoost models learn to approximate. It is
deliberately a *simulator*, not a curve fit: salinity emerges from the daily
interaction of irrigation water quality, evapotranspiration, rainfall leaching,
drainage capacity and capillary rise from a shallow water table.

That mechanism matters. Salt does not evaporate — water leaves the root zone as
vapour and the salt it carried stays behind. Every irrigation event therefore
*adds* salt, and only percolating water below the root zone removes it. Fields
with poor drainage or a shallow saline water table accumulate salt no matter how
carefully they are watered, which is exactly the trap this tool warns about.

References
----------
Allen et al. (1998) FAO-56 — ET0, Kc, TAW/RAW, Ks water stress coefficient.
Ayers & Westcot (1985) FAO-29 Rev.1 — leaching requirement, salt tolerance.
Maas & Hoffman (1977) — piecewise-linear salt tolerance response.
Doorenbos & Kassam (1979) FAO-33 — yield response factor Ky.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field as dc_field

from app.ml.crop_profiles import (
    CropSpec,
    SoilSpec,
    get_crop,
    get_drainage_factor,
    get_soil,
)

# Ratio of soil-water EC at field capacity to saturated-paste EC (ECe).
# The saturation percentage is roughly twice field capacity, so the soil
# solution a root actually experiences is about twice as concentrated as ECe.
SOIL_WATER_TO_ECE = 2.0

# EC of shallow groundwater in the saline tracts of NW India (dS/m).
DEFAULT_GROUNDWATER_EC = 4.0

# FAO-33 yield response factor: proportional yield loss per unit ET deficit.
YIELD_RESPONSE_KY = 1.1

MAX_ECE = 30.0  # physical clamp; beyond this the field is not farmland

# Irrigate when depletion reaches this fraction of readily available water.
# Below 1.0 so the recommendation precedes the onset of stress.
IRRIGATION_TRIGGER_FRACTION = 0.65


# --------------------------------------------------------------------------- #
# Reference evapotranspiration
# --------------------------------------------------------------------------- #
def hargreaves_et0(t_mean: float, t_max: float, t_min: float, lat_deg: float, doy: int) -> float:
    """Hargreaves-Samani ET0 (mm/day).

    Only used as a fallback: Open-Meteo supplies FAO-56 Penman-Monteith ET0
    directly, which is more accurate. This keeps the simulator runnable offline
    and keeps the synthetic generator independent of any network call.
    """
    lat = math.radians(lat_deg)
    dr = 1 + 0.033 * math.cos(2 * math.pi * doy / 365)
    decl = 0.409 * math.sin(2 * math.pi * doy / 365 - 1.39)

    # Sunset hour angle, guarded against domain errors at high latitude.
    x = max(-1.0, min(1.0, -math.tan(lat) * math.tan(decl)))
    ws = math.acos(x)

    # Extraterrestrial radiation (MJ/m2/day) -> mm/day equivalent (x 0.408).
    ra = (24 * 60 / math.pi) * 0.0820 * dr * (
        ws * math.sin(lat) * math.sin(decl) + math.cos(lat) * math.cos(decl) * math.sin(ws)
    )
    td = max(0.0, t_max - t_min)
    et0 = 0.0023 * (t_mean + 17.8) * math.sqrt(td) * 0.408 * ra
    return max(0.0, et0)


def crop_coefficient(spec: CropSpec, days_after_planting: int) -> float:
    """FAO-56 Kc interpolated across the four growth stages.

    Stage lengths as fractions of season: initial 20%, development 25%,
    mid-season 30%, late 25%.
    """
    if spec.season_days <= 0:
        return spec.kc_mid
    f = max(0.0, min(1.0, days_after_planting / spec.season_days))

    if f <= 0.20:
        return spec.kc_init
    if f <= 0.45:  # development: linear rise init -> mid
        return spec.kc_init + (spec.kc_mid - spec.kc_init) * (f - 0.20) / 0.25
    if f <= 0.75:
        return spec.kc_mid
    # late season: linear decline mid -> late
    return spec.kc_mid + (spec.kc_late - spec.kc_mid) * (f - 0.75) / 0.25


def growth_stage(spec: CropSpec, days_after_planting: int) -> str:
    if spec.season_days <= 0:
        return "mid"
    f = max(0.0, min(1.0, days_after_planting / spec.season_days))
    if f <= 0.20:
        return "initial"
    if f <= 0.45:
        return "development"
    if f <= 0.75:
        return "mid"
    return "late"


# --------------------------------------------------------------------------- #
# Soil water
# --------------------------------------------------------------------------- #
def total_available_water(soil: SoilSpec, root_depth_m: float) -> float:
    """TAW (mm) held between field capacity and wilting point in the root zone."""
    return 1000.0 * (soil.theta_fc - soil.theta_wp) * root_depth_m


def readily_available_water(taw: float, depletion_fraction: float) -> float:
    """RAW (mm) — depletion beyond this point starts closing stomata."""
    return taw * depletion_fraction


def water_stress_coefficient(depletion_mm: float, taw: float, p: float) -> float:
    """FAO-56 Ks in [0, 1]. 1.0 = unstressed, 0.0 = transpiration halted."""
    if taw <= 0:
        return 1.0
    raw = readily_available_water(taw, p)
    if depletion_mm <= raw:
        return 1.0
    denom = taw - raw
    if denom <= 0:
        return 0.0
    return max(0.0, min(1.0, (taw - depletion_mm) / denom))


def effective_rainfall(precip_mm: float, soil: SoilSpec) -> float:
    """Rainfall minus runoff and interception.

    Heavy rain on clay largely runs off; the same rain on sand infiltrates. This
    is why clay fields leach poorly and salinise faster.
    """
    if precip_mm <= 1.0:
        return 0.0
    runoff_fraction = max(0.0, min(0.6, precip_mm / (precip_mm + soil.infiltration_mm_hr * 4)))
    return max(0.0, (precip_mm - 1.0) * (1.0 - runoff_fraction))


def capillary_rise(
    water_table_depth_m: float, root_depth_m: float, et0_mm: float, soil: SoilSpec
) -> float:
    """Upward flux of saline groundwater into the root zone (mm/day).

    This is the dominant salinisation pathway in irrigated semi-arid plains: a
    water table within ~2 m of the roots wicks salt upward under evaporative
    demand, and no amount of surface management stops it.
    """
    gap = water_table_depth_m - root_depth_m
    if gap <= 0:
        # Water table inside the root zone: waterlogged and strongly saline.
        return min(et0_mm * 0.9, 8.0)
    reference = 5.0 * (soil.theta_fc / 0.28)  # finer soils wick more strongly
    flux = reference * math.exp(-gap / 0.7)
    # Capillary rise is driven by atmospheric demand; it cannot exceed it.
    return max(0.0, min(flux, et0_mm * 0.6))


# --------------------------------------------------------------------------- #
# Salt tolerance and stress
# --------------------------------------------------------------------------- #
def maas_hoffman_relative_yield(ece: float, threshold_a: float, slope_b: float) -> float:
    """Relative yield (%) under salinity, per Maas & Hoffman (1977).

        Yr = 100                        for ECe <= a
        Yr = 100 - b * (ECe - a)        for ECe >  a
    """
    if ece <= threshold_a:
        return 100.0
    return max(0.0, 100.0 - slope_b * (ece - threshold_a))


def temperature_stress_factor(t_max_c: float) -> float:
    """Heat penalty in [0.6, 1.0]. Most cereals lose yield above ~35 C."""
    if t_max_c <= 35.0:
        return 1.0
    return max(0.6, 1.0 - 0.4 * min(1.0, (t_max_c - 35.0) / 15.0))


def leaching_requirement(irrigation_ec: float, crop_threshold_a: float) -> float:
    """LR — fraction of applied water that must percolate to hold salt steady.

    FAO-29:  LR = EC_iw / (5 * ECe_target - EC_iw)

    Capped at 0.5 because beyond that the recommendation stops being irrigation
    advice and becomes "this water is not fit for this crop".
    """
    denom = 5.0 * crop_threshold_a - irrigation_ec
    if denom <= 0:
        return 0.5
    return max(0.0, min(0.5, irrigation_ec / denom))


def salinity_risk_level(ece: float) -> str:
    """USDA soil salinity classes, collapsed to four UI risk bands."""
    if ece < 2.0:
        return "low"
    if ece < 4.0:
        return "moderate"
    if ece < 8.0:
        return "high"
    return "critical"


def crop_health_score(ece: float, ks: float, t_max_c: float, spec: CropSpec) -> float:
    """Composite 0-100 health, multiplying the three independent stresses.

    Multiplicative rather than additive because the stresses compound: a crop
    that is both salt-stressed and water-stressed does worse than the sum of
    either alone. Salt raises the osmotic potential of the soil solution, which
    makes the *same* soil moisture harder to extract.
    """
    salt = maas_hoffman_relative_yield(ece, spec.salt_threshold_a, spec.salt_slope_b) / 100.0
    water = max(0.0, 1.0 - YIELD_RESPONSE_KY * (1.0 - ks))
    heat = temperature_stress_factor(t_max_c)
    return max(0.0, min(100.0, 100.0 * salt * water * heat))


# --------------------------------------------------------------------------- #
# Daily state machine
# --------------------------------------------------------------------------- #
@dataclass
class FieldState:
    """Mutable root-zone state advanced one day at a time."""

    crop: str
    soil_texture: str
    drainage_class: str
    root_depth_m: float
    irrigation_water_ec: float
    water_table_depth_m: float
    groundwater_ec: float = DEFAULT_GROUNDWATER_EC

    depletion_mm: float = 0.0      # Dr: water deficit below field capacity
    salt_mass: float = 0.0         # dS/m * mm, expressed on a saturated basis
    days_since_irrigation: int = 0

    _spec: CropSpec = dc_field(init=False)
    _soil: SoilSpec = dc_field(init=False)

    def __post_init__(self) -> None:
        self._spec = get_crop(self.crop)
        self._soil = get_soil(self.soil_texture)

    # -- derived quantities ------------------------------------------------- #
    @property
    def spec(self) -> CropSpec:
        return self._spec

    @property
    def soil(self) -> SoilSpec:
        return self._soil

    @property
    def taw(self) -> float:
        return total_available_water(self._soil, self.root_depth_m)

    @property
    def saturated_water_mm(self) -> float:
        """Water held at saturation — the basis on which ECe is defined."""
        theta_sat = self._soil.theta_fc * SOIL_WATER_TO_ECE
        return 1000.0 * theta_sat * self.root_depth_m

    @property
    def ece(self) -> float:
        """Saturated-paste extract EC (dS/m) implied by current salt mass."""
        w = self.saturated_water_mm
        if w <= 0:
            return 0.0
        return max(0.0, min(MAX_ECE, self.salt_mass / w))

    def set_initial_ece(self, ece: float) -> None:
        self.salt_mass = max(0.0, ece) * self.saturated_water_mm

    @property
    def soil_moisture_pct(self) -> float:
        """Volumetric moisture (%) implied by current depletion."""
        theta = self._soil.theta_fc - (self.depletion_mm / (1000.0 * self.root_depth_m))
        return max(self._soil.theta_wp, min(self._soil.theta_fc, theta)) * 100.0

    # -- the daily step ----------------------------------------------------- #
    def step(
        self,
        *,
        precip_mm: float,
        et0_mm: float,
        t_max_c: float,
        days_after_planting: int,
        irrigation_mm: float = 0.0,
    ) -> "DayResult":
        """Advance one day and return the resulting agronomic state.

        Order matters: water arrives, the crop transpires what it can reach,
        and only the surplus that actually drains carries salt away.
        """
        spec, soil = self._spec, self._soil
        taw = self.taw

        kc = crop_coefficient(spec, days_after_planting)
        ks = water_stress_coefficient(self.depletion_mm, taw, spec.depletion_fraction)
        etc_actual = kc * et0_mm * ks

        p_eff = effective_rainfall(precip_mm, soil)
        cap_rise = capillary_rise(self.water_table_depth_m, self.root_depth_m, et0_mm, soil)

        # Water balance: depletion shrinks with inflow, grows with ET.
        inflow = p_eff + irrigation_mm + cap_rise
        new_depletion = self.depletion_mm - inflow + etc_actual

        # Surplus beyond field capacity percolates; how much *leaves* the root
        # zone depends on drainage class.
        if new_depletion < 0:
            percolation = -new_depletion
            new_depletion = 0.0
        else:
            percolation = 0.0
        drained = percolation * get_drainage_factor(self.drainage_class)

        self.depletion_mm = max(0.0, min(taw, new_depletion))

        # Salt balance. Irrigation and capillary rise import salt; only drainage
        # exports it. ET removes pure water, concentrating what remains.
        salt_in = irrigation_mm * self.irrigation_water_ec + cap_rise * self.groundwater_ec
        soil_solution_ec = self.ece * SOIL_WATER_TO_ECE
        salt_out = drained * soil_solution_ec * soil.leaching_efficiency
        self.salt_mass = max(0.0, self.salt_mass + salt_in - salt_out)

        cap = MAX_ECE * self.saturated_water_mm
        if self.salt_mass > cap:
            self.salt_mass = cap

        self.days_since_irrigation = 0 if irrigation_mm > 0 else self.days_since_irrigation + 1

        ece = self.ece
        return DayResult(
            ece=ece,
            water_stress_index=1.0 - ks,
            ks=ks,
            kc=kc,
            etc_mm=etc_actual,
            percolation_mm=drained,
            capillary_rise_mm=cap_rise,
            effective_rain_mm=p_eff,
            depletion_mm=self.depletion_mm,
            soil_moisture_pct=self.soil_moisture_pct,
            health_score=crop_health_score(ece, ks, t_max_c, spec),
            irrigation_need_mm=self.irrigation_need(),
            risk_level=salinity_risk_level(ece),
        )

    def irrigation_need(self, trigger_fraction: float = IRRIGATION_TRIGGER_FRACTION) -> float:
        """Gross irrigation depth (mm) needed now, including leaching overhead.

        The trigger sits at a *fraction* of RAW rather than at RAW itself. This
        is deliberate on both agronomic and product grounds: water stress begins
        the moment depletion exceeds RAW, so advice that waits until RAW is
        reached is advice that arrives too late to prevent the damage. Firing
        early gives the farmer lead time to arrange a canal turn or fuel a pump.

        It also keeps this signal genuinely distinct from `water_stress_index`.
        Triggering exactly at RAW would make "needs irrigation" and "is stressed"
        the same boolean, and two of the four forecasts would be duplicates.
        """
        spec = self._spec
        taw = self.taw
        raw = readily_available_water(taw, spec.depletion_fraction)
        if self.depletion_mm < raw * trigger_fraction:
            return 0.0
        net = self.depletion_mm
        lr = leaching_requirement(self.irrigation_water_ec, spec.salt_threshold_a)
        gross = net / max(0.5, 1.0 - lr)
        return round(min(gross, 150.0), 1)


@dataclass(frozen=True)
class DayResult:
    """Outcome of a single simulated day — the ML training targets live here."""

    ece: float
    water_stress_index: float
    ks: float
    kc: float
    etc_mm: float
    percolation_mm: float
    capillary_rise_mm: float
    effective_rain_mm: float
    depletion_mm: float
    soil_moisture_pct: float
    health_score: float
    irrigation_need_mm: float
    risk_level: str
