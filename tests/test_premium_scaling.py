"""Premium must scale with implied vol, and the payoff must truncate upside."""

import numpy as np

from covered_call_sim.config import SimConfig
from covered_call_sim.pricing import bs_call
from covered_call_sim.strategy import single_cycle


def test_premium_increases_with_implied_vol():
    sigmas = np.array([0.10, 0.20, 0.30, 0.40])
    premiums = bs_call(100, 100, 1 / 12, 0.045, sigmas)
    assert np.all(np.diff(premiums) > 0)


def test_payoff_truncates_upside():
    cfg = SimConfig(m=0.0)
    s0 = np.full(3, 100.0)
    s1 = np.array([90.0, 100.0, 130.0])  # down, flat, up
    sigma_implied = np.full(3, 0.20)
    cyc = single_cycle(s0, s1, sigma_implied, cfg)

    # Above the strike (last path), price_value is capped at K = 100.
    assert cyc.price_value[2] == 100.0
    assert cyc.called_away[2]
    assert not cyc.called_away[0]

    # Covered-call value above strike = K + premium, strictly below holding S1.
    assert cyc.cc_value[2] < s1[2]


def test_otm_strike_reduces_premium_but_lifts_cap():
    cfg_atm = SimConfig(m=0.0)
    cfg_otm = SimConfig(m=0.05)
    s0 = np.array([100.0])
    s1 = np.array([103.0])  # between ATM strike (100) and OTM strike (105)
    sig = np.array([0.20])

    atm = single_cycle(s0, s1, sig, cfg_atm)
    otm = single_cycle(s0, s1, sig, cfg_otm)

    # OTM collects less premium...
    assert otm.premium[0] < atm.premium[0]
    # ...but caps at a higher strike, so this in-between outcome keeps gains.
    assert atm.called_away[0] and not otm.called_away[0]
    # OTM keeps the full price move; ATM truncates it at the strike.
    assert otm.price_value[0] == 103.0
    assert atm.price_value[0] == 100.0
