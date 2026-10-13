# Partner Review — Weak Links and Fixes

*Reviewed 2026-10-13. Each claim was tested against the data, and the evidence is shown. The test code lives in this session's scratch work; the fixes below say where it belongs in `src/`.*

## Bottom line

**The pick survives review. The way it's presented doesn't, quite.**

Milwaukee stays the favorite under every fix I tried. The weak links are:
- **Overconfidence:** the report presents the 57% as more certain than it is.
- **An unsupported narrative:** the Dodgers explanation leans on a method that failed its own test.
- **A brittle report:** it will show wrong numbers after the next refresh.

---

## Ranked findings

Severity reflects what would most damage the project's credibility or correctness, not how hard each fix is.

### 1. The headline understates uncertainty — **High**

**What's weak:** the hero shows "51–60%, range across 9 alternative model setups." That only measures *modeling choices*. It ignores the larger source of uncertainty: the ratings come from a single noisy season.

**Evidence:** I resampled the 2026 season 300 times, refit the model each time and re-ran the bracket.

| Team | Point estimate | 90% interval |
|---|---|---|
| Milwaukee | 57% | **43%–70%** |
| Cleveland | 16% | 9%–26% |
| Tampa Bay | 16% | 8%–25% |
| Dodgers | 12% | 7%–20% |

The honest range is roughly 2.5 times wider than the one on the page.

**Fix:** add the bootstrap to `sensitivity.py` and show "57% (90% interval 43–70%)" as the headline. Keep the scenario table, labeled as the robustness check it is.

### 2. The Dodgers explanation rests on a method that failed its own test — **High**

**What's weak:** the market section says the market likely prices in the Dodgers' October rotation, citing the roster adjustment (staff FIP 3.85 → 3.50, title odds 12% → 16%). That adjustment was never backtested.

**Evidence:** I prototyped the closest testable version: adjusting each postseason game for its *actual* starting pitchers by regressed FIP. I backtested it on 387 games from 2015–2025 (excluding 2020).

| Starter weight | Postseason log loss |
|---|---|
| 0 (current model) | **0.6882** |
| 0.30 | 0.6881 |
| 0.55 | 0.6890 |
| 1.00 | 0.6929 |

- Giving starters a realistic weight made predictions *slightly worse*. It beat the plain model in only 42% of bootstrap resamples.
- Season-FIP pitcher tweaks show **no detectable predictive value** in October, so the roster-adjusted 16% shouldn't carry the Dodgers argument.

**Fix:**
- Reword the market section: the Dodgers gap is *unexplained*, and the October-rotation story is a hypothesis, not a finding.
- Either backtest the full roster adjustment, or drop it to a footnote.
- Pitcher quality likely matters but isn't captured by season FIP at this sample size. A better pitcher metric, such as projection-based or Statcast-based, would be the next thing to try.

### 3. The report will show wrong numbers after the next update — **High (for this project)**

**What's weak:** the charts and tables read from `data.json`, but the prose doesn't. I found **17 hardcoded facts** in `report/template.html`, including "Oct 13", "G2 tonight", "CLE vs MIL", "43% chance", "from 36% to 57%", "near 20%", "has 12%", "below 4%", "16th" and "2–0". The market odds are also hand-typed into `report/build.py`, and `as_of` is hardcoded.

That contradicts the project's own claim that "no number on the page is typed by hand."

**Fix:**
- Generate every sentence that contains a number from `data.json`, using small template strings in the page script.
- Move market prices into `data/market_odds.csv`, with a timestamp and source per row.
- Derive `as_of` from the data.
- Add `report/build.py` to `run_all.sh`; it isn't there now.

### 4. The market comparison is thin — **Medium**

**What's weak:**
- It uses one snapshot, typed by hand.
- Sources disagreed: a Polymarket figure in the same search had Milwaukee at 33%, though it was a day older.
- Vig was removed proportionally. Futures prices carry a known *favorite–longshot bias*: underdogs are overpriced, which likely understates the market's true Milwaukee number.

**Fix:**
- Record prices from 2–3 books over time.
- Use a power or Shin de-vig method instead of proportional.
- Compare at the series level: LCS series prices are more liquid than futures.

### 5. Home-field advantage is estimated wrong, but it barely matters — **Medium (correctness), Low (impact)**

**What's weak:** the model learns home field from runs. Home teams that lead after 8½ innings don't bat in the 9th, so their run totals are cut short.

**Evidence:**

| | Home win % between equal teams |
|---|---|
| Model's implied home field | 50.5% |
| Actual 2026 | 52.9% |
| Actual 2015–2025 | 53.3% |
| Actual postseason | 53.6% |

Correcting it moves Milwaukee from 57.2% to 57.5% and backtest log loss from 0.6850 to 0.6848. The edge mostly cancels out because hosting alternates within a series.

**Fix:** estimate home field from wins rather than runs, or pin it to the pooled 53.3% rate. It's a correctness fix more than an accuracy fix.

### 6. "Well calibrated" overstates what 113 series can show — **Medium**

**What's weak:** the report says the model is well calibrated because favorites won 60.2% against 57.6% predicted. With 113 series, the 95% interval on 60.2% is about **51%–69%**. The data is *consistent with* good calibration; it doesn't establish it.

The "World Series favorites went 8 for 11" stat includes favorites at 50.2% and 50.4%, which are coin flips.

**Fix:** soften the wording to "consistent with good calibration," show the interval, and drop or caveat the 8-for-11 line.

### 7. Engineering gaps — **Medium/Low**

| Gap | Risk | Fix |
|---|---|---|
| No tests, no CI | A silent regression changes the forecast | `tests/`: exact series math vs simulation (verified 0.1776 vs 0.1771), model recovers known ratings on synthetic data, Pythagenpat symmetry. Add a GitHub Action. |
| The LCS-state logic is duplicated in `predict.py` and `sensitivity.py` | The two copies drift apart | One `series_states()` function in `predict.py` |
| World Series home-field tiebreak: on equal records the NL team always gets home field | Wrong on a tie (latent this year) | Apply MLB's tiebreakers: head-to-head, then division record |
| `ROSTER_DATE` and the team list are hardcoded | Stale rosters on refresh | Derive both from the live bracket |
| Outputs are overwritten on every run | Can't show how the forecast evolved, or score it | Write `outputs/history/<date>/` snapshots |
| `predict.record()` has a no-op `pd.concat` | Confusing to read | Simplify |

### 8. No accountability loop — **Medium**

**What's weak:** the project makes a forecast but has no plan to grade it.

**Fix:** after each refresh, append that day's title odds to `outputs/forecast_history.csv`. When the World Series ends, compute a Brier score against the market's history. That makes it a real test of the model rather than a single guess.

---

## What I checked that held up

- **The shrinkage setting (λ):** postseason log loss is flat from λ=20 to λ=160 (0.6851–0.6852), so the tuning choice isn't fragile.
- **The series math:** the exact calculation matches a 400,000-run brute-force simulation (0.1776 vs 0.1771).
- **The data:** full regular seasons and postseasons are present every year, and starters are named for 100% of postseason games.
- **The pick:** Milwaukee leads under every variant, including every fix above.

---

## Suggested order of work

| Priority | Item | Effort |
|---|---|---|
| 1 | Bootstrap interval in the headline (#1), softer calibration wording (#6) | Small |
| 2 | Drive all report prose from data; market odds file; build step in `run_all.sh` (#3) | Medium |
| 3 | Reword the Dodgers/market section and demote the roster adjustment (#2) | Small |
| 4 | Forecast history and scoring plan (#8), dated output snapshots | Small |
| 5 | Tests and CI, dedupe, tiebreak (#7) | Medium |
| 6 | Home field from wins (#5); better market de-vig (#4) | Small |
| 7 | Research: a pitcher metric that actually predicts October | Large |

---

## Resolution (2026-10-13)

Every finding was addressed. Re-running the full pipeline after the fixes gives **Milwaukee 57.4% (90% interval 43–70%)**, so the pick is unchanged.

| # | Finding | What changed |
|---|---|---|
| 1 | Understated uncertainty | `sensitivity.py` now runs 1,000 bootstrap refits and writes `outputs/uncertainty.csv`. The report headline shows the 90% interval, and the odds chart has interval whiskers. The scenario range is relabeled as sensitivity to modeling choices. |
| 2 | Dodgers story on an untested method | Added `src/sp_backtest.py`, which makes the starting-pitcher test reproducible: the plain model 0.6878 vs 0.6887 with starters; the starter version is better in 39% of resamples. The market section now calls the Dodgers gap unexplained. The roster adjustment is labeled "untested" everywhere. |
| 3 | Hardcoded report prose | `report/build.py` computes every number-bearing sentence into `facts`, and the template only displays them. Market prices moved to `data/market_odds.csv` (source, URL, capture date). `as_of` comes from the data. `run_all.sh` now ends with the report build. |
| 4 | Thin market comparison | `src/market.py` uses two sources, power-method de-vig, and keeps proportional results for comparison. Milwaukee's market number moved from 45% to 47%. Prices over time can be added as new rows. |
| 5 | Home field estimated from truncated runs | `model.fit` now sets home field so that average teams reproduce the observed home win rate (52.9% in 2026). Postseason game log loss improved from 0.6850 to 0.6848, and the best-fit confidence scale moved from 1.18 to 0.96 (closer to 1). Series log loss went slightly the other way (0.6649 → 0.6663). λ=80 is still the best setting. |
| 6 | Calibration overclaimed | The page shows the 95% interval (49–67%) and says "consistent with, not proof of" good calibration. The World Series record notes that only 7 of the 11 favorites were clear favorites (5 of 7 won). |
| 7 | Engineering | Added `src/bracket.py`, a pure shared module that removes the duplicate series code. Added the MLB tiebreak (record, then head-to-head, then intradivision record; it raises an error if still tied) and World Series in-progress support. `fetch_rosters.py` now finds the alive teams itself and takes the date from `ROSTER_DATE` or today. There are 12 `unittest` tests plus a GitHub Actions workflow. The tests caught a real bug: World Series placeholder teams ("AL Champion") were parsed as a live series. That is fixed. |
| 8 | No accountability loop | Every `predict.py` run appends to `outputs/forecast_history.csv`, ready to score against the outcome and the market. |

**Still open:** a pitcher metric that actually predicts October results. That's research, not a fix.
