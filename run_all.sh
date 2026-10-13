#!/usr/bin/env bash
# Rebuild the entire forecast from scratch, then the report.
#   tests -> data -> tuning -> backtests -> 2026 odds -> rosters -> market -> uncertainty/sensitivity -> report
set -euo pipefail
cd "$(dirname "$0")"
PY=.venv/bin/python
$PY -m unittest discover -s tests
$PY src/fetch_data.py
$PY src/tune.py
$PY src/backtest.py
$PY src/sp_backtest.py
$PY src/predict.py
$PY src/fetch_rosters.py
$PY src/roster_adjust.py
$PY src/market.py
$PY src/sensitivity.py
$PY report/build.py
$PY report/build_md.py
