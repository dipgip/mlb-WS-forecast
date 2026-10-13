"""2026 World Series forecast dashboard (Streamlit).

Runs locally; nothing is hosted. It reads the same outputs as the reports
(report/data.json and outputs/), and its what-if simulator calls the real
model code in src/ live.

Run:  .venv/bin/streamlit run dashboard/app.py
"""
import json
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import bracket as B  # noqa: E402
import predict as P  # noqa: E402
from model import fit  # noqa: E402
from sensitivity import Scaled  # noqa: E402

st.set_page_config(page_title="2026 World Series Forecast", page_icon="⚾", layout="wide")

DATA_PATH = ROOT / "report/data.json"
if not DATA_PATH.exists():
    st.error("No results yet. Run `./run_all.sh` from the project folder first, then reload this page.")
    st.stop()

# ---------------------------------------------------------------- data
@st.cache_data
def load_report():
    d = json.loads(DATA_PATH.read_text())
    out = ROOT / "outputs"
    extra = {
        "ratings_all": pd.read_csv(out / "ratings_2026.csv"),
        "sp": pd.read_csv(out / "sp_backtest.csv"),
        "sp_summary": json.loads((out / "sp_backtest_summary.json").read_text()),
        "history": pd.read_csv(out / "forecast_history.csv") if (out / "forecast_history.csv").exists() else None,
        "tuning": pd.read_csv(out / "tuning_grid.csv"),
    }
    return d, extra


@st.cache_resource
def model_inputs():
    return P.load()


@st.cache_resource
def ratings_for(lam):
    return fit(model_inputs()["reg"], lam=lam)


DATA, EXTRA = load_report()
F = DATA["facts"]
now = DATA["odds"]["odds_now"]
pre = DATA["odds"]["odds_before_lcs"]
ORDER = sorted(now, key=lambda t: -now[t]["ws"])
UNC = {u["team"]: u for u in DATA["uncertainty"]}

dark = getattr(getattr(st.context, "theme", None), "type", "light") == "dark"
TEAM_COLORS = ({"Milwaukee Brewers": "#c98500", "Los Angeles Dodgers": "#3987e5",
                "Cleveland Guardians": "#d95926", "Tampa Bay Rays": "#199e70"} if dark else
               {"Milwaukee Brewers": "#eda100", "Los Angeles Dodgers": "#2a78d6",
                "Cleveland Guardians": "#eb6834", "Tampa Bay Rays": "#1baf7a"})
INK = "#eef1ec" if dark else "#15191b"
MUTED = "#89918b" if dark else "#7d847f"
ACCENT = "#5cc493" if dark else "#0f5c3c"
TEAM_AXIS = alt.Axis(labelLimit=240, labelFontSize=12)
COLOR_SCALE = alt.Scale(domain=ORDER, range=[TEAM_COLORS.get(t, "#888888") for t in ORDER])


def short(t):
    w = t.split()
    return " ".join(w[-2:]) if w[-1] == "Sox" else w[-1]


def pct(x, d=1):
    return f"{x * 100:.{d}f}%"


# ---------------------------------------------------------------- header
st.title(f"⚾ The pick: {F['fav']}")
st.caption(F["asof"] + " · Data: MLB Stats API · Model and reports: github.com/dipgip/mlb-WS-forecast")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Model: title odds", f"{F['fav_pct']}%",
          delta=f"{(now[ORDER[0]]['ws'] - pre[ORDER[0]]['ws']) * 100:+.1f} pts since LCS began")
c2.metric("90% interval", F["fav_ci"], help="From refitting the model on 1,000 resampled 2026 seasons.")
c3.metric("Betting market", F["fav_mkt"], help=F["mkt_note"])
c4.metric("Most likely World Series", F["top_mu"], help=f"Chance this matchup happens: {F['top_mu_pct']}")
st.write(F["lede"])

tabs = st.tabs(["Overview", "What-if simulator", "Backtest", "Stress test", "Market", "Team ratings", "Method & limits"])


# ---------------------------------------------------------------- shared charts
def odds_chart(odds_df, interval=True, before=True):
    base = alt.Chart(odds_df).encode(y=alt.Y("team:N", sort=ORDER, title=None, axis=TEAM_AXIS))
    bars = base.mark_bar(cornerRadiusEnd=4, height=26).encode(
        x=alt.X("title:Q", title="Chance to win the World Series", axis=alt.Axis(format="%"),
                scale=alt.Scale(domain=[0, max(0.75, odds_df["title"].max() + 0.1)])),
        color=alt.Color("team:N", scale=COLOR_SCALE, legend=None),
        tooltip=[alt.Tooltip("team:N", title="Team"), alt.Tooltip("title:Q", title="Title", format=".1%"),
                 alt.Tooltip("pennant:Q", title="Pennant", format=".1%")]
        + ([alt.Tooltip("p05:Q", title="90% low", format=".1%"), alt.Tooltip("p95:Q", title="90% high", format=".1%")] if interval else [])
        + ([alt.Tooltip("before:Q", title="Before LCS", format=".1%")] if before else []))
    layers = [bars]
    if interval:
        layers.append(base.mark_rule(color=INK, strokeWidth=1.5).encode(x="p05:Q", x2="p95:Q"))
        layers.append(base.mark_tick(color=INK, thickness=1.5, size=12).encode(x="p05:Q"))
        layers.append(base.mark_tick(color=INK, thickness=1.5, size=12).encode(x="p95:Q"))
    if before:
        layers.append(base.mark_tick(color=INK, thickness=3, size=34).encode(x="before:Q"))
    label_x = "p95:Q" if interval else "title:Q"
    layers.append(base.mark_text(align="left", dx=8, fontSize=14, fontWeight="bold", color=INK).encode(
        x=label_x, text=alt.Text("title:Q", format=".1%")))
    return alt.layer(*layers).properties(height=60 * len(odds_df))


def scoreboard_html(desc, games):
    teams = [games[0]["away"], games[0]["home"]]
    wins = {t: 0 for t in teams}
    for g in games:
        if g["home_runs"] is not None:
            wins[g["home"] if g["home_runs"] > g["away_runs"] else g["away"]] += 1
    a, b = sorted(teams, key=lambda t: -wins[t])
    status = f"Tied {wins[a]}–{wins[b]}" if wins[a] == wins[b] else \
        f"{short(a)} {'win' if wins[a] == 4 else 'lead'} {wins[a]}–{wins[b]}"
    cell = "padding:6px 10px;text-align:center;border-bottom:1px solid #234536;font-variant-numeric:tabular-nums"
    h = (f'<div style="background:#10261d;color:#f3f1e4;border-radius:6px;padding:16px 18px;margin-bottom:12px;'
         f'font-family:system-ui,sans-serif"><div style="display:flex;justify-content:space-between;flex-wrap:wrap;'
         f'gap:8px;font-weight:700;font-size:1.05rem;text-transform:uppercase;letter-spacing:.03em">'
         f'<span>{desc}</span><span style="color:#f2c14e">{status}</span></div>'
         f'<div style="overflow-x:auto"><table style="border-collapse:collapse;width:100%;min-width:520px;margin-top:8px">'
         f'<tr><th style="{cell};text-align:left;color:#8fa89a;font-weight:500">Best of {len(games)}</th>'
         + "".join(f'<th style="{cell};color:#8fa89a;font-weight:500">G{g["g"]}</th>' for g in games)
         + f'<th style="{cell};color:#8fa89a;font-weight:500">W</th></tr>')
    for t in teams:
        h += (f'<tr><td style="{cell};text-align:left;font-weight:700;white-space:nowrap">'
              f'<span style="display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:8px;'
              f'background:{TEAM_COLORS.get(t, "#888")}"></span>{short(t)}</td>')
        for g in games:
            if g["home_runs"] is None:
                h += f'<td style="{cell};color:#234536">·</td>'
                continue
            r = g["home_runs"] if g["home"] == t else g["away_runs"]
            o = g["away_runs"] if g["home"] == t else g["home_runs"]
            h += f'<td style="{cell};font-weight:700;font-size:1.15rem;color:{"#f2c14e" if r > o else "#8fa89a"}">{r}</td>'
        h += f'<td style="{cell};font-weight:800;font-size:1.25rem;color:#f2c14e">{wins[t]}</td></tr>'
    h += (f'<tr><td style="{cell};text-align:left;font-size:.72rem;color:#8fa89a;border:0">Home</td>'
          + "".join(f'<td style="{cell};font-size:.72rem;color:#8fa89a;border:0">{short(g["home"])}</td>' for g in games)
          + f'<td style="{cell};border:0"></td></tr></table></div>')
    nxt = next((g for g in games if g["home_runs"] is None), None)
    if nxt and max(wins.values()) < 4:
        sp = f" · {nxt['away_sp']} vs {nxt['home_sp']}" if nxt.get("away_sp") and nxt.get("home_sp") else ""
        h += (f'<div style="font-size:.75rem;color:#8fa89a;margin-top:8px">Next: G{nxt["g"]}, {nxt["date"]}, '
              f'{short(nxt["away"])} @ {short(nxt["home"])}{sp}</div>')
    return h + "</div>"


def current_odds_frame():
    return pd.DataFrame([{"team": t, "title": now[t]["ws"], "pennant": now[t]["pennant"],
                          "p05": UNC[t]["p05"], "p95": UNC[t]["p95"], "before": pre[t]["ws"]} for t in ORDER])


# ---------------------------------------------------------------- Overview
with tabs[0]:
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.subheader("Title odds for the last four teams")
        st.caption("Bar = now · whisker = 90% interval (1,000 resampled seasons) · thick tick = before LCS Game 1. "
                   + F["swing"])
        st.altair_chart(odds_chart(current_odds_frame()), width="stretch")
        mu = pd.DataFrame([{"Possible World Series": f"{short(k.split(' vs ')[0])} vs {short(k.split(' vs ')[1])}",
                            "Chance it happens": v["p_matchup"], "AL team wins": v["p_al_wins"],
                            "NL team wins": 1 - v["p_al_wins"],
                            "Home field": short(DATA["odds"]["ws_home_field"][k]["team"])}
                           for k, v in DATA["odds"]["ws_matchups"].items()]).sort_values("Chance it happens", ascending=False)
        st.dataframe(mu, hide_index=True, width="stretch", column_config={
            c: st.column_config.ProgressColumn(c, format="percent", min_value=0, max_value=1, color=ACCENT)
            for c in ("Chance it happens", "AL team wins", "NL team wins")})
    with right:
        st.subheader("Where the series stand")
        for desc, games in DATA["series"].items():
            st.html(scoreboard_html(desc, games))
        st.subheader("What the next game does")
        st.caption(F["watch_text"])
        wf = pd.DataFrame(DATA["whatif"])
        for r in wf.itertuples():
            with st.container(border=True):
                st.markdown(f"**If the {short(r.if_wins)} win {r.series} Game {r.game}**")
                cols = st.columns(len(ORDER))
                for col, t in zip(cols, ORDER):
                    v = wf.loc[r.Index, t]
                    col.metric(short(t), pct(v), delta=f"{(v - now[t]['ws']) * 100:+.1f}", delta_color="normal")

    hist = EXTRA["history"]
    if hist is not None and hist.as_of.nunique() > 1:
        st.subheader("How the forecast has moved")
        st.altair_chart(alt.Chart(hist).mark_line(point=True).encode(
            x=alt.X("as_of:T", title="Forecast date"), y=alt.Y("p_title:Q", axis=alt.Axis(format="%"), title="Title odds"),
            color=alt.Color("team:N", scale=COLOR_SCALE), tooltip=["as_of", "state", "team", alt.Tooltip("p_title", format=".1%")]),
            width="stretch")

# ---------------------------------------------------------------- What-if simulator
with tabs[1]:
    st.subheader("What-if simulator")
    st.write("Set any series score and modeling choice, and the real model recomputes every team's title odds. "
             "Nothing here changes the saved forecast.")
    d = model_inputs()
    cA, cN, cM = st.columns(3, gap="large")

    def series_inputs(col, key, label):
        teams, home, wins = d[key]
        with col:
            st.markdown(f"**{label}**")
            vals = {}
            for t in teams:
                vals[t] = st.select_slider(f"{short(t)} wins", options=[0, 1, 2, 3, 4], value=wins[t], key=f"{key}-{t}")
        if all(v == 4 for v in vals.values()):
            col.error("Both teams can't have 4 wins.")
            return None
        return vals

    al_w = series_inputs(cA, "alcs", "ALCS")
    nl_w = series_inputs(cN, "nlcs", "NLCS")
    with cM:
        st.markdown("**Model settings**")
        lam = st.select_slider("Shrinkage toward average (λ)", options=[20, 40, 80, 160, 320], value=80,
                               help="80 was chosen by out-of-sample tuning. Lower trusts 2026 results more.")
        k = st.slider("Confidence (logit scale k)", 0.0, 1.5, 1.0, 0.05,
                      help="1.0 is the model as tuned. 0 makes every game a coin flip; above 1 is more confident.")
    if al_w and nl_w:
        r = Scaled(ratings_for(lam), k=k) if k != 1.0 else ratings_for(lam)
        sim, sim_mu = B.bracket_odds(r, d["alcs"], d["nlcs"], d["reg"], d["divisions"],
                                     alcs_wins=al_w, nlcs_wins=nl_w)
        rows = []
        for t in ORDER:
            rows.append({"team": t, "Scenario": sim[t]["ws"], "Current forecast": now[t]["ws"]})
        df = pd.DataFrame(rows).melt("team", var_name="Version", value_name="title")
        chart = alt.Chart(df).mark_bar(cornerRadiusEnd=3).encode(
            y=alt.Y("team:N", sort=ORDER, title=None, axis=TEAM_AXIS),
            yOffset=alt.YOffset("Version:N", sort=["Scenario", "Current forecast"]),
            x=alt.X("title:Q", axis=alt.Axis(format="%"), title="Chance to win the World Series"),
            color=alt.Color("team:N", scale=COLOR_SCALE, legend=None),
            opacity=alt.Opacity("Version:N", scale=alt.Scale(domain=["Scenario", "Current forecast"], range=[1, 0.35]),
                                legend=alt.Legend(title=None, orient="top")),
            tooltip=["team", "Version", alt.Tooltip("title:Q", format=".1%")])
        st.altair_chart(chart.properties(height=280), width="stretch")
        mcols = st.columns(len(ORDER))
        for col, t in zip(mcols, ORDER):
            col.metric(short(t), pct(sim[t]["ws"]), delta=f"{(sim[t]['ws'] - now[t]['ws']) * 100:+.1f} vs now",
                       help=f"Pennant: {pct(sim[t]['pennant'])}")
        with st.expander("World Series matchups in this scenario"):
            st.dataframe(pd.DataFrame([{"Matchup": k_, "Chance it happens": v["p_matchup"], "AL team wins": v["p_al_wins"]}
                                       for k_, v in sim_mu.items()]).sort_values("Chance it happens", ascending=False),
                         hide_index=True, width="stretch", column_config={
                             c: st.column_config.ProgressColumn(c, format="percent", min_value=0, max_value=1, color=ACCENT)
                             for c in ("Chance it happens", "AL team wins")})

# ---------------------------------------------------------------- Backtest
with tabs[2]:
    bt = DATA["backtest"]
    st.subheader("Can it be trusted? 11 real Octobers")
    st.write(F["bt_series"])
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Series favorites won", pct(bt["series_fav_won"], 0), help=f"Predicted {pct(bt['series_fav_pred'], 0)}; "
              f"95% interval {pct(bt['series_fav_ci'][0], 0)}–{pct(bt['series_fav_ci'][1], 0)}")
    m2.metric("Game favorites won", pct(bt["game_fav_won"]), help=f"{bt['n_games']} playoff games")
    m3.metric("World Series favorites", f"{sum(r['fav_won'] for r in bt['ws'])} of {len(bt['ws'])}")
    m4.metric("Playoff log loss", f"{bt['game_ll']['model']:.4f}",
              delta=f"{bt['game_ll']['model'] - bt['game_ll']['coin']:.4f} vs coin flip", delta_color="inverse",
              help=f"Coin flip {bt['game_ll']['coin']:.4f}, standings {bt['game_ll']['log5']:.4f}. Lower is better.")
    cl, cr = st.columns([3, 2], gap="large")
    with cl:
        cal = pd.DataFrame(bt["calibration"])
        line = alt.Chart(pd.DataFrame({"x": [0.5, 0.85], "y": [0.5, 0.85]})).mark_line(strokeDash=[5, 5], color=MUTED).encode(
            x=alt.X("x:Q", scale=alt.Scale(domain=[0.45, 0.85]), axis=alt.Axis(format="%"),
                    title="Predicted series win probability for the favorite"),
            y=alt.Y("y:Q", scale=alt.Scale(domain=[0.45, 0.85]), axis=alt.Axis(format="%"), title="How often the favorite won"))
        pts = alt.Chart(cal).mark_circle(size=140, color="#5cc493" if dark else "#0f5c3c").encode(
            x="predicted:Q", y="actual:Q",
            tooltip=[alt.Tooltip("n:Q", title="Series"), alt.Tooltip("predicted:Q", format=".1%"),
                     alt.Tooltip("actual:Q", format=".1%")])
        lbl = alt.Chart(cal).mark_text(align="left", dx=10, color=MUTED).encode(
            x="predicted:Q", y="actual:Q", text=alt.Text("n:Q", format="d"))
        st.altair_chart((line + pts + lbl).properties(height=340, title="Series calibration, 2015–2025"),
                        width="stretch")
        st.caption(F["calib_note"])
    with cr:
        ws = pd.DataFrame(bt["ws"]).rename(columns={"season": "Year", "fav": "Model favorite", "p_fav": "Fav. chance",
                                                     "winner": "Winner", "fav_won": "Called"})
        ws["Called"] = ws["Called"].map({1: "✓", 0: "✗ upset", True: "✓", False: "✗ upset"})
        st.dataframe(ws, hide_index=True, width="stretch",
                     column_config={"Year": st.column_config.NumberColumn(format="%d"),
                                    "Fav. chance": st.column_config.NumberColumn(format="percent")})
        st.caption(F["ws_clear"])
    st.subheader("Does adjusting for starting pitchers help? No.")
    sp = EXTRA["sp"]
    s = EXTRA["sp_summary"]
    st.write(f"Each past playoff game was adjusted for its actual starters (season FIP, regressed) at increasing weight. "
             f"Predictions got slightly worse, not better: at a realistic weight the starter model beat the plain model in "
             f"only {pct(s['share_boot_better'], 0)} of bootstrap resamples ({s['n_games']} games).")
    st.altair_chart(alt.Chart(sp).mark_line(point=True, color=INK).encode(
        x=alt.X("starter_weight:Q", title="Weight on starting pitcher (0 = current model)"),
        y=alt.Y("log_loss:Q", scale=alt.Scale(zero=False), title="Postseason log loss (lower is better)"),
        tooltip=["starter_weight", alt.Tooltip("log_loss", format=".4f")]).properties(height=240),
        width="stretch")

# ---------------------------------------------------------------- Stress test
with tabs[3]:
    st.subheader(F["sens_head"])
    st.write(f"Each row changes one judgment call. Across these the favorite's title odds range {F['sens_range']}. "
             f"That range measures sensitivity to choices; the 90% interval measures statistical noise. With every remaining "
             f"game a coin flip, the current series lead alone still gives the favorite {F['coin_pct']}.")
    sens = pd.DataFrame(DATA["sensitivity"])
    long = sens.melt("scenario", var_name="team", value_name="title")
    long["faded"] = long.scenario.str.contains("untested|coin flip")
    sc_order = list(sens.scenario)
    st.altair_chart(alt.Chart(long).mark_bar(cornerRadiusEnd=3).encode(
        y=alt.Y("scenario:N", sort=sc_order, title=None),
        x=alt.X("title:Q", axis=alt.Axis(format="%"), title=None),
        color=alt.Color("team:N", scale=COLOR_SCALE, legend=None),
        opacity=alt.condition("datum.faded", alt.value(0.4), alt.value(1)),
        column=alt.Column("team:N", sort=ORDER, title=None, header=alt.Header(labelFontWeight="bold", labelFontSize=13)),
        tooltip=["team", "scenario", alt.Tooltip("title:Q", format=".1%")],
    ).properties(width=190, height=330), width="content")
    st.caption("Faded rows are untested (the roster adjustment) or deliberately extreme (coin flips).")
    st.dataframe(sens.set_index("scenario")[ORDER], width="stretch",
                 column_config={t: st.column_config.ProgressColumn(short(t), format="percent", min_value=0, max_value=1, color=ACCENT)
                                for t in ORDER})

# ---------------------------------------------------------------- Market
with tabs[4]:
    st.subheader("Model vs the betting market")
    st.write(F["market_text"])
    st.info(F["market_why"])
    adj = next(r for r in DATA["sensitivity"] if "(100%)" in r["scenario"])
    mk = pd.DataFrame([{"team": t, "Model": now[t]["ws"], "Roster-adjusted (untested)": adj[t],
                        "Market": DATA["market"][t]["implied"]} for t in ORDER])
    long = mk.melt("team", var_name="Source", value_name="p")
    st.altair_chart(alt.Chart(long).mark_point(size=160, filled=True).encode(
        y=alt.Y("team:N", sort=ORDER, title=None, axis=TEAM_AXIS),
        x=alt.X("p:Q", axis=alt.Axis(format="%"), title="Chance to win the World Series"),
        shape=alt.Shape("Source:N", scale=alt.Scale(domain=["Model", "Roster-adjusted (untested)", "Market"],
                                                    range=["circle", "triangle-up", "diamond"]),
                        legend=alt.Legend(orient="top", title=None)),
        color=alt.Color("team:N", scale=COLOR_SCALE, legend=None),
        tooltip=["team", "Source", alt.Tooltip("p:Q", format=".1%")]).properties(height=260),
        width="stretch")
    st.caption(F["mkt_note"] + ". Sources: " + ", ".join(f"[{s['source']}]({s['url']})" for s in DATA["market_sources"]))
    ro = pd.DataFrame([{"Team": short(t), "Starters used": ", ".join(v["sps"]),
                        "Staff FIP (season)": v["fip_season"], "Staff FIP (October)": v["fip_oct"],
                        "Lineup wOBA (season)": v["woba_season"], "Lineup wOBA (October)": v["woba_oct"],
                        "Market price": DATA["market"][t]["american"]}
                       for t, v in DATA["roster"].items()])
    st.markdown("**October roster check (untested)**")
    st.dataframe(ro, hide_index=True, width="stretch", column_config={
        c: st.column_config.NumberColumn(format="%.2f" if "FIP" in c else "%.3f")
        for c in ro.columns if "FIP" in c or "wOBA" in c})

# ---------------------------------------------------------------- Ratings
with tabs[5]:
    st.subheader("2026 team ratings, all 30 clubs")
    st.write(F["ratings_text"])
    ra = EXTRA["ratings_all"].copy()
    ra["Left in playoffs"] = ra.team.isin(ORDER)
    cl, cr = st.columns([2, 3], gap="large")
    with cl:
        pts = alt.Chart(ra).mark_circle(size=90).encode(
            x=alt.X("exp_RA_pg:Q", scale=alt.Scale(zero=False, reverse=True), title="Expected runs allowed / game (better →)"),
            y=alt.Y("exp_RS_pg:Q", scale=alt.Scale(zero=False), title="Expected runs scored / game"),
            color=alt.condition("datum['Left in playoffs']", alt.Color("team:N", scale=COLOR_SCALE, legend=None),
                                alt.value(MUTED)),
            size=alt.condition("datum['Left in playoffs']", alt.value(220), alt.value(70)),
            tooltip=["rank", "team", "W", alt.Tooltip("exp_RS_pg", format=".2f"), alt.Tooltip("exp_RA_pg", format=".2f"),
                     alt.Tooltip("exp_wpct", format=".3f")])
        txt = alt.Chart(ra[ra["Left in playoffs"]]).mark_text(align="left", dx=10, fontWeight="bold", color=INK).encode(
            x="exp_RA_pg:Q", y="exp_RS_pg:Q", text=alt.Text("team:N"))
        st.altair_chart((pts + txt).properties(height=420, title="Offense vs run prevention (top-right is best)"),
                        width="stretch")
    with cr:
        q = st.text_input("Filter teams", "", placeholder="Type a team name")
        view = ra[ra.team.str.contains(q, case=False)] if q else ra
        st.dataframe(view[["rank", "team", "W", "exp_RS_pg", "exp_RA_pg", "exp_wpct"]].rename(columns={
            "rank": "Rank", "team": "Team", "W": "Wins", "exp_RS_pg": "Exp. runs scored / G",
            "exp_RA_pg": "Exp. runs allowed / G", "exp_wpct": "Win % vs avg"}),
            hide_index=True, width="stretch", height=420,
            column_config={"Exp. runs scored / G": st.column_config.NumberColumn(format="%.2f"),
                           "Exp. runs allowed / G": st.column_config.NumberColumn(format="%.2f"),
                           "Win % vs avg": st.column_config.NumberColumn(format="%.3f")})

# ---------------------------------------------------------------- Method
with tabs[6]:
    st.subheader("How I got here")
    st.markdown(f"""
1. **Pulled every game since 2015.** {F['n_games_total']} regular-season and postseason results from the official MLB Stats API, plus the live bracket, rosters and announced starters.
2. **Rated every team on runs, not wins.** A Poisson model gives each team an offense and a defense rating, adjusted for opponents and pulled toward average. Home field is set from actual home win rates ({F['home_rate']} between equal teams), because run totals understate it.
3. **Tuned it on games it hadn't seen.** Fit through August, predict September, ten seasons over. Heavy shrinkage won, and weighting recent form didn't help.
4. **Graded it on 11 real Octobers.** Every playoff game and series from 2015–2025, each predicted using only that year's regular season. Adjusting for starting pitchers was also tested; it doesn't help.
5. **Ran the live bracket.** Each series from its current state, then all four possible World Series, with home field set by MLB's tiebreak rules.
6. **Measured the uncertainty and tried to break it.** 1,000 resampled seasons for the interval, eleven alternative setups, and a comparison against betting markets.

The full log is in `LOG.md`, the partner review in `REVIEW.md`, and the static report in `report/REPORT.md`.
""")
    st.subheader("What this model can't see")
    st.markdown(f"""
- It rates teams on the full season. Injuries and October roster changes appear only in the roster-adjusted scenario, which is not backtested.
- {F['next_matchup_caveat']}
- Bullpen fatigue, travel and day-to-day lineup choices are not modeled.
- {F['sample_caveat']}
- Market prices are a recorded snapshot from published articles, not a live feed.
""")
    st.caption(f"Data through {F['data_through']}. Rebuild with `./run_all.sh`, then reload this page.")
