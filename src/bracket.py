"""Bracket logic shared by predict.py, sensitivity.py and the tests.

Pure functions: no file I/O. Each takes the DataFrames it needs as arguments.

A series state is a tuple (teams, home_order, wins):
  teams      : [team_a, team_b] (sorted)
  home_order : home team for games 1..7, from the real MLB schedule
  wins       : {team: games won so far}
"""
import pandas as pd

from simulate import series_win_prob

ROUND_TYPES = {"F": "Wild Card", "D": "Division Series", "L": "LCS", "W": "World Series"}


def series_states(sched_season, post_games, game_type, known_teams=None):
    """Current state of every series of one round, keyed by series description.

    sched_season : one season's full schedule (incl. unplayed "if necessary" games)
    post_games   : that season's completed postseason games
    known_teams  : real club names. A series whose participants aren't known yet
                   is skipped: MLB lists them as placeholders ("AL Champion",
                   team ids 21/31). Without the list, names containing
                   "Champion" or "Winner" are treated as placeholders.
    """
    def real(t):
        if known_teams is not None:
            return t in known_teams
        return "Champion" not in t and "Winner" not in t

    s = sched_season[(sched_season.game_type == game_type) & sched_season.home.notna()]
    states = {}
    for desc, grp in s.groupby("series_desc"):
        grp = grp.drop_duplicates("series_game", keep="last").sort_values("series_game")
        teams = sorted(set(grp.home) | set(grp.away))
        if len(teams) != 2 or not all(real(t) for t in teams):
            continue
        played = post_games[(post_games.game_type == game_type)
                            & post_games.home.isin(teams) & post_games.away.isin(teams)]
        wins = {t: 0 for t in teams}
        for x in played.itertuples():
            wins[x.home if x.home_runs > x.away_runs else x.away] += 1
        home = list(grp.home)
        if game_type in ("L", "W") and len(home) < 7:
            # MLB drops unneeded "if necessary" games once a series ends; restore
            # the 2-3-2 order so counterfactuals (e.g. odds before the LCS) still work.
            h0 = home[0]
            other = teams[1] if teams[0] == h0 else teams[0]
            home += [h0, h0, other, other, other, h0, h0][len(home):]
        states[desc] = (teams, home, wins)
    return states


def win_pct(reg_games):
    w = reg_games.home.where(reg_games.home_runs > reg_games.away_runs, reg_games.away).value_counts()
    g = pd.concat([reg_games.home, reg_games.away]).value_counts()
    return (w.reindex(g.index, fill_value=0) / g), w.reindex(g.index, fill_value=0)


def ws_home_team(a, b, reg_games, divisions):
    """MLB rule: better regular-season record hosts. Tiebreakers: head-to-head
    record, then record within one's own division. Returns (home_team, reason)."""
    pct, _ = win_pct(reg_games)
    if pct[a] != pct[b]:
        return (a if pct[a] > pct[b] else b), "better record"
    h2h = reg_games[((reg_games.home == a) & (reg_games.away == b)) | ((reg_games.home == b) & (reg_games.away == a))]
    if len(h2h):
        aw = (h2h.home.where(h2h.home_runs > h2h.away_runs, h2h.away) == a).sum()
        if aw * 2 != len(h2h):
            return (a if aw * 2 > len(h2h) else b), "head-to-head"

    def div_pct(t):
        mates = [x for x, d in divisions.items() if d == divisions[t] and x != t]
        gm = reg_games[((reg_games.home == t) & reg_games.away.isin(mates)) |
                       ((reg_games.away == t) & reg_games.home.isin(mates))]
        won = (gm.home.where(gm.home_runs > gm.away_runs, gm.away) == t).sum()
        return won / len(gm) if len(gm) else 0.0

    da, db = div_pct(a), div_pct(b)
    if da != db:
        return (a if da > db else b), "intradivision record"
    raise ValueError(f"World Series home field unresolved for {a} vs {b}: apply MLB's further tiebreakers by hand")


def ws_home_order(al, nl, reg_games, divisions):
    top, _ = ws_home_team(al, nl, reg_games, divisions)
    other = nl if top == al else al
    return [top, top, other, other, other, top, top]


def bracket_odds(r, alcs, nlcs, reg_games, divisions, ws_state=None,
                 alcs_wins=None, nlcs_wins=None):
    """Pennant and title odds for the four LCS teams.

    r          : ratings (anything with p_home_win(home, away))
    alcs, nlcs : series states; a finished LCS (4 wins) gives that team P=1
    ws_state   : World Series state once it has started (overrides the matchup sum)
    """
    (al_t, al_home, al_w), (nl_t, nl_home, nl_w) = alcs, nlcs
    al_w = al_w if alcs_wins is None else alcs_wins
    nl_w = nl_w if nlcs_wins is None else nlcs_wins
    pen = {}
    for teams, home, w in ((al_t, al_home, al_w), (nl_t, nl_home, nl_w)):
        a, b = teams
        pen[a] = series_win_prob(r, a, b, home, 4, w[a], w[b])
        pen[b] = 1 - pen[a]

    out = {t: {"pennant": pen[t], "ws": 0.0} for t in pen}
    matchups = {}
    for al in al_t:
        for nl in nl_t:
            joint = pen[al] * pen[nl]
            if ws_state and set(ws_state[0]) == {al, nl}:
                teams, home, w = ws_state
                p_al = series_win_prob(r, al, nl, home, 4, w[al], w[nl])
            else:
                p_al = series_win_prob(r, al, nl, ws_home_order(al, nl, reg_games, divisions), 4)
            out[al]["ws"] += joint * p_al
            out[nl]["ws"] += joint * (1 - p_al)
            matchups[f"{al} vs {nl}"] = {"p_matchup": joint, "p_al_wins": p_al}
    return out, matchups


def american_to_prob(odds):
    odds = float(odds)
    return 100 / (odds + 100) if odds > 0 else -odds / (-odds + 100)


def devig_power(implied):
    """Remove the bookmaker margin with the power method: find k so that
    sum(q_i ** k) == 1. Unlike proportional scaling, it takes more margin off
    longshots, which is where futures markets overcharge (favorite-longshot bias)."""
    from scipy.optimize import brentq
    q = list(implied)
    k = brentq(lambda k: sum(x ** k for x in q) - 1, 0.5, 5.0)
    return [x ** k for x in q]
