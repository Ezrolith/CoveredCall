"""Tabular summaries built from the metrics suite."""

from __future__ import annotations

from typing import Dict

import pandas as pd

from ..sim.monte_carlo import RegimeRun


def metrics_table(run: RegimeRun) -> pd.DataFrame:
    """Side-by-side covered-call vs buy-and-hold metrics for one regime."""
    m = run.metrics
    cc, bh = m["covered_call"], m["buy_and_hold"]

    rows = {
        "Mean CAGR": (cc["mean_cagr"], bh["mean_cagr"]),
        "CAGR p5": (cc["cagr_percentiles"]["p5"], bh["cagr_percentiles"]["p5"]),
        "CAGR p25": (cc["cagr_percentiles"]["p25"], bh["cagr_percentiles"]["p25"]),
        "CAGR p50": (cc["cagr_percentiles"]["p50"], bh["cagr_percentiles"]["p50"]),
        "CAGR p75": (cc["cagr_percentiles"]["p75"], bh["cagr_percentiles"]["p75"]),
        "CAGR p95": (cc["cagr_percentiles"]["p95"], bh["cagr_percentiles"]["p95"]),
        "Ann. vol": (cc["mean_vol"], bh["mean_vol"]),
        "Max drawdown": (cc["mean_max_drawdown"], bh["mean_max_drawdown"]),
        "Sharpe": (cc["mean_sharpe"], bh["mean_sharpe"]),
        "Sortino": (cc["mean_sortino"], bh["mean_sortino"]),
    }
    df = pd.DataFrame(rows, index=["Covered call", "Buy & hold"]).T

    # Append the asymmetry / fund-wrapper diagnostics (CC column only).
    cap, dist = m["capture"], m["distribution"]
    extra = {
        "Upside capture": cap["upside_capture"],
        "Downside capture": cap["downside_capture"],
        "Dist. yield (headline)": dist["avg_annual_dist_yield"],
        "NAV CAGR": dist["mean_nav_cagr"],
        "Yield − total return": dist["yield_minus_total_return"],
        "P(CC beats BH)": m["p_cc_beats_bh"],
        "Called-away rate": m["called_away_rate"],
    }
    for k, v in extra.items():
        df.loc[k] = [v, float("nan")]
    return df


def regime_comparison_table(runs: Dict[str, RegimeRun]) -> pd.DataFrame:
    """One row per regime, headline numbers — the at-a-glance summary."""
    rows = []
    for key, run in runs.items():
        m = run.metrics
        rows.append({
            "regime": run.label,
            "cc_cagr": m["covered_call"]["mean_cagr"],
            "bh_cagr": m["buy_and_hold"]["mean_cagr"],
            "cc_vol": m["covered_call"]["mean_vol"],
            "bh_vol": m["buy_and_hold"]["mean_vol"],
            "cc_max_dd": m["covered_call"]["mean_max_drawdown"],
            "bh_max_dd": m["buy_and_hold"]["mean_max_drawdown"],
            "cc_sharpe": m["covered_call"]["mean_sharpe"],
            "bh_sharpe": m["buy_and_hold"]["mean_sharpe"],
            "upside_capture": m["capture"]["upside_capture"],
            "downside_capture": m["capture"]["downside_capture"],
            "dist_yield": m["distribution"]["avg_annual_dist_yield"],
            "yield_minus_tr": m["distribution"]["yield_minus_total_return"],
            "p_cc_beats_bh": m["p_cc_beats_bh"],
        })
    return pd.DataFrame(rows).set_index("regime")
