"""Step 4 — Fit 2026 ratings and compute World Series odds from the live bracket.

Everything is exact (dynamic programming over series states), so no Monte
Carlo noise. Home-field order for each series comes from the real MLB
schedule. World Series home field follows MLB rules (better record, then
head-to-head, then intradivision record); see bracket.ws_home_team.

Outputs: outputs/ratings_2026.csv, outputs/odds_2026.json. The permanent,
timestamped record of each forecast is written separately by snapshot.py.
"""
import json
from pathlib import Path

import pandas as pd

import bracket as B
from model import fit

ROOT = Path(__file__).resolve().parents[1]
SEASON = 2026
LAM = 80


def load():
    """Everything predict/sensitivity need, read once from data/processed."""
    games = pd.read_csv(ROOT / "data/processed/games.csv")
    sched = pd.read_csv(ROOT / "data/processed/schedule_all.csv")
    teams = pd.read_csv(ROOT / "data/processed/teams.csv")
    g = games[games.season == SEASON]
    d = {
        "reg": g[g.game_type == "R"],
        "post": g[g.game_type != "R"],
        "sched": sched[sched.season == SEASON],
        "divisions": dict(zip(teams.team, teams.division)),
        "team_ids": dict(zip(teams.team, teams.id)),
    }
    known = set(teams.team)
    lcs = B.series_states(d["sched"], d["post"], "L", known)
    d["alcs"] = lcs["AL Championship Series"]
    d["nlcs"] = lcs["NL Championship Series"]
    d["ws"] = next(iter(B.series_states(d["sched"], d["post"], "W", known).values()), None)
    d["as_of"] = str(d["post"].date.max())
    return d


def alive_teams(d):
    """Teams that can still win the title."""
    if d["ws"]:
        return [t for t in d["ws"][0] if max(d["ws"][2].values()) < 4 or d["ws"][2][t] == 4]
    return [t for teams, _, w in (d["alcs"], d["nlcs"]) for t in teams
            if max(w.values()) < 4 or w[t] == 4]


def odds(r, d, **kw):
    return B.bracket_odds(r, d["alcs"], d["nlcs"], d["reg"], d["divisions"], ws_state=d["ws"], **kw)


def main(verbose=True):
    d = load()
    r = fit(d["reg"], lam=LAM)
    _, wins = B.win_pct(d["reg"])
    tab = r.table()
    tab["W"] = tab.team.map(wins).fillna(0).astype(int)
    tab["rank"] = range(1, len(tab) + 1)
    tab.to_csv(ROOT / "outputs/ratings_2026.csv", index=False)

    now, matchups = odds(r, d)
    zero = {t: 0 for t in d["alcs"][0] + d["nlcs"][0]}
    pre_lcs, _ = B.bracket_odds(r, d["alcs"], d["nlcs"], d["reg"], d["divisions"],
                                alcs_wins={t: 0 for t in d["alcs"][0]},
                                nlcs_wins={t: 0 for t in d["nlcs"][0]})
    ws_home = {k: dict(zip(("team", "reason"), B.ws_home_team(*k.split(" vs "), d["reg"], d["divisions"])))
               for k in matchups}

    result = {
        "as_of": d["as_of"],
        "series_state": {"ALCS": d["alcs"][2], "NLCS": d["nlcs"][2],
                         **({"WS": d["ws"][2]} if d["ws"] else {})},
        "odds_now": now,
        "odds_before_lcs": pre_lcs,
        "ws_matchups": matchups,
        "ws_home_field": ws_home,
        "alive": alive_teams(d),
        "home_win_rate_equal_teams": r.p_home_win(r.teams[0], r.teams[0]),
    }
    (ROOT / "outputs/odds_2026.json").write_text(json.dumps(result, indent=2))

    if verbose:
        four = list(zero)
        cols = ["rank", "team", "W", "exp_RS_pg", "exp_RA_pg", "exp_wpct"]
        print("Ratings (top 10 + final four):")
        print(tab[(tab["rank"] <= 10) | tab.team.isin(four)][cols].round(3).to_string(index=False))
        print(f"\nHome win % between equal teams: {result['home_win_rate_equal_teams']:.3f}")
        print("Series state:", result["series_state"])
        print("\n               pennant   WS   (before LCS: pennant / WS)")
        for t in sorted(now, key=lambda t: -now[t]["ws"]):
            print(f"{t:24s} {now[t]['pennant']:.3f}  {now[t]['ws']:.3f}     "
                  f"{pre_lcs[t]['pennant']:.3f} / {pre_lcs[t]['ws']:.3f}")
        print("\nWorld Series matchups:")
        for k, v in sorted(matchups.items(), key=lambda kv: -kv[1]["p_matchup"]):
            print(f"  {k:48s} P(matchup)={v['p_matchup']:.3f}  P(AL wins)={v['p_al_wins']:.3f}"
                  f"  home: {ws_home[k]['team'].split()[-1]} ({ws_home[k]['reason']})")
    return r, result


if __name__ == "__main__":
    main()
