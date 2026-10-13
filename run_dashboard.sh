#!/usr/bin/env bash
# Start the dashboard locally at http://localhost:8501 (bound to this machine only).
set -euo pipefail
cd "$(dirname "$0")"
exec .venv/bin/streamlit run dashboard/app.py --server.port "${PORT:-8501}"
