"""Monte Carlo orchestration: paths -> strategy -> metrics, per regime.

This is the layer the CLI and dashboard call into. It wires the path
generators to the rolling covered-call writer and the metrics suite, and
provides convenience runners for the four regimes and for parameter sweeps.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from ..config import REGIMES, Regime, SimConfig
from ..models.paths import (
    PathBundle,
    simulate_gbm_paths,
    simulate_regime_paths,
)
from ..strategy import StrategyResult, roll_covered_call
from ..metrics import summarise


@dataclass
class RegimeRun:
    """Everything produced for one regime (or the blended cycle)."""

    label: str
    bundle: PathBundle
    result: StrategyResult
    metrics: dict


def run_regime(regime: Regime, cfg: SimConfig, rng=None) -> RegimeRun:
    """Simulate a single fixed regime end-to-end."""
    bundle = simulate_gbm_paths(regime, cfg, rng=rng)
    result = roll_covered_call(bundle, cfg)
    metrics = summarise(result, cfg.r)
    return RegimeRun(label=regime.name, bundle=bundle, result=result, metrics=metrics)


def run_blended(cfg: SimConfig, regimes: Dict[str, Regime] = None, rng=None) -> RegimeRun:
    """Simulate the Markov regime-switching "full cycle" case."""
    regimes = regimes or REGIMES
    bundle = simulate_regime_paths(regimes, cfg.switching, cfg, rng=rng)
    result = roll_covered_call(bundle, cfg)
    metrics = summarise(result, cfg.r)
    return RegimeRun(label="Full cycle (blended)", bundle=bundle, result=result,
                     metrics=metrics)


def run_all_regimes(
    cfg: SimConfig, regimes: Dict[str, Regime] = None
) -> Dict[str, RegimeRun]:
    """Run all three single regimes plus the blended cycle.

    Each regime gets its own independent RNG stream (derived from ``cfg.seed``)
    so results are reproducible and regimes don't share shocks.
    """
    regimes = regimes or REGIMES
    runs: Dict[str, RegimeRun] = {}
    seed_seq = np.random.SeedSequence(cfg.seed)
    children = seed_seq.spawn(len(regimes) + 1)

    for child, (key, regime) in zip(children, regimes.items()):
        rng = np.random.default_rng(child)
        runs[key] = run_regime(regime, cfg, rng=rng)

    rng = np.random.default_rng(children[-1])
    runs["blended"] = run_blended(cfg, regimes, rng=rng)
    return runs


def sweep(
    cfg: SimConfig,
    strike_offsets: List[float],
    coverages: List[float],
    regime_key: str = "blended",
    regimes: Dict[str, Regime] = None,
) -> "pandas.DataFrame":
    """Parameter sweep over strike offset x coverage ratio.

    Returns a tidy DataFrame (one row per (m, coverage) cell) with the headline
    asymmetry metrics, ready for the capture-ratio scatter plot.
    """
    import pandas as pd

    regimes = regimes or REGIMES
    rows = []
    base_seq = np.random.SeedSequence(cfg.seed)

    for i, m in enumerate(strike_offsets):
        for j, cov in enumerate(coverages):
            # Deterministic but distinct stream per cell.
            child = base_seq.spawn(1)[0]
            child = np.random.SeedSequence(
                entropy=child.entropy, spawn_key=(i, j)
            )
            rng = np.random.default_rng(child)
            cell_cfg = cfg.with_(m=m, coverage=cov)

            if regime_key == "blended":
                run = run_blended(cell_cfg, regimes, rng=rng)
            else:
                run = run_regime(regimes[regime_key], cell_cfg, rng=rng)

            cap = run.metrics["capture"]
            dist = run.metrics["distribution"]
            rows.append({
                "strike_offset": m,
                "coverage": cov,
                "upside_capture": cap["upside_capture"],
                "downside_capture": cap["downside_capture"],
                "cc_cagr": run.metrics["covered_call"]["mean_cagr"],
                "bh_cagr": run.metrics["buy_and_hold"]["mean_cagr"],
                "cc_vol": run.metrics["covered_call"]["mean_vol"],
                "cc_max_dd": run.metrics["covered_call"]["mean_max_drawdown"],
                "dist_yield": dist["avg_annual_dist_yield"],
                "yield_minus_total_return": dist["yield_minus_total_return"],
                "p_cc_beats_bh": run.metrics["p_cc_beats_bh"],
                "called_away_rate": run.metrics["called_away_rate"],
            })
    return pd.DataFrame(rows)
