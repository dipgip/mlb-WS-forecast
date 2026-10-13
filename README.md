# 2026 World Series Prediction

**Call (as of Oct 13, 2026): Milwaukee Brewers, 57%** (90% interval 43–70% from 1,000 resampled seasons). Milwaukee leads under all 11 modeling scenarios, and the betting market says about 47%.

![tests](https://github.com/dipgip/mlb-WS-forecast/actions/workflows/tests.yml/badge.svg)

- `LOG.md` — the step-by-step record of every decision and result. Start here.
- `REVIEW.md` — a partner review of the weak links, with evidence and the fixes made.
- **[report/REPORT.md](report/REPORT.md) — the full report, readable right here on GitHub.**
- **Dashboard** — an interactive Streamlit app with a live what-if simulator. It runs locally; nothing is hosted:
  ```bash
  ./run_dashboard.sh
  ```
  Then open http://localhost:8501. It's bound to this machine only.
- `report/index.html` — the same report as an interactive web page (open it in a browser for hover detail).
- `run_all.sh` — rebuilds everything from the MLB Stats API.

**Data:** raw API responses (`data/raw/`) are not committed. They are MLB Advanced Media content, and the fetch scripts rebuild them. The committed `data/processed/` tables contain only game facts (dates, teams, scores, starting pitchers).

| Step | Script | Output |
|---|---|---|
| 1. Data pull, 2015–2026 | `src/fetch_data.py` | `data/processed/games.csv` |
| 2. Tune shrinkage and recency on held-out Septembers | `src/tune.py` | `outputs/tuning_grid.csv` |
| 3. Backtest on 11 postseasons | `src/backtest.py` | `outputs/backtest_*.csv` |
| 3b. Does adjusting for starting pitchers help? (No) | `src/sp_backtest.py` | `outputs/sp_backtest*.{csv,json}` |
| 4. 2026 ratings and exact bracket odds | `src/predict.py`, `src/bracket.py` | `outputs/ratings_2026.csv`, `outputs/odds_2026.json`, `outputs/forecast_history.csv` |
| 5a. Postseason roster adjustment | `src/fetch_rosters.py`, `src/roster_adjust.py` | `outputs/roster_adjustments_2026.json` |
| 5b. Uncertainty, sensitivity and what-ifs | `src/sensitivity.py` | `outputs/uncertainty.csv`, `outputs/sensitivity.csv`, `outputs/whatif_next_game.csv` |
| 6. Market comparison | `src/market.py` (prices in `data/market_odds.csv`) | `outputs/market_2026.json` |
| 7. Report | `report/build.py` (interactive), `report/build_md.py` (static) | `report/index.html`, `report/REPORT.md` + `report/figures/` |

Tests: `.venv/bin/python -m unittest discover -s tests -v` (they also run on every push via GitHub Actions).

Setup: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` (Python 3.11)

Model: a ridge-regularized Poisson regression on runs, with offense and defense terms, converted to win probability with Pythagenpat. Home field is calibrated to the observed home win rate, because run totals understate it. Series odds are computed exactly by dynamic programming over series states and the real home/away order.
