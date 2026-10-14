---
name: ws-forecast-update
description: Refresh the 2026 World Series forecast after new postseason games, record pregame forecasts, and publish. Use when asked to update, re-run, or refresh the MLB prediction, or when the scheduled refresh runs.
---

# Refresh the World Series forecast

Project: `/Users/koonima/Documents/mlb_showcase`. GitHub: `git@github.com:dipgip/mlb-WS-forecast.git` (push over SSH).

**Purpose:** record the model's forecasts *before* the games they predict, so the trail can be graded. A refresh doesn't improve the model. The model is frozen at v2 (λ=80, no recency weighting, home field calibrated from wins). Team ratings come from the 2026 regular season only; new games change only the bracket state.

## Hard rules
- Never modify or delete anything already in `forecasts/`. It's append-only, and `tests/test_forecast_record.py` checks every file against `forecasts/MANIFEST.sha256`.
- Never re-tune or change the model, and never run `src/tune.py` or `src/backtest.py` during a refresh.
- Never commit `data/raw/`; it's MLB's copyrighted content and git-ignored.
- Commit as the repo's configured no-reply identity. Never force-push or rewrite history.
- If the tests fail, don't push. Report the failure instead.

## Steps

The refresh pushes in **two phases**, so a report bug can never hold the forecast record back past first pitch. (On 2026-10-14 a report crash left valid forecasts unpushed.)

### Phase 1: record forecasts (time-critical)
1. `cd /Users/koonima/Documents/mlb_showcase && git pull --ff-only`
2. Pull new data and recompute:
   ```
   .venv/bin/python src/fetch_data.py
   .venv/bin/python src/predict.py
   .venv/bin/python src/fetch_rosters.py
   .venv/bin/python src/roster_adjust.py
   ```
3. **Market prices (optional).** Search the web for World Series futures odds published *today* by a reputable outlet that lists every team still alive. If you find them, append one row per team to `data/market_odds.csv` (capture date, source, URL, team, American odds), recording the prices exactly as published. Never edit old rows. If nothing qualifies, skip this step.
4. ```
   .venv/bin/python src/market.py
   .venv/bin/python src/sensitivity.py
   .venv/bin/python src/snapshot.py
   .venv/bin/python -m unittest tests.test_core tests.test_forecast_record
   ```
5. If `forecasts/` changed and those tests pass, commit `forecasts/ data/ outputs/` right away. Tag new snapshots with `forecast-<YYYY-MM-DD>-<short state>` (annotated), then push main and the tag. **If these tests fail, push nothing and report it.**

### Phase 2: reports (not time-critical)
6. ```
   .venv/bin/python report/build.py
   .venv/bin/python report/build_md.py
   .venv/bin/python -m unittest discover -s tests
   ```
7. If anything changed, append a dated "Update" entry to `LOG.md`:
   - the results since the last entry;
   - the new series state;
   - title odds with 90% intervals for each team, and the change since the last snapshot;
   - which games were newly forecast, with their probabilities;
   - how the latest graded games went.
8. If the full test suite passes, commit and push the reports and `LOG.md`. If a report step fails, the forecasts are already safe from Phase 1. Don't push broken reports; report the error clearly instead.
9. If the Artifact tool is available, republish `report/index.html` to https://claude.ai/artifact/4vMEBXCDwCmGWZfo77XmFP. The Streamlit dashboard redeploys from the push on its own.

## When the World Series is over
`record.score()` returns the champion and scores every live snapshot. Add a final "Grade" entry to `LOG.md` with the champion, the title-forecast scores against the market and equal odds, and the per-game record. Commit, tag `forecast-final`, and push. Then the scheduled refresh can be turned off.
