"""Step 3 — Backtest on real postseasons, 2015–2025.

For each year, fit the model on that regular season only (lam=80, no recency
weighting, as chosen in Step 2), then predict:
  (a) every postseason game, and
  (b) every postseason series, from its first pitch, via simulation over the
      real home/away schedule.
Score against a coin flip and against log5-on-record.

This is the honesty check: how much can a regular-season model see in October?
"""
from pathlib import Path

import numpy as np
import pandas as pd

from model import fit, log_loss, brier
from simulate import series_win_prob

ROOT = Path(__file__).resolve().parents[1]
games = pd.read_csv(ROOT / "data/processed/games.csv")
sched = pd.read_csv(ROOT / "data/processed/schedule_all.csv")
LAM = 80
SEASONS = list(range(2015, 2026))


def log5(pa, pb):
    return pa * (1 - pb) / (pa * (1 - pb) + pb * (1 - pa))


def series_key(df):
    # A series = same season, same round, same pair of teams
    pair = df.apply(lambda r: " v ".join(sorted([r.home, r.away])), axis=1)
    return df.season.astype(str) + "|" + df.game_type + "|" + pair


game_rows, series_rows = [], []
for s in SEASONS:
    g = games[games.season == s]
    reg, post = g[g.game_type == "R"], g[g.game_type != "R"].copy()
    r = fit(reg, lam=LAM)
    rec = pd.concat([
        pd.DataFrame({"t": reg.home, "w": reg.home_runs > reg.away_runs}),
        pd.DataFrame({"t": reg.away, "w": reg.away_runs > reg.home_runs}),
    ]).groupby("t").w.mean()

    post["p_model"] = [r.p_home_win(h, a) for h, a in zip(post.home, post.away)]
    post["p_log5"] = log5(post.home.map(rec), post.away.map(rec))
    post["home_won"] = (post.home_runs > post.away_runs).astype(int)
    # Strength gap ignoring home field (which team is genuinely better)
    post["p_neutral"] = [r.p_home_win(h, a, neutral=True) for h, a in zip(post.home, post.away)]
    game_rows.append(post)

    # Series level: use the full scheduled slate (incl. unplayed "if necessary" games) for home order
    post["key"] = series_key(post)
    sch = sched[(sched.season == s) & (sched.game_type != "R") & sched.home.notna()].copy()
    for key, sg in post.groupby("key"):
        sg = sg.sort_values(["date", "game_pk"])
        t1, t2 = sorted([sg.home.iloc[0], sg.away.iloc[0]])
        wins = {t1: 0, t2: 0}
        for _, x in sg.iterrows():
            wins[x.home if x.home_won else x.away] += 1
        n_games_needed = max(wins.values())
        winner = max(wins, key=wins.get)
        # Home order of the scheduled series (games 1..N)
        ss = sch[(sch.game_type == sg.game_type.iloc[0]) &
                 (((sch.home == t1) & (sch.away == t2)) | ((sch.home == t2) & (sch.away == t1)))]
        ss = ss.drop_duplicates("series_game").sort_values("series_game")
        best_of = 2 * n_games_needed - 1
        home_order = list(ss.home)[:best_of]
        if len(home_order) < best_of:  # fall back: higher seed (game-1 host) gets 2-3-2 / 2-2-1 / all
            h0 = sg.home.iloc[0]
            other = t2 if h0 == t1 else t1
            pattern = {3: [1, 1, 1], 5: [1, 1, 0, 0, 1], 7: [1, 1, 0, 0, 0, 1, 1]}.get(best_of, [1] * best_of)
            home_order = [h0 if x else other for x in pattern]
        p_t1 = series_win_prob(r, t1, t2, home_order, wins_needed=n_games_needed)
        series_rows.append({
            "season": s, "round": sg.game_type.iloc[0], "team1": t1, "team2": t2,
            "best_of": best_of, "winner": winner, "p_team1_model": p_t1,
            "t1_won": int(winner == t1),
        })

gp = pd.concat(game_rows)
sp = pd.DataFrame(series_rows)
gp.to_csv(ROOT / "outputs/backtest_games.csv", index=False)
sp.to_csv(ROOT / "outputs/backtest_series.csv", index=False)

y = gp.home_won.to_numpy()
print(f"Postseason games 2015–2025: n={len(gp)}")
print(f"  home team won           {y.mean():.3f}")
print(f"  log loss  coin flip     {log_loss(np.full(len(y), .5), y):.4f}")
print(f"  log loss  log5 record   {log_loss(gp.p_log5.to_numpy(), y):.4f}")
print(f"  log loss  model         {log_loss(gp.p_model.to_numpy(), y):.4f}")
print(f"  brier     coin / model  {brier(np.full(len(y), .5), y):.4f} / {brier(gp.p_model.to_numpy(), y):.4f}")

# Did the better team (model, neutral) win?
fav_won = np.where(gp.p_neutral >= .5, gp.home_won, 1 - gp.home_won)
print(f"  model favorite won      {fav_won.mean():.3f}   (avg predicted {np.maximum(gp.p_neutral, 1-gp.p_neutral).mean():.3f})")

# Calibration recalibration factor: fit k on logit(p) -> how over/under-confident?
from scipy.optimize import minimize_scalar
lo = np.log(gp.p_model / (1 - gp.p_model)).to_numpy()
k = minimize_scalar(lambda k: log_loss(1 / (1 + np.exp(-k * lo)), y), bounds=(0, 3), method="bounded").x
print(f"  best logit scale k      {k:.2f}   (1.0 = perfectly calibrated spread)")

print(f"\nSeries 2015–2025: n={len(sp)}")
sp["p_fav"] = np.maximum(sp.p_team1_model, 1 - sp.p_team1_model)
sp["fav_won"] = np.where(sp.p_team1_model >= .5, sp.t1_won, 1 - sp.t1_won)
print(f"  model favorite won      {sp.fav_won.mean():.3f}   (avg predicted {sp.p_fav.mean():.3f})")
ys = sp.t1_won.to_numpy()
print(f"  log loss coin / model   {log_loss(np.full(len(ys), .5), ys):.4f} / {log_loss(sp.p_team1_model.to_numpy(), ys):.4f}")
bins = pd.cut(sp.p_fav, [.5, .55, .6, .65, 1.0])
print(sp.groupby(bins, observed=True).agg(n=("fav_won", "size"), predicted=("p_fav", "mean"), actual=("fav_won", "mean")).round(3).to_string())
ws = sp[sp["round"] == "W"]
print("\nWorld Series favorites:")
print(ws.assign(fav=np.where(ws.p_team1_model >= .5, ws.team1, ws.team2))[["season", "fav", "p_fav", "winner", "fav_won"]].round(3).to_string(index=False))
