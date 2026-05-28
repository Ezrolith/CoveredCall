"""Path-generation sanity checks (GBM moments + Markov switching)."""

import numpy as np

from covered_call_sim.config import REGIMES, Regime, SimConfig, RegimeSwitching
from covered_call_sim.models.paths import (
    simulate_gbm_paths,
    simulate_regime_paths,
    sample_markov_regimes,
)


def test_gbm_terminal_moments():
    cfg = SimConfig(n_paths=200_000, horizon_months=12, seed=3)
    regime = Regime("t", mu=0.10, sigma_realised=0.20, vrp=0.0)
    bundle = simulate_gbm_paths(regime, cfg)
    terminal = bundle.prices[:, -1] / cfg.s0
    # E[S_T/S_0] = exp(mu * T) under GBM.
    assert abs(terminal.mean() - np.exp(0.10)) < 0.01


def test_gbm_reproducible_with_seed():
    cfg = SimConfig(n_paths=1000, horizon_months=12, seed=99)
    regime = REGIMES["bull"]
    a = simulate_gbm_paths(regime, cfg)
    b = simulate_gbm_paths(regime, cfg)
    assert np.allclose(a.prices, b.prices)


def test_markov_regimes_shape_and_range():
    rng = np.random.default_rng(0)
    sw = RegimeSwitching()
    idx = sample_markov_regimes(sw, 500, 240, rng)
    assert idx.shape == (500, 240)
    assert idx.min() >= 0 and idx.max() < len(sw.order)


def test_switching_paths_carry_per_step_vrp():
    cfg = SimConfig(n_paths=2000, horizon_months=120, seed=5)
    bundle = simulate_regime_paths(REGIMES, cfg.switching, cfg)
    assert bundle.regime_idx is not None
    # VRP should take on the distinct regime values, not a single constant.
    distinct = np.unique(np.round(bundle.vrp, 6))
    assert len(distinct) >= 2


def test_student_t_has_fatter_tails():
    cfg_g = SimConfig(n_paths=200_000, horizon_months=1, use_student_t=False, seed=1)
    cfg_t = SimConfig(n_paths=200_000, horizon_months=1, use_student_t=True,
                      t_dof=4, seed=1)
    regime = Regime("t", mu=0.0, sigma_realised=0.20, vrp=0.0)
    g = simulate_gbm_paths(regime, cfg_g).prices[:, -1]
    t = simulate_gbm_paths(regime, cfg_t).prices[:, -1]
    # Fatter tails => more extreme minimum log return.
    assert np.log(t).min() < np.log(g).min()
