"""All simulation parameters in one place.

Two volatilities matter and must never be conflated (see README §1.2):

* ``sigma_realised`` drives the actual simulated price path ``S1``.
* ``sigma_implied`` prices the option we sell, i.e. the premium ``c`` collected.

The structural edge of the strategy is the volatility risk premium (VRP),
modelled as ``sigma_implied = sigma_realised + vrp``.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Dict


# --------------------------------------------------------------------------- #
# Regime definition
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Regime:
    """A market regime expressed on the *realised* return process.

    Attributes
    ----------
    name:
        Human-readable label.
    mu:
        Annualised drift of the realised price process (real-world measure).
    sigma_realised:
        Annualised volatility of the realised price process.
    vrp:
        Volatility risk premium, in *vol points* (e.g. ``0.02`` == +2 points).
        ``sigma_implied = sigma_realised + vrp``.
    """

    name: str
    mu: float
    sigma_realised: float
    vrp: float

    @property
    def sigma_implied(self) -> float:
        """Implied vol used to price the sold call."""
        return self.sigma_realised + self.vrp


# Long-run-grounded defaults (see README §2). All configurable.
REGIMES: Dict[str, Regime] = {
    "bull": Regime(name="Trending bull", mu=0.13, sigma_realised=0.13, vrp=0.02),
    "bear": Regime(name="Bear", mu=-0.18, sigma_realised=0.28, vrp=0.05),
    "flat": Regime(name="Flat / choppy", mu=0.02, sigma_realised=0.18, vrp=0.03),
}


# --------------------------------------------------------------------------- #
# Markov regime-switching (for the "full cycle" blended case)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class RegimeSwitching:
    """Markov chain over the three single regimes for the blended cycle.

    ``transition`` is a row-stochastic matrix ordered as ``order``. Entry
    ``[i, j]`` is the monthly probability of moving from regime ``i`` to ``j``.

    The defaults imply persistent regimes (bull markets last ~years, bears are
    shorter and sharper) and are tuned so the long-run blended drift/vol land
    near a developed-world equity baseline (~7-9% nominal, ~15% vol).
    """

    order: tuple = ("bull", "bear", "flat")
    # rows: from {bull, bear, flat}; cols: to {bull, bear, flat}
    transition: tuple = (
        (0.94, 0.02, 0.04),  # from bull
        (0.10, 0.80, 0.10),  # from bear
        (0.08, 0.07, 0.85),  # from flat
    )
    initial: tuple = (0.6, 0.1, 0.3)  # start-of-sim regime probabilities


# --------------------------------------------------------------------------- #
# Global simulation configuration
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class SimConfig:
    """Top-level configuration for a Monte Carlo run."""

    # Market / contract parameters
    r: float = 0.045
    """Risk-free rate (annual). VERIFY against the current rate before running;
    this is the one input that drifts meaningfully over time."""

    q: float = 0.0
    """Continuous dividend yield on the underlying (annual)."""

    m: float = 0.0
    """Strike offset: ``K = S0 * (1 + m)``. 0 == at-the-money. Sweep 0 -> +0.05
    to expose the upside-cap trade-off."""

    coverage: float = 1.0
    """Fraction of the portfolio written against. 1.0 ~ QYLD-like, 0.5 ~
    JEPI-like."""

    # Horizon / sampling
    horizon_months: int = 120  # 10 years
    n_paths: int = 10_000
    dt: float = 1.0 / 12.0
    s0: float = 100.0
    seed: int = 12345

    # Path dynamics
    use_student_t: bool = False
    """If True, draw fat-tailed Student-t shocks instead of Gaussian."""
    t_dof: float = 5.0
    """Degrees of freedom for Student-t shocks (lower == fatter tails)."""

    # Regime switching
    switching: RegimeSwitching = field(default_factory=RegimeSwitching)

    def with_(self, **changes) -> "SimConfig":
        """Return a copy with the given fields replaced (handy for sweeps)."""
        return replace(self, **changes)


DEFAULT_CONFIG = SimConfig()

TRADING_MONTHS_PER_YEAR = 12
