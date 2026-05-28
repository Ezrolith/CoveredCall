"""BS pricer must match known reference values for vanilla options."""

import numpy as np

from covered_call_sim.pricing import bs_call, bs_put, bs_call_delta


def test_atm_reference_value():
    # Classic textbook case: S=K=100, T=1, r=5%, sigma=20%, q=0.
    # Reference call price ~ 10.4506.
    c = bs_call(100, 100, 1.0, 0.05, 0.20, 0.0)
    assert abs(float(c) - 10.4506) < 1e-3


def test_put_reference_value():
    # Same parameters; reference put ~ 5.5735.
    p = bs_put(100, 100, 1.0, 0.05, 0.20, 0.0)
    assert abs(float(p) - 5.5735) < 1e-3


def test_put_call_parity():
    S, K, T, r, sigma = 100.0, 110.0, 0.5, 0.03, 0.25
    c = bs_call(S, K, T, r, sigma)
    p = bs_put(S, K, T, r, sigma)
    # c - p = S - K e^{-rT}
    assert abs(float(c - p) - (S - K * np.exp(-r * T))) < 1e-9


def test_deep_itm_and_otm():
    # Deep ITM call ~ S - K e^{-rT}; deep OTM ~ 0.
    itm = bs_call(200, 100, 1.0, 0.05, 0.20)
    assert abs(float(itm) - (200 - 100 * np.exp(-0.05))) < 0.5
    otm = bs_call(50, 100, 1.0, 0.05, 0.20)
    assert float(otm) < 0.5


def test_zero_time_collapses_to_intrinsic():
    assert abs(float(bs_call(120, 100, 0.0, 0.05, 0.2)) - 20.0) < 1e-9
    assert float(bs_call(80, 100, 0.0, 0.05, 0.2)) == 0.0


def test_delta_bounds():
    d = bs_call_delta(np.array([50.0, 100.0, 200.0]), 100, 1.0, 0.05, 0.2)
    assert np.all((d >= 0) & (d <= 1))
    assert d[2] > d[1] > d[0]


def test_vectorised():
    S = np.array([90.0, 100.0, 110.0])
    c = bs_call(S, 100, 0.25, 0.04, 0.2)
    assert c.shape == (3,)
    assert np.all(np.diff(c) > 0)  # call increasing in spot
