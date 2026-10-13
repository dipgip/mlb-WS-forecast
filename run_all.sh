#!/usr/bin/env bash
# Rebuild the entire forecast from scratch: data -> tuning -> backtest -> 2026 odds -> rosters -> sensitivity.
set -euo pipefail
cd "$(dirname "$0")"
PY=.venv/bin/python
$PY src/fetch_data.py
$PY src/tune.py
$PY src/backtest.py
$PY src/predict.py
$PY src/fetch_rosters.py
$PY src/roster_adjust.py
$PY src/sensitivity.py
