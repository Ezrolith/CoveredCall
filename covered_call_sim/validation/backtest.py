"""Real-data validation (README §4.4 / Phase 5).

Pull covered-call funds (QYLD, JEPI) and their underlyings (QQQ, SPY) via
yfinance and compare total-return and drawdown behaviour to the simulation's
qualitative predictions. The sim need not match exactly; the *shape* should
reproduce:

* a lag in trending bull markets,
* a cushion-but-still-falls profile in bears,
* NAV erosion in choppy markets (price return << total return).

Network access is required only for this phase. Functions degrade gracefully
(raise a clear error) if yfinance is offline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


# (covered-call fund, its underlying) pairs to compare.
DEFAULT_PAIRS: List[Tuple[str, str]] = [
    ("QYLD", "QQQ"),   # QYLD writes ATM calls on the Nasdaq-100 (~100% coverage)
    ("JEPI", "SPY"),   # JEPI writes OTM calls on ~part of an S&P-ish book
]


def fetch_total_return(ticker: str, start: str = "2014-01-01",
                       end: str = None) -> pd.Series:
    """Monthly total-return index (dividends reinvested) for ``ticker``.

    Uses yfinance ``auto_adjust=True`` adjusted closes, which fold dividends
    back in — so this is a *total return* series, the right thing to compare a
    distribution-paying covered-call fund against.
    """
    import yfinance as yf

    data = yf.download(ticker, start=start, end=end, auto_adjust=True,
                       progress=False)
    if data is None or len(data) == 0:
        raise RuntimeError(f"No data returned for {ticker} (network/offline?)")
    close = data["Close"]
    if isinstance(close, pd.DataFrame):  # yfinance sometimes returns a frame
        close = close.iloc[:, 0]
    monthly = close.resample("ME").last().dropna()
    return monthly / monthly.iloc[0]


def _max_drawdown(index: pd.Series) -> float:
    running_max = index.cummax()
    return float((index / running_max - 1.0).min())


def _cagr(index: pd.Series) -> float:
    years = (index.index[-1] - index.index[0]).days / 365.25
    if years <= 0:
        return float("nan")
    return float((index.iloc[-1] / index.iloc[0]) ** (1 / years) - 1)


@dataclass
class BacktestResult:
    fund: str
    underlying: str
    metrics: pd.DataFrame  # rows: fund/underlying, cols: cagr/vol/maxdd
    aligned: pd.DataFrame  # aligned total-return indices

    @property
    def lag_in_bull(self) -> bool:
        """Did the covered-call fund trail its underlying over the full sample
        (the bull-market lag the sim predicts)?"""
        return self.metrics.loc[self.fund, "cagr"] < \
            self.metrics.loc[self.underlying, "cagr"]

    @property
    def lower_drawdown(self) -> bool:
        """Did the fund cushion drawdowns relative to the underlying?"""
        return self.metrics.loc[self.fund, "max_drawdown"] > \
            self.metrics.loc[self.underlying, "max_drawdown"]


def backtest_pair(fund: str, underlying: str, start: str = "2014-01-01",
                  end: str = None) -> BacktestResult:
    """Fetch and compare one (fund, underlying) pair."""
    f = fetch_total_return(fund, start, end)
    u = fetch_total_return(underlying, start, end)
    aligned = pd.concat([f.rename(fund), u.rename(underlying)], axis=1).dropna()
    # Re-base both to 1.0 at the common start so total returns are comparable.
    aligned = aligned / aligned.iloc[0]

    rets = aligned.pct_change().dropna()
    rows = {}
    for col in aligned.columns:
        rows[col] = {
            "cagr": _cagr(aligned[col]),
            "ann_vol": float(rets[col].std() * np.sqrt(12)),
            "max_drawdown": _max_drawdown(aligned[col]),
        }
    metrics = pd.DataFrame(rows).T[["cagr", "ann_vol", "max_drawdown"]]
    return BacktestResult(fund=fund, underlying=underlying, metrics=metrics,
                          aligned=aligned)


def run_backtests(pairs: List[Tuple[str, str]] = None, start: str = "2014-01-01",
                  end: str = None) -> Dict[str, BacktestResult]:
    """Run all configured pairs. Pairs that fail (e.g. offline) are skipped with
    a warning rather than aborting the whole run."""
    pairs = pairs or DEFAULT_PAIRS
    results: Dict[str, BacktestResult] = {}
    for fund, underlying in pairs:
        try:
            results[fund] = backtest_pair(fund, underlying, start, end)
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(f"[validation] skipped {fund}/{underlying}: {exc}")
    return results
