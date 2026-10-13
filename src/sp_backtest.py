"""Step 5c — Does adjusting each postseason game for its starting pitchers help?

The team ratings treat every game alike, so an ace and a 4th starter look the
same. This tests the obvious fix on 2015–2025 postseasons (2020 excluded: no
comparable season stats):

  runs_allowed(team) += w * (starter_FIP - team's average-starter FIP)

where FIP is regressed toward league average (+60 IP) and the team average is
weighted by games started. w = 0 is the current model; ~0.55 matches a
starter's typical share of October innings.

Data: one bulk pitching-stats call per season (cached in data/raw/, git-ignored).
The bulk endpoint lists each pitcher once with full-season totals under his
final team, so a traded starter's whole season counts toward that team's
rotation average. That's a small known distortion.

Output: outputs/sp_backtest.csv, outputs/sp_backtest_summary.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from fetch_data import API, get_json
from model import fit, log_loss, pythagenpat

ROOT = Path(__file__).resolve().parents[1]
SEASONS = [2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025]
WEIGHTS = [0.0, 0.15, 0.3, 0.55, 0.8, 1.0]
IP0 = 60.0


def fip_core(s):
    return 13 * s.get("homeRuns", 0) + 3 * (s.get("baseOnBalls", 0) + s.get("hitByPitch", 0)) - 2 * s.get("strikeOuts", 0)


def pitcher_tables(season):
    data = get_json(f"{API}/stats", {"stats": "season", "group": "pitching", "season": season,
                                     "sportIds": 1, "playerPool": "ALL", "limit": 3000},
                    f"pitching_{season}.json")
    df = pd.DataFrame([{"name": x["player"]["fullName"], "team": x.get("team", {}).get("name"),
                        "outs": x["stat"].get("outs", 0), "gs": x["stat"].get("gamesStarted", 0),
                        "er": x["stat"].get("earnedRuns", 0), "core": fip_core(x["stat"])}
                       for x in data["stats"][0]["splits"]])
    df = df[df.outs > 0]
    ip = df.outs.sum() / 3
    c_fip = 9 * df.er.sum() / ip - df.core.sum() / ip
    lg = df.core.sum() / ip + c_fip
    pip = df.outs / 3
    df["fip"] = ((df.core / pip + c_fip) * pip + lg * IP0) / (pip + IP0)
    quality = df.groupby("name").fip.first().to_dict()
    st = df[df.gs > 0]
    team_avg = st.groupby("team").apply(lambda t: (t.fip * t.gs).sum() / t.gs.sum(), include_groups=False).to_dict()
    return quality, team_avg


def predictions(cases, w):
    p, y = [], []
    for m, quality, team_avg, games in cases:
        for g in games.itertuples():
            rh, ra = m.exp_runs(g.home, g.away)
            qa = quality.get(g.away_prob_sp, team_avg[g.away])
            qh = quality.get(g.home_prob_sp, team_avg[g.home])
            rh = max(rh + w * (qa - team_avg[g.away]), 0.5)
            ra = max(ra + w * (qh - team_avg[g.home]), 0.5)
            p.append(pythagenpat(rh, ra))
            y.append(int(g.home_runs > g.away_runs))
    return np.array(p), np.array(y)


def main():
    games = pd.read_csv(ROOT / "data/processed/games.csv")
    cases, n_named, n_total = [], 0, 0
    for s in SEASONS:
        gs = games[games.season == s]
        quality, team_avg = pitcher_tables(s)
        post = gs[gs.game_type != "R"]
        n_total += 2 * len(post)
        n_named += post.home_prob_sp.isin(quality).sum() + post.away_prob_sp.isin(quality).sum()
        cases.append((fit(gs[gs.game_type == "R"]), quality, team_avg, post))

    rows = []
    for w in WEIGHTS:
        p, y = predictions(cases, w)
        rows.append({"starter_weight": w, "log_loss": log_loss(p, y), "brier": float(np.mean((p - y) ** 2)), "n": len(y)})
    res = pd.DataFrame(rows)
    res.to_csv(ROOT / "outputs/sp_backtest.csv", index=False)

    # Paired bootstrap: realistic weight vs none
    p0, y = predictions(cases, 0.0)
    p1, _ = predictions(cases, 0.55)
    nll = lambda p: -(y * np.log(p) + (1 - y) * np.log(1 - p))
    diff = nll(p1) - nll(p0)  # negative = starter model better
    rng = np.random.default_rng(0)
    boot = np.array([diff[rng.integers(0, len(diff), len(diff))].mean() for _ in range(2000)])
    summary = {"n_games": int(len(y)), "starter_match_rate": n_named / n_total,
               "log_loss_none": float(nll(p0).mean()), "log_loss_w055": float(nll(p1).mean()),
               "share_boot_better": float((boot < 0).mean()),
               "improvement_ci90": [float(-np.percentile(boot, 95)), float(-np.percentile(boot, 5))]}
    (ROOT / "outputs/sp_backtest_summary.json").write_text(json.dumps(summary, indent=2))
    print(res.round(4).to_string(index=False))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
