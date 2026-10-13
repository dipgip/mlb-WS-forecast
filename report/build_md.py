"""Step 7b — The static report: report/REPORT.md plus chart images.

Readable as-is on GitHub or in any Markdown viewer, with no JavaScript and no
claude.ai link. It reads the same report/data.json as the interactive page
(written by report/build.py), so the two versions can't disagree.

Each chart is drawn twice, light and dark, and REPORT.md uses <picture> so
GitHub shows the one matching the reader's theme.

Usage: .venv/bin/python report/build_md.py   (run after report/build.py)
"""
import json
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REP = ROOT / "report"
FIG = REP / "figures"
DATA = json.loads((REP / "data.json").read_text())
F = DATA["facts"]

THEMES = {
    "light": {"bg": "#fcfcfb", "ink": "#15191b", "ink2": "#4c5450", "muted": "#7d847f", "grid": "#dcdfd8",
              "axis": "#c3c6bd", "accent": "#0f5c3c",
              "team": {"Milwaukee Brewers": "#eda100", "Los Angeles Dodgers": "#2a78d6",
                       "Cleveland Guardians": "#eb6834", "Tampa Bay Rays": "#1baf7a"}},
    "dark": {"bg": "#161b18", "ink": "#eef1ec", "ink2": "#bcc4be", "muted": "#89918b", "grid": "#2a312d",
             "axis": "#3b443f", "accent": "#5cc493",
             "team": {"Milwaukee Brewers": "#c98500", "Los Angeles Dodgers": "#3987e5",
                      "Cleveland Guardians": "#d95926", "Tampa Bay Rays": "#199e70"}},
}
FALLBACK = ["#8a8a8a", "#6f6f6f", "#a5a5a5", "#5a5a5a"]

now = DATA["odds"]["odds_now"]
pre = DATA["odds"]["odds_before_lcs"]
order = sorted(now, key=lambda t: -now[t]["ws"])
unc = {u["team"]: u for u in DATA["uncertainty"]}


def short(t):
    w = t.split()
    return " ".join(w[-2:]) if w[-1] == "Sox" else w[-1]


def pct(x, d=1):
    return f"{x * 100:.{d}f}%"


def color(th, t):
    return th["team"].get(t, FALLBACK[order.index(t) % 4] if t in order else FALLBACK[0])


def style(ax, th, xmax):
    ax.set_facecolor(th["bg"])
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(th["axis"])
    ax.tick_params(colors=th["muted"], labelsize=9, length=0)
    ax.xaxis.grid(True, color=th["grid"], linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_xlim(0, xmax)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v * 100:.0f}%"))


def save(fig, name, th_name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}-{th_name}.png", dpi=160, facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)


def chart_odds(th, name):
    xmax = max(0.6, max(u["p95"] for u in unc.values()) + 0.05)
    fig, ax = plt.subplots(figsize=(8.6, 3.2), facecolor=th["bg"])
    style(ax, th, xmax)
    for i, t in enumerate(order):
        y = len(order) - 1 - i
        ax.barh(y, now[t]["ws"], height=0.55, color=color(th, t), zorder=2)
        u = unc[t]
        ax.errorbar(now[t]["ws"], y, xerr=[[now[t]["ws"] - u["p05"]], [u["p95"] - now[t]["ws"]]],
                    fmt="none", ecolor=th["ink"], elinewidth=1.3, capsize=4, zorder=3)
        ax.plot([pre[t]["ws"]] * 2, [y - 0.36, y + 0.36], color=th["ink"], linewidth=3, zorder=4,
                solid_capstyle="butt")
        ax.text(u["p95"] + 0.012, y, pct(now[t]["ws"]), va="center",
                color=th["ink"], fontsize=12, fontweight="bold")
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(list(reversed(order)), color=th["ink"], fontsize=10)
    ax.set_title("Chance to win the 2026 World Series", loc="left", color=th["ink"], fontsize=12,
                 fontweight="bold", pad=22)
    ax.text(0, 1.04, "Bar = now  ·  whisker = 90% interval (1,000 resampled seasons)  ·  thick tick = before LCS Game 1",
            transform=ax.transAxes, color=th["ink2"], fontsize=8.5)
    save(fig, name, th["_name"])


def chart_calibration(th, name):
    cal = DATA["backtest"]["calibration"]
    fig, ax = plt.subplots(figsize=(8.6, 3.6), facecolor=th["bg"])
    ax.set_facecolor(th["bg"])
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("bottom", "left"):
        ax.spines[s].set_color(th["axis"])
    ax.tick_params(colors=th["muted"], labelsize=9, length=0)
    ax.grid(True, color=th["grid"], linewidth=0.8)
    ax.set_axisbelow(True)
    lo, hi = 0.45, 0.85
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    fmt = matplotlib.ticker.FuncFormatter(lambda v, _: f"{v * 100:.0f}%")
    ax.xaxis.set_major_formatter(fmt)
    ax.yaxis.set_major_formatter(fmt)
    ax.plot([0.5, hi], [0.5, hi], linestyle=(0, (5, 5)), color=th["muted"], linewidth=1.5, label="Perfect calibration")
    ax.scatter([c["predicted"] for c in cal], [c["actual"] for c in cal], s=70, color=th["accent"],
               edgecolor=th["bg"], linewidth=1.5, zorder=3, label="Actual favorite win rate")
    for c in cal:
        ax.annotate(f"n={c['n']}", (c["predicted"], c["actual"]), xytext=(9, -3), textcoords="offset points",
                    color=th["muted"], fontsize=8.5)
    ax.set_xlabel("Model's predicted series win probability for the favorite", color=th["ink2"], fontsize=9)
    ax.set_ylabel("How often the favorite won", color=th["ink2"], fontsize=9)
    ax.set_title("Series calibration, 2015–2025", loc="left", color=th["ink"], fontsize=12, fontweight="bold")
    leg = ax.legend(loc="upper left", frameon=False, fontsize=8.5)
    for txt in leg.get_texts():
        txt.set_color(th["ink2"])
    save(fig, name, th["_name"])


SCEN_SHORT = {
    "Baseline (λ=80, full season)": "Baseline",
    "Less shrinkage (λ=40)": "Less shrinkage",
    "More shrinkage (λ=160)": "More shrinkage",
    "Recency-weighted (60-day half-life)": "Recent form weighted",
    "Include 2026 postseason games": "+ this October's games",
    "Home field from runs (old method)": "Old home-field method",
    "Roster adjustment, untested (50%)": "Roster adj. 50%*",
    "Roster adjustment, untested (100%)": "Roster adj. 100%*",
    "More confident (k=1.18)": "More confident",
    "Less confident (k=0.6)": "Less confident",
    "Every game a coin flip": "Coin flips",
}


def chart_sensitivity(th, name):
    rows = DATA["sensitivity"]
    xmax = max(0.6, max(r[t] for r in rows for t in order) + 0.05)
    fig, axes = plt.subplots(1, len(order), figsize=(11, 4.2), sharey=True, facecolor=th["bg"])
    labels = [SCEN_SHORT.get(r["scenario"], r["scenario"]) for r in rows]
    ys = list(range(len(rows)))[::-1]
    for ax, t in zip(axes, order):
        style(ax, th, xmax)
        for y, r, lab in zip(ys, rows, labels):
            faint = r["scenario"].startswith("Every") or "untested" in r["scenario"]
            ax.barh(y, r[t], height=0.62, color=color(th, t), alpha=0.45 if faint else 1, zorder=2)
            ax.text(r[t] + 0.01, y, f"{r[t] * 100:.0f}", va="center", color=th["ink"], fontsize=8)
        ax.set_title(short(t), color=th["ink"], fontsize=11, fontweight="bold", loc="left")
        step = 0.2 if xmax > 0.5 else 0.1
        ax.set_xticks([i * step for i in range(int(xmax / step + 1e-9) + 1)])
    axes[0].set_yticks(ys)
    axes[0].set_yticklabels(labels, color=th["ink2"], fontsize=9)
    axes[0].get_yticklabels()[0].set_fontweight("bold")
    fig.suptitle("Title odds under each modeling choice (%)", x=0.01, ha="left", color=th["ink"],
                 fontsize=12, fontweight="bold")
    fig.text(0.01, -0.02, "* Untested: the roster adjustment has not been backtested. Faded bars mark untested or deliberately extreme rows.",
             color=th["muted"], fontsize=8.5)
    fig.tight_layout()
    save(fig, name, th["_name"])


def chart_market(th, name):
    adj = next(r for r in DATA["sensitivity"] if "(100%)" in r["scenario"])
    fig, ax = plt.subplots(figsize=(8.6, 3.0), facecolor=th["bg"])
    style(ax, th, 0.65)
    for i, t in enumerate(order):
        y = len(order) - 1 - i
        m, a, k = now[t]["ws"], adj[t], DATA["market"][t]["implied"]
        ax.plot([min(m, a, k), max(m, a, k)], [y, y], color=th["axis"], linewidth=2, zorder=1)
        ax.scatter([k], [y], marker="D", s=60, facecolor=th["bg"], edgecolor=th["ink"], linewidth=1.8, zorder=3,
                   label="Market (margin removed)" if i == 0 else None)
        ax.scatter([a], [y], marker="o", s=70, facecolor=th["bg"], edgecolor=color(th, t), linewidth=2.5, zorder=3,
                   label="Roster-adjusted (untested)" if i == 0 else None)
        ax.scatter([m], [y], marker="o", s=90, color=color(th, t), edgecolor=th["bg"], linewidth=1.5, zorder=4,
                   label="Model" if i == 0 else None)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(list(reversed(order)), color=th["ink"], fontsize=10)
    ax.set_ylim(-0.6, len(order) - 0.4)
    ax.set_title("Title probability, three ways", loc="left", color=th["ink"], fontsize=12, fontweight="bold", pad=26)
    leg = ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, frameon=False, fontsize=8.5,
                    handletextpad=0.3, columnspacing=1.2)
    for txt in leg.get_texts():
        txt.set_color(th["ink2"])
    for h in leg.legend_handles:
        h.set_edgecolor(th["ink2"])
        if h.get_label() == "Model":
            h.set_facecolor(th["ink2"])
    save(fig, name, th["_name"])


def picture(name, alt):
    return (f'<picture>\n  <source media="(prefers-color-scheme: dark)" srcset="figures/{name}-dark.png">\n'
            f'  <img alt="{alt}" src="figures/{name}-light.png" width="100%">\n</picture>')


def table(headers, rows, align=None):
    align = align or ["---"] + ["---:"] * (len(headers) - 1)
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(align) + " |"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def linescore(desc, games):
    teams = [games[0]["away"], games[0]["home"]]
    wins = {t: 0 for t in teams}
    for g in games:
        if g["home_runs"] is not None:
            wins[g["home"] if g["home_runs"] > g["away_runs"] else g["away"]] += 1
    head = ["", *[f"G{g['g']}" for g in games], "W"]
    rows = []
    for t in teams:
        cells = []
        for g in games:
            if g["home_runs"] is None:
                cells.append("·")
                continue
            r = g["home_runs"] if g["home"] == t else g["away_runs"]
            o = g["away_runs"] if g["home"] == t else g["home_runs"]
            cells.append(f"**{r}**" if r > o else str(r))
        rows.append([f"**{short(t)}**", *cells, f"**{wins[t]}**"])
    rows.append(["*Home*", *[f"*{short(g['home'])}*" for g in games], ""])
    a, b = sorted(teams, key=lambda t: -wins[t])
    status = f"tied {wins[a]}–{wins[b]}" if wins[a] == wins[b] else \
        f"{short(a)} {'win' if wins[a] == 4 else 'lead'} {wins[a]}–{wins[b]}"
    nxt = next((g for g in games if g["home_runs"] is None), None)
    nxt_line = ""
    if nxt and max(wins.values()) < 4:
        sp = f", {nxt['away_sp']} vs {nxt['home_sp']}" if nxt.get("away_sp") and nxt.get("home_sp") else ""
        nxt_line = f"\n\nNext: Game {nxt['g']}, {nxt['date']}, {short(nxt['away'])} at {short(nxt['home'])}{sp}."
    return f"### {desc}: {status}\n\n" + table(head, rows, ["---"] + [":---:"] * (len(head) - 1)) + nxt_line


def build_markdown():
    bt = DATA["backtest"]
    mkt = DATA["market"]
    adj = next(r for r in DATA["sensitivity"] if "(100%)" in r["scenario"])
    hf = DATA["odds"]["ws_home_field"]
    L = []
    L += ["# 2026 World Series Forecast", "",
          f"*{F['asof']}. Static version of the report. The [live dashboard](https://mlb-ws-forecast-w3huajspduv8ae2mctsydr.streamlit.app/) has the same numbers plus a what-if simulator.*", "",
          f"## The pick: {F['fav']}, {F['fav_pct']}%", "",
          table(["", ""], [["Model", f"**{F['fav_pct']}%**"],
                           ["90% interval (1,000 resampled seasons)", F["fav_ci"]],
                           ["Betting market, margin removed", F["fav_mkt"]],
                           ["Most likely World Series", f"{F['top_mu']} ({F['top_mu_pct']})"]],
                ["---", "---:"]), "",
          F["lede"] + " October baseball is mostly noise, and this report shows how much.", "",
          "## Where the series stand", ""]
    for desc, games in DATA["series"].items():
        L += [linescore(desc, games), ""]
    L += ["## Title odds", "",
          "Exact probabilities from every remaining path through the bracket, using the real home/away schedule. "
          + F["swing"], "",
          picture("odds", "Chance to win the 2026 World Series by team, with 90% intervals"), "",
          table(["Team", "Title now", "90% interval", "Pennant now", "Title before LCS", "Market"],
                [[t, f"**{pct(now[t]['ws'])}**", f"{pct(unc[t]['p05'], 0)}–{pct(unc[t]['p95'], 0)}",
                  pct(now[t]["pennant"]), pct(pre[t]["ws"]), pct(mkt[t]["implied"], 0)] for t in order]), "",
          table(["Possible World Series", "Chance it happens", "AL team wins", "NL team wins", "Home field"],
                [[f"{short(k.split(' vs ')[0])} vs {short(k.split(' vs ')[1])}", pct(v["p_matchup"]),
                  pct(v["p_al_wins"]), pct(1 - v["p_al_wins"]), f"{short(hf[k]['team'])} ({hf[k]['reason']})"]
                 for k, v in sorted(DATA["odds"]["ws_matchups"].items(), key=lambda kv: -kv[1]["p_matchup"])]), "",
          "## How I got here", "",
          "The full log with every number is in [LOG.md](../LOG.md), and a partner review of the weak spots is in "
          "[REVIEW.md](../REVIEW.md). The core method was fixed before any 2026 odds were computed.", "",
          f"1. **Pulled every game since 2015.** {F['n_games_total']} regular-season and postseason results from the "
          "official MLB Stats API, plus the live bracket, rosters and announced starters.",
          "2. **Rated every team on runs, not wins.** A Poisson model gives each team an offense and a defense rating, "
          f"adjusted for opponents and pulled toward average. Home field is set from actual home win rates ({F['home_rate']} "
          "between equal teams), because run totals understate it.",
          "3. **Tuned it on games it hadn't seen.** Fit through August, predict September, ten seasons over. Heavy "
          "shrinkage won, and weighting recent form didn't help.",
          "4. **Graded it on 11 real Octobers.** Every playoff game and series from 2015–2025, each predicted using only "
          "that year's regular season. Also tested whether adjusting for each game's starting pitchers helps; it doesn't.",
          "5. **Ran the live bracket.** Each series from its current state, then all four possible World Series, with "
          "home field set by MLB's tiebreak rules.",
          "6. **Measured the uncertainty and tried to break it.** 1,000 resampled seasons for the interval, eleven "
          "alternative setups, and a comparison against betting markets.", "",
          "## Can it be trusted? The backtest", "",
          "The stronger team does not reliably win in October, so the useful question is whether the model's "
          "probabilities are honest. " + F["bt_series"], "",
          table(["Measure", "Result"],
                [["Series favorites won", f"{pct(bt['series_fav_won'], 0)} of {bt['n_series']} (predicted {pct(bt['series_fav_pred'], 0)})"],
                 ["Game favorites won", f"{pct(bt['game_fav_won'])} of {bt['n_games']}"],
                 ["Playoff log loss: model / standings / coin flip (lower is better)",
                  f"{bt['game_ll']['model']:.4f} / {bt['game_ll']['log5']:.4f} / {bt['game_ll']['coin']:.4f}"]],
                ["---", "---:"]), "",
          picture("calibration", "Predicted versus actual series win rate for model favorites"), "",
          F["calib_note"], "",
          table(["World Series", "Model favorite", "Fav. chance", "Winner", ""],
                [[r["season"], r["fav"], pct(r["p_fav"]), r["winner"], "✓ called" if r["fav_won"] else "✗ upset"]
                 for r in bt["ws"]], ["---", "---", "---:", "---", "---"]), "",
          F["ws_clear"], "",
          f"## Stress test: {F['sens_head'].replace('The ', 'the ', 1)}", "",
          "Each row changes one judgment call. Across these the favorite's title odds range "
          f"{F['sens_range']}. That range measures sensitivity to choices; the wider interval above measures "
          f"statistical noise. With every remaining game a coin flip, the current series lead alone still gives the "
          f"favorite {F['coin_pct']}.", "",
          picture("sensitivity", "Title odds for each team under each modeling scenario"), "",
          "## Model vs the betting market", "",
          F["market_text"], "", F["market_why"], "",
          picture("market", "Model, roster-adjusted, and market title odds by team"), "",
          table(["Team", "Model", "Roster-adjusted (untested)", "Market", "Sportsbook prices"],
                [[t, pct(now[t]["ws"]), pct(adj[t]), pct(mkt[t]["implied"]), mkt[t]["american"]] for t in order]), "",
          F["mkt_note"] + ".", "",
          table(["October roster check (untested)", "Starters used", "Staff FIP: season → Oct", "Lineup wOBA: season → Oct"],
                [[short(t), ", ".join(DATA["roster"][t]["sps"]),
                  f"{DATA['roster'][t]['fip_season']:.2f} → {DATA['roster'][t]['fip_oct']:.2f}",
                  f"{DATA['roster'][t]['woba_season']:.3f} → {DATA['roster'][t]['woba_oct']:.3f}"]
                 for t in order if t in DATA["roster"]], ["---", "---", "---:", "---:"]), "",
          f"## {F['watch_head']}", "", F["watch_text"], "",
          table(["If this happens", *[short(t) for t in order]],
                [[f"{short(r['if_wins'])} win {r['series']} G{r['game']}",
                  *[f"{pct(r[t])} ({'+' if r[t] >= now[t]['ws'] else '−'}{abs(r[t] - now[t]['ws']) * 100:.1f})" for t in order]]
                 for r in DATA["whatif"]]), "",
          "## 2026 team ratings", "", F["ratings_text"], "",
          table(["Rank", "Team", "Wins", "Exp. runs scored / G", "Exp. runs allowed / G", "Win % vs avg"],
                [[r["rank"], f"**{r['team']}**" if r["team"] in now else r["team"], r["W"],
                  f"{r['exp_RS_pg']:.2f}", f"{r['exp_RA_pg']:.2f}", f"{r['exp_wpct']:.3f}".lstrip("0")]
                 for r in DATA["ratings"]], ["---:", "---", "---:", "---:", "---:", "---:"]), "",
          "## What this model can't see", "",
          "- It rates teams on the full season. Injuries and October roster changes appear only in the roster-adjusted "
          "scenario, which is not backtested.",
          f"- {F['next_matchup_caveat']}",
          "- Bullpen fatigue, travel and day-to-day lineup choices are not modeled.",
          f"- {F['sample_caveat']}",
          "- Market prices are a recorded snapshot from published articles, not a live feed, and they move by the hour.", "",
          "---", "",
          f"Data: MLB Stats API (statsapi.mlb.com), games through {F['data_through']}. Market prices: "
          + ", ".join(f"[{s['source']}]({s['url']})" for s in DATA["market_sources"]) + ". "
          f"Generated {date.today().isoformat()} by `report/build_md.py`; rebuild everything with `./run_all.sh`.", ""]
    (REP / "REPORT.md").write_text("\n".join(L))


def main():
    for th_name, th in THEMES.items():
        th = dict(th, _name=th_name)
        chart_odds(th, "odds")
        chart_calibration(th, "calibration")
        chart_sensitivity(th, "sensitivity")
        chart_market(th, "market")
    build_markdown()
    print(f"wrote report/REPORT.md and {len(list(FIG.glob('*.png')))} figures")


if __name__ == "__main__":
    main()
