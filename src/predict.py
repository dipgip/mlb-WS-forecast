"""Step 4 — Fit 2026 ratings and compute World Series odds from the live bracket.

Everything is exact (dynamic programming over series states), so no Monte
Carlo noise. Home-field order for each LCS comes from the real MLB schedule.
World Series home field goes to the team with the better regular-season
record, per MLB rules.

Outputs: outputs/ratings_2026.csv, outputs/odds_2026.json
"""
import json
from pathlib import Path

import pandas as pd

from model import fit
from simulate import series_win_prob

ROOT = Path(__file__).resolve().parents[1]
LAM = 80

games = pd.read_csv(ROOT / "data/processed/games.csv")
sched = pd.read_csv(ROOT / "data/processed/schedule_all.csv")
g26 = games[games.season == 2026]
reg26 = g26[g26.game_type == "R"]
post26 = g26[g26.game_type != "R"]


def record(df):
    w = pd.concat([df.home.where(df.home_runs > df.away_runs, df.away)])
    return w.value_counts()


WINS = record(reg26)


def ws_home_order(al, nl):
    top = al if WINS[al] > WINS[nl] else nl
    other = nl if top == al else al
    return [top, top, other, other, other, top, top]


def bracket_odds(r, alcs, nlcs, alcs_wins=None, nlcs_wins=None):
    """Return {team: {'pennant': p, 'ws': p}} for the four remaining teams."""
    (al_t, al_home, al_w), (nl_t, nl_home, nl_w) = alcs, nlcs
    al_w = al_w if alcs_wins is None else alcs_wins
    nl_w = nl_w if nlcs_wins is None else nlcs_wins
    pen = {}
    a, b = al_t
    pen[a] = series_win_prob(r, a, b, al_home, 4, al_w[a], al_w[b])
    pen[b] = 1 - pen[a]
    a, b = nl_t
    pen[a] = series_win_prob(r, a, b, nl_home, 4, nl_w[a], nl_w[b])
    pen[b] = 1 - pen[a]

    out = {t: {"pennant": pen[t], "ws": 0.0} for t in pen}
    matchups = {}
    for al in al_t:
        for nl in nl_t:
            p_al = series_win_prob(r, al, nl, ws_home_order(al, nl), 4)
            joint = pen[al] * pen[nl]
            out[al]["ws"] += joint * p_al
            out[nl]["ws"] += joint * (1 - p_al)
            matchups[f"{al} vs {nl}"] = {"p_matchup": joint, "p_al_wins": p_al}
    return out, matchups


def main(verbose=True):
    r = fit(reg26, lam=LAM)
    tab = r.table()
    tab["W"] = tab.team.map(WINS).fillna(0).astype(int)
    tab.to_csv(ROOT / "outputs/ratings_2026.csv", index=False)

    # Both LCS share game_type "L"; split them by series description
    s = sched[(sched.season == 2026) & (sched.game_type == "L")]
    states = {}
    for desc, grp in s.groupby("series_desc"):
        grp = grp.drop_duplicates("series_game", keep="last").sort_values("series_game")
        teams = sorted(set(grp.home) | set(grp.away))
        played = post26[(post26.game_type == "L") & post26.home.isin(teams) & post26.away.isin(teams)]
        wins = {t: 0 for t in teams}
        for _, x in played.iterrows():
            wins[x.home if x.home_runs > x.away_runs else x.away] += 1
        states[desc] = (teams, list(grp.home), wins)
    alcs = states["AL Championship Series"]
    nlcs = states["NL Championship Series"]

    now, matchups = bracket_odds(r, alcs, nlcs)
    zero_al = {t: 0 for t in alcs[0]}
    zero_nl = {t: 0 for t in nlcs[0]}
    pre_lcs, _ = bracket_odds(r, alcs, nlcs, alcs_wins=zero_al, nlcs_wins=zero_nl)

    result = {
        "as_of": str(post26.date.max()),
        "series_state": {"ALCS": alcs[2], "NLCS": nlcs[2]},
        "odds_now": now,
        "odds_before_lcs": pre_lcs,
        "ws_matchups": matchups,
        "hfa_runs_multiplier": float(pow(2.718281828, r.hfa)),
    }
    (ROOT / "outputs/odds_2026.json").write_text(json.dumps(result, indent=2))

    if verbose:
        four = alcs[0] + nlcs[0]
        print("Ratings (top 10 + final four):")
        cols = ["team", "W", "exp_RS_pg", "exp_RA_pg", "exp_wpct"]
        print(tab[tab.index.isin(range(10)) | tab.team.isin(four)][cols].round(3).to_string())
        print(f"\nHome-field: x{result['hfa_runs_multiplier']:.3f} runs")
        print("\nSeries state:", result["series_state"])
        print("\n               pennant   WS   (before LCS: pennant / WS)")
        for t in sorted(now, key=lambda t: -now[t]["ws"]):
            print(f"{t:24s} {now[t]['pennant']:.3f}  {now[t]['ws']:.3f}     "
                  f"{pre_lcs[t]['pennant']:.3f} / {pre_lcs[t]['ws']:.3f}")
        print("\nWorld Series matchups:")
        for k, v in sorted(matchups.items(), key=lambda kv: -kv[1]["p_matchup"]):
            print(f"  {k:48s} P(matchup)={v['p_matchup']:.3f}  P(AL wins)={v['p_al_wins']:.3f}")
    return r, result


if __name__ == "__main__":
    main()
