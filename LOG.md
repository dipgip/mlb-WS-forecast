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

## Step 11 — Static report (`REPORT.md`, `report/build_md.py`)

The interactive page needs a browser, and its claude.ai link is private. So the report now also exists as plain Markdown, which reads as-is on GitHub or in any Markdown viewer.

- `report/build_md.py` reads the same `report/data.json` as the interactive page, so the numbers can't drift apart.
- Four charts (title odds with 90% intervals, calibration, sensitivity, model vs market) are rendered with matplotlib into `report/figures/`, in light and dark versions. `<picture>` tags show the right one for the reader's GitHub theme.
- Every table on the interactive page is reproduced as a Markdown table, including the series linescores.
- Wired into `run_all.sh` and the refresh skill. The two versions link to each other.
