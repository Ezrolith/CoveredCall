#!/usr/bin/env python3
"""Streamlit dashboard (Phase 6, stretch) for interactive parameter sweeps.

Run with::

    streamlit run dashboard.py

Sliders cover strike offset, coverage ratio, the regime-specific VRP, and the
number of paths. Charts and the metrics table update live. Streamlit is an
optional dependency — install it with ``pip install streamlit``.
"""

from __future__ import annotations

import numpy as np

try:
    import streamlit as st
except ImportError:  # pragma: no cover - optional dependency
    raise SystemExit("Streamlit not installed. Run: pip install streamlit")

import matplotlib.pyplot as plt

from covered_call_sim.config import DEFAULT_CONFIG, REGIMES, Regime
from covered_call_sim.sim.monte_carlo import run_regime, run_blended
from covered_call_sim.reporting import (
    metrics_table,
    fan_chart,
    nav_decomposition_chart,
)


st.set_page_config(page_title="Covered-Call Fund Simulator", layout="wide")
st.title("Covered-Call Fund Simulator")
st.caption("Capped upside, lightly-cushioned downside, and a thin VRP edge — "
           "made visible across market regimes.")

with st.sidebar:
    st.header("Parameters")
    regime_key = st.selectbox(
        "Regime", ["blended", "bull", "bear", "flat"], index=0,
        format_func=lambda k: {"blended": "Full cycle (blended)"}.get(
            k, REGIMES.get(k).name if k in REGIMES else k),
    )
    m = st.slider("Strike offset (OTM %)", 0.0, 0.05, DEFAULT_CONFIG.m, 0.005)
    coverage = st.slider("Coverage ratio", 0.0, 1.0, DEFAULT_CONFIG.coverage, 0.05)
    r = st.slider("Risk-free rate", 0.0, 0.08, DEFAULT_CONFIG.r, 0.005)
    horizon = st.slider("Horizon (months)", 12, 240, DEFAULT_CONFIG.horizon_months, 12)
    n_paths = st.select_slider("Paths", [1000, 2000, 5000, 10000], value=2000)
    fat_tails = st.checkbox("Fat tails (Student-t)", value=False)

    st.subheader("Volatility risk premium (vol points)")
    vrp_bull = st.slider("Bull VRP", 0.0, 0.10, REGIMES["bull"].vrp, 0.005)
    vrp_bear = st.slider("Bear VRP", 0.0, 0.10, REGIMES["bear"].vrp, 0.005)
    vrp_flat = st.slider("Flat VRP", 0.0, 0.10, REGIMES["flat"].vrp, 0.005)

cfg = DEFAULT_CONFIG.with_(
    r=r, m=m, coverage=coverage, horizon_months=horizon,
    n_paths=int(n_paths), use_student_t=fat_tails,
)

regimes = {
    "bull": Regime(REGIMES["bull"].name, REGIMES["bull"].mu,
                   REGIMES["bull"].sigma_realised, vrp_bull),
    "bear": Regime(REGIMES["bear"].name, REGIMES["bear"].mu,
                   REGIMES["bear"].sigma_realised, vrp_bear),
    "flat": Regime(REGIMES["flat"].name, REGIMES["flat"].mu,
                   REGIMES["flat"].sigma_realised, vrp_flat),
}

rng = np.random.default_rng(cfg.seed)
if regime_key == "blended":
    run = run_blended(cfg, regimes, rng=rng)
else:
    run = run_regime(regimes[regime_key], cfg, rng=rng)

# Headline metric cards.
m_ = run.metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("CC CAGR", f"{m_['covered_call']['mean_cagr']:.2%}",
          f"{m_['covered_call']['mean_cagr'] - m_['buy_and_hold']['mean_cagr']:+.2%} vs BH")
c2.metric("Headline dist. yield", f"{m_['distribution']['avg_annual_dist_yield']:.2%}")
c3.metric("Yield − total return", f"{m_['distribution']['yield_minus_total_return']:.2%}",
          help="How much of the 'yield' is just returned capital")
c4.metric("P(CC beats BH)", f"{m_['p_cc_beats_bh']:.1%}")

c5, c6, c7 = st.columns(3)
c5.metric("Upside capture", f"{m_['capture']['upside_capture']:.2f}")
c6.metric("Downside capture", f"{m_['capture']['downside_capture']:.2f}")
c7.metric("CC max drawdown", f"{m_['covered_call']['mean_max_drawdown']:.2%}",
          f"{m_['buy_and_hold']['mean_max_drawdown']:.2%} BH")

# Charts.
left, right = st.columns(2)
with left:
    fig1, ax1 = plt.subplots(figsize=(7, 4.5))
    fan_chart(run, ax=ax1)
    st.pyplot(fig1)
with right:
    fig2, ax2 = plt.subplots(figsize=(7, 4.5))
    nav_decomposition_chart(run, ax=ax2)
    st.pyplot(fig2)

st.subheader("Full metrics")
st.dataframe(metrics_table(run).style.format("{:.4f}", na_rep=""))
