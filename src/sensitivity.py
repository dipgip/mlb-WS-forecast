"""Step 5 — Does the answer survive reasonable changes to the method?

Each scenario changes one thing from the baseline and recomputes title odds
from the live bracket. Also computes "what-if" odds for the next game in each
LCS, so the forecast can be updated as results come in.
"""
import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd

from model import fit
import predict as P

ROOT = Path(__file__).resolve().parents[1]
ADJ = json.loads((ROOT / "outputs/roster_adjustments_2026.json").read_text())


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


def roster_adjusted(r, strength=1.0):
    r2 = copy.deepcopy(r)
    for team, a in ADJ.items():
        if team == "league":
            continue
        i = r2.idx(team)
        rs_pg, ra_pg = np.exp(r2.mu + r2.hfa / 2 + r2.off[i]), np.exp(r2.mu + r2.hfa / 2 - r2.dfn[i])
        r2.off[i] += np.log((rs_pg + strength * a["hitting"]["delta_runs_scored_pg"]) / rs_pg)
        r2.dfn[i] -= np.log((ra_pg + strength * a["pitching"]["delta_runs_allowed_pg"]) / ra_pg)
    return r2


def lcs_states():
    s = P.sched[(P.sched.season == 2026) & (P.sched.game_type == "L")]
    states = {}
    for desc, grp in s.groupby("series_desc"):
        grp = grp.drop_duplicates("series_game", keep="last").sort_values("series_game")
        teams = sorted(set(grp.home) | set(grp.away))
        played = P.post26[(P.post26.game_type == "L") & P.post26.home.isin(teams) & P.post26.away.isin(teams)]
        wins = {t: 0 for t in teams}
        for _, x in played.iterrows():
            wins[x.home if x.home_runs > x.away_runs else x.away] += 1
        states[desc] = (teams, list(grp.home), wins)
    return states["AL Championship Series"], states["NL Championship Series"]


def main():
    alcs, nlcs = lcs_states()
    base = fit(P.reg26, lam=P.LAM)
    with_post = fit(pd.concat([P.reg26, P.post26]), lam=P.LAM)
    scenarios = {
        "Baseline (λ=80, full season)": base,
        "Less shrinkage (λ=40)": fit(P.reg26, lam=40),
        "More shrinkage (λ=160)": fit(P.reg26, lam=160),
        "Recency-weighted (60-day half-life)": fit(P.reg26, lam=P.LAM, half_life=60),
        "Include 2026 postseason games": with_post,
        "Postseason roster adjustment (50%)": roster_adjusted(base, 0.5),
        "Postseason roster adjustment (100%)": roster_adjusted(base, 1.0),
        "Backtest-calibrated spread (k=1.18)": Scaled(base, 1.18),
        "Flatter probabilities (k=0.6)": Scaled(base, 0.6),
        "Every game a coin flip": Scaled(base, coin=True),
    }
    rows = []
    for name, r in scenarios.items():
        odds, _ = P.bracket_odds(r, alcs, nlcs)
        rows.append({"scenario": name, **{t: odds[t]["ws"] for t in odds}})
    df = pd.DataFrame(rows).set_index("scenario")
    df = df[df.loc["Baseline (λ=80, full season)"].sort_values(ascending=False).index]
    print("World Series win probability by scenario:\n")
    print((df * 100).round(1).to_string())
    df.to_csv(ROOT / "outputs/sensitivity.csv")

    # ---- What-if: the next LCS game in each series
    whatif = []
    for label, st, other in [("ALCS", alcs, nlcs), ("NLCS", nlcs, alcs)]:
        teams, home, wins = st
        g = sum(wins.values())
        for winner in teams:
            w2 = dict(wins)
            w2[winner] += 1
            if label == "ALCS":
                odds, _ = P.bracket_odds(base, (teams, home, w2), other)
            else:
                odds, _ = P.bracket_odds(base, other, (teams, home, w2))
            whatif.append({"series": label, "game": g + 1, "if_wins": winner,
                           "new_state": " ".join(f"{t.split()[-1]} {w2[t]}" for t in teams),
                           **{t: odds[t]["ws"] for t in odds}})
    wf = pd.DataFrame(whatif)
    print("\nWhat-if: next game in each LCS (title odds after the result):\n")
    print(wf.round(3).to_string(index=False))
    wf.to_csv(ROOT / "outputs/whatif_next_game.csv", index=False)


if __name__ == "__main__":
    main()
