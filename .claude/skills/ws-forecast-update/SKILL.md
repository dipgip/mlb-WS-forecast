---
name: ws-forecast-update
description: Refresh the 2026 World Series forecast after new postseason games are played. Use when asked to update, re-run, or refresh the MLB prediction, or after an LCS/World Series game finishes.
---

# Refresh the World Series forecast

The model is frozen at v2 (λ=80, no recency weighting, home field calibrated from wins; see LOG.md Steps 2 and 10). A refresh only brings in new games, rosters and prices.

1. If there are new sportsbook futures prices, append rows to `data/market_odds.csv` (capture date, source, URL, team, American odds). Never overwrite old rows.
2. Pull new data and recompute, without re-tuning:
   ```
   .venv/bin/python -m unittest discover -s tests
   .venv/bin/python src/fetch_data.py
   .venv/bin/python src/predict.py
   .venv/bin/python src/fetch_rosters.py
   .venv/bin/python src/roster_adjust.py
   .venv/bin/python src/market.py
   .venv/bin/python src/sensitivity.py
   .venv/bin/python report/build.py
   ```
   Teams and roster date come from the live bracket and today's date. A World Series in progress is picked up automatically from game type "W".
3. Do NOT re-run tune.py and change λ, and do not change the model after seeing results. That would be fitting to the answer.
4. Append a dated "Update" entry to LOG.md: the new series state, title odds with 90% intervals for each team, and the change since the previous entry.
5. Republish `report/index.html` to the same artifact URL (recorded in LOG.md Step 7).
6. Commit and push with the repo's no-reply identity. Never commit `data/raw/`; it's git-ignored because it's MLB's copyrighted content.
