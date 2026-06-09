# Covered Call Fund Simulator

> **Also in this repo:** [`address_change/`](address_change/README.md) — a
> zero-dependency web app that tracks everything you need to update when
> moving home (banks, government, utilities, subscriptions, …).
> Run it with `python address_change/app.py`.

A Monte Carlo engine that simulates how a **covered call (buy-write)** strategy
behaves versus simply **holding the underlying**, across realistic market
regimes (trending bull, bear, flat/choppy, and a blended full cycle).

The goal is to make the strategy's true risk/return **asymmetry** visible:
capped upside, lightly-cushioned downside, and a thin volatility-risk-premium
edge that survives or dies depending on regime.

> **The one question this answers:** after the cap and across a realistic regime
> mix, does the covered-call wrapper deliver better risk-adjusted outcomes than
> holding the underlying — or is the headline yield mostly a repackaging of
> capped capital returns?

---

## Quick start

```bash
pip install -r requirements.txt

# Run all four regimes, print tables, save charts to ./output
python run.py

# Faster smoke run + strike × coverage sweep
python run.py --paths 2000 --sweep

# Verify the risk-free rate first, fatten the tails, add the real-data backtest
python run.py --rate 0.05 --fat-tails --backtest

# Interactive dashboard (optional; needs `pip install streamlit`)
streamlit run dashboard.py

# Validation / sanity test suite
pytest -q
```

> ⚠️ **Verify the risk-free rate (`--rate`) before running.** It is the one
> input that drifts meaningfully over time; the default is `4.5%`.

---

## The financial model

### Single monthly cycle

Each month the fund holds the underlying and writes one 1-month call against it.

- Start-of-month price `S0`; strike `K = S0 * (1 + m)` (`m` is the OTM offset,
  `m = 0` ⇒ at-the-money).
- Premium received `c = BlackScholesCall(S0, K, T=1/12, r, sigma_implied)`.
- End-of-month price `S1` drawn from the **realised** return process.

```
cc_value       = min(S1, K) + c
r_covered_call = (min(S1, K) + c) / S0 - 1
r_buy_and_hold = S1 / S0 - 1
```

The `min(S1, K)` truncation is the entire story: above the strike all gains are
called away; the only compensation is the premium `c`.

### Two volatilities (the crux of the edge)

These must never be conflated:

- **`sigma_realised`** drives the actual simulated price path `S1`.
- **`sigma_implied`** prices the option you *sell* (how much premium you collect).

The structural edge is the **volatility risk premium (VRP)**:

```
sigma_implied = sigma_realised + VRP_regime
```

VRP is regime-dependent — in bears, implied vol spikes (VIX-style), so the fund
collects fatter premiums exactly when markets are scary.

**No-free-lunch check:** set `VRP = 0`, `m = 0` and the covered call must
*underperform* buy-and-hold in expectation (a fairly-priced premium is no
compensation for giving up the upside). This is enforced in
`tests/test_no_free_lunch.py`.

### Price-path generation

Geometric Brownian motion per monthly step:

```
S1 = S0 * exp((mu - 0.5 * sigma_realised^2) * dt + sigma_realised * sqrt(dt) * Z)
dt = 1/12,  Z ~ N(0,1)   (or standardised Student-t with --fat-tails)
```

The blended "full cycle" replaces a single regime with a **Markov
regime-switching** process over {bull, bear, flat}.

### Fund wrapper: NAV vs distributions

The raw strategy and the *fund* are modelled separately:

- Each month the fund **distributes** the premium `c` as income (headline "yield").
- The fund's **NAV** tracks the *price* outcome only — `min(S1, K)` compounded.
- **Total return = NAV change + reinvested distributions.**

This separation exposes **NAV erosion**: in a choppy-but-rising market the cap
repeatedly truncates the recovery while premiums are paid out, so NAV grinds
down even as distributions look healthy. The reports place headline distribution
yield *next to* total return so the gap is explicit.

The **coverage ratio** blends a written fraction `w` with a buy-and-hold
remainder, spanning QYLD-like (`w=1`) to JEPI-like (`w≈0.5`) profiles.

---

## Regimes & default parameters

| Regime | mu (ann.) | sigma_realised | VRP | Notes |
|--------|-----------|----------------|-----|-------|
| Trending bull | +13% | 13% | +2 pts | Calls constantly called away; strategy lags worst |
| Bear | −18% | 28% | +5 pts | High premiums partly cushion; cap irrelevant |
| Flat / choppy | +2% | 18% | +3 pts | Strategy's best relative environment |
| Full cycle | Markov-switching | — | — | The realistic case |

All parameters live in [`covered_call_sim/config.py`](covered_call_sim/config.py)
and are configurable. Globals: `r=4.5%`, `m=0%` (ATM), coverage `100%`, horizon
`120 months`, `N=10,000` paths.

---

## Outputs & metrics

Per regime (and blended), covered call vs buy-and-hold:

- CAGR / total return with full percentile distribution (p5/p25/p50/p75/p95)
- Annualised volatility, max drawdown, Sharpe, Sortino
- **Upside / downside capture** ratios — the cleanest expression of the asymmetry
- **Distribution yield vs total return** — quantifies returned-capital "yield"
- NAV path (to visualise erosion)
- **P(covered call beats buy-and-hold)**, by regime

Charts (written to `./output`): per-regime terminal-wealth fan charts,
NAV-vs-total-return decomposition, and an upside/downside capture scatter across
the strike × coverage sweep.

---

## Project layout

```
covered_call_sim/
  config.py        # all parameters, regimes, Markov switching
  pricing/         # Black-Scholes (vectorised)
  models/          # GBM / Student-t / regime-switching path generators
  strategy/        # covered-call payoff, rolling writer, fund/NAV wrapper
  sim/             # Monte Carlo orchestration + parameter sweep
  metrics/         # CAGR, drawdown, Sharpe/Sortino, capture, yield-vs-TR
  reporting/       # matplotlib charts + summary tables
  validation/      # yfinance backtest (QYLD/JEPI vs QQQ/SPY)
run.py             # CLI entry point
dashboard.py       # optional Streamlit front-end
tests/             # pytest validation / sanity suite
```

---

## Validation

`pytest` enforces the sanity checks from the spec:

1. **BS pricer** matches known reference values (`test_black_scholes.py`).
2. **No-free-lunch** — VRP=0, ATM ⇒ CC underperforms BH (`test_no_free_lunch.py`).
3. **Premium scales with vol**; payoff truncates upside (`test_premium_scaling.py`).
4. **Fund wrapper** — total return = NAV + distributions; choppy regime shows NAV
   erosion alongside a healthy yield (`test_fund_wrapper.py`).

**Real-data backtest** (`--backtest`): pulls QYLD/JEPI and their underlyings
(QQQ/SPY) via yfinance and checks the qualitative shape (bull lag, bear cushion,
NAV erosion). This requires a network policy that allows Yahoo Finance hosts; if
they're blocked the backtest skips gracefully with a message rather than
aborting the run.

---

## Stretch / advanced extensions (hooks present)

- Delta-targeted strike selection (`bs_call_delta` is implemented).
- Fat-tailed shocks via `--fat-tails` (Student-t).
- Transaction costs / bid-ask on premiums, tax-aware mode, and an equity/bond
  blend comparison at matched volatility are natural next steps on top of the
  existing strategy layer.
