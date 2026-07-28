"""Physics conservation tests.

These tests check that the FAO-56 water balance and salt mass balance satisfy
their physical invariants. A model trained on data that violates conservation
laws will make confidently wrong predictions, so these are run before any ML
training pass.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from app.ml.physics import (
    FieldState,
    crop_health_score,
    hargreaves_et0,
    leaching_requirement,
    maas_hoffman_relative_yield,
    salinity_risk_level,
    total_available_water,
    water_stress_coefficient,
)
from app.ml.crop_profiles import get_crop


# --- ET0 -------------------------------------------------------------------- #

def test_hargreaves_et0_positive():
    """ET0 must always be positive — water only moves upward via evaporation."""
    et0 = hargreaves_et0(25.0, 32.0, 18.0, lat_deg=28.0, doy=150)
    assert et0 > 0


def test_hargreaves_et0_seasonal():
    """Summer (doy≈180) ET0 should exceed winter (doy≈15) at the same lat."""
    summer = hargreaves_et0(30.0, 37.0, 23.0, lat_deg=28.0, doy=180)
    winter = hargreaves_et0(12.0, 19.0, 5.0, lat_deg=28.0, doy=15)
    assert summer > winter


def test_hargreaves_et0_polar_clamp():
    """Even at extreme latitudes ET0 must remain non-negative."""
    assert hargreaves_et0(0.0, 3.0, -3.0, lat_deg=89.0, doy=1) >= 0


# --- water stress ------------------------------------------------------------ #

def test_water_stress_full_supply():
    """No depletion → Ks = 1 → stress = 0."""
    from app.ml.crop_profiles import get_soil
    spec = get_crop("wheat")
    soil = get_soil("loam")
    taw = total_available_water(soil, spec.root_depth_m)
    ks = water_stress_coefficient(depletion_mm=0.0, taw=taw, p=spec.depletion_fraction)
    assert ks == pytest.approx(1.0)


def test_water_stress_wilting_point():
    """Depletion at TAW → Ks = 0 → maximum stress."""
    from app.ml.crop_profiles import get_soil
    spec = get_crop("wheat")
    soil = get_soil("loam")
    taw = total_available_water(soil, spec.root_depth_m)
    ks = water_stress_coefficient(depletion_mm=taw, taw=taw, p=spec.depletion_fraction)
    assert ks == pytest.approx(0.0)


def test_water_stress_monotone():
    """Stress must increase monotonically with depletion."""
    from app.ml.crop_profiles import get_soil
    spec = get_crop("cotton")
    soil = get_soil("clay")
    taw = total_available_water(soil, spec.root_depth_m)
    depletions = [taw * i / 10 for i in range(11)]
    ks_values = [
        water_stress_coefficient(d, taw, spec.depletion_fraction)
        for d in depletions
    ]
    for a, b in zip(ks_values, ks_values[1:]):
        assert a >= b


# --- Maas-Hoffman salt tolerance --------------------------------------------- #

def test_maas_hoffman_below_threshold():
    """Below the salt threshold there is no yield penalty."""
    spec = get_crop("wheat")
    yr = maas_hoffman_relative_yield(ece=2.0, threshold_a=spec.salt_threshold_a,
                                     slope_b=spec.salt_slope_b)
    assert yr == pytest.approx(100.0)


def test_maas_hoffman_above_threshold():
    """Above the threshold, yield must fall."""
    spec = get_crop("wheat")
    yr_low = maas_hoffman_relative_yield(ece=7.0, threshold_a=spec.salt_threshold_a,
                                          slope_b=spec.salt_slope_b)
    yr_high = maas_hoffman_relative_yield(ece=12.0, threshold_a=spec.salt_threshold_a,
                                           slope_b=spec.salt_slope_b)
    assert yr_low > yr_high
    assert yr_high >= 0.0


def test_maas_hoffman_clipped_at_zero():
    """Relative yield can never go below zero."""
    spec = get_crop("wheat")
    yr = maas_hoffman_relative_yield(ece=50.0, threshold_a=spec.salt_threshold_a,
                                      slope_b=spec.salt_slope_b)
    assert yr == 0.0


# --- salt risk level --------------------------------------------------------- #

def test_risk_level_thresholds():
    assert salinity_risk_level(1.5) == "low"
    assert salinity_risk_level(3.0) == "moderate"
    assert salinity_risk_level(6.0) == "high"
    assert salinity_risk_level(10.0) == "critical"


# --- FieldState water balance ------------------------------------------------ #

class TestFieldStateWaterBalance:
    def setup_method(self):
        self.state = FieldState(
            crop="wheat",
            soil_texture="loam",
            drainage_class="moderate",
            root_depth_m=1.0,
            irrigation_water_ec=1.0,
            water_table_depth_m=5.0,
        )
        self.state.set_initial_ece(2.0)

    def test_step_returns_result(self):
        result = self.state.step(precip_mm=5.0, et0_mm=4.0, t_max_c=28.0,
                                 days_after_planting=60, irrigation_mm=0.0)
        assert result.ece > 0
        assert 0 <= result.water_stress_index <= 1
        assert 0 <= result.health_score <= 100

    def test_depletion_bounded_by_taw(self):
        """Soil depletion can never exceed total available water."""
        for _ in range(30):
            self.state.step(precip_mm=0.0, et0_mm=5.0, t_max_c=35.0,
                            days_after_planting=90, irrigation_mm=0.0)
        assert self.state.depletion_mm <= self.state.taw + 1e-6

    def test_irrigation_reduces_depletion(self):
        """Applying water must reduce or hold depletion, not increase it."""
        self.state.step(precip_mm=0.0, et0_mm=5.0, t_max_c=35.0,
                        days_after_planting=90, irrigation_mm=0.0)
        dep_before = self.state.depletion_mm

        self.state.step(precip_mm=0.0, et0_mm=5.0, t_max_c=35.0,
                        days_after_planting=91, irrigation_mm=50.0)
        dep_after = self.state.depletion_mm
        # depletion after can exceed before only if ET0 > irrigation, but by
        # at most one day's ET.
        assert dep_after <= dep_before + 6.0

    def test_salt_accumulates_under_poor_drainage(self):
        """Without leaching and with poor drainage, ECe should rise."""
        poor_state = FieldState(
            crop="wheat", soil_texture="clay", drainage_class="poor",
            root_depth_m=1.0, irrigation_water_ec=3.0, water_table_depth_m=1.0,
        )
        poor_state.set_initial_ece(2.0)
        for _ in range(60):
            poor_state.step(precip_mm=0.0, et0_mm=5.0, t_max_c=38.0,
                            days_after_planting=60, irrigation_mm=30.0)
        assert poor_state.ece > 2.0

    def test_leaching_reduces_salinity(self):
        """Heavy leaching irrigation with low-EC water should decrease ECe."""
        hi_salt = FieldState(
            crop="wheat", soil_texture="sandy_loam", drainage_class="good",
            root_depth_m=1.0, irrigation_water_ec=0.3, water_table_depth_m=8.0,
        )
        hi_salt.set_initial_ece(8.0)
        initial_ec = hi_salt.ece
        for _ in range(10):
            hi_salt.step(precip_mm=20.0, et0_mm=3.0, t_max_c=25.0,
                         days_after_planting=60, irrigation_mm=60.0)
        assert hi_salt.ece < initial_ec


# --- leaching requirement ---------------------------------------------------- #

def test_leaching_requirement_increases_with_water_ec():
    """Higher irrigation EC → more water needed to leach, so LR must rise."""
    lr_low = leaching_requirement(irrigation_ec=0.5, crop_threshold_a=6.0)
    lr_high = leaching_requirement(irrigation_ec=2.0, crop_threshold_a=6.0)
    assert lr_high > lr_low


def test_leaching_requirement_bounded():
    """LR must be in [0, 1] and never exceed 1."""
    lr = leaching_requirement(irrigation_ec=5.0, crop_threshold_a=2.0)
    assert 0 <= lr <= 1


# --- crop health ------------------------------------------------------------- #

def test_health_perfect_conditions():
    spec = get_crop("rice")
    health = crop_health_score(ece=0.5, ks=1.0, t_max_c=28.0, spec=spec)
    assert health == pytest.approx(100.0)


def test_health_degraded_under_stress():
    spec = get_crop("wheat")
    perfect = crop_health_score(ece=2.0, ks=1.0, t_max_c=28.0, spec=spec)
    stressed = crop_health_score(ece=8.0, ks=0.3, t_max_c=42.0, spec=spec)
    assert stressed < perfect
    assert stressed >= 0
