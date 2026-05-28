"""Matplotlib charts: terminal-wealth fan charts, NAV-vs-total-return
decomposition, and the capture-ratio sweep scatter.

These run locally (not in the chat artifact renderer), so they write PNGs to
disk via :func:`save_all_regime_charts`.
"""

from __future__ import annotations

import os
from typing import Dict

import numpy as np

import matplotlib
matplotlib.use("Agg")  # headless: write files, never pop a window
import matplotlib.pyplot as plt

from ..sim.monte_carlo import RegimeRun


_PCTS = [5, 25, 50, 75, 95]


def _percentile_band(index: np.ndarray):
    """Return (months, dict-of-percentile-curves) for an index array (N, M+1)."""
    months = np.arange(index.shape[1])
    curves = {p: np.percentile(index, p, axis=0) for p in _PCTS}
    return months, curves


def fan_chart(run: RegimeRun, ax=None):
    """Percentile fan of terminal-wealth paths, covered call vs buy-and-hold."""
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 5.5))

    months, cc = _percentile_band(run.result.total_return_index)
    _, bh = _percentile_band(run.result.bh_index)

    ax.fill_between(months, cc[5], cc[95], color="tab:blue", alpha=0.15,
                    label="CC p5–p95")
    ax.fill_between(months, cc[25], cc[75], color="tab:blue", alpha=0.30,
                    label="CC p25–p75")
    ax.plot(months, cc[50], color="tab:blue", lw=2, label="CC median")

    ax.plot(months, bh[50], color="tab:orange", lw=2, ls="--", label="BH median")
    ax.plot(months, bh[5], color="tab:orange", lw=0.8, ls=":", alpha=0.7)
    ax.plot(months, bh[95], color="tab:orange", lw=0.8, ls=":", alpha=0.7)

    ax.set_title(f"Terminal-wealth fan — {run.label}")
    ax.set_xlabel("Month")
    ax.set_ylabel("Wealth index (start = 1.0)")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.3)
    return ax


def nav_decomposition_chart(run: RegimeRun, ax=None):
    """Median total return vs median NAV, with cumulative distributions — the
    NAV-erosion picture."""
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 5.5))

    res = run.result
    months = np.arange(res.nav_index.shape[1])

    tr = np.median(res.total_return_index, axis=0)
    nav = np.median(res.nav_index, axis=0)
    dist = np.median(res.cum_distributions, axis=0)

    ax.plot(months, tr, color="tab:green", lw=2, label="Total return (median)")
    ax.plot(months, nav, color="tab:red", lw=2, label="NAV (median)")
    ax.fill_between(months, nav, nav + dist, color="tab:blue", alpha=0.25,
                    label="Cumulative distributions")

    ax.axhline(1.0, color="grey", lw=0.8, ls=":")
    ax.set_title(f"NAV vs total-return decomposition — {run.label}")
    ax.set_xlabel("Month")
    ax.set_ylabel("Index (start = 1.0)")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.3)
    return ax


def capture_scatter(sweep_df, ax=None):
    """Upside vs downside capture across the strike × coverage sweep.

    Marker colour = coverage, marker size = strike offset. The ideal corner is
    top-left (high upside capture, low downside capture)."""
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 6))

    sizes = 40 + 1200 * sweep_df["strike_offset"]
    sc = ax.scatter(
        sweep_df["downside_capture"], sweep_df["upside_capture"],
        c=sweep_df["coverage"], s=sizes, cmap="viridis",
        edgecolor="k", linewidth=0.4, alpha=0.85,
    )
    ax.plot([0, 1.2], [0, 1.2], color="grey", ls=":", lw=0.8,
            label="symmetric capture")
    ax.set_xlabel("Downside capture (lower is better)")
    ax.set_ylabel("Upside capture (higher is better)")
    ax.set_title("Upside vs downside capture — strike × coverage sweep")
    cb = plt.colorbar(sc, ax=ax)
    cb.set_label("Coverage ratio")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    # Annotate that marker size encodes strike offset.
    ax.text(0.02, 0.02, "marker size ∝ strike offset (OTM %)",
            transform=ax.transAxes, fontsize=8, alpha=0.7)
    return ax


def save_all_regime_charts(runs: Dict[str, RegimeRun], outdir: str,
                           sweep_df=None) -> list:
    """Render and save fan + NAV-decomposition charts per regime (and the sweep
    scatter if provided). Returns the list of written file paths."""
    os.makedirs(outdir, exist_ok=True)
    written = []

    for key, run in runs.items():
        fig, axes = plt.subplots(1, 2, figsize=(16, 5.5))
        fan_chart(run, ax=axes[0])
        nav_decomposition_chart(run, ax=axes[1])
        fig.tight_layout()
        path = os.path.join(outdir, f"regime_{key}.png")
        fig.savefig(path, dpi=110)
        plt.close(fig)
        written.append(path)

    if sweep_df is not None and len(sweep_df):
        fig, ax = plt.subplots(figsize=(8, 6))
        capture_scatter(sweep_df, ax=ax)
        fig.tight_layout()
        path = os.path.join(outdir, "capture_sweep.png")
        fig.savefig(path, dpi=110)
        plt.close(fig)
        written.append(path)

    return written
