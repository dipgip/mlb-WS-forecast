# 2026 World Series Forecast

*Forecast as of Oct 14, 2026 games · next: ALCS G3 Oct 15, NLCS G4 Oct 15. Static version of the report. The [live dashboard](https://mlb-ws-forecast-w3huajspduv8ae2mctsydr.streamlit.app/) has the same numbers plus a what-if simulator.*

## The pick: Milwaukee Brewers, 65%

|  |  |
| --- | ---: |
| Model | **65%** |
| 90% interval (1,000 resampled seasons) | 51%–76% |
| Betting market, margin removed | 46% |
| Most likely World Series | TB vs MIL (54%) |

The Brewers finished 103–59, the best record in baseball. They lead the Dodgers 3–0 in the NLCS and would host Games 1, 2, 6 and 7 of any World Series. Every version of the model makes them the favorite. That still leaves a 35% chance the trophy goes somewhere else. October baseball is mostly noise, and this report shows how much.

## Where the series stand

### AL Championship Series: tied 1–1

|  | G1 | G2 | G3 | G4 | G5 | G6 | G7 | W |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Guardians** | **7** | 1 | · | · | · | · | · | **1** |
| **Rays** | 3 | **3** | · | · | · | · | · | **1** |
| *Home* | *Rays* | *Rays* | *Guardians* | *Guardians* | *Guardians* | *Rays* | *Rays* |  |

Next: Game 3, 2026-10-15, Rays at Guardians, Griffin Jax vs Gavin Williams.

### NL Championship Series: Brewers lead 3–0

|  | G1 | G2 | G3 | G4 | G5 | G6 | G7 | W |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Dodgers** | 1 | 4 | 2 | · | · | · | · | **0** |
| **Brewers** | **2** | **7** | **6** | · | · | · | · | **3** |
| *Home* | *Brewers* | *Brewers* | *Dodgers* | *Dodgers* | *Dodgers* | *Brewers* | *Brewers* |  |

Next: Game 4, 2026-10-15, Brewers at Dodgers, Shane Drohan vs Tyler Glasnow.

## Title odds

Exact probabilities from every remaining path through the bracket, using the real home/away schedule. Since the LCS began, the Brewers moved from 36% to 65% and the Dodgers went from 32% to 4%.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="figures/odds-dark.png">
  <img alt="Chance to win the 2026 World Series by team, with 90% intervals" src="figures/odds-light.png" width="100%">
</picture>

| Team | Title now | 90% interval | Pennant now | Title before LCS | Market |
| --- | ---: | ---: | ---: | ---: | ---: |
| Milwaukee Brewers | **65.1%** | 51%–76% | 94.2% | 36.4% | 46% |
| Tampa Bay Rays | **19.7%** | 11%–32% | 57.1% | 21.3% | 20% |
| Cleveland Guardians | **11.3%** | 6%–20% | 42.9% | 10.7% | 13% |
| Los Angeles Dodgers | **3.9%** | 2%–7% | 5.8% | 31.5% | 20% |

| Possible World Series | Chance it happens | AL team wins | NL team wins | Home field |
| --- | ---: | ---: | ---: | ---: |
| Rays vs Brewers | 53.8% | 34.4% | 65.6% | Brewers (better record) |
| Guardians vs Brewers | 40.4% | 26.2% | 73.8% | Brewers (better record) |
| Rays vs Dodgers | 3.3% | 36.4% | 63.6% | Dodgers (better record) |
| Guardians vs Dodgers | 2.5% | 28.0% | 72.0% | Dodgers (better record) |

## The forecast record

Every forecast is saved before the games it predicts and never changed afterward. Each one is fingerprinted, checked by the test suite and pushed to GitHub with a timestamped tag. The model is frozen; new games only change the bracket situation, and each refresh adds forecasts it can be graded on. Retrospective rows were computed afterward for context and are never scored.

| Forecast | Kind | Made (UTC) | Series state | Before first pitch | Brewers | Rays | Guardians | Dodgers | Code |
| --- | --- | --- | --- | :---: | ---: | ---: | ---: | ---: | --- |
| Before LCS (retro) | retrospective | 2026-10-13 22:32:03 | ALCS 0–0 · NLCS 0–0 | n/a | 36.4% | 21.3% | 10.7% | 31.5% | [17d0d6b](https://github.com/dipgip/mlb-WS-forecast/commit/17d0d6b) |
| Oct 13 · v1 | live | 2026-10-13 18:58:10 | ALCS CLE 1–0 · NLCS MIL 2–0 | ✓ | 57.2% | 15.2% | 15.6% | 12.0% | [5455bc2](https://github.com/dipgip/mlb-WS-forecast/commit/5455bc2) |
| Oct 13 · v2 | live | 2026-10-13 22:32:03 | ALCS CLE 1–0 · NLCS MIL 2–0 | ✓ | 57.4% | 14.9% | 15.2% | 12.5% | [17d0d6b](https://github.com/dipgip/mlb-WS-forecast/commit/17d0d6b) |
| Oct 14 · v2 | live | 2026-10-14 16:10:11 | ALCS 1–1 · NLCS MIL 2–0 | ✓ | 56.5% | 19.9% | 11.4% | 12.3% | [590fdb6](https://github.com/dipgip/mlb-WS-forecast/commit/590fdb6) |
| Oct 15 · v2 | live | 2026-10-15 18:32:43 | ALCS 1–1 · NLCS MIL 3–0 | ✗ | 65.1% | 19.7% | 11.3% | 3.9% | [b91e22b](https://github.com/dipgip/mlb-WS-forecast/commit/b91e22b) |

- **Oct 13 · v1 → Oct 13 · v2:** no new games; model v1 → v2.
- **Oct 13 · v2 → Oct 14 · v2:** ALCS G2: Cleveland Guardians 1, Tampa Bay Rays 3.
- **Oct 14 · v2 → Oct 15 · v2:** NLCS G3: Milwaukee Brewers 6, Los Angeles Dodgers 2.

**Game-by-game forecasts**

| Game | Matchup | First pitch (UTC) | Forecast made (UTC) | Model favorite | Chance | Result |
| --- | --- | --- | --- | --- | ---: | --- |
| ALCS G2 | Cleveland Guardians @ Tampa Bay Rays | 2026-10-14 00:00:00 | 2026-10-13 22:34:05 | Tampa Bay Rays | 57.1% | ✓ Tampa Bay Rays (3–1) |
| ALCS G3 | Tampa Bay Rays @ Cleveland Guardians | 2026-10-15 17:00:00 | 2026-10-14 16:10:12 | Tampa Bay Rays | 51.6% | not played yet |
| NLCS G3 | Milwaukee Brewers @ Los Angeles Dodgers | 2026-10-15 00:00:00 | 2026-10-13 22:34:05 | Los Angeles Dodgers | 51.9% | ✗ Milwaukee Brewers (6–2) |
| NLCS G4 | Milwaukee Brewers @ Los Angeles Dodgers | 2026-10-16 00:00:00 | 2026-10-15 18:32:44 | Los Angeles Dodgers | 51.9% | not played yet |

## How I got here

The full log with every number is in [LOG.md](../LOG.md), and a partner review of the weak spots is in [REVIEW.md](../REVIEW.md). The core method was fixed before any 2026 odds were computed.

1. **Pulled every game since 2015.** 28,091 regular-season and postseason results from the official MLB Stats API, plus the live bracket, rosters and announced starters.
2. **Rated every team on runs, not wins.** A Poisson model gives each team an offense and a defense rating, adjusted for opponents and pulled toward average. Home field is set from actual home win rates (53% between equal teams), because run totals understate it.
3. **Tuned it on games it hadn't seen.** Fit through August, predict September, ten seasons over. Heavy shrinkage won, and weighting recent form didn't help.
4. **Graded it on 11 real Octobers.** Every playoff game and series from 2015–2025, each predicted using only that year's regular season. Also tested whether adjusting for each game's starting pitchers helps; it doesn't.
5. **Ran the live bracket.** Each series from its current state, then all four possible World Series, with home field set by MLB's tiebreak rules.
6. **Measured the uncertainty and tried to break it.** 1,000 resampled seasons for the interval, eleven alternative setups, and a comparison against betting markets.

## Can it be trusted? The backtest

The stronger team does not reliably win in October, so the useful question is whether the model's probabilities are honest. When the model's series favorite was predicted to win 59% of the time, favorites actually won 58% across 113 series. With a sample that small, the 95% interval on that win rate is 49%–67%: consistent with good calibration, but not proof of it.

| Measure | Result |
| --- | ---: |
| Series favorites won | 58% of 113 (predicted 59%) |
| Game favorites won | 54.5% of 440 |
| Playoff log loss: model / standings / coin flip (lower is better) | 0.6848 / 0.6893 / 0.6931 |

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="figures/calibration-dark.png">
  <img alt="Predicted versus actual series win rate for model favorites" src="figures/calibration-light.png" width="100%">
</picture>

Dots show how often the model's series favorite actually won, grouped by how confident the model was. Each bin holds only 19–38 series, so expect scatter around the line.

| World Series | Model favorite | Fav. chance | Winner |  |
| --- | --- | ---: | --- | --- |
| 2015 | Kansas City Royals | 58.7% | Kansas City Royals | ✓ called |
| 2016 | Chicago Cubs | 65.4% | Chicago Cubs | ✓ called |
| 2017 | Los Angeles Dodgers | 50.7% | Houston Astros | ✗ upset |
| 2018 | Boston Red Sox | 50.8% | Boston Red Sox | ✓ called |
| 2019 | Houston Astros | 62.7% | Washington Nationals | ✗ upset |
| 2020 | Los Angeles Dodgers | 68.1% | Los Angeles Dodgers | ✓ called |
| 2021 | Houston Astros | 59.2% | Atlanta Braves | ✗ upset |
| 2022 | Houston Astros | 69.4% | Houston Astros | ✓ called |
| 2023 | Texas Rangers | 68.2% | Texas Rangers | ✓ called |
| 2024 | Los Angeles Dodgers | 52.1% | Los Angeles Dodgers | ✓ called |
| 2025 | Los Angeles Dodgers | 52.9% | Los Angeles Dodgers | ✓ called |

Of 11 World Series since 2015, the model's favorite won 8. Counting only clear favorites (55% or more), it's 5 of 7; the rest were near coin flips.

## Stress test: the Brewers lead under every setup

Each row changes one judgment call. Across these the favorite's title odds range 58%–68%. That range measures sensitivity to choices; the wider interval above measures statistical noise. With every remaining game a coin flip, the current series lead alone still gives the favorite 47%.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="figures/sensitivity-dark.png">
  <img alt="Title odds for each team under each modeling scenario" src="figures/sensitivity-light.png" width="100%">
</picture>

## Model vs the betting market

Sportsbooks agree on the favorite: the market has the Brewers at 46% after removing the bookmaker margin, against the model's 65%. The biggest disagreement is the Dodgers: market 20%, model 4%.

One natural explanation is October deployment: the Dodgers' playoff rotation (Tarik Skubal, Blake Snell, Tyler Glasnow, Yoshinobu Yamamoto) projects to a 3.51 FIP against 3.85 for the season, and an adjustment for that moves them to 5%. But I tested the closest checkable version, adjusting each past playoff game for its actual starting pitchers (387 games, 2015–2025), and it did not improve predictions: it beat the plain model in only 39% of bootstrap resamples. So the gap is unexplained. The rotation story is a hypothesis, not a finding.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="figures/market-dark.png">
  <img alt="Model, roster-adjusted, and market title odds by team" src="figures/market-light.png" width="100%">
</picture>

| Team | Model | Roster-adjusted (untested) | Market | Sportsbook prices |
| --- | ---: | ---: | ---: | ---: |
| Milwaukee Brewers | 65.1% | 63.8% | 46.3% | +105 |
| Tampa Bay Rays | 19.7% | 19.1% | 20.4% | +340 |
| Cleveland Guardians | 11.3% | 11.6% | 13.4% | +550 |
| Los Angeles Dodgers | 3.9% | 5.5% | 19.9% | +350 |

1 sportsbook sources captured Oct 14, 2026, margin removed with the power method.

| October roster check (untested) | Starters used | Staff FIP: season → Oct | Lineup wOBA: season → Oct |
| --- | --- | ---: | ---: |
| Brewers | Jacob Misiorowski, Logan Henderson, Robert Gasser, Dustin May | 3.81 → 3.68 | 0.323 → 0.323 |
| Rays | Drew Rasmussen, Freddy Peralta, Nick Martinez, Griffin Jax | 3.98 → 3.86 | 0.318 → 0.318 |
| Guardians | Parker Messick, Gavin Williams, Daniel Espino, Foster Griffin | 3.93 → 3.84 | 0.311 → 0.313 |
| Dodgers | Tarik Skubal, Blake Snell, Tyler Glasnow, Yoshinobu Yamamoto | 3.85 → 3.51 | 0.327 → 0.329 |

## What the next game in each series does

Title odds after each possible result. The largest single swing: if the Guardians win ALCS Game 3, the Rays fall from 20% to 13%.

| If this happens | Brewers | Rays | Guardians | Dodgers |
| --- | ---: | ---: | ---: | ---: |
| Guardians win ALCS G3 | 66.6% (+1.5) | 13.1% (−6.6) | 16.3% (+5.0) | 4.0% (+0.1) |
| Rays win ALCS G3 | 63.7% (−1.4) | 25.9% (+6.2) | 6.6% (−4.7) | 3.8% (−0.1) |
| Dodgers win NLCS G4 | 61.4% (−3.7) | 19.8% (+0.1) | 11.3% (+0.0) | 7.5% (+3.6) |
| Brewers win NLCS G4 | 69.1% (+4.0) | 19.7% (−0.1) | 11.2% (−0.0) | 0.0% (−3.9) |

## 2026 team ratings

Expected runs per game against a league-average opponent after shrinkage, and the implied win rate. The Guardians rank 16th, the lowest of the four teams left.

| Rank | Team | Wins | Exp. runs scored / G | Exp. runs allowed / G | Win % vs avg |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | **Milwaukee Brewers** | 103 | 5.09 | 4.00 | .612 |
| 2 | **Los Angeles Dodgers** | 100 | 4.91 | 3.93 | .602 |
| 3 | Chicago Cubs | 89 | 5.23 | 4.44 | .578 |
| 4 | New York Yankees | 93 | 4.67 | 4.00 | .571 |
| 5 | Atlanta Braves | 94 | 4.65 | 4.04 | .565 |
| 6 | **Tampa Bay Rays** | 98 | 4.65 | 4.23 | .543 |
| 7 | Boston Red Sox | 87 | 4.40 | 4.02 | .541 |
| 8 | Detroit Tigers | 76 | 4.52 | 4.23 | .531 |
| 9 | Chicago White Sox | 84 | 4.82 | 4.59 | .523 |
| 10 | San Diego Padres | 91 | 4.53 | 4.32 | .522 |
| 11 | Pittsburgh Pirates | 82 | 4.80 | 4.60 | .521 |
| 12 | Philadelphia Phillies | 88 | 4.52 | 4.40 | .513 |
| 16 | **Cleveland Guardians** | 85 | 4.29 | 4.30 | .499 |

## What this model can't see

- It rates teams on the full season. Injuries and October roster changes appear only in the roster-adjusted scenario, which is not backtested.
- It ignores the specific pitching matchup in each game (for example Griffin Jax vs Gavin Williams in ALCS Game 3). The backtest found that adding starters by season FIP doesn't help, so a better pitcher metric is open work.
- Bullpen fatigue, travel and day-to-day lineup choices are not modeled.
- The backtest covers 113 series: enough to show the probabilities aren't badly off, not enough to fine-tune them.
- Market prices are a recorded snapshot from published articles, not a live feed, and they move by the hour.

---

Data: MLB Stats API (statsapi.mlb.com), games through Oct 14, 2026. Market prices: [SI (DraftKings)](https://www.si.com/betting/world-series-odds-rays-jump-ahead-of-guardians-dodgers-to-no-2-spot-after-evening-alcs). Generated 2026-10-15 by `report/build_md.py`; rebuild everything with `./run_all.sh`.
