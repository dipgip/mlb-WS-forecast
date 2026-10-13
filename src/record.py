"""Read, label, explain and (eventually) score the forecast record in forecasts/.

Shared by the dashboard and both reports, so they all tell the same story:
- timeline(): one row per team per snapshot, in time order, with readable labels
- changes(): which game results arrived between consecutive live snapshots
- score(): once the World Series ends, scores every *live* snapshot (never
  retrospective ones) against the champion, alongside the market and a
  know-nothing baseline
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FC = ROOT / "forecasts"
REPO = "https://github.com/dipgip/mlb-WS-forecast"


def snapshots():
    out = []
    for p in sorted(FC.glob("*.json")):
        s = json.loads(p.read_text())
        s["_file"] = p.name
        out.append(s)
    return sorted(out, key=lambda s: (s["kind"] != "retrospective", s["created_at_utc"], s["model_version"]))


def _abbr():
    t = pd.read_csv(ROOT / "data/processed/teams.csv")
    return dict(zip(t.team, t.abbrev))


def state_label(series_state):
    ab = _abbr()
    parts = []
    for s, w in series_state.items():
        (a, na), (b, nb) = sorted(w.items(), key=lambda kv: -kv[1])
        parts.append(f"{s} {ab.get(a, a)} {na}–{nb}" if na != nb else f"{s} {na}–{nb}")
    return " · ".join(parts)


def label(s):
    if s["kind"] == "retrospective":
        return "Before LCS (retro)" if all(sum(w.values()) == 0 for w in s["series_state"].values()) \
            else f"{state_label(s['series_state'])} (retro)"
    d = pd.Timestamp(s["created_at_utc"])
    return f"{d.strftime('%b')} {d.day} · {s['model_version']}"


def timeline():
    rows = []
    for i, s in enumerate(snapshots()):
        for t, v in s["odds"].items():
            rows.append({"seq": i, "label": label(s), "snapshot_id": s["snapshot_id"], "kind": s["kind"],
                         "model_version": s["model_version"], "created_at_utc": s["created_at_utc"],
                         "state": state_label(s["series_state"]), "pregame_verified": s["pregame_verified"],
                         "commit": s["code_commit"]["sha"], "team": t, "title": v["title"],
                         "p05": v.get("title_p05"), "p95": v.get("title_p95"), "pennant": v["pennant"],
                         "market": (s.get("market") or {}).get("fair_power", {}).get(t)})
    return pd.DataFrame(rows)


def table():
    """One row per snapshot, for display."""
    rows = []
    for s in snapshots():
        nxt = s["next_games"][0] if s["next_games"] else None
        rows.append({
            "Snapshot": label(s), "Kind": s["kind"], "Model": s["model_version"],
            "Created (UTC)": s["created_at_utc"].replace("T", " ").rstrip("Z"),
            "Series state": state_label(s["series_state"]),
            "Next first pitch (UTC)": nxt["first_pitch_utc"].replace("T", " ").rstrip("Z") if nxt else "—",
            "Before first pitch": "✓" if s["pregame_verified"] else ("n/a (retro)" if s["kind"] == "retrospective" else "✗"),
            "Code": s["code_commit"]["sha"],
            "Code link": f"{REPO}/commit/{s['code_commit']['sha']}",
            "File": f"{REPO}/blob/main/forecasts/{s['_file']}",
            "Note": s.get("notes", ""),
        })
    return pd.DataFrame(rows)


def changes():
    """Game results that arrived between consecutive live snapshots."""
    games = pd.read_csv(ROOT / "data/processed/games.csv")
    post = games[(games.season == 2026) & (games.game_type.isin(["L", "W"]))]
    live = [s for s in snapshots() if s["kind"] == "live"]
    out = []
    for prev, cur in zip(live, live[1:]):
        new = post[(post.date > prev["information"]["games_through"]) & (post.date <= cur["information"]["games_through"])]
        results = [f"{r.series_desc.replace('Championship Series', 'CS').replace('AL ', 'AL').replace('NL ', 'NL')} "
                   f"G{int(r.series_game)}: {r.away} {r.away_runs}, {r.home} {r.home_runs}" for r in new.itertuples()]
        why = "; ".join(results) if results else (
            f"no new games; model {prev['model_version']} → {cur['model_version']}"
            if prev["model_version"] != cur["model_version"] else "no new games")
        moves = {t: cur["odds"][t]["title"] - prev["odds"].get(t, {}).get("title", np.nan) for t in cur["odds"]}
        out.append({"from": label(prev), "to": label(cur), "what_happened": why, "moves": moves})
    return out


def champion():
    games = pd.read_csv(ROOT / "data/processed/games.csv")
    ws = games[(games.season == 2026) & (games.game_type == "W")]
    if ws.empty:
        return None
    w = ws.home.where(ws.home_runs > ws.away_runs, ws.away).value_counts()
    return w.index[0] if w.iloc[0] >= 4 else None


def score():
    """Brier (multi-class, lower is better) and log score for every live snapshot.
    Returns None until the World Series is decided."""
    champ = champion()
    if champ is None:
        return None
    rows = []
    for s in snapshots():
        if s["kind"] != "live":
            continue
        teams = list(s["odds"])
        p = np.array([s["odds"][t]["title"] for t in teams])
        o = np.array([t == champ for t in teams], dtype=float)
        row = {"Snapshot": label(s), "Model Brier": float(((p - o) ** 2).sum()),
               "Model log score": float(-np.log(max(s["odds"].get(champ, {}).get("title", 0), 1e-6)))}
        mk = (s.get("market") or {}).get("fair_power")
        if mk:
            q = np.array([mk[t] for t in teams])
            row["Market Brier"] = float(((q - o) ** 2).sum())
        u = np.full(len(teams), 1 / len(teams))
        row["Equal-odds Brier"] = float(((u - o) ** 2).sum())
        rows.append(row)
    return {"champion": champ, "rows": rows}


def game_forecasts():
    """Every per-game forecast on record, joined to its result once played."""
    games = pd.read_csv(ROOT / "data/processed/games.csv")
    done = games.set_index("game_pk")
    rows = []
    for p in sorted((FC / "games").glob("*.json")):
        g = json.loads(p.read_text())
        fav = g["home"] if g["p_home_win"] >= 0.5 else g["away"]
        p_fav = max(g["p_home_win"], g["p_away_win"])
        row = {"Game": f"{g['series'].replace(' Championship Series', 'CS')} G{g['game']}",
               "Matchup": f"{g['away']} @ {g['home']}", "First pitch (UTC)": g["first_pitch_utc"],
               "Forecast made (UTC)": g["created_at_utc"], "Model favorite": fav, "Favorite's chance": p_fav,
               "Winner": None, "Called it": None, "_p_home": g["p_home_win"], "_home": g["home"],
               "File": f"{REPO}/blob/main/forecasts/games/{p.name}"}
        if g["game_pk"] in done.index:
            r = done.loc[g["game_pk"]]
            winner = r.home if r.home_runs > r.away_runs else r.away
            row.update({"Winner": f"{winner} ({max(r.home_runs, r.away_runs)}–{min(r.home_runs, r.away_runs)})",
                        "Called it": winner == fav, "_home_won": winner == g["home"]})
        rows.append(row)
    return pd.DataFrame(rows)


def game_summary():
    gf = game_forecasts()
    graded = gf[gf["Called it"].notna()] if len(gf) else gf
    if graded.empty:
        return {"n_forecast": int(len(gf)), "n_graded": 0}
    y = graded["_home_won"].astype(float).to_numpy()
    p = np.clip(graded["_p_home"].to_numpy(), 1e-6, 1 - 1e-6)
    return {"n_forecast": int(len(gf)), "n_graded": int(len(graded)),
            "called": int(graded["Called it"].sum()),
            "log_loss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
            "log_loss_coin": float(np.log(2)),
            "brier": float(np.mean((p - y) ** 2))}
