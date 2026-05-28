"""Metrics correctness on inputs with known answers."""

import numpy as np

from covered_call_sim.metrics import (
    cagr,
    annualised_vol,
    max_drawdown,
    capture_ratios,
)


def test_cagr_known():
    # Index doubling over exactly 1 year (12 monthly steps) -> 100% CAGR.
    index = np.linspace(1.0, 2.0, 13).reshape(1, -1)
    assert abs(float(cagr(index)[0]) - 1.0) < 1e-9


def test_max_drawdown_known():
    # Up to 2.0, down to 1.0 -> -50% drawdown.
    index = np.array([[1.0, 1.5, 2.0, 1.0, 1.2]])
    assert abs(float(max_drawdown(index)[0]) + 0.5) < 1e-12


def test_annualised_vol_scales():
    rng = np.random.default_rng(0)
    monthly = rng.normal(0, 0.05, size=(1, 100_000))
    vol = float(annualised_vol(monthly)[0])
    assert abs(vol - 0.05 * np.sqrt(12)) < 0.01


def test_capture_ratio_directions():
    # Covered call that keeps half the upside and all the downside:
    bh = np.array([[0.10, -0.10, 0.20, -0.05]])
    cc = np.array([[0.05, -0.10, 0.10, -0.05]])
    cap = capture_ratios(cc, bh)
    assert abs(cap["upside_capture"] - 0.5) < 1e-9
    assert abs(cap["downside_capture"] - 1.0) < 1e-9
