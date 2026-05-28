"""No-free-lunch check (README §1.2 / §4.2).

With VRP = 0 and ATM strikes (m = 0), the covered call must UNDERPERFORM
buy-and-hold in expectation: a fairly-priced premium is no compensation for
giving up the upside. If this fails, the option pricing is wrong.
"""

import numpy as np

from covered_call_sim.config import Regime, SimConfig
from covered_call_sim.models.paths import simulate_gbm_paths
from covered_call_sim.strategy import roll_covered_call, single_cycle


def test_no_free_lunch_single_cycle():
    cfg = SimConfig(n_paths=200_000, horizon_months=1, m=0.0, seed=7)
    # VRP = 0: implied vol equals realised vol.
    regime = Regime("test", mu=0.08, sigma_realised=0.18, vrp=0.0)
    bundle = simulate_gbm_paths(regime, cfg)

    s0 = bundle.prices[:, 0]
    s1 = bundle.prices[:, 1]
    cyc = single_cycle(s0, s1, bundle.sigma_implied[:, 0], cfg)

    mean_cc = cyc.r_covered_call.mean()
    mean_bh = cyc.r_buy_and_hold.mean()
    assert mean_cc < mean_bh, (mean_cc, mean_bh)


def test_no_free_lunch_rolled():
    cfg = SimConfig(n_paths=20_000, horizon_months=120, m=0.0, seed=11)
    regime = Regime("test", mu=0.08, sigma_realised=0.18, vrp=0.0)
    bundle = simulate_gbm_paths(regime, cfg)
    result = roll_covered_call(bundle, cfg)

    # Mean terminal total-return wealth of CC should trail buy-and-hold.
    assert result.terminal_cc.mean() < result.terminal_bh.mean()


def test_positive_vrp_helps():
    """Sanity counterpart: a healthy VRP should narrow or reverse the gap."""
    cfg = SimConfig(n_paths=20_000, horizon_months=120, m=0.0, seed=11)
    zero = Regime("z", mu=0.08, sigma_realised=0.18, vrp=0.0)
    juicy = Regime("j", mu=0.08, sigma_realised=0.18, vrp=0.06)

    r_zero = roll_covered_call(simulate_gbm_paths(zero, cfg), cfg)
    r_juicy = roll_covered_call(simulate_gbm_paths(juicy, cfg), cfg)

    assert r_juicy.terminal_cc.mean() > r_zero.terminal_cc.mean()
