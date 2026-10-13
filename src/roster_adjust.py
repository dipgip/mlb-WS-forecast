"""Step 5a — Postseason roster adjustment (sensitivity scenario).

The Step 4 ratings describe the team that played 162 games. October is
different: injured players are gone, rotations shrink to four starters, and the
best relievers pitch a much bigger share of innings. This script measures how
the *active postseason roster*, deployed October-style, compares with the
full-season team, and turns that into run adjustments.

Pitching quality = FIP. Hitting quality = wOBA (standard linear weights).
Every player's rate is regressed toward league average (pitchers +60 IP of
league-average, hitters +220 PA), because a 15-inning reliever's FIP is
mostly noise. The baseline and the October roster go through the same
regression, so the comparison is apples to apples.

October usage assumptions:
  pitching: the 4 starters used most this postseason (actual + announced
            starts from the MLB schedule; filled by season GS if fewer)
            throw 55% of innings, split by their share of October starts;
            the 7 most-used relievers throw 45%, in proportion to season IP.
  hitting:  the 9 position players with most PA get 90% of PA equally;
            the rest of the bench gets 10% in proportion to PA.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
SCHED = pd.read_csv(ROOT / "data/processed/schedule_all.csv")
TEAMS = {158: "Milwaukee Brewers", 119: "Los Angeles Dodgers",
         139: "Tampa Bay Rays", 114: "Cleveland Guardians"}
IP0, PA0 = 60.0, 220.0
WOBA_SCALE, PA_PER_GAME = 1.2, 38.0


def ip(s):
    return s.get("outs", 0) / 3.0


def woba_num(s):
    singles = s["hits"] - s["doubles"] - s["triples"] - s["homeRuns"]
    ubb = s["baseOnBalls"] - s.get("intentionalWalks", 0)
    return (0.69 * ubb + 0.72 * s.get("hitByPitch", 0) + 0.88 * singles
            + 1.25 * s["doubles"] + 1.58 * s["triples"] + 2.03 * s["homeRuns"])


def woba_den(s):
    return (s["atBats"] + s["baseOnBalls"] - s.get("intentionalWalks", 0)
            + s.get("sacFlies", 0) + s.get("hitByPitch", 0))


def fip_core(s):
    return 13 * s["homeRuns"] + 3 * (s["baseOnBalls"] + s.get("hitByPitch", 0)) - 2 * s["strikeOuts"]


# ---- league constants
lg = json.loads((RAW / "league_team_stats_2026.json").read_text())
lg_tot = {}
for block in lg["stats"]:
    grp = block["group"]["displayName"]
    agg = {}
    for sp in block["splits"]:
        for k, v in sp["stat"].items():
            if isinstance(v, (int, float)):
                agg[k] = agg.get(k, 0) + v
    lg_tot[grp] = agg
LG_IP = lg_tot["pitching"]["outs"] / 3
C_FIP = 9 * lg_tot["pitching"]["earnedRuns"] / LG_IP - fip_core(lg_tot["pitching"]) / LG_IP  # FIP scaled to ERA
LG_FIP = fip_core(lg_tot["pitching"]) / LG_IP + C_FIP
LG_WOBA = woba_num(lg_tot["hitting"]) / woba_den(lg_tot["hitting"])


def reg_fip(s):
    i = ip(s)
    raw = (fip_core(s) / i + C_FIP) if i > 0 else LG_FIP
    return (raw * i + LG_FIP * IP0) / (i + IP0)


def reg_woba(s):
    d = woba_den(s)
    raw = woba_num(s) / d if d > 0 else LG_WOBA
    return (raw * d + LG_WOBA * PA0) / (d + PA0)


def full_season_lines(team_id):
    """Full-2026 lines (summed across teams) for active-roster players."""
    d = json.loads((RAW / f"roster_stats_{team_id}.json").read_text())
    out = {}
    for p in d["people"]:
        lines = {"name": p["fullName"], "pos": p["primaryPosition"]["abbreviation"]}
        for st in p.get("stats", []):
            g = st["group"]["displayName"]
            splits = st["splits"]
            total = [x for x in splits if "team" not in x]
            use = total if total else splits
            agg = {}
            for x in use:
                for k, v in x["stat"].items():
                    if isinstance(v, (int, float)):
                        agg[k] = agg.get(k, 0) + v
            lines[g] = agg
        out[p["id"]] = lines
    return out


def team_player_lines(team_id, grp):
    d = json.loads((RAW / f"teamplayers_{grp}_{team_id}.json").read_text())
    return {x["player"]["id"]: x["stat"] for x in d["stats"][0]["splits"]}


def adjust(team_id):
    roster = full_season_lines(team_id)
    rows = {}

    # ---------- pitching
    tp = team_player_lines(team_id, "pitching")
    # Baseline: who actually threw the team's innings, at regressed talent
    base_w = np.array([ip(s) for s in tp.values()])
    base_q = np.array([reg_fip(roster[pid]["pitching"]) if pid in roster and "pitching" in roster[pid]
                       else reg_fip(s) for pid, s in tp.items()])
    base_fip = (base_w * base_q).sum() / base_w.sum()

    pitchers = [(pid, r) for pid, r in roster.items() if r["pos"] in ("P", "TWP") and "pitching" in r]
    # October rotation = who has actually started (or is announced) this postseason
    post = SCHED[(SCHED.season == 2026) & (SCHED.game_type != "R")]
    name = TEAMS[team_id]
    starts = pd.concat([post.loc[post.home == name, "home_prob_sp"],
                        post.loc[post.away == name, "away_prob_sp"]]).dropna().value_counts()
    by_name = {r["name"]: (pid, r) for pid, r in pitchers}
    sps = [by_name[n] for n in starts.index if n in by_name][:4]
    sp_starts = [starts[r["name"]] for _, r in sps]
    rest = sorted([x for x in pitchers if x not in sps], key=lambda x: -x[1]["pitching"].get("gamesStarted", 0))
    while len(sps) < 4:  # fill from season GS
        sps.append(rest.pop(0))
        sp_starts.append(1)
    rps = sorted(rest, key=lambda x: -ip(x[1]["pitching"]))[:7]
    usage = []
    sp_w = np.array(sp_starts, dtype=float) / sum(sp_starts)
    for (pid, r), w in zip(sps, sp_w):
        usage.append((r["name"], "SP", .55 * w, reg_fip(r["pitching"])))
    rp_ip = np.array([ip(r["pitching"]) for _, r in rps])
    for (pid, r), w in zip(rps, rp_ip / rp_ip.sum()):
        usage.append((r["name"], "RP", .45 * w, reg_fip(r["pitching"])))
    oct_fip = sum(u[2] * u[3] for u in usage)
    rows["pitching"] = {"season_staff_FIP": base_fip, "october_staff_FIP": oct_fip,
                        "delta_runs_allowed_pg": oct_fip - base_fip,
                        "staff": [{"name": n, "role": ro, "share": round(s, 3), "FIP_reg": round(q, 2)}
                                  for n, ro, s, q in usage]}

    # ---------- hitting
    th = team_player_lines(team_id, "hitting")
    hb_w = np.array([woba_den(s) for s in th.values()], dtype=float)
    hb_q = np.array([reg_woba(roster[pid]["hitting"]) if pid in roster and "hitting" in roster[pid]
                     and woba_den(roster[pid]["hitting"]) > 0 else reg_woba(s) for pid, s in th.items()])
    base_woba = (hb_w * hb_q).sum() / hb_w.sum()

    hitters = [(pid, r) for pid, r in roster.items() if r["pos"] not in ("P",) and "hitting" in r
               and woba_den(r["hitting"]) > 0]
    hitters.sort(key=lambda x: -woba_den(x[1]["hitting"]))
    starters, bench = hitters[:9], hitters[9:]
    lineup = [(r["name"], "starter", .90 / len(starters), reg_woba(r["hitting"])) for _, r in starters]
    if bench:
        bpa = np.array([woba_den(r["hitting"]) for _, r in bench], dtype=float)
        lineup += [(r["name"], "bench", .10 * w, reg_woba(r["hitting"])) for (_, r), w in zip(bench, bpa / bpa.sum())]
    else:
        lineup = [(n, ro, s / .90, q) for n, ro, s, q in lineup]
    oct_woba = sum(u[2] * u[3] for u in lineup)
    rows["hitting"] = {"season_lineup_wOBA": base_woba, "october_lineup_wOBA": oct_woba,
                       "delta_runs_scored_pg": (oct_woba - base_woba) / WOBA_SCALE * PA_PER_GAME,
                       "lineup": [{"name": n, "role": ro, "share": round(s, 3), "wOBA_reg": round(q, 3)}
                                  for n, ro, s, q in lineup]}
    return rows


def main():
    out = {"league": {"FIP": LG_FIP, "wOBA": LG_WOBA}}
    print(f"League FIP {LG_FIP:.2f}, wOBA {LG_WOBA:.3f}\n")
    for tid, name in TEAMS.items():
        a = adjust(tid)
        out[name] = a
        p, h = a["pitching"], a["hitting"]
        print(f"{name}")
        print(f"  pitching  season {p['season_staff_FIP']:.2f} -> October {p['october_staff_FIP']:.2f}"
              f"   ({p['delta_runs_allowed_pg']:+.2f} R/G allowed)")
        print("    SP: " + ", ".join(f"{s['name']} {s['FIP_reg']}" for s in p["staff"] if s["role"] == "SP"))
        print("    RP: " + ", ".join(f"{s['name']} {s['FIP_reg']}" for s in p["staff"] if s["role"] == "RP"))
        print(f"  hitting   season {h['season_lineup_wOBA']:.3f} -> October {h['october_lineup_wOBA']:.3f}"
              f"   ({h['delta_runs_scored_pg']:+.2f} R/G scored)")
        print("    lineup: " + ", ".join(f"{s['name']} {s['wOBA_reg']}" for s in h["lineup"] if s["role"] == "starter"))
        print()
    (ROOT / "outputs/roster_adjustments_2026.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
