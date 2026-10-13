"""Forecast record: append-only, timestamped snapshots of every forecast.

Why: the point is to show what the model said *before* each result, and how
the forecast moved as information arrived. So the record must be:

- Append-only. A snapshot file is never modified or deleted. This script refuses
  to overwrite, and forecasts/MANIFEST.sha256 plus tests/test_forecast_record.py
  make any edit detectable.
- Timestamped against the games. Each snapshot stores its UTC creation time and
  the scheduled first pitch of the next game(s). It counts as "pregame" only if
  it was created before first pitch. Git commit and tag times on GitHub serve
  as the external clock.
- Explicit about what it knew: model version, code commit, and the games included.
- Honest about kind. "live" means made before the outcomes it predicts.
  "retrospective" means computed afterwards for context; it is clearly labeled
  and never scored.

Outputs: forecasts/<snapshot_id>.json, forecasts/index.csv (one row per team per
snapshot), forecasts/MANIFEST.sha256.

Usage (after predict.py and sensitivity.py):
    .venv/bin/python src/snapshot.py              # live snapshot of current outputs
"""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FC = ROOT / "forecasts"
MODEL_VERSION = "v2"


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def code_commit():
    sha = git("rev-parse", "--short", "HEAD")
    dirty = bool(git("status", "--porcelain", "--", "src"))
    return {"sha": sha, "src_has_uncommitted_changes": dirty}


def abbrevs():
    t = pd.read_csv(ROOT / "data/processed/teams.csv")
    return dict(zip(t.team, t.abbrev))


def state_key(series_state):
    ab = abbrevs()
    parts = []
    for s, w in series_state.items():
        parts.append(s + "-" + "-".join(f"{ab.get(t, t[:3])}{n}" for t, n in sorted(w.items(), key=lambda kv: -kv[1])))
    return "_".join(parts)


def next_games(sched_season):
    """Scheduled-but-unplayed postseason games, earliest first pitch first."""
    s = sched_season[(sched_season.game_type != "R") & (sched_season.status != "Final")
                     & sched_season.game_time_utc.notna()].sort_values("game_time_utc")
    real = set(abbrevs())
    s = s[s.home.isin(real) & s.away.isin(real)]
    first = s.game_time_utc.min() if len(s) else None
    nxt = s[s.game_time_utc == first] if first else s.iloc[0:0]
    return [{"series": r.series_desc, "game": int(r.series_game), "first_pitch_utc": r.game_time_utc,
             "matchup": f"{r.away} @ {r.home}"} for r in nxt.itertuples()]


def write(snapshot):
    FC.mkdir(exist_ok=True)
    path = FC / f"{snapshot['snapshot_id']}.json"
    if path.exists():
        raise FileExistsError(f"{path.name} already exists. Snapshots are append-only and never overwritten.")
    body = json.dumps(snapshot, indent=2, sort_keys=False) + "\n"
    path.write_text(body)
    digest = hashlib.sha256(body.encode()).hexdigest()
    with open(FC / "MANIFEST.sha256", "a") as f:
        f.write(f"{digest}  {path.name}\n")

    rows = [{"snapshot_id": snapshot["snapshot_id"], "kind": snapshot["kind"],
             "model_version": snapshot["model_version"], "created_at_utc": snapshot["created_at_utc"],
             "games_through": snapshot["information"]["games_through"],
             "state": snapshot["state_key"], "pregame_verified": snapshot["pregame_verified"],
             "team": t, "p_title": round(v["title"], 4),
             "p_title_p05": None if v.get("title_p05") is None else round(v["title_p05"], 4),
             "p_title_p95": None if v.get("title_p95") is None else round(v["title_p95"], 4),
             "p_pennant": round(v["pennant"], 4)}
            for t, v in snapshot["odds"].items()]
    idx = FC / "index.csv"
    new = pd.DataFrame(rows)
    if idx.exists():
        new = pd.concat([pd.read_csv(idx), new])
    new.to_csv(idx, index=False)
    print(f"wrote {path}  sha256 {digest[:16]}…")
    return path


def build(kind, odds_now, series_state, games_through, n_post_games, created_at, commit, next_g,
          model_version=MODEL_VERSION, intervals=None, market=None, notes=""):
    first_pitch = min((g["first_pitch_utc"] for g in next_g), default=None)
    pregame = bool(kind == "live" and first_pitch and created_at < first_pitch)
    sk = state_key(series_state)
    odds = {}
    for t, v in odds_now.items():
        odds[t] = {"title": v["ws"], "pennant": v["pennant"]}
        if intervals and t in intervals:
            odds[t]["title_p05"], odds[t]["title_p95"] = intervals[t]
    return {
        "snapshot_id": f"{created_at[:10]}_{model_version}_{kind}_{sk}",
        "kind": kind,
        "model_version": model_version,
        "created_at_utc": created_at,
        "code_commit": commit,
        "information": {"games_through": games_through, "postseason_games_included": n_post_games},
        "series_state": series_state,
        "state_key": sk,
        "next_games": next_g,
        "pregame_verified": pregame,
        "odds": odds,
        "market": market,
        "notes": notes,
    }


def live_from_outputs():
    import predict as P
    d = P.load()
    odds = json.loads((ROOT / "outputs/odds_2026.json").read_text())
    unc = pd.read_csv(ROOT / "outputs/uncertainty.csv").set_index("team")
    mk_path = ROOT / "outputs/market_2026.json"
    market = None
    if mk_path.exists():
        m = json.loads(mk_path.read_text())
        market = {"captured": m["captured"], "fair_power": {t: v["fair_power"] for t, v in m["teams"].items()}}
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    snap = build("live", odds["odds_now"], odds["series_state"], odds["as_of"], int(len(d["post"])), created,
                 code_commit(), next_games(d["sched"]),
                 intervals={t: (r.p05, r.p95) for t, r in unc.iterrows()}, market=market)
    idx = FC / "index.csv"
    if idx.exists():
        prev = pd.read_csv(idx)
        same = prev[(prev.state == snap["state_key"]) & (prev.model_version == MODEL_VERSION) & (prev.kind == "live")]
        if len(same):
            print(f"No new information since {same.snapshot_id.iloc[0]} (same series state, same model). Nothing written.")
            return None
    return write(snap)




# ---------------------------------------------------------------- per-game forecasts
def game_forecasts():
    """Record the model's win probability for the next game of every live series.

    Title odds get graded once, when the World Series ends. These single-game
    calls get graded every night, so by the end there are dozens of scored,
    pre-registered predictions. Written to forecasts/games/, append-only and
    hashed into the same MANIFEST. A game already on record is never rewritten.
    """
    import predict as P
    from model import fit
    d = P.load()
    r = fit(d["reg"], lam=P.LAM)
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sched = d["sched"]
    gdir = FC / "games"
    gdir.mkdir(parents=True, exist_ok=True)
    written = []
    for key in ("alcs", "nlcs", "ws"):
        st = d.get(key)
        if not st or max(st[2].values()) == 4:
            continue
        teams, home_order, wins = st
        n = sum(wins.values())
        home = home_order[n]
        away = teams[0] if teams[1] == home else teams[1]
        row = sched[(sched.home == home) & (sched.away == away) & (sched.series_game == n + 1)
                    & (sched.game_type != "R")].iloc[0]
        gid = f"{row.series_desc.replace(' ', '')}_G{n + 1}"
        path = gdir / f"{gid}.json"
        if path.exists():
            continue
        p_home = float(r.p_home_win(home, away))
        rec = {"game_id": gid, "game_pk": int(row.game_pk), "series": row.series_desc, "game": n + 1,
               "home": home, "away": away, "first_pitch_utc": row.game_time_utc,
               "created_at_utc": created, "pregame_verified": bool(created < row.game_time_utc),
               "model_version": MODEL_VERSION, "code_commit": code_commit(),
               "series_state_before": wins, "p_home_win": p_home, "p_away_win": 1 - p_home}
        body = json.dumps(rec, indent=2) + "\n"
        path.write_text(body)
        with open(FC / "MANIFEST.sha256", "a") as f:
            f.write(f"{hashlib.sha256(body.encode()).hexdigest()}  games/{path.name}\n")
        written.append(rec)
        print(f"wrote forecasts/games/{path.name}: {away} @ {home}  P(home)={p_home:.3f}  first pitch {row.game_time_utc}")
    return written


if __name__ == "__main__":
    live_from_outputs()
    game_forecasts()
