---
name: ws-forecast-update
description: Refresh the 2026 World Series forecast after new postseason games are played. Use when asked to update, re-run, or refresh the MLB prediction, or after an LCS/World Series game finishes.
---

# Refresh the World Series forecast

The model and its hyperparameters are frozen (λ=80, no recency weighting; see LOG.md Step 2).
Only the live bracket state and rosters change, so an update only needs fresh data.

1. Re-pull the current season. Past seasons are cached, and 2026 always refreshes:
   `.venv/bin/python src/fetch_data.py`
2. Re-pull rosters and stats: set `ROSTER_DATE` (and drop eliminated teams from `TEAM_IDS`) in `src/fetch_rosters.py`, then run `.venv/bin/python src/fetch_rosters.py`.
3. `.venv/bin/python src/predict.py`, then `.venv/bin/python src/roster_adjust.py`, then `.venv/bin/python src/sensitivity.py`.
4. Do NOT re-run tune.py or backtest.py, and do not change λ after seeing results. That would be fitting to the answer.
5. Append a dated "Update" entry to LOG.md with the new series state, the title odds for each team, and the change since the previous entry.
6. Update the report page (`report/index.html`) numbers and republish it to the same artifact URL.

Once a series ends, `bracket_odds` handles it automatically: a 4-win state gives that team P=1.
For the World Series itself, predict.py would need the WS state read from game_type "W". Add that the first time a WS game is final.
