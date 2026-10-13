"""Step 7 — Bundle every result into report/data.json and inject it into report/index.html.

The page's numbers all come from outputs/; nothing is typed by hand.
Usage: .venv/bin/python report/build.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
REP = ROOT / "report"

odds = json.loads((OUT / "odds_2026.json").read_text())
sens = pd.read_csv(OUT / "sensitivity.csv")
whatif = pd.read_csv(OUT / "whatif_next_game.csv")
ratings = pd.read_csv(OUT / "ratings_2026.csv")
roster = json.loads((OUT / "roster_adjustments_2026.json").read_text())
bg = pd.read_csv(OUT / "backtest_games.csv")
bs = pd.read_csv(OUT / "backtest_series.csv")
grid = pd.read_csv(OUT / "tuning_grid.csv")
base = pd.read_csv(OUT / "tuning_baselines.csv")
sched = pd.read_csv(ROOT / "data/processed/schedule_all.csv")


def ll(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


# ---- series tracker (game-by-game linescore of each LCS)
series = {}
s26 = sched[(sched.season == 2026) & (sched.game_type == "L")]
for desc, grp in s26.groupby("series_desc"):
    grp = grp.drop_duplicates("series_game", keep="last").sort_values("series_game")
    series[desc] = [{
        "g": int(r.series_game), "date": r.date, "home": r.home, "away": r.away,
        "status": r.status,
        "home_runs": None if pd.isna(r.home_runs) else int(r.home_runs),
        "away_runs": None if pd.isna(r.away_runs) else int(r.away_runs),
        "home_sp": None if pd.isna(r.home_prob_sp) else r.home_prob_sp,
        "away_sp": None if pd.isna(r.away_prob_sp) else r.away_prob_sp,
    } for r in grp.itertuples()]

# ---- backtest summary
y = bg.home_won.to_numpy()
bs["p_fav"] = np.maximum(bs.p_team1_model, 1 - bs.p_team1_model)
bs["fav_won"] = np.where(bs.p_team1_model >= .5, bs.t1_won, 1 - bs.t1_won)
bins = pd.cut(bs.p_fav, [.5, .55, .6, .65, 1.0])
calib = bs.groupby(bins, observed=True).agg(n=("fav_won", "size"), predicted=("p_fav", "mean"),
                                            actual=("fav_won", "mean")).reset_index(drop=True)
ws = bs[bs["round"] == "W"].copy()
ws["fav"] = np.where(ws.p_team1_model >= .5, ws.team1, ws.team2)
ws["dog"] = np.where(ws.p_team1_model >= .5, ws.team2, ws.team1)
fav_g = np.where(bg.p_neutral >= .5, bg.home_won, 1 - bg.home_won)
backtest = {
    "n_games": int(len(bg)), "n_series": int(len(bs)),
    "game_ll": {"coin": ll(np.full(len(y), .5), y), "log5": ll(bg.p_log5.to_numpy(), y),
                "model": ll(bg.p_model.to_numpy(), y)},
    "series_ll": {"coin": ll(np.full(len(bs), .5), bs.t1_won.to_numpy()),
                  "model": ll(bs.p_team1_model.to_numpy(), bs.t1_won.to_numpy())},
    "game_fav_won": float(fav_g.mean()),
    "series_fav_won": float(bs.fav_won.mean()), "series_fav_pred": float(bs.p_fav.mean()),
    "home_won": float(y.mean()),
    "calibration": calib.to_dict("records"),
    "ws": ws[["season", "fav", "dog", "p_fav", "winner", "fav_won"]].to_dict("records"),
}

best = grid.iloc[0]
tuning = {
    "best": {"lam": int(best.lam), "half_life": int(best.half_life), "log_loss": float(best.log_loss),
             "accuracy": float(best.accuracy)},
    "home_only": float((base.ll_home_only * base.n).sum() / base.n.sum()),
    "log5": float((base.ll_log5_record * base.n).sum() / base.n.sum()),
    "n_games": int(base.n.sum()),
    "by_lam": grid[grid.half_life == 0].sort_values("lam")[["lam", "log_loss"]].to_dict("records"),
}

# ---- market (Oct 13 sportsbook prices, SI / Fox Sports-DraftKings)
american = {"Milwaukee Brewers": 105, "Los Angeles Dodgers": 350,
            "Cleveland Guardians": 400, "Tampa Bay Rays": 475}
imp = {t: 100 / (a + 100) for t, a in american.items()}
tot = sum(imp.values())
market = {t: {"american": f"+{a}", "implied": imp[t] / tot} for t, a in american.items()}

rost = {t: {"fip_season": v["pitching"]["season_staff_FIP"], "fip_oct": v["pitching"]["october_staff_FIP"],
            "dra": v["pitching"]["delta_runs_allowed_pg"],
            "woba_season": v["hitting"]["season_lineup_wOBA"], "woba_oct": v["hitting"]["october_lineup_wOBA"],
            "drs": v["hitting"]["delta_runs_scored_pg"],
            "sps": [s["name"] for s in v["pitching"]["staff"] if s["role"] == "SP"]}
        for t, v in roster.items() if t != "league"}

data = {
    "as_of": "2026-10-13",
    "odds": odds,
    "series": series,
    "sensitivity": sens.to_dict("records"),
    "whatif": whatif.to_dict("records"),
    "ratings": ratings.head(12).assign(rank=range(1, 13)).to_dict("records")
               + ratings[ratings.team == "Cleveland Guardians"].assign(
                   rank=int(ratings.index[ratings.team == "Cleveland Guardians"][0]) + 1).to_dict("records"),
    "roster": rost,
    "backtest": backtest,
    "tuning": tuning,
    "market": market,
}
(REP / "data.json").write_text(json.dumps(data, indent=1, default=float))

html = (REP / "template.html").read_text()
(REP / "index.html").write_text(html.replace("/*__DATA__*/null", json.dumps(data, default=float)))
print("wrote report/index.html")
