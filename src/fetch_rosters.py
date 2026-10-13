"""Step 5 input — Pull postseason rosters and player/team stats for the teams still alive.

Writes the files src/roster_adjust.py reads into data/raw/ (git-ignored:
they are verbatim MLB Advanced Media responses, so they are re-fetched
rather than redistributed). Rosters are pinned to ROSTER_DATE so a re-run
reproduces the same snapshot.

Usage:  .venv/bin/python src/fetch_rosters.py
"""
from pathlib import Path

from fetch_data import API, RAW, get_json

SEASON = 2026
ROSTER_DATE = "2026-10-13"
TEAM_IDS = {158: "Milwaukee Brewers", 119: "Los Angeles Dodgers",
            139: "Tampa Bay Rays", 114: "Cleveland Guardians"}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for tid, name in TEAM_IDS.items():
        active = get_json(f"{API}/teams/{tid}/roster",
                          {"rosterType": "active", "date": ROSTER_DATE, "hydrate": "person"},
                          f"roster_active_{tid}.json", refresh=True)
        get_json(f"{API}/teams/{tid}/roster", {"rosterType": "40Man", "date": ROSTER_DATE},
                 f"roster_40_{tid}.json", refresh=True)
        ids = ",".join(str(p["person"]["id"]) for p in active["roster"])
        get_json(f"{API}/people",
                 {"personIds": ids,
                  "hydrate": f"stats(group=[hitting,pitching],type=[season],season={SEASON})"},
                 f"roster_stats_{tid}.json", refresh=True)
        get_json(f"{API}/teams/{tid}/stats",
                 {"stats": "season", "group": "hitting,pitching", "season": SEASON},
                 f"team_stats_{tid}.json", refresh=True)
        for grp in ("hitting", "pitching"):
            get_json(f"{API}/stats",
                     {"stats": "season", "group": grp, "season": SEASON, "teamId": tid,
                      "playerPool": "ALL", "limit": 300},
                     f"teamplayers_{grp}_{tid}.json", refresh=True)
        print(f"{name}: {len(active['roster'])} active players")
    get_json(f"{API}/teams/stats",
             {"stats": "season", "group": "pitching,hitting", "season": SEASON, "sportIds": 1},
             f"league_team_stats_{SEASON}.json", refresh=True)


if __name__ == "__main__":
    main()
