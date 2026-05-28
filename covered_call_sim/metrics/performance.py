"""Performance & risk metrics, computed across Monte Carlo paths.

All functions accept index arrays of shape (N, M+1) or monthly-return arrays
of shape (N, M) as noted. Capture ratios and the "yield vs total return" gap
are the cleanest expressions of the covered-call asymmetry, so they get first-
class treatment here.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict

import numpy as np

from ..config import TRADING_MONTHS_PER_YEAR as MPY


def cagr(index: np.ndarray, periods_per_year: int = MPY) -> np.ndarray:
    """Per-path compound annual growth rate from a wealth index (N, M+1)."""
    n_periods = index.shape[1] - 1
    years = n_periods / periods_per_year
    terminal = index[:, -1] / index[:, 0]
    return terminal ** (1.0 / years) - 1.0


def annualised_vol(returns: np.ndarray, periods_per_year: int = MPY) -> np.ndarray:
    """Per-path annualised volatility from monthly returns (N, M)."""
    return returns.std(axis=1, ddof=1) * np.sqrt(periods_per_year)


def max_drawdown(index: np.ndarray) -> np.ndarray:
    """Per-path maximum drawdown (a negative number) from an index (N, M+1)."""
    running_max = np.maximum.accumulate(index, axis=1)
    drawdown = index / running_max - 1.0
    return drawdown.min(axis=1)


def sharpe(returns: np.ndarray, r: float, periods_per_year: int = MPY) -> np.ndarray:
    """Per-path annualised Sharpe ratio from monthly returns (N, M)."""
    rf_monthly = (1.0 + r) ** (1.0 / periods_per_year) - 1.0
    excess = returns - rf_monthly
    mean = excess.mean(axis=1) * periods_per_year
    vol = returns.std(axis=1, ddof=1) * np.sqrt(periods_per_year)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(vol > 0, mean / vol, np.nan)
    return out


def sortino(returns: np.ndarray, r: float, periods_per_year: int = MPY) -> np.ndarray:
    """Per-path annualised Sortino ratio (downside deviation only)."""
    rf_monthly = (1.0 + r) ** (1.0 / periods_per_year) - 1.0
    excess = returns - rf_monthly
    mean = excess.mean(axis=1) * periods_per_year
    downside = np.minimum(excess, 0.0)
    dd = np.sqrt((downside**2).mean(axis=1)) * np.sqrt(periods_per_year)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(dd > 0, mean / dd, np.nan)
    return out


def capture_ratios(cc_returns: np.ndarray, bh_returns: np.ndarray) -> Dict[str, float]:
    """Upside / downside capture of the covered call versus the underlying.

    Capture is pooled across all path-months (a robust Monte Carlo estimate):

    * upside capture   = mean(CC return | BH up)   / mean(BH return | BH up)
    * downside capture = mean(CC return | BH down) / mean(BH return | BH down)

    Ideal asymmetry is *low* downside capture with *high* upside capture; the
    covered call structurally does the opposite (caps upside, only lightly
    cushions downside), which these two numbers make explicit.
    """
    cc = cc_returns.ravel()
    bh = bh_returns.ravel()

    up = bh > 0
    down = bh < 0

    def _ratio(mask):
        denom = bh[mask].mean()
        if denom == 0 or mask.sum() == 0:
            return float("nan")
        return float(cc[mask].mean() / denom)

    return {
        "upside_capture": _ratio(up),
        "downside_capture": _ratio(down),
    }


def distribution_yield(result, periods_per_year: int = MPY) -> Dict[str, float]:
    """Headline distribution yield vs total return — quantifies how much of the
    "yield" is just returned capital.

    * ``avg_annual_dist_yield``: mean monthly distribution / NAV, annualised.
      This is the number a fund factsheet would advertise.
    * ``mean_cc_cagr``: mean total-return CAGR across paths.
    * ``yield_minus_total_return``: the gap. A large positive gap means the
      headline yield substantially overstates what investors actually earned —
      capital was handed back as "income".
    """
    income = result.income  # (N, M) per-unit-NAV monthly yield
    avg_monthly_yield = income.mean()
    avg_annual_yield = avg_monthly_yield * periods_per_year

    cc_cagr = cagr(result.total_return_index, periods_per_year)
    nav_cagr = cagr(result.nav_index, periods_per_year)

    return {
        "avg_annual_dist_yield": float(avg_annual_yield),
        "mean_total_return_cagr": float(np.nanmean(cc_cagr)),
        "mean_nav_cagr": float(np.nanmean(nav_cagr)),
        "yield_minus_total_return": float(avg_annual_yield - np.nanmean(cc_cagr)),
    }


def prob_cc_beats_bh(result) -> float:
    """Fraction of paths where covered-call terminal total wealth exceeds
    buy-and-hold."""
    return float((result.terminal_cc > result.terminal_bh).mean())


def percentiles(values: np.ndarray, ps=(5, 25, 50, 75, 95)) -> Dict[str, float]:
    """Named percentiles of a 1-D array."""
    vals = np.asarray(values, dtype=float)
    vals = vals[np.isfinite(vals)]
    qs = np.percentile(vals, ps)
    return {f"p{p}": float(q) for p, q in zip(ps, qs)}


@dataclass
class LegSummary:
    """Summary metrics for one leg (covered call or buy-and-hold)."""

    mean_cagr: float
    cagr_percentiles: Dict[str, float]
    mean_vol: float
    mean_max_drawdown: float
    mean_sharpe: float
    mean_sortino: float

    def to_dict(self) -> dict:
        return asdict(self)


def _leg_summary(index, returns, r) -> LegSummary:
    cg = cagr(index)
    return LegSummary(
        mean_cagr=float(np.nanmean(cg)),
        cagr_percentiles=percentiles(cg),
        mean_vol=float(np.nanmean(annualised_vol(returns))),
        mean_max_drawdown=float(np.nanmean(max_drawdown(index))),
        mean_sharpe=float(np.nanmean(sharpe(returns, r))),
        mean_sortino=float(np.nanmean(sortino(returns, r))),
    )


def summarise(result, r: float) -> dict:
    """Full metrics suite for a :class:`StrategyResult`."""
    cc = _leg_summary(result.total_return_index, result.cc_returns, r)
    bh = _leg_summary(result.bh_index, result.bh_returns, r)
    return {
        "covered_call": cc.to_dict(),
        "buy_and_hold": bh.to_dict(),
        "capture": capture_ratios(result.cc_returns, result.bh_returns),
        "distribution": distribution_yield(result),
        "p_cc_beats_bh": prob_cc_beats_bh(result),
        "called_away_rate": float(result.called_away.mean()),
    }
