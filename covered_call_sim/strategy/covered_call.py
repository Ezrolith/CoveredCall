"""Covered-call payoff, the rolling monthly writer, and the fund/NAV wrapper.

The single most important line in the whole project is the payoff::

    cc_value = min(S1, K) + c

Above the strike all gains are called away; the only compensation is the
premium ``c``. Everything downstream — NAV erosion, capped upside, the thin VRP
edge — falls out of this one truncation.

Fund wrapper (README §1.4)
--------------------------
The raw strategy and the *fund* are modelled separately:

* Each month the fund **distributes** the premium as income (the headline
  "yield").
* The fund's **NAV** therefore tracks the *price* outcome only:
  ``min(S1, K)`` compounded.
* **Total return = NAV change + reinvested distributions**.

Holding these apart is what exposes NAV erosion: in a choppy-but-rising market
the cap repeatedly truncates the recovery while premiums are paid out, so NAV
grinds down even while distributions look healthy.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..config import SimConfig
from ..models.paths import PathBundle
from ..pricing import bs_call


@dataclass
class SingleCycle:
    """Result of one monthly covered-call cycle (per unit of S0 invested)."""

    premium: np.ndarray       # c, the option premium collected
    strike: np.ndarray        # K
    cc_value: np.ndarray      # min(S1, K) + c  (terminal wealth per S0)
    price_value: np.ndarray   # min(S1, K)      (NAV component per S0, ex-premium)
    r_covered_call: np.ndarray
    r_buy_and_hold: np.ndarray
    called_away: np.ndarray   # bool mask: S1 > K (upside truncated)


def single_cycle(s0, s1, sigma_implied, cfg: SimConfig, m=None) -> SingleCycle:
    """One monthly covered-call cycle.

    Parameters
    ----------
    s0, s1:
        Start- and end-of-month prices (arrays or scalars).
    sigma_implied:
        Implied vol used to price the sold call (= realised + VRP).
    cfg:
        Global config (supplies ``r``, ``q``, ``m``, ``dt``).
    m:
        Optional strike offset override; defaults to ``cfg.m``.
    """
    s0 = np.asarray(s0, dtype=float)
    s1 = np.asarray(s1, dtype=float)
    m = cfg.m if m is None else m

    K = s0 * (1.0 + m)
    c = bs_call(s0, K, cfg.dt, cfg.r, sigma_implied, cfg.q)

    capped = np.minimum(s1, K)
    cc_value = capped + c

    return SingleCycle(
        premium=c,
        strike=K,
        cc_value=cc_value,
        price_value=capped,
        r_covered_call=cc_value / s0 - 1.0,
        r_buy_and_hold=s1 / s0 - 1.0,
        called_away=s1 > K,
    )


@dataclass
class StrategyResult:
    """Rolled monthly results across all paths.

    Index arrays start at 1.0 (column 0) and have shape (N, M + 1). Per-step
    arrays have shape (N, M).
    """

    # Wealth indices (reinvested), normalised to 1.0 at t=0
    total_return_index: np.ndarray   # covered-call total return (NAV + dists)
    nav_index: np.ndarray            # covered-call NAV only (price component)
    bh_index: np.ndarray             # buy-and-hold underlying

    # Per-step series
    cc_returns: np.ndarray           # monthly covered-call total return
    bh_returns: np.ndarray           # monthly buy-and-hold return
    income: np.ndarray               # monthly distribution yield (per unit NAV)
    premium: np.ndarray              # raw option premium c (per unit S0)
    called_away: np.ndarray          # bool: upside truncated that month

    # Distribution accounting
    distributions_cash: np.ndarray   # cash distributed each month (per unit start NAV)
    cum_distributions: np.ndarray    # cumulative distributed cash, shape (N, M + 1)

    cfg: SimConfig | None = None

    @property
    def terminal_cc(self) -> np.ndarray:
        return self.total_return_index[:, -1]

    @property
    def terminal_bh(self) -> np.ndarray:
        return self.bh_index[:, -1]


def roll_covered_call(bundle: PathBundle, cfg: SimConfig) -> StrategyResult:
    """Roll the monthly covered-call cycle over the full horizon.

    Applies the ``coverage`` ratio: a fraction ``w`` of the book is written
    (covered call), the remaining ``1 - w`` simply holds the underlying. This
    spans QYLD-like (w=1) to JEPI-like (w~0.5) profiles.
    """
    prices = bundle.prices
    n, m_plus_1 = prices.shape
    m = m_plus_1 - 1
    w = cfg.coverage

    s0 = prices[:, :-1]            # (N, M) start-of-month
    s1 = prices[:, 1:]             # (N, M) end-of-month
    sigma_implied = bundle.sigma_implied  # (N, M)

    K = s0 * (1.0 + cfg.m)
    c = bs_call(s0, K, cfg.dt, cfg.r, sigma_implied, cfg.q)
    capped = np.minimum(s1, K)

    # Per-unit-of-S0 monthly factors, blended by coverage ratio.
    bh_gross = s1 / s0                                   # buy-and-hold growth
    cc_price_gross = w * (capped / s0) + (1 - w) * bh_gross   # NAV growth factor
    income = w * (c / s0)                                # distributed yield
    cc_total_gross = cc_price_gross + income             # total return factor

    bh_returns = bh_gross - 1.0
    cc_returns = cc_total_gross - 1.0

    # Build reinvested wealth indices.
    nav_index = _to_index(cc_price_gross)
    total_return_index = _to_index(cc_total_gross)
    bh_index = _to_index(bh_gross)

    # Cash distributions: income earned on the NAV held at the start of each
    # month. NAV at start of month t is nav_index[:, t].
    distributions_cash = income * nav_index[:, :-1]
    cum_distributions = np.concatenate(
        [np.zeros((n, 1)), np.cumsum(distributions_cash, axis=1)], axis=1
    )

    return StrategyResult(
        total_return_index=total_return_index,
        nav_index=nav_index,
        bh_index=bh_index,
        cc_returns=cc_returns,
        bh_returns=bh_returns,
        income=income,
        premium=c,
        called_away=s1 > K,
        distributions_cash=distributions_cash,
        cum_distributions=cum_distributions,
        cfg=cfg,
    )


def _to_index(gross_factors: np.ndarray) -> np.ndarray:
    """Turn per-step gross-return factors (N, M) into a wealth index (N, M+1)
    starting at 1.0."""
    n = gross_factors.shape[0]
    idx = np.empty((n, gross_factors.shape[1] + 1), dtype=float)
    idx[:, 0] = 1.0
    idx[:, 1:] = np.cumprod(gross_factors, axis=1)
    return idx
