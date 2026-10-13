"""Step 2 — Choose the shrinkage (lam) and recency half-life by out-of-sample test.

Protocol, for each full season 2015–2025 (2020 skipped: 60-game season):
  fit on regular-season games through Aug 31, predict every game from Sep 1 on.
The postseason is never touched here, so the Step 3 backtest stays honest.

Baselines for context:
  - home-field only: every home team gets the league home win rate
  - log5 on win%: the classic "just use records" approach
"""
import itertools
from pathlib import Path

import numpy as np
import pandas as pd

from model import fit, log_loss, brier

ROOT = Path(__file__).resolve().parents[1]
games = pd.read_csv(ROOT / "data/processed/games.csv")
reg = games[games.game_type == "R"]
SEASONS = [s for s in range(2015, 2026) if s != 2020]

LAMS = [0, 5, 10, 20, 40, 80, 160]
HALF_LIVES = [None, 120, 60, 30]


def log5(pa, pb):
    return pa * (1 - pb) / (pa * (1 - pb) + pb * (1 - pa))


rows = []
base_rows = []
for s in SEASONS:
    g = reg[reg.season == s]
    train, test = g[g.date < f"{s}-09-01"], g[g.date >= f"{s}-09-01"]
    y = (test.home_runs > test.away_runs).to_numpy().astype(float)

    hw = (train.home_runs > train.away_runs).mean()
    p_home = np.full(len(test), hw)
    rec = pd.concat([
        pd.DataFrame({"t": train.home, "w": train.home_runs > train.away_runs}),
        pd.DataFrame({"t": train.away, "w": train.away_runs > train.home_runs}),
    ]).groupby("t").w.mean()
    p_rec = log5(test.home.map(rec).to_numpy(), test.away.map(rec).to_numpy())
    # add home edge on the log-odds scale
    lo = np.log(p_rec / (1 - p_rec)) + np.log(hw / (1 - hw))
    p_rec = 1 / (1 + np.exp(-lo))
    base_rows.append({"season": s, "n": len(test),
                      "ll_home_only": log_loss(p_home, y), "ll_log5_record": log_loss(p_rec, y)})

    for lam, hl in itertools.product(LAMS, HALF_LIVES):
        r = fit(train, lam=lam, half_life=hl, ref_date=f"{s}-09-01")
        p = np.array([r.p_home_win(h, a) for h, a in zip(test.home, test.away)])
        rows.append({"season": s, "lam": lam, "half_life": hl or 0, "n": len(test),
                     "ll": log_loss(p, y), "brier": brier(p, y), "acc": ((p > .5) == y).mean()})

res = pd.DataFrame(rows)
base = pd.DataFrame(base_rows)
# game-weighted average across seasons
agg = (res.assign(llw=res.ll * res.n, bw=res.brier * res.n, aw=res.acc * res.n)
          .groupby(["lam", "half_life"])[["llw", "bw", "aw", "n"]].sum())
agg = pd.DataFrame({"log_loss": agg.llw / agg.n, "brier": agg.bw / agg.n,
                    "accuracy": agg.aw / agg.n}).sort_values("log_loss")
print("Model grid (best first):\n", agg.round(5).head(12).to_string())
bw = base[["ll_home_only", "ll_log5_record"]].mul(base.n, axis=0).sum() / base.n.sum()
print("\nBaselines (log loss):\n", bw.round(5).to_string())

out = ROOT / "outputs"
agg.reset_index().to_csv(out / "tuning_grid.csv", index=False)
base.to_csv(out / "tuning_baselines.csv", index=False)
