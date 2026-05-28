"""Price-path generators.

Baseline is geometric Brownian motion (GBM) per monthly step. Stretch dynamics
add fat-tailed (Student-t) shocks and a Markov regime-switching process for the
realistic "full cycle" blended case.

Every generator returns a :class:`PathBundle` carrying not just the price path
but the *per-step* realised volatility and VRP, so the strategy layer can price
each month's option with the correct implied vol
(``sigma_implied = sigma_realised + vrp``).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..config import Regime, RegimeSwitching, SimConfig


@dataclass
class PathBundle:
    """Container for a simulated cross-section of paths.

    Shapes (``N`` paths, ``M`` months):

    * ``prices``           -> (N, M + 1), column 0 is ``s0``.
    * ``sigma_realised``   -> (N, M), realised annual vol used each step.
    * ``vrp``              -> (N, M), vol-risk-premium applied each step.
    * ``regime_idx``       -> (N, M) or None, regime active each step.
    """

    prices: np.ndarray
    sigma_realised: np.ndarray
    vrp: np.ndarray
    regime_idx: np.ndarray | None = None

    @property
    def sigma_implied(self) -> np.ndarray:
        return self.sigma_realised + self.vrp


def _draw_shocks(rng, shape, cfg: SimConfig) -> np.ndarray:
    """Unit-variance shocks: standard normal, or standardised Student-t."""
    if cfg.use_student_t:
        v = cfg.t_dof
        if v <= 2:
            raise ValueError("t_dof must be > 2 for finite variance")
        raw = rng.standard_t(v, size=shape)
        return raw * np.sqrt((v - 2.0) / v)  # rescale to unit variance
    return rng.standard_normal(size=shape)


def gbm_step(s0, mu, sigma, dt, z):
    """Single GBM step. Vectorised over arrays.

    ``S1 = S0 * exp((mu - 0.5 sigma^2) dt + sigma sqrt(dt) Z)``
    """
    s0 = np.asarray(s0, dtype=float)
    return s0 * np.exp((mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * z)


def simulate_gbm_paths(regime: Regime, cfg: SimConfig, rng=None) -> PathBundle:
    """Simulate ``cfg.n_paths`` GBM paths under a single fixed regime."""
    rng = rng if rng is not None else np.random.default_rng(cfg.seed)
    n, m, dt = cfg.n_paths, cfg.horizon_months, cfg.dt

    z = _draw_shocks(rng, (n, m), cfg)
    log_increments = (regime.mu - 0.5 * regime.sigma_realised**2) * dt + \
        regime.sigma_realised * np.sqrt(dt) * z

    prices = np.empty((n, m + 1), dtype=float)
    prices[:, 0] = cfg.s0
    prices[:, 1:] = cfg.s0 * np.exp(np.cumsum(log_increments, axis=1))

    sigma = np.full((n, m), regime.sigma_realised)
    vrp = np.full((n, m), regime.vrp)
    return PathBundle(prices=prices, sigma_realised=sigma, vrp=vrp)


def sample_markov_regimes(
    switching: RegimeSwitching, n_paths: int, n_months: int, rng
) -> np.ndarray:
    """Sample a regime index per path per month from the Markov chain.

    Returns an int array (n_paths, n_months) of indices into
    ``switching.order``.
    """
    P = np.asarray(switching.transition, dtype=float)
    n_states = P.shape[0]
    if P.shape != (n_states, n_states):
        raise ValueError("transition matrix must be square")
    if not np.allclose(P.sum(axis=1), 1.0):
        raise ValueError("transition matrix rows must sum to 1")

    # Pre-compute cumulative distributions for fast inverse-CDF sampling.
    cum_P = np.cumsum(P, axis=1)
    cum_init = np.cumsum(np.asarray(switching.initial, dtype=float))

    idx = np.empty((n_paths, n_months), dtype=np.int64)
    u0 = rng.random(n_paths)
    state = np.searchsorted(cum_init, u0, side="right")
    state = np.clip(state, 0, n_states - 1)

    u = rng.random((n_paths, n_months))
    for t in range(n_months):
        idx[:, t] = state
        # next state via inverse CDF of the row for the current state
        rows = cum_P[state]  # (n_paths, n_states)
        state = (u[:, t][:, None] > rows).sum(axis=1)
        state = np.clip(state, 0, n_states - 1)
    return idx


def simulate_regime_paths(
    regimes: dict, switching: RegimeSwitching, cfg: SimConfig, rng=None
) -> PathBundle:
    """Simulate paths with Markov regime switching (the blended "full cycle").

    Each month, every path draws its mu/sigma/VRP from whichever regime is
    currently active. Bear tails get both higher realised vol *and* a fatter
    VRP, reproducing the VIX-style premium spike when markets are scary.
    """
    rng = rng if rng is not None else np.random.default_rng(cfg.seed)
    n, m, dt = cfg.n_paths, cfg.horizon_months, cfg.dt

    regime_idx = sample_markov_regimes(switching, n, m, rng)

    # Map regime index -> parameter arrays.
    order = switching.order
    mu_by_state = np.array([regimes[name].mu for name in order])
    sig_by_state = np.array([regimes[name].sigma_realised for name in order])
    vrp_by_state = np.array([regimes[name].vrp for name in order])

    mu_step = mu_by_state[regime_idx]
    sigma_step = sig_by_state[regime_idx]
    vrp_step = vrp_by_state[regime_idx]

    z = _draw_shocks(rng, (n, m), cfg)
    log_increments = (mu_step - 0.5 * sigma_step**2) * dt + \
        sigma_step * np.sqrt(dt) * z

    prices = np.empty((n, m + 1), dtype=float)
    prices[:, 0] = cfg.s0
    prices[:, 1:] = cfg.s0 * np.exp(np.cumsum(log_increments, axis=1))

    return PathBundle(
        prices=prices,
        sigma_realised=sigma_step,
        vrp=vrp_step,
        regime_idx=regime_idx,
    )
