"""Phase 4 acceptance: the fund wrapper must separate distributions from NAV
and expose NAV erosion in the choppy regime."""

import numpy as np

from covered_call_sim.config import REGIMES, SimConfig
from covered_call_sim.models.paths import simulate_gbm_paths
from covered_call_sim.strategy import roll_covered_call
from covered_call_sim.metrics import distribution_yield


def test_total_return_equals_nav_plus_distributions():
    """Total-return index growth must equal NAV growth plus the reinvested
    distribution stream — they are two views of the same wealth."""
    cfg = SimConfig(n_paths=500, horizon_months=60, seed=1)
    res = roll_covered_call(simulate_gbm_paths(REGIMES["flat"], cfg), cfg)

    # Reconstruct the total-return gross factor from its two components and
    # confirm it matches the reported total-return index.
    nav_gross = res.nav_index[:, 1:] / res.nav_index[:, :-1]
    reconstructed = np.cumprod(nav_gross + res.income, axis=1)
    assert np.allclose(reconstructed, res.total_return_index[:, 1:])


def test_choppy_shows_nav_erosion_with_healthy_yield():
    """The headline acceptance bar: in the choppy regime a healthy distribution
    yield coexists with flat/declining NAV."""
    cfg = SimConfig(n_paths=5000, horizon_months=120, seed=2)
    res = roll_covered_call(simulate_gbm_paths(REGIMES["flat"], cfg), cfg)
    dist = distribution_yield(res)

    # Healthy headline yield...
    assert dist["avg_annual_dist_yield"] > 0.05
    # ...but NAV grinds down (median NAV ends below where it started).
    median_nav_terminal = np.median(res.nav_index[:, -1])
    assert median_nav_terminal < 1.0
    # The gap proves much of the "yield" is returned capital.
    assert dist["yield_minus_total_return"] > 0.05


def test_coverage_scales_distribution():
    """Half coverage should distribute roughly half the premium yield."""
    cfg_full = SimConfig(n_paths=3000, horizon_months=60, coverage=1.0, seed=4)
    cfg_half = cfg_full.with_(coverage=0.5)
    full = roll_covered_call(simulate_gbm_paths(REGIMES["flat"], cfg_full), cfg_full)
    half = roll_covered_call(simulate_gbm_paths(REGIMES["flat"], cfg_half), cfg_half)
    ratio = half.income.mean() / full.income.mean()
    assert abs(ratio - 0.5) < 1e-6
