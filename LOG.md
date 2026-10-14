# Project Log — 2026 World Series Prediction

A running, timestamped record of every step, decision, and result. Newest steps at the bottom.

---

## Step 0 — Framing (2026-10-13)

**Question:** Who wins the 2026 World Series?

**Where things stand today** (pulled live from `statsapi.mlb.com`):

| Series | Status | Next game |
|---|---|---|
| ALCS: Cleveland Guardians vs Tampa Bay Rays | CLE leads 1–0 | G2 tonight @ TB |
| NLCS: Milwaukee Brewers vs Los Angeles Dodgers | MIL leads 2–0 | G3 Oct 14 @ LAD |
| World Series | Starts Oct 23 | — |

Road to here: NYY swept BOS and CWS beat HOU in the AL Wild Card round. In the NL WC round SD swept CHC and ATL beat PHI 2–1. In the Division Series, TB beat NYY 3–0, CLE beat CWS 3–2, LAD beat ATL 3–1, and MIL beat SD 3–1.

**Approach (decided up front, so results can't steer the method):**
1. **Data:** every regular-season and postseason game from 2015–2026, from the official MLB Stats API.
2. **Team strength:** a ridge-regularized Poisson model of runs scored, with a separate offense and defense rating for each team plus home-field advantage. Fit on each season's games, so ratings account for opponent strength.
3. **Validation:** backtest on every postseason from 2015–2025. Fit only on that year's regular season, predict each playoff game, and score the model against a coin flip and against a naive win-% baseline. This tells us how much to trust *any* prediction here.
4. **Simulation:** Monte Carlo the rest of the bracket game by game, starting from the actual series states and following the real home/away schedule.
5. **Sensitivity:** check whether the answer survives reasonable changes (recency weighting, postseason pitching-staff adjustment, shrinkage strength).

**Why this design:** win-loss record is noisy. Run differential predicts future wins better, and a game-level model also corrects for schedule strength. Baseball playoffs are famously close to random, so the backtest matters most: it puts honest error bars on the headline number.

---

## Step 1 — Data pull (`src/fetch_data.py`)

Every game from 2015–2026 came from the MLB Stats API `/schedule` endpoint, with game types R, F, D, L and W. Raw JSON is cached in `data/raw/`, and the tidy table is `data/processed/games.csv`.

- Count check: about 2,430 regular-season games each year, 898 in 2020, and 2,429 in 2026. Every postseason game through Oct 12, 2026 is included.
- Postponed games that were replayed keep only their final record. Ties are dropped.

**2026 regular season, the final four:**

| Team | W–L | Run diff | Pythag W% |
|---|---|---|---|
| Milwaukee Brewers | 103–59 | +214 | .633 |
| Los Angeles Dodgers | 100–62 | +201 | .629 |
| Tampa Bay Rays | 98–64 | +86 | .557 |
| Cleveland Guardians | 85–77 | **+11** | .507 |

First read: the NLCS is a meeting of MLB's two best teams. Cleveland played like a .500 team and has won with run prevention plus some October luck.

---

## Step 2 — Tuning the model (`src/model.py`, `src/tune.py`)

**Model:** a Poisson regression on runs, with an offense and defense rating per team, a home-field term, and a ridge penalty λ that shrinks ratings toward average. Expected runs become a win probability through the Pythagenpat formula.

**Tuning protocol:** for each season from 2015–2025 (skipping 2020), fit on games through Aug 31 and predict every game from Sep 1 on. That's about 4,000 held-out games, and the playoffs are never used here.

| Method | Log loss (lower is better) |
|---|---|
| Home field only | 0.6925 |
| log5 on win % | 0.6792 |
| **Poisson model, λ=80, no recency weighting** | **0.6772** |

Decisions:
- **λ = 80.** Strong shrinkage wins. Raw 2026 ratings overstate how far apart teams really are.
- **No recency weighting.** Weighting recent games (half-lives of 30, 60 or 120 days) never helped, so the model uses the full season equally weighted.
- The gains over baselines are real but small. Even the best model calls only about 57% of single games correctly, and that is the nature of baseball.

---

## Step 3 — Postseason backtest, 2015–2025 (`src/backtest.py`)

For each year, fit on that regular season only, then predict every playoff game (440) and every playoff series (113). Series odds are computed **exactly** with dynamic programming over series states and the real home/away order (`src/simulate.py`). That replaced the Monte Carlo planned in Step 0: same answer, no sampling noise.

| | Coin flip | log5 on record | **Model** |
|---|---|---|---|
| Game log loss | 0.6931 | 0.6893 | **0.6850** |
| Game Brier | 0.2500 | — | **0.2460** |
| Series log loss | 0.6931 | — | **0.6649** |

- Series favorites won **60.2%** of the time, against 57.6% predicted. The model is well calibrated and, if anything, a little modest.
- The best-fit logit scale was k = 1.18, but its bootstrap 95% CI is [0.32, 2.11]. That's too uncertain to act on, so **no recalibration** is applied.
- World Series favorites went **8 for 11** from 2015–2025.
- **Takeaway:** the model finds a real but modest edge. October is noisy, and every probability below should be read with that in mind.

---

## Step 4 — 2026 ratings and live bracket odds (`src/predict.py`)

Fit on all 2,429 games of the 2026 regular season. Neutral-site expected win % against an average team: MIL .611, LAD .602, TB .543, CLE .499 (16th in MLB).

World Series home field goes to the team with the better record. That's the NL champion in every possible matchup (MIL 103 or LAD 100 wins, versus TB 98 and CLE 85).

| Team | Before LCS: pennant / title | **Now: pennant / title** |
|---|---|---|
| Milwaukee Brewers | 52.2% / 35.5% | **82.2% / 57.2%** |
| Cleveland Guardians | 40.4% / 11.2% | 57.2% / 15.6% |
| Tampa Bay Rays | 59.6% / 21.5% | 42.8% / 15.2% |
| Los Angeles Dodgers | 47.8% / 31.7% | 17.8% / 12.0% |

Most likely World Series: CLE vs MIL (47%, MIL wins it 73%), then TB vs MIL (35%, MIL wins it 65%).

---

## Step 5 — Roster adjustment and sensitivity (`src/fetch_rosters.py`, `src/roster_adjust.py`, `src/sensitivity.py`)

**Roster adjustment:** used each team's active 26-man postseason roster and the actual October starters from the MLB schedule. October pitching was modeled as 55% from the 4 starters and 45% from the top 7 relievers. Player FIP and wOBA were regressed toward league average.

| Team | Staff FIP: season → October | Lineup wOBA: season → October |
|---|---|---|
| LAD | 3.85 → **3.50** (−0.35 R/G) | .327 → .329 |
| MIL | 3.81 → 3.68 | .323 → .323 |
| TB | 3.98 → 3.86 | .318 → .318 |
| CLE | 3.93 → 3.84 | .311 → .313 |

The Dodgers benefit most: Skubal, Snell, Yamamoto and Glasnow start, with Ohtani in the mix. This adjustment is **not backtested**, so it is used only as a scenario, not in the headline.

**Title odds by scenario (%):**

| Scenario | MIL | CLE | TB | LAD |
|---|---|---|---|---|
| **Baseline** | **57.2** | 15.6 | 15.2 | 12.0 |
| λ=40 / λ=160 | 58.7 / 54.8 | 14.1 / 17.9 | 14.9 / 15.6 | 12.2 / 11.7 |
| Recency weighting (60-day half-life) | 56.0 | 16.8 | 16.9 | 10.3 |
| Include 2026 postseason games | 57.0 | 16.4 | 14.7 | 11.9 |
| Roster adjustment 50% / 100% | 55.7 / 54.0 | 15.5 / 15.4 | 14.8 / 14.2 | 14.0 / 16.3 |
| Spread k=1.18 / k=0.6 | 59.7 / 51.0 | 13.2 / 21.7 | 14.7 / 16.2 | 12.4 / 11.1 |
| Every game a coin flip | 40.6 | 32.8 | 17.2 | 9.4 |

**Milwaukee is the favorite in every scenario.** Even with pure coin flips, its 2–0 lead makes it the most likely champion.

**What-if for the next game in each series:**
- **ALCS G2 tonight:** a CLE win puts CLE at 20.6% and TB at 8.7%. A TB win puts TB at 20.6% and CLE at 11.5%.
- **NLCS G3, Oct 14:** a MIL win puts MIL at 65.5% and LAD at 3.9%. A LAD win puts MIL at 48.8% and LAD at 20.2%.

---

## Step 6 — External check: betting markets (Oct 13)

Sportsbook prices from SI and Fox/DraftKings are roughly MIL +105, LAD +350, CLE +400 and TB +475. Removing the vig gives **MIL ≈45%, LAD ≈20%, CLE ≈18%, TB ≈16%.**

- The market and the model agree on the order at the top and on Milwaukee as the clear favorite.
- **The biggest disagreement is the Dodgers** (market 20% vs model 12%). The market is paying for star power and the October rotation, the same effect the roster scenario captures (16%). Milwaukee's lower market price is the mirror image.
- I keep the pre-registered model as the headline and report the market gap openly rather than tuning toward it.

---

## Final call

**Milwaukee Brewers win the 2026 World Series. Model: 57%; range 51–60% across all sensible scenarios; market ≈45%.**
Most likely Fall Classic: **Guardians vs Brewers**, with Milwaukee holding home field.

---

## Step 7 — Presentation (`report/`)

- `report/build.py` bundles every output into `report/data.json` and injects it into `report/template.html`, producing `report/index.html`. No number on the page is typed by hand.
- Published as a private artifact: https://claude.ai/artifact/4vMEBXCDwCmGWZfo77XmFP
- Palette: the four reference categorical slots (LAD blue, CLE orange, TB aqua, MIL gold). Every mark carries a direct team label, so color never identifies a team on its own. Node wasn't installed, so the palette validator script couldn't run; this order relies on the reference palette's documented adjacent-pair pass.

## How to refresh after tonight's games

Use the project skill `.claude/skills/ws-forecast-update/SKILL.md`: re-fetch data, run predict, roster and sensitivity, then rebuild and republish. The model stays frozen.

---

## Step 8 — Public-repo audit (2026-10-13)

Scanned everything pushed to GitHub before treating the repo as shareable.

- **Clean:** no API keys, tokens, passwords, private keys or local file paths.
- **Fixed: personal email in commit metadata.** The commit author email is now the GitHub no-reply address, and this repo's git config uses it for all future commits.
- **Fixed: verbatim MLB data republished.** The 25 raw JSON responses in `data/raw/` carry MLB Advanced Media's copyright notice and player birthdates and birthplaces. They are now git-ignored and removed from history. The new `src/fetch_rosters.py` rebuilds them; it replaces the ad-hoc curl pulls and closes a gap where `run_all.sh` couldn't rebuild the roster inputs. A re-fetch matched the original snapshot exactly: same values, with only the order of stat groups differing. The roster-adjustment output was unchanged.
- **Kept:** `data/processed/` (game facts only) and `outputs/` (my own analysis).

---

## Step 9 — Partner review (`REVIEW.md`)

I re-read the project as a skeptical partner and tested each suspected weak link. The full write-up with evidence and fixes is in `REVIEW.md`.

- **The pick holds up under every fix.** The weak links are in confidence and presentation.
- **Uncertainty:** the bootstrap 90% interval for Milwaukee is 43–70%. That's far wider than the 51–60% scenario range shown on the page.
- **Pitcher adjustments:** a game-level starting-pitcher adjustment did *not* improve the postseason backtest (log loss 0.6882 → 0.6890). That undercuts the FIP-based roster adjustment behind the Dodgers explanation.
- **Home field:** it is underestimated (50.5% implied vs 53.3% actual), but fixing it barely moves the answer (57.2% → 57.5%).
- **Report brittleness:** the prose contains 17 hardcoded facts that will go stale on the next update.
- **Held up:** the λ choice is robust, and the series math was verified against a 400,000-run simulation.

---

## Step 10 — Fixes from the review (model v2)

All 8 findings were fixed (see the Resolution table in `REVIEW.md`), and the whole pipeline was re-run.

| | Model v1 | **Model v2** |
|---|---|---|
| Home win % between equal teams | 50.5% | 52.9% (observed rate) |
| Postseason game log loss | 0.6850 | 0.6848 |
| Postseason series log loss | 0.6649 | 0.6663 |
| Series favorites won / predicted | 60.2% / 57.6% | 58.4% / 58.8% |

**2026 title odds (Oct 13), v2:**

| Team | Point | 90% interval | Market (power de-vig) |
|---|---|---|---|
| **Milwaukee Brewers** | **57.4%** | 43–70% | 47% |
| Cleveland Guardians | 15.2% | 8–25% | 18% |
| Tampa Bay Rays | 14.9% | 8–26% | 15% |
| Los Angeles Dodgers | 12.5% | 7–20% | 20% |

**Final call unchanged:** Milwaukee Brewers, 57% (90% interval 43–70%).

---

## Step 11 — Static report (`report/REPORT.md`, `report/build_md.py`)

The interactive page needs a browser, and its claude.ai link is private. So the report now also exists as plain Markdown, which reads as-is on GitHub or in any Markdown viewer.

- `report/build_md.py` reads the same `report/data.json` as the interactive page, so the numbers can't drift apart.
- Four charts (title odds with 90% intervals, calibration, sensitivity, model vs market) are rendered with matplotlib into `report/figures/`, in light and dark versions. `<picture>` tags show the right one for the reader's GitHub theme.
- Every table on the interactive page is reproduced as a Markdown table, including the series linescores.
- Wired into `run_all.sh` and the refresh skill. The two versions link to each other.

---

## Step 12 — Local dashboard (`dashboard/app.py`)

A Streamlit dashboard that mirrors the report and runs locally (`./run_dashboard.sh`, http://localhost:8501). Nothing is hosted.

**Why Streamlit:** it's Python, so the dashboard calls the real model code instead of a reimplementation. Power BI's desktop app is Windows-only and would need its own copy of the model.

**Tabs:** Overview (headline metrics, odds with 90% intervals, scoreboards, next-game what-ifs, forecast history), **What-if simulator**, Backtest (with the pitcher test), Stress test, Market, Team ratings (all 30 teams, with a scatter plot and a filter), and Method & limits.

**What-if simulator:** set any LCS score, shrinkage λ and confidence k, and the model recomputes title odds live with `bracket.bracket_odds`. Checked:
- Dodgers rally to 3–2: Dodgers 48.7%.
- Dodgers win the NLCS: Brewers 0%, Dodgers 68.4%.
- Both ALCS teams set to 4 wins: the app shows a clear error instead of crashing.

**Problems found and fixed while testing:**
- Streamlit listens on the whole network by default. It's now bound to localhost only.
- Any top-level `[theme]` setting forced a light page while the charts followed the OS dark mode, which made labels invisible. Accent colors now go in `[theme.light]` / `[theme.dark]`.
- Team names were truncated on chart axes, and Streamlit's deprecated `use_container_width` was replaced.

**Tests:** `tests/test_dashboard.py` (Streamlit AppTest) checks that the app renders with no errors and that the simulator recomputes odds. The suite is now 14 tests.

**Also:** `REPORT.md` moved into `report/`, next to the other report files.

---

## Step 13 — Dashboard deployed

Deployed to Streamlit Community Cloud from `main` / `dashboard/app.py`: https://mlb-ws-forecast-w3huajspduv8ae2mctsydr.streamlit.app/

- **Access:** granted only for the personal account; no organization access was given.
- **Public:** an anonymous visitor reaches the app (HTTP 200 after Streamlit's cookie redirects), not a login page.
- **Rendering:** checked the headline, metrics, odds chart, matchup table and scoreboards, and they match the local version.
- **Updates:** it redeploys on every push, so each refresh reaches the dashboard automatically.
- **Links:** the README, the interactive report and `report/REPORT.md` all link to it.

---

## Step 14 — Forecast record and scheduled refresh

**What new games are for.** The model is frozen (v2), and team ratings come from the regular season only. New games don't make it smarter; they only change the bracket state. Each refresh records new forecasts *before* the games they predict. That gives the model many graded predictions instead of one, shows how the uncertainty resolves, and lets it be compared with the market as both update.

**The record (`forecasts/`)** is append-only:
- **Title-odds snapshots** (`forecasts/*.json`). Each holds its UTC creation time, model version, code commit, the games it knew about, and the next first pitch. A snapshot counts as pregame only if it was created before that first pitch.
- **Per-game forecasts** (`forecasts/games/`). The model's win probability for the next game of each live series, written only before first pitch.
- **Fingerprints** in `forecasts/MANIFEST.sha256`, checked in CI by `tests/test_forecast_record.py`. GitHub commit and tag times serve as the external clock.
- **Retrospective snapshots** are labeled as such and never scored.

**On record before ALCS Game 2** (first pitch 2026-10-14 00:00 UTC; tags `forecast-2026-10-13-pre-ALCS-G2` and `forecast-2026-10-13-games`):

| Record | Forecast | Created (UTC) |
|---|---|---|
| Original call (v1, from commit 5455bc2) | MIL 57.2% | 18:58 |
| Current forecast (v2) | MIL 57.4% (90% interval 42.7–69.6%) | 22:32 |
| ALCS G2: CLE @ TB | TB 57.1% | 22:34 |
| NLCS G3: MIL @ LAD | LAD 51.9% | 22:34 |

`outputs/forecast_history.csv` was removed, because it could be silently overwritten.

**Scheduled refresh.** A local scheduled task (`ws-forecast-refresh`) runs at 09:00 and 13:00 local time daily and follows `.claude/skills/ws-forecast-update/SKILL.md`. That's after the previous night's games and before the earliest first pitch (15:00 local). The 13:00 run is a backup in case the app was closed in the morning. A game whose first pitch has passed is skipped rather than recorded late. After the World Series, the task writes the final grade and turns itself off.

---

## Update — 2026-10-14 (ALCS tied 1–1)

**Result:** the Rays beat the Guardians 3–1 in ALCS Game 2. The model had the Rays at 57.1% before first pitch, so **1 of 1 graded game forecasts was correct**. Log loss is 0.560, against 0.693 for a coin flip.

**State:** ALCS tied 1–1 · NLCS Brewers lead 2–0.

| Team | Title odds | 90% interval | Change | Market (SI, today) |
|---|---|---|---|---|
| Milwaukee Brewers | 56.5% | 41–69% | −1.0 | 46% |
| Tampa Bay Rays | 19.9% | 11–32% | +5.0 | 20% |
| Los Angeles Dodgers | 12.3% | 7–20% | −0.2 | 20% |
| Cleveland Guardians | 11.4% | 6–19% | −3.8 | 13% |

**Newly forecast:** ALCS Game 3 (Rays @ Guardians, first pitch 2026-10-15 17:00 UTC; MLB moved it to a day game): Rays 51.6%. NLCS Game 3 (tonight, 00:00 UTC) was already on record from Oct 13: Dodgers 51.9%.

Tag `forecast-2026-10-14-ALCS1-1-NLCS2-0` was pushed at 18:29 UTC, before both games.

## Step 15 — Fixing the crashed refresh

**What happened:** the 09:00 scheduled run computed everything correctly. It wrote the snapshot and the ALCS Game 3 forecast at 16:10 UTC, then crashed in `report/build_md.py`. It correctly pushed nothing, which left valid forecasts stuck on this machine.

**Cause:** the first unplayed game in the record had its result stored as NaN, not empty. NaN counts as "true" in Python, so the builder tried to print it as text and crashed. The model tests couldn't catch it, because no test ran the report builders.

**Fixes:**
1. **The record went out first.** The pending forecasts were pushed and tagged at 18:29 UTC, before any affected first pitch.
2. **The bug, at its source.** `report/build.py` now turns missing values into `null`. It also writes strict JSON (`allow_nan=False`), so any future NaN fails loudly in the builder instead of downstream.
3. **A test that would have caught it.** `tests/test_reports.py` builds both reports end to end into a temp folder (`REPORT_OUT`). It reproduces the crash with the old code and passes with the fix. That makes 21 tests.
4. **The design flaw.** A report bug blocked the time-critical forecast record. Refreshes now push in two phases: (1) record the forecasts, run the model and record tests, then push and tag immediately; (2) build the reports, run the full suite, then push. A report failure can no longer delay the record. Both the skill and the scheduled task prompt were updated.
