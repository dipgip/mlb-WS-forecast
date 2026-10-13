# 2026 World Series Prediction

**Call (as of Oct 13, 2026): Milwaukee Brewers, 57%.** The range across sensitivity scenarios is 51–60%, and the betting market says about 45%.

- `LOG.md` — the step-by-step record of every decision and result. Start here.
- `report/index.html` — the presentation of findings.
- `run_all.sh` — rebuilds everything from the MLB Stats API.

**Data:** raw API responses (`data/raw/`) are not committed. They are MLB Advanced Media content, and the fetch scripts rebuild them. The committed `data/processed/` tables contain only game facts (dates, teams, scores, starting pitchers).

| Step | Script | Output |
|---|---|---|
| 1. Data pull, 2015–2026 | `src/fetch_data.py` | `data/processed/games.csv` |
| 2. Tune shrinkage and recency on held-out Septembers | `src/tune.py` | `outputs/tuning_grid.csv` |
| 3. Backtest on 11 postseasons | `src/backtest.py` | `outputs/backtest_*.csv` |
| 4. 2026 ratings and exact bracket odds | `src/predict.py` | `outputs/ratings_2026.csv`, `outputs/odds_2026.json` |
| 5a. Postseason roster adjustment | `src/fetch_rosters.py`, `src/roster_adjust.py` | `outputs/roster_adjustments_2026.json` |
| 5b. Sensitivity and what-ifs | `src/sensitivity.py` | `outputs/sensitivity.csv`, `outputs/whatif_next_game.csv` |

Setup: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` (Python 3.11)

Model: a ridge-regularized Poisson regression on runs, with offense, defense and home-field terms, converted to win probability with Pythagenpat. Series odds are computed exactly by dynamic programming over series states and the real home/away order.
