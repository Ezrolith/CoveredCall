"""Black-Scholes-Merton pricing for European options.

All functions are vectorised over numpy arrays so they can price an entire
Monte Carlo cross-section (N paths) at once.

Conventions
-----------
* ``S`` spot, ``K`` strike, ``T`` time to expiry in *years*.
* ``r`` risk-free rate, ``q`` continuous dividend yield (both annual).
* ``sigma`` is the *implied* volatility used to price the option — this is the
  volatility risk premium lever, NOT the realised path volatility.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import norm


def _d1_d2(S, K, T, r, sigma, q=0.0):
    S = np.asarray(S, dtype=float)
    K = np.asarray(K, dtype=float)
    T = np.asarray(T, dtype=float)
    sigma = np.asarray(sigma, dtype=float)

    # Guard against degenerate inputs (T == 0 or sigma == 0) to avoid div-by-0.
    vol_sqrt_t = sigma * np.sqrt(T)
    with np.errstate(divide="ignore", invalid="ignore"):
        d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / vol_sqrt_t
        d2 = d1 - vol_sqrt_t
    return d1, d2, vol_sqrt_t


def bs_call(S, K, T, r, sigma, q=0.0):
    """European call price.

    At expiry (or zero vol) collapses to the discounted intrinsic value.
    """
    S = np.asarray(S, dtype=float)
    K = np.asarray(K, dtype=float)
    T = np.asarray(T, dtype=float)

    d1, d2, vol_sqrt_t = _d1_d2(S, K, T, r, sigma, q)
    price = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)

    # Degenerate cases: no time or no vol -> discounted intrinsic.
    intrinsic = np.maximum(S * np.exp(-q * T) - K * np.exp(-r * T), 0.0)
    degenerate = ~np.isfinite(vol_sqrt_t) | (vol_sqrt_t <= 0)
    price = np.where(degenerate, intrinsic, price)
    return price


def bs_put(S, K, T, r, sigma, q=0.0):
    """European put price (via put-call parity for consistency)."""
    S = np.asarray(S, dtype=float)
    K = np.asarray(K, dtype=float)
    T = np.asarray(T, dtype=float)
    call = bs_call(S, K, T, r, sigma, q)
    return call - S * np.exp(-q * T) + K * np.exp(-r * T)


def bs_call_delta(S, K, T, r, sigma, q=0.0):
    """Call delta, ``N(d1)`` adjusted for dividends. Used by delta-targeted
    strike selection (stretch goal)."""
    d1, _, vol_sqrt_t = _d1_d2(S, K, T, r, sigma, q)
    delta = np.exp(-q * np.asarray(T, dtype=float)) * norm.cdf(d1)
    # Degenerate: deep ITM -> 1, OTM -> 0.
    intrinsic_delta = (np.asarray(S) > np.asarray(K)).astype(float)
    degenerate = ~np.isfinite(vol_sqrt_t) | (vol_sqrt_t <= 0)
    return np.where(degenerate, intrinsic_delta, delta)
