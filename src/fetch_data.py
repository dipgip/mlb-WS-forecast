"""Step 1 — Pull game-level data from the official MLB Stats API.

Caches raw JSON in data/raw/ so re-runs are fast and reproducible, and writes a
tidy games table to data/processed/games.csv (one row per completed game).

Usage:  .venv/bin/python src/fetch_data.py
"""
import json
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
API = "https://statsapi.mlb.com/api/v1"

SEASONS = list(range(2015, 2027))
# Game types: R = regular season, F = wild card, D = division series,
# L = league championship series, W = World Series
GAME_TYPES = "R,F,D,L,W"


def get_json(url, params, cache_name, refresh=False):
    path = RAW / cache_name
    if path.exists() and not refresh:
        return json.loads(path.read_text())
    for attempt in range(4):
        try:
            r = requests.get(url, params=params, timeout=60)
            r.raise_for_status()
            data = r.json()
            path.write_text(json.dumps(data))
            return data
        except requests.RequestException as e:
            print(f"  retry {attempt + 1}: {e}")
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url} {params}")


def fetch_season(season):
    # The current season is always re-fetched; past seasons are frozen.
    refresh = season == SEASONS[-1]
    data = get_json(
        f"{API}/schedule",
        {"sportId": 1, "season": season, "gameType": GAME_TYPES,
         "hydrate": "probablePitcher"},
        f"schedule_{season}.json",
        refresh=refresh,
    )
    rows = []
    for day in data.get("dates", []):
        for g in day["games"]:
            status = g["status"]
            away, home = g["teams"]["away"], g["teams"]["home"]
            rows.append({
                "season": season,
                "game_pk": g["gamePk"],
                "date": g["officialDate"],
                "game_type": g["gameType"],
                "series_desc": g.get("seriesDescription"),
                "series_game": g.get("seriesGameNumber"),
                "status": status["detailedState"],
                "coded_state": status.get("codedGameState"),
                "home_id": home["team"].get("id"),
                "home": home["team"].get("name"),
                "away_id": away["team"].get("id"),
                "away": away["team"].get("name"),
                "home_runs": home.get("score"),
                "away_runs": away.get("score"),
                "home_prob_sp": (home.get("probablePitcher") or {}).get("fullName"),
                "away_prob_sp": (away.get("probablePitcher") or {}).get("fullName"),
                "venue": g.get("venue", {}).get("name"),
            })
    return rows


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    PROC.mkdir(parents=True, exist_ok=True)
    rows = []
    for s in SEASONS:
        season_rows = fetch_season(s)
        print(f"{s}: {len(season_rows)} scheduled games")
        rows.extend(season_rows)
    df = pd.DataFrame(rows)
    df.to_csv(PROC / "schedule_all.csv", index=False)

    # Completed games only. "F" = Final; also excludes suspended/postponed.
    done = df[(df.coded_state == "F") & df.home_runs.notna() & df.away_runs.notna()].copy()
    # A postponed game reappears later under the same gamePk; keep the final one.
    done = done.drop_duplicates("game_pk", keep="last")
    done["home_runs"] = done.home_runs.astype(int)
    done["away_runs"] = done.away_runs.astype(int)
    done = done[done.home_runs != done.away_runs]  # drop the rare official tie
    done.to_csv(PROC / "games.csv", index=False)

    # Team metadata (league/division), needed for the World Series home-field tiebreak
    teams = get_json(f"{API}/teams", {"sportId": 1, "season": SEASONS[-1]},
                     f"teams_{SEASONS[-1]}.json", refresh=True)
    pd.DataFrame([{"id": t["id"], "team": t["name"], "abbrev": t.get("abbreviation"),
                   "league": t["league"]["name"], "division": t["division"]["name"]}
                  for t in teams["teams"]]).to_csv(PROC / "teams.csv", index=False)

    summary = done.groupby(["season", "game_type"]).size().unstack(fill_value=0)
    print("\nCompleted games by season/type:\n", summary)


if __name__ == "__main__":
    main()
