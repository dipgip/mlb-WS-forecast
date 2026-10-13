"""Step 6 — Turn recorded sportsbook futures prices into fair probabilities.

Input: data/market_odds.csv, one row per (capture date, source, team) with
American odds, recorded by hand from the cited article. Prices are facts we
cite, not data we can pull from an API.

Each source is de-vigged with the power method (bracket.devig_power), which
handles the favorite–longshot bias better than proportional scaling. The
sources are then averaged. Proportional results are kept for comparison.

Output: outputs/market_2026.json (latest capture date only)
"""
import json
from pathlib import Path

import pandas as pd

import bracket as B

ROOT = Path(__file__).resolve().parents[1]


def main():
    m = pd.read_csv(ROOT / "data/market_odds.csv")
    latest = m[m.captured == m.captured.max()].copy()
    latest["implied"] = latest.american.map(B.american_to_prob)
    per_source = []
    for src, g in latest.groupby("source"):
        g = g.copy()
        g["power"] = B.devig_power(g.implied)
        g["proportional"] = g.implied / g.implied.sum()
        g["overround"] = g.implied.sum() - 1
        per_source.append(g)
    allp = pd.concat(per_source)
    avg = allp.groupby("team")[["power", "proportional"]].mean()
    out = {
        "captured": str(latest.captured.max()),
        "sources": [{"source": s, "url": u} for s, u in latest[["source", "url"]].drop_duplicates().values],
        "overround": {s: float(v) for s, v in allp.groupby("source").overround.first().items()},
        "teams": {t: {"fair_power": float(r.power), "fair_proportional": float(r.proportional),
                      "american": " / ".join(f"+{a}" if a > 0 else str(a)
                                             for a in latest[latest.team == t].american)}
                  for t, r in avg.iterrows()},
    }
    (ROOT / "outputs/market_2026.json").write_text(json.dumps(out, indent=2))
    print(f"Market, captured {out['captured']} ({len(out['sources'])} sources)")
    for t, v in sorted(out["teams"].items(), key=lambda kv: -kv[1]["fair_power"]):
        print(f"  {t:22s} power {v['fair_power']:.3f}   proportional {v['fair_proportional']:.3f}   ({v['american']})")


if __name__ == "__main__":
    main()
