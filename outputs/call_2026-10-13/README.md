# The call: outputs as of 2026-10-13

These are the model's outputs exactly as committed in `854a843`, the commit tagged
`forecast-2026-10-13-pre-ALCS-G2` and pushed at 22:32 UTC on 2026-10-13, before ALCS Game 2.
They were copied out of git history unchanged with `git show 854a843:outputs/<file>`.

Once the World Series is decided, the reports present the analysis from the moment of the
call (odds, uncertainty, stress test, market comparison and what-ifs) using these files,
next to the final result and grade. The latest outputs in `outputs/` describe the finished
bracket (everything 0% or 100%), so they can't stand in for a forecast.

Verify: `git show 854a843:outputs/odds_2026.json | diff - odds_2026.json`
