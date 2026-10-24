# Lab notes

One entry per experiment: question, result, decision. Dropped ideas stay here so we do not retry them.
Rule: nothing goes into the live model without AD's approval, a win on two time splits, and 30+ settled paper bets for anything about picks.
Scripts live in `lab/`. They only read data; they never change the model.

## 1. Do overs run cold early in a season? (Oct 24, 2026)
Script: `lab/overs_early_season.py START END`. Prices each player from earlier games only, at a line equal to his last-10 average, and compares the model's average P(over) with the real over rate.
- Oct 20 to 23, 2026 (first 4 days, n=1200 lines): model said 47.7% over, actual 36.9%. Points 36.1%, rebounds 42.6%, assists 38.0%, threes 31.0%. Players scored 1.8 points under their line on average.
- Nov 10 to 25, 2025: model 47.8%, actual 47.2% (no gap). Dec 1, 2025 to Jan 15, 2026: model 46.7%, actual 44.8% (small gap).
- Not caused by playoff minutes: players whose last 10 games were regular season missed more (33.6% over) than playoff-heavy ones (41.4%). Minutes were only 0.8 below their last-10 average.
- League scoring: average game total this week 226.3 (28 games) vs 230.4 for the rest of last regular season and 234.4 for the first two weeks last year. Only about 1 standard error, so not conclusive alone.
- Paper log agrees: overs 9 of 22, unders 11 of 12 (small sample).

## 2. Does the league-wide miss persist day to day? (Oct 24, 2026)
Script: `lab/league_drift.py`. For 148 regular-season days in 2025-26, the correlation between the previous 7 days' miss and the next day's miss was -0.04. A day's miss has sd about 7.6 points of probability.
- Meaning: during a season, a bad day does not predict the next day, so a rolling "league drift" correction would not have helped. The first-week gap is about 3.8 standard deviations of a normal 4-day window, so it is unusual, but we have only one season of data and cannot tell if it repeats every October.

## Decision (pending AD approval)
- No model change yet. One week of data and one prior season is not enough to build a correction.
- Practical rule for now: treat overs as weaker than the model says for the first two weeks of the season, and prefer unders when the edge is similar.
- Re-run `python lab/overs_early_season.py 2026-10-20 <today>` in two weeks (around Nov 7). If the gap is still over 5 points, propose a temporary early-season over discount for AD to approve; if it closes, drop the idea and record that here.
- Needs data we do not have: 2024-25 and earlier Octobers to see whether early-season cold overs repeat. Backfilling them with `nba_edge.py sync --since 2024-10-01` is possible but takes a few minutes; ask AD first.
