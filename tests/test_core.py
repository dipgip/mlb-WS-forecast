"""Core correctness tests. Synthetic data only: no network, no MLB files.

Run:  .venv/bin/python -m unittest discover -s tests -v
"""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import bracket as B  # noqa: E402
from model import fit, pythagenpat  # noqa: E402
from simulate import series_win_prob  # noqa: E402


class FixedP:
    """Ratings stub: home team wins with a fixed probability per team."""
    def __init__(self, strength, hfa=0.04):
        self.s, self.hfa = strength, hfa

    def p_home_win(self, home, away, neutral=False):
        x = self.s[home] - self.s[away] + (0 if neutral else self.hfa)
        return 1 / (1 + np.exp(-x))


def simulate_series(r, a, b, home_order, a_w, b_w, n, seed=0):
    rng = np.random.default_rng(seed)
    won = 0
    for _ in range(n):
        aw, bw = a_w, b_w
        while aw < 4 and bw < 4:
            h = home_order[aw + bw]
            p = r.p_home_win(a, b) if h == a else 1 - r.p_home_win(b, a)
            if rng.random() < p:
                aw += 1
            else:
                bw += 1
        won += aw == 4
    return won / n


class TestSeriesMath(unittest.TestCase):
    def setUp(self):
        self.r = FixedP({"A": 0.3, "B": 0.0})
        self.order = ["A", "A", "B", "B", "B", "A", "A"]

    def test_exact_matches_simulation(self):
        for a_w, b_w in [(0, 0), (0, 2), (2, 1), (3, 3)]:
            exact = series_win_prob(self.r, "A", "B", self.order, 4, a_w, b_w)
            sim = simulate_series(self.r, "A", "B", self.order, a_w, b_w, 40000)
            self.assertAlmostEqual(exact, sim, delta=0.01, msg=f"state {a_w}-{b_w}")

    def test_finished_series(self):
        self.assertEqual(series_win_prob(self.r, "A", "B", self.order, 4, 4, 2), 1.0)
        self.assertEqual(series_win_prob(self.r, "A", "B", self.order, 4, 1, 4), 0.0)

    def test_equal_teams_symmetric_home_order(self):
        r = FixedP({"A": 0.0, "B": 0.0}, hfa=0.0)
        self.assertAlmostEqual(series_win_prob(r, "A", "B", self.order, 4), 0.5)


class TestModel(unittest.TestCase):
    def test_pythagenpat_symmetry(self):
        self.assertAlmostEqual(pythagenpat(4.5, 4.5), 0.5)
        self.assertAlmostEqual(pythagenpat(5.0, 4.0) + pythagenpat(4.0, 5.0), 1.0)

    def test_recovers_known_ratings_and_home_rate(self):
        rng = np.random.default_rng(3)
        teams = [f"T{i}" for i in range(12)]
        off = rng.normal(0, 0.12, 12)
        dfn = rng.normal(0, 0.12, 12)
        rows = []
        for _ in range(6000):
            h, a = rng.choice(12, 2, replace=False)
            rh = rng.poisson(np.exp(np.log(4.4) + 0.03 + off[h] - dfn[a]))
            ra = rng.poisson(np.exp(np.log(4.4) + off[a] - dfn[h]))
            if rh != ra:
                rows.append({"home": teams[h], "away": teams[a], "home_runs": rh,
                             "away_runs": ra, "date": "2026-06-01"})
        g = pd.DataFrame(rows)
        r = fit(g, lam=5)
        est = np.array([r.off[r.idx(t)] for t in teams])
        self.assertGreater(np.corrcoef(est, off)[0, 1], 0.9)
        est_d = np.array([r.dfn[r.idx(t)] for t in teams])
        self.assertGreater(np.corrcoef(est_d, dfn)[0, 1], 0.9)
        # Home field is calibrated so two league-average teams reproduce the observed home win rate
        observed = (g.home_runs > g.away_runs).mean()
        avg = np.exp(r.mu)
        self.assertAlmostEqual(pythagenpat(avg * np.exp(r.hfa), avg), observed, places=6)

    def test_shrinkage_pulls_toward_average(self):
        g = pd.DataFrame({"home": ["A", "B"] * 10, "away": ["B", "A"] * 10,
                          "home_runs": [6, 2] * 10, "away_runs": [2, 6] * 10, "date": "2026-06-01"})
        loose, tight = fit(g, lam=1), fit(g, lam=200)
        self.assertGreater(abs(loose.off[loose.idx("A")]), abs(tight.off[tight.idx("A")]))


def game(home, away, hr, ar):
    return {"home": home, "away": away, "home_runs": hr, "away_runs": ar}


class TestWorldSeriesHomeField(unittest.TestCase):
    divisions = {"A": "East", "X": "East", "B": "West", "Y": "West"}

    def test_better_record_hosts(self):
        g = pd.DataFrame([game("A", "X", 5, 1), game("A", "X", 5, 1), game("B", "Y", 1, 5)])
        self.assertEqual(B.ws_home_team("A", "B", g, self.divisions), ("A", "better record"))

    def test_head_to_head_breaks_tie(self):
        g = pd.DataFrame([game("A", "X", 5, 1), game("Y", "B", 1, 5),
                          game("A", "B", 1, 3), game("X", "A", 1, 4), game("B", "Y", 2, 7)])
        # A and B both 2-1; B won the head-to-head game
        self.assertEqual(B.ws_home_team("A", "B", g, self.divisions), ("B", "head-to-head"))

    def test_unresolved_tie_raises(self):
        g = pd.DataFrame([game("A", "B", 3, 1), game("B", "A", 3, 1)])
        with self.assertRaises(ValueError):
            B.ws_home_team("A", "B", g, {"A": "East", "B": "West"})


class TestSeriesStates(unittest.TestCase):
    def test_parses_state_and_skips_placeholders(self):
        sched = pd.DataFrame([
            {"game_type": "L", "series_desc": "NLCS", "series_game": i + 1, "home": h, "away": a}
            for i, (h, a) in enumerate([("M", "D"), ("M", "D"), ("D", "M"), ("D", "M"), ("D", "M"), ("M", "D"), ("M", "D")])
        ] + [{"game_type": "W", "series_desc": "World Series", "series_game": 1,
              "home": "NL Champion", "away": "AL Champion"}])
        post = pd.DataFrame([{"game_type": "L", "home": "M", "away": "D", "home_runs": 2, "away_runs": 1},
                             {"game_type": "L", "home": "M", "away": "D", "home_runs": 7, "away_runs": 4}])
        st = B.series_states(sched, post, "L")["NLCS"]
        self.assertEqual(st[0], ["D", "M"])
        self.assertEqual(st[1][:3], ["M", "M", "D"])
        self.assertEqual(st[2], {"D": 0, "M": 2})
        self.assertEqual(B.series_states(sched, post, "W"), {})
        self.assertEqual(B.series_states(sched, post, "W", known_teams={"M", "D"}), {})
        self.assertIn("NLCS", B.series_states(sched, post, "L", known_teams={"M", "D"}))

    def test_decided_series_keeps_full_home_order(self):
        # After a sweep MLB removes games 5-7 from the schedule
        sched = pd.DataFrame([
            {"game_type": "L", "series_desc": "NLCS", "series_game": i + 1, "home": h, "away": a}
            for i, (h, a) in enumerate([("M", "D"), ("M", "D"), ("D", "M"), ("D", "M")])
        ])
        post = pd.DataFrame([{"game_type": "L", "home": h, "away": a, "home_runs": hr, "away_runs": ar}
                             for h, a, hr, ar in [("M", "D", 2, 1), ("M", "D", 7, 4), ("D", "M", 2, 6), ("D", "M", 4, 6)]])
        st = B.series_states(sched, post, "L")["NLCS"]
        self.assertEqual(st[1], ["M", "M", "D", "D", "D", "M", "M"])
        self.assertEqual(st[2], {"D": 0, "M": 4})


class TestMarket(unittest.TestCase):
    def test_american_odds(self):
        self.assertAlmostEqual(B.american_to_prob(100), 0.5)
        self.assertAlmostEqual(B.american_to_prob(-200), 2 / 3)

    def test_power_devig_sums_to_one_and_trims_longshots(self):
        q = [B.american_to_prob(a) for a in (105, 350, 400, 475)]
        fair = B.devig_power(q)
        self.assertAlmostEqual(sum(fair), 1.0, places=9)
        prop = [x / sum(q) for x in q]
        self.assertGreater(fair[0], prop[0])   # favorite gets more
        self.assertLess(fair[-1], prop[-1])    # longshot gets less


if __name__ == "__main__":
    unittest.main()
