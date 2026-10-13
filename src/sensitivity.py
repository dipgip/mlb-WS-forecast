"""Step 5 — How sure are we, and does the answer survive other reasonable choices?

1. Statistical uncertainty (the headline interval): bootstrap the 2026
   regular season (resample games with replacement), refit, and re-run the
   bracket. This captures how noisy one season of ratings is.
2. Robustness: each scenario changes one modeling choice and recomputes title
   odds. This measures sensitivity to judgment calls, not statistical error.
3. What-ifs: title odds after each possible result of the next game in each
   live series.

Outputs: outputs/uncertainty.csv, outputs/sensitivity.csv, outputs/whatif_next_game.csv
"""
import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd

from model import fit
import predict as P

ROOT = Path(__file__).resolve().parents[1]
N_BOOT = 1000


class Scaled:
    """Wrap ratings to stretch/shrink win probabilities on the log-odds scale."""
    def __init__(self, r, k=1.0, coin=False):
        self.r, self.k, self.coin = r, k, coin

    def p_home_win(self, home, away, neutral=False):
        if self.coin:
            return 0.5
        p = self.r.p_home_win(home, away, neutral)
        lo = np.log(p / (1 - p)) * self.k
        return 1 / (1 + np.exp(-lo))


def roster_adjusted(r, adj, strength=1.0):
    r2 = copy.deepcopy(r)
    for team, a in adj.items():
        if team == "league" or team not in r2.teams:
            continue
        i = r2.idx(team)
        rs_pg, ra_pg = np.exp(r2.mu + r2.off[i]), np.exp(r2.mu - r2.dfn[i])
        r2.off[i] += np.log((rs_pg + strength * a["hitting"]["delta_runs_scored_pg"]) / rs_pg)
        r2.dfn[i] -= np.log((ra_pg + strength * a["pitching"]["delta_runs_allowed_pg"]) / ra_pg)
    return r2


def bootstrap(d, n=N_BOOT, seed=2026):
    rng = np.random.default_rng(seed)
    reg = d["reg"]
    rows = []
    for _ in range(n):
        sample = reg.iloc[rng.integers(0, len(reg), len(reg))]
        o, _ = P.odds(fit(sample, lam=P.LAM), d)
        rows.append({t: v["ws"] for t, v in o.items()})
    draws = pd.DataFrame(rows)
    return pd.DataFrame({"team": draws.columns,
                         "p05": draws.quantile(.05).values, "p50": draws.median().values,
                         "p95": draws.quantile(.95).values})


def main():
    d = P.load()
    base = fit(d["reg"], lam=P.LAM)

    unc = bootstrap(d)
    point, _ = P.odds(base, d)
    unc["point"] = unc.team.map(lambda t: point[t]["ws"])
    unc.to_csv(ROOT / "outputs/uncertainty.csv", index=False)
    print(f"Statistical uncertainty ({N_BOOT} bootstrap refits), title odds:")
    for r in unc.sort_values("point", ascending=False).itertuples():
        print(f"  {r.team:22s} {r.point:.3f}   90% interval [{r.p05:.3f}, {r.p95:.3f}]")

    adj_path = ROOT / "outputs/roster_adjustments_2026.json"
    adj = json.loads(adj_path.read_text()) if adj_path.exists() else {}
    scenarios = {
        "Baseline (λ=80, full season)": base,
        "Less shrinkage (λ=40)": fit(d["reg"], lam=40),
        "More shrinkage (λ=160)": fit(d["reg"], lam=160),
        "Recency-weighted (60-day half-life)": fit(d["reg"], lam=P.LAM, half_life=60),
        "Include 2026 postseason games": fit(pd.concat([d["reg"], d["post"]]), lam=P.LAM),
        "Home field from runs (old method)": fit(d["reg"], lam=P.LAM, hfa_from_wins=False),
        "Roster adjustment, untested (50%)": roster_adjusted(base, adj, 0.5),
        "Roster adjustment, untested (100%)": roster_adjusted(base, adj, 1.0),
        "More confident (k=1.18)": Scaled(base, 1.18),
        "Less confident (k=0.6)": Scaled(base, 0.6),
        "Every game a coin flip": Scaled(base, coin=True),
    }
    rows = []
    for name, r in scenarios.items():
        o, _ = P.odds(r, d)
        rows.append({"scenario": name, **{t: o[t]["ws"] for t in o}})
    df = pd.DataFrame(rows).set_index("scenario")
    df = df[df.iloc[0].sort_values(ascending=False).index]
    print("\nWorld Series win probability by scenario (%):\n")
    print((df * 100).round(1).to_string())
    df.to_csv(ROOT / "outputs/sensitivity.csv")

    # What-if: the next game of every series still in progress
    whatif = []
    live = [("ALCS", "alcs"), ("NLCS", "nlcs")] + ([("WS", "ws")] if d["ws"] else [])
    for label, key in live:
        teams, home, wins = d[key]
        if max(wins.values()) == 4:
            continue
        g = sum(wins.values())
        for winner in teams:
            d2 = dict(d)
            w2 = dict(wins)
            w2[winner] += 1
            d2[key] = (teams, home, w2)
            o, _ = P.odds(base, d2)
            whatif.append({"series": label, "game": g + 1, "home": home[g], "if_wins": winner,
                           **{t: o[t]["ws"] for t in o}})
    wf = pd.DataFrame(whatif)
    print("\nWhat-if: next game in each series (title odds after the result):\n")
    print(wf.round(3).to_string(index=False))
    wf.to_csv(ROOT / "outputs/whatif_next_game.csv", index=False)


if __name__ == "__main__":
    main()
