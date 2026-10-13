"""Series math and bracket Monte Carlo.

series_win_prob: exact probability (dynamic programming, no sampling noise)
that team A wins a series given the remaining home/away order of games.
"""
from functools import lru_cache


def series_win_prob(ratings, team_a, team_b, home_order, wins_needed,
                    a_wins=0, b_wins=0, p_adjust=None):
    """P(team_a wins the series).

    home_order : list of home teams for game 1..N of the full series
    a_wins/b_wins : current series state (games already played)
    p_adjust : optional fn(p_a, game_index) -> p_a for scenario tweaks
    """
    p_game = []
    for k, home in enumerate(home_order):
        if home == team_a:
            p = ratings.p_home_win(team_a, team_b)
        else:
            p = 1 - ratings.p_home_win(team_b, team_a)
        if p_adjust:
            p = p_adjust(p, k)
        p_game.append(p)

    @lru_cache(None)
    def f(a, b):
        if a == wins_needed:
            return 1.0
        if b == wins_needed:
            return 0.0
        p = p_game[a + b]
        return p * f(a + 1, b) + (1 - p) * f(a, b + 1)

    return f(a_wins, b_wins)
