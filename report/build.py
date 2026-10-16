"""Step 7 — Bundle every result into report/data.json and inject it into report/index.html.

Every number and every number-bearing sentence on the page is computed here
from outputs/ and data/. The template holds no hand-typed facts, so a
refresh can't leave stale prose behind.

Usage: .venv/bin/python report/build.py
"""
import json
import math
import os
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import bracket as B  # noqa: E402
import predict as P  # noqa: E402
import record as R  # noqa: E402

OUT = ROOT / "outputs"
REP = ROOT / "report"
# REPORT_OUT lets the tests build into a temp folder without touching report/
DEST = Path(os.environ.get("REPORT_OUT", REP))


def ll(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def wilson(k, n, z=1.96):
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return c - h, c + h


def short(t):
    w = t.split()
    return " ".join(w[-2:]) if w[-1] == "Sox" else w[-1]


def pc(x):
    return f"{round(x * 100)}%"


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def nice_date(s):
    d = date.fromisoformat(s)
    return f"{d.strftime('%b')} {d.day}, {d.year}"


odds = json.loads((OUT / "odds_2026.json").read_text())
unc = pd.read_csv(OUT / "uncertainty.csv").set_index("team")
sens = pd.read_csv(OUT / "sensitivity.csv")
whatif = pd.read_csv(OUT / "whatif_next_game.csv")
ratings = pd.read_csv(OUT / "ratings_2026.csv")
roster = json.loads((OUT / "roster_adjustments_2026.json").read_text())
market = json.loads((OUT / "market_2026.json").read_text())
spb = json.loads((OUT / "sp_backtest_summary.json").read_text())
bg = pd.read_csv(OUT / "backtest_games.csv")
bs = pd.read_csv(OUT / "backtest_series.csv")
grid = pd.read_csv(OUT / "tuning_grid.csv")
base = pd.read_csv(OUT / "tuning_baselines.csv")
games = pd.read_csv(ROOT / "data/processed/games.csv")
d = P.load()

now = odds["odds_now"]
pre = odds["odds_before_lcs"]
order = sorted(now, key=lambda t: -now[t]["ws"])
fav = order[0]

# ---- series tracker (game-by-game linescore of each live series)
series = {}
for key, label in (("alcs", "AL Championship Series"), ("nlcs", "NL Championship Series"), ("ws", "World Series")):
    if not d.get(key):
        continue
    s = d["sched"][(d["sched"].series_desc == label) & d["sched"].home.isin(d[key][0])]
    s = s.drop_duplicates("series_game", keep="last").sort_values("series_game")
    series[label] = [{
        "g": int(r.series_game), "date": r.date, "home": r.home, "away": r.away,
        "home_runs": None if pd.isna(r.home_runs) or r.status != "Final" else int(r.home_runs),
        "away_runs": None if pd.isna(r.away_runs) or r.status != "Final" else int(r.away_runs),
        "home_sp": None if pd.isna(r.home_prob_sp) else r.home_prob_sp,
        "away_sp": None if pd.isna(r.away_prob_sp) else r.away_prob_sp,
    } for r in s.itertuples()]


def series_line(label):
    gs = series[label]
    teams = [gs[0]["away"], gs[0]["home"]]
    w = {t: 0 for t in teams}
    for g in gs:
        if g["home_runs"] is not None:
            w[g["home"] if g["home_runs"] > g["away_runs"] else g["away"]] += 1
    a, b = sorted(teams, key=lambda t: -w[t])
    nxt = next((g for g in gs if g["home_runs"] is None), None)
    return a, b, w, nxt


# ---- backtest summary
y = bg.home_won.to_numpy()
bs["p_fav"] = np.maximum(bs.p_team1_model, 1 - bs.p_team1_model)
bs["fav_won"] = np.where(bs.p_team1_model >= .5, bs.t1_won, 1 - bs.t1_won)
calib = (bs.groupby(pd.cut(bs.p_fav, [.5, .55, .6, .65, 1.0]), observed=True)
           .agg(n=("fav_won", "size"), predicted=("p_fav", "mean"), actual=("fav_won", "mean"))
           .reset_index(drop=True))
ws_hist = bs[bs["round"] == "W"].copy()
ws_hist["fav"] = np.where(ws_hist.p_team1_model >= .5, ws_hist.team1, ws_hist.team2)
fav_g = np.where(bg.p_neutral >= .5, bg.home_won, 1 - bg.home_won)
lo, hi = wilson(int(bs.fav_won.sum()), len(bs))
clear = ws_hist[ws_hist.p_fav >= .55]
backtest = {
    "n_games": int(len(bg)), "n_series": int(len(bs)),
    "game_ll": {"coin": ll(np.full(len(y), .5), y), "log5": ll(bg.p_log5.to_numpy(), y),
                "model": ll(bg.p_model.to_numpy(), y)},
    "game_fav_won": float(fav_g.mean()),
    "series_fav_won": float(bs.fav_won.mean()), "series_fav_pred": float(bs.p_fav.mean()),
    "series_fav_ci": [float(lo), float(hi)],
    "calibration": calib.to_dict("records"),
    "ws": ws_hist[["season", "fav", "p_fav", "winner", "fav_won"]].to_dict("records"),
}

# ---- facts: every number-bearing phrase on the page
fs = short(fav)
reg = d["reg"]
_, wins = B.win_pct(reg)
games_played = pd.concat([reg.home, reg.away]).value_counts()
rank = {r.team: int(r.rank) for r in ratings.itertuples()}
four = list(now)
weakest = max(four, key=lambda t: rank[t])

hosts_all = all(v["team"] == fav for k, v in odds["ws_home_field"].items() if fav in k)
nl_a, nl_b, nl_w, nl_next = series_line("NL Championship Series")
al_a, al_b, al_w, al_next = series_line("AL Championship Series")


fav_series = (nl_a, nl_b, nl_w) if fav in nl_w else (al_a, al_b, al_w)
if fav_series[0] == fav and fav_series[2][fav] > fav_series[2][fav_series[1]]:
    fav_state = f"lead the {short(fav_series[1])} {fav_series[2][fav]}–{fav_series[2][fav_series[1]]}"
else:
    other = fav_series[1] if fav_series[0] == fav else fav_series[0]
    fav_state = f"are {fav_series[2][fav]}–{fav_series[2][other]} against the {short(other)}"
best_record = wins.idxmax() == fav

lede = (
    f"The {fs} finished {int(wins[fav])}–{int(games_played[fav] - wins[fav])}"
    f"{', the best record in baseball' if best_record else ''}. They {fav_state} in the "
    f"{'NLCS' if fav in nl_w else 'ALCS'}"
    + (" and would host Games 1, 2, 6 and 7 of any World Series." if hosts_all else ".")
    + f" Every version of the model makes them the favorite. That still leaves a {pc(1 - now[fav]['ws'])} chance "
      "the trophy goes somewhere else.")

delta = {t: now[t]["ws"] - pre[t]["ws"] for t in four}
riser, faller = max(delta, key=delta.get), min(delta, key=delta.get)
swing = (f"Since the LCS began, the {short(riser)} moved from {pc(pre[riser]['ws'])} to {pc(now[riser]['ws'])}"
         f" and the {short(faller)} went from {pc(pre[faller]['ws'])} to {pc(now[faller]['ws'])}.")

scen = sens.set_index("scenario")
non_coin = scen[~scen.index.str.startswith("Every")]
fav_top_everywhere = all(r.idxmax() == fav for _, r in scen.iterrows())
mk = {t: v["fair_power"] for t, v in market["teams"].items()}
mk.update({t: 0.0 for t in four if t not in mk})  # eliminated teams drop out of the market
gap_team = max(four, key=lambda t: abs(mk[t] - now[t]["ws"]) if t != fav else -1)
roster_full = scen.loc[[i for i in scen.index if "100%" in i][0]]
sp_better = spb["share_boot_better"]

topmu = max(odds["ws_matchups"].items(), key=lambda kv: kv[1]["p_matchup"])
mu_al, mu_nl = topmu[0].split(" vs ")
abbrev = dict(pd.read_csv(ROOT / "data/processed/teams.csv")[["team", "abbrev"]].values)


def next_label(lbl, nxt):
    return f"{lbl} G{nxt['g']} {nice_date(nxt['date']).rsplit(',', 1)[0]}" if nxt else None


nexts = [x for x in (next_label("ALCS", al_next), next_label("NLCS", nl_next)) if x]
mkt_note = (f"{len(market['sources'])} sportsbook sources captured {nice_date(market['captured'])}, "
            "margin removed with the power method")

biggest = whatif.copy()
biggest["drop"] = [min(r[t] - now[t]["ws"] for t in four) for _, r in biggest.iterrows()]
bw = biggest.sort_values("drop").iloc[0]
bw_team = min(four, key=lambda t: bw[t] - now[t]["ws"])

facts = {
    "asof": f"Forecast as of {nice_date(odds['as_of'])} games" + (f" · next: {', '.join(nexts)}" if nexts else ""),
    "fav": fav, "fav_short": fs,
    "fav_pct": round(now[fav]["ws"] * 100),
    "fav_ci": f"{pc(unc.loc[fav, 'p05'])}–{pc(unc.loc[fav, 'p95'])}",
    "fav_mkt": pc(mk[fav]),
    "top_mu": f"{abbrev.get(mu_al, short(mu_al))} vs {abbrev.get(mu_nl, short(mu_nl))}",
    "top_mu_pct": pc(topmu[1]["p_matchup"]),
    "lede": lede,
    "swing": swing,
    "n_games_total": f"{len(games):,}",
    "bt_series": f"When the model's series favorite was predicted to win {pc(backtest['series_fav_pred'])} of the time, "
                 f"favorites actually won {pc(backtest['series_fav_won'])} across {backtest['n_series']} series. "
                 f"With a sample that small, the 95% interval on that win rate is {pc(lo)}–{pc(hi)}: consistent with good "
                 "calibration, but not proof of it.",
    "ws_clear": f"Of {len(ws_hist)} World Series since 2015, the model's favorite won {int(ws_hist.fav_won.sum())}. "
                f"Counting only clear favorites (55% or more), it's {int(clear.fav_won.sum())} of {len(clear)}; "
                "the rest were near coin flips.",
    "sens_head": f"The {fs} lead under every setup" if fav_top_everywhere else f"The {fs} lead under most setups",
    "sens_range": f"{pc(non_coin[fav].min())}–{pc(non_coin[fav].max())}",
    "coin_pct": pc(scen.loc[[i for i in scen.index if i.startswith('Every')][0], fav]),
    "market_text": (
        f"Sportsbooks agree on the favorite: the market has the {fs} at {pc(mk[fav])} after removing the bookmaker margin, "
        f"against the model's {pc(now[fav]['ws'])}. The biggest disagreement is the {short(gap_team)}: market {pc(mk[gap_team])}, "
        f"model {pc(now[gap_team]['ws'])}."),
    "market_why": (
        f"One natural explanation is October deployment: the {short(gap_team)}' playoff rotation "
        f"({', '.join(roster[gap_team]['pitching']['staff'][i]['name'] for i in range(4))}) projects to a "
        f"{roster[gap_team]['pitching']['october_staff_FIP']:.2f} FIP against {roster[gap_team]['pitching']['season_staff_FIP']:.2f} "
        f"for the season, and an adjustment for that moves them to {pc(roster_full[gap_team])}. "
        f"But I tested the closest checkable version, adjusting each past playoff game for its actual starting "
        f"pitchers ({spb['n_games']} games, 2015–2025), and it did not improve predictions: it beat the plain model in only "
        f"{pc(sp_better)} of bootstrap resamples. So the gap is unexplained. The rotation story is a hypothesis, not a finding."),
    "mkt_note": mkt_note,
    "watch_head": "What the next game in each series does",
    "watch_text": (f"Title odds after each possible result. The largest single swing: if the {short(bw.if_wins)} win "
                   f"{bw.series} Game {int(bw.game)}, the {short(bw_team)} fall from {pc(now[bw_team]['ws'])} to {pc(bw[bw_team])}."),
    "ratings_text": (f"Expected runs per game against a league-average opponent after shrinkage, and the implied win rate. "
                     f"The {short(weakest)} rank {ordinal(rank[weakest])}, the lowest of the four teams left."),
    "next_matchup_caveat": (
        f"It ignores the specific pitching matchup in each game (for example {al_next['away_sp']} vs {al_next['home_sp']} "
        f"in ALCS Game {al_next['g']}). The backtest found that adding starters by season FIP doesn't help, so a better "
        "pitcher metric is open work."
        if al_next and al_next.get("away_sp") and al_next.get("home_sp") else
        "It ignores the specific pitching matchup in each game. The backtest found that adding starters by season FIP "
        "doesn't help, so a better pitcher metric is open work."),
    "data_through": nice_date(odds["as_of"]),
    "calib_note": (f"Dots show how often the model's series favorite actually won, grouped by how confident the model "
                   f"was. Each bin holds only {int(calib.n.min())}–{int(calib.n.max())} series, so expect scatter around the line."),
    "sample_caveat": (f"The backtest covers {backtest['n_series']} series: enough to show the probabilities aren't badly off, "
                      "not enough to fine-tune them."),
    "home_rate": pc(odds["home_win_rate_equal_teams"]),
}

data = {
    "as_of": odds["as_of"],
    "facts": facts,
    "odds": odds,
    "uncertainty": unc.reset_index().to_dict("records"),
    "series": series,
    "sensitivity": sens.to_dict("records"),
    "whatif": whatif.to_dict("records"),
    "ratings": ratings[(ratings["rank"] <= 12) | ratings.team.isin(four)].to_dict("records"),
    "roster": {t: {"fip_season": v["pitching"]["season_staff_FIP"], "fip_oct": v["pitching"]["october_staff_FIP"],
                   "dra": v["pitching"]["delta_runs_allowed_pg"],
                   "woba_season": v["hitting"]["season_lineup_wOBA"], "woba_oct": v["hitting"]["october_lineup_wOBA"],
                   "sps": [s["name"] for s in v["pitching"]["staff"] if s["role"] == "SP"]}
               for t, v in roster.items() if t != "league"},
    "backtest": backtest,
    "market": {t: ({"american": market["teams"][t]["american"], "implied": mk[t]} if t in market["teams"]
                   else {"american": "out", "implied": 0.0}) for t in four},
    "market_sources": market["sources"],
}
tl = R.timeline()
wide = []
for seq, g in tl.groupby("seq"):
    first = g.iloc[0]
    wide.append({"label": first.label, "kind": first.kind, "model": first.model_version,
                 "created": first.created_at_utc.replace("T", " ").rstrip("Z"), "state": first.state,
                 "pregame": bool(first.pregame_verified), "commit": first.commit,
                 **{t: float(v) for t, v in zip(g.team, g.title)}})
gf = R.game_forecasts()
data["record"] = {
    "snapshots": wide,
    "changes": [{"from": c["from"], "to": c["to"], "what": c["what_happened"],
                 "moves": {t: float(v) for t, v in c["moves"].items()}} for c in R.changes()],
    "games": [] if gf.empty else [
        {"game": r["Game"], "matchup": r["Matchup"], "first_pitch": r["First pitch (UTC)"],
         "made": r["Forecast made (UTC)"], "fav": r["Model favorite"], "p_fav": float(r["Favorite's chance"]),
         "winner": r["Winner"] if isinstance(r["Winner"], str) else None,
         "called": bool(r["Called it"]) if isinstance(r["Called it"], (bool, np.bool_)) else None}
        for _, r in gf.iterrows()],
    "game_summary": R.game_summary(),
    "score": R.score(),
    "repo": R.REPO,
}
def clean(x):
    """Strict JSON: missing values (NaN) become null, so the page and REPORT.md
    never mistake "not played yet" for a value."""
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        return None if math.isnan(x) or math.isinf(x) else float(x)
    return x


data = clean(data)
DEST.mkdir(parents=True, exist_ok=True)
(DEST / "data.json").write_text(json.dumps(data, indent=1, allow_nan=False))
html = (REP / "template.html").read_text()
assert "/*__DATA__*/null" in html
(DEST / "index.html").write_text(html.replace("/*__DATA__*/null", json.dumps(data, allow_nan=False)))
print("wrote report/index.html")
