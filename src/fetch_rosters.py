"""Step 5 input — Pull postseason rosters and player/team stats for the teams still alive.

Writes the files src/roster_adjust.py reads into data/raw/ (git-ignored:
they are verbatim MLB Advanced Media responses, so they are re-fetched
rather than redistributed).

Teams: whoever is still alive in the live bracket (from predict.load()).
Date:  the ROSTER_DATE environment variable if set (to reproduce an old
       snapshot), else today. The date and teams used are written to
       data/raw/roster_meta.json, and roster_adjust.py records them in its output.

Usage:  .venv/bin/python src/fetch_rosters.py
        ROSTER_DATE=2026-10-13 .venv/bin/python src/fetch_rosters.py
"""
import datetime as dt
import json
import os

from fetch_data import API, RAW, get_json
import predict as P

SEASON = P.SEASON


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    d = P.load()
    roster_date = os.environ.get("ROSTER_DATE", dt.date.today().isoformat())
    team_ids = {d["team_ids"][t]: t for t in P.alive_teams(d)}
    print(f"Roster date {roster_date}; teams alive: {', '.join(team_ids.values())}")
    for tid, name in team_ids.items():
        active = get_json(f"{API}/teams/{tid}/roster",
                          {"rosterType": "active", "date": roster_date, "hydrate": "person"},
                          f"roster_active_{tid}.json", refresh=True)
        get_json(f"{API}/teams/{tid}/roster", {"rosterType": "40Man", "date": roster_date},
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
    (RAW / "roster_meta.json").write_text(json.dumps(
        {"date": roster_date, "teams": {name: tid for tid, name in team_ids.items()}}, indent=2))


if __name__ == "__main__":
    main()
