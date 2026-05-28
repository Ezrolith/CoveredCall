#!/usr/bin/env python3
"""Covered-call fund simulator — command-line entry point.

Examples
--------
Run all regimes with defaults, print tables, save charts to ./output::

    python run.py

A quick smoke run (fewer paths) and a strike × coverage sweep::

    python run.py --paths 2000 --sweep

Verify the risk-free rate first, fatten the tails, and run the real-data
backtest too::

    python run.py --rate 0.05 --fat-tails --backtest
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from covered_call_sim.config import DEFAULT_CONFIG, SimConfig
from covered_call_sim.sim.monte_carlo import run_all_regimes, sweep
from covered_call_sim.reporting import (
    metrics_table,
    regime_comparison_table,
    save_all_regime_charts,
)


def _fmt(df: pd.DataFrame) -> str:
    return df.to_string(float_format=lambda x: f"{x:,.4f}")


def build_config(args) -> SimConfig:
    return DEFAULT_CONFIG.with_(
        r=args.rate,
        m=args.strike_offset,
        coverage=args.coverage,
        horizon_months=args.horizon,
        n_paths=args.paths,
        seed=args.seed,
        use_student_t=args.fat_tails,
    )


def main():
    parser = argparse.ArgumentParser(description="Covered-call fund simulator")
    parser.add_argument("--rate", type=float, default=DEFAULT_CONFIG.r,
                        help="Risk-free rate (VERIFY against current rate!)")
    parser.add_argument("--strike-offset", type=float, default=DEFAULT_CONFIG.m,
                        help="OTM strike offset m (0 = ATM)")
    parser.add_argument("--coverage", type=float, default=DEFAULT_CONFIG.coverage,
                        help="Fraction of book written (1.0 ~ QYLD, 0.5 ~ JEPI)")
    parser.add_argument("--horizon", type=int,
                        default=DEFAULT_CONFIG.horizon_months,
                        help="Horizon in months")
    parser.add_argument("--paths", type=int, default=DEFAULT_CONFIG.n_paths,
                        help="Number of Monte Carlo paths")
    parser.add_argument("--seed", type=int, default=DEFAULT_CONFIG.seed)
    parser.add_argument("--fat-tails", action="store_true",
                        help="Use Student-t shocks instead of Gaussian")
    parser.add_argument("--sweep", action="store_true",
                        help="Run the strike x coverage parameter sweep")
    parser.add_argument("--backtest", action="store_true",
                        help="Run the yfinance real-data validation (needs net)")
    parser.add_argument("--outdir", default="output",
                        help="Directory for chart PNGs")
    parser.add_argument("--no-charts", action="store_true",
                        help="Skip rendering charts")
    args = parser.parse_args()

    cfg = build_config(args)

    print("=" * 78)
    print("COVERED-CALL FUND SIMULATOR")
    print("=" * 78)
    print(f"  paths={cfg.n_paths:,}  horizon={cfg.horizon_months}m  "
          f"r={cfg.r:.3%}  strike_offset={cfg.m:.2%}  coverage={cfg.coverage:.0%}"
          f"  fat_tails={cfg.use_student_t}")
    print()

    runs = run_all_regimes(cfg)

    print("REGIME COMPARISON (means across paths)")
    print("-" * 78)
    print(_fmt(regime_comparison_table(runs)))
    print()

    for key, run in runs.items():
        print(f"\n### {run.label} ###")
        print(_fmt(metrics_table(run)))

    sweep_df = None
    if args.sweep:
        print("\n" + "=" * 78)
        print("PARAMETER SWEEP (blended cycle): strike offset x coverage")
        print("-" * 78)
        sweep_df = sweep(
            cfg,
            strike_offsets=[0.0, 0.02, 0.05],
            coverages=[0.5, 1.0],
        )
        print(_fmt(sweep_df.set_index(["strike_offset", "coverage"])))

    if not args.no_charts:
        written = save_all_regime_charts(runs, args.outdir, sweep_df=sweep_df)
        print(f"\nCharts written: {written}")

    if args.backtest:
        from covered_call_sim.validation import run_backtests
        print("\n" + "=" * 78)
        print("REAL-DATA VALIDATION (yfinance)")
        print("-" * 78)
        results = run_backtests()
        for fund, res in results.items():
            print(f"\n{fund} vs {res.underlying}")
            print(_fmt(res.metrics))
            print(f"  lag in bull (CC trails underlying): {res.lag_in_bull}")
            print(f"  cushioned drawdown:                 {res.lower_drawdown}")

    print("\nDone.")


if __name__ == "__main__":
    main()
