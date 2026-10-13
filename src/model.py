"""Team-strength model: ridge-regularized Poisson regression on runs scored.

For every game we get two observations:
    runs(home) ~ Poisson( exp(mu + hfa + off[home] - def[away]) )
    runs(away) ~ Poisson( exp(mu        + off[away] - def[home]) )

- off[t]  > 0  means team t scores more than average
- def[t]  > 0  means team t allows fewer runs than average
- An L2 (ridge) penalty `lam` pulls every rating toward 0 (league average).
  This is the statistical version of "regress to the mean". 162 games is a
  small sample, and unpenalized ratings overstate how different teams are.
- Optional exponential recency weighting with half-life `half_life` days, so
  a team's late-season form counts more than April.

Expected runs then become a win probability via the Pythagenpat formula.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize


@dataclass
class Ratings:
    teams: list
    off: np.ndarray
    dfn: np.ndarray
    mu: float
    hfa: float

    def idx(self, team):
        return self.teams.index(team)

    def exp_runs(self, home, away, neutral=False):
        i, j = self.idx(home), self.idx(away)
        h = 0.0 if neutral else self.hfa
        rh = np.exp(self.mu + h + self.off[i] - self.dfn[j])
        ra = np.exp(self.mu + self.off[j] - self.dfn[i])
        return rh, ra

    def p_home_win(self, home, away, neutral=False):
        rh, ra = self.exp_runs(home, away, neutral)
        return pythagenpat(rh, ra)

    def table(self):
        df = pd.DataFrame({"team": self.teams, "off": self.off, "def": self.dfn})
        base = np.exp(self.mu + self.hfa / 2)
        df["exp_RS_pg"] = base * np.exp(df.off)
        df["exp_RA_pg"] = base * np.exp(-df["def"])
        df["net"] = df.off + df["def"]
        # Win % vs a perfectly average team on a neutral field
        df["exp_wpct"] = pythagenpat(df.exp_RS_pg, df.exp_RA_pg)
        return df.sort_values("net", ascending=False).reset_index(drop=True)


def pythagenpat(rs, ra):
    x = (rs + ra) ** 0.287
    return rs ** x / (rs ** x + ra ** x)


def fit(games, lam=30.0, half_life=None, ref_date=None):
    """Fit ratings on a games DataFrame (home, away, home_runs, away_runs, date)."""
    teams = sorted(set(games.home) | set(games.away))
    t_ix = {t: k for k, t in enumerate(teams)}
    n = len(teams)
    hi = games.home.map(t_ix).to_numpy()
    ai = games.away.map(t_ix).to_numpy()
    off_i = np.concatenate([hi, ai])
    def_i = np.concatenate([ai, hi])
    is_home = np.concatenate([np.ones(len(games)), np.zeros(len(games))])
    y = np.concatenate([games.home_runs.to_numpy(), games.away_runs.to_numpy()]).astype(float)

    if half_life:
        ref = pd.Timestamp(ref_date) if ref_date else pd.to_datetime(games.date).max()
        age = (ref - pd.to_datetime(games.date)).dt.days.to_numpy()
        w_game = 0.5 ** (age / half_life)
        w_game = w_game / w_game.mean()  # keep effective sample size comparable
    else:
        w_game = np.ones(len(games))
    w = np.concatenate([w_game, w_game])

    def unpack(p):
        return p[0], p[1], p[2:2 + n], p[2 + n:]

    def nll(p):
        mu, hfa, off, dfn = unpack(p)
        eta = mu + hfa * is_home + off[off_i] - dfn[def_i]
        lam_hat = np.exp(eta)
        loss = np.sum(w * (lam_hat - y * eta)) + lam * (off @ off + dfn @ dfn)
        r = w * (lam_hat - y)
        g = np.empty_like(p)
        g[0] = r.sum()
        g[1] = (r * is_home).sum()
        g[2:2 + n] = np.bincount(off_i, r, n) + 2 * lam * off
        g[2 + n:] = -np.bincount(def_i, r, n) + 2 * lam * dfn
        return loss, g

    p0 = np.zeros(2 + 2 * n)
    p0[0] = np.log(y.mean())
    res = minimize(nll, p0, jac=True, method="L-BFGS-B")
    mu, hfa, off, dfn = unpack(res.x)
    # Center ratings so 0 = league average (mu absorbs the shift)
    mu = mu + off.mean() - dfn.mean()
    return Ratings(teams, off - off.mean(), dfn - dfn.mean(), mu, hfa)


def log_loss(p, outcome):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return -np.mean(outcome * np.log(p) + (1 - outcome) * np.log(1 - p))


def brier(p, outcome):
    return np.mean((p - outcome) ** 2)
