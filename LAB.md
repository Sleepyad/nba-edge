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

## 3. Does the first-week over gap repeat every October? (Oct 24, 2026)
Backfilled 2023-24 and 2024-25 into a separate lab database (not the repo): `NBA_DB=<path> python nba_edge.py --db <path> sync --since 2023-10-01 --until 2025-10-19 --no-lines`, then ran `lab/overs_early_season.py` with `NBA_DB` set. Each October is priced with the full previous season as history, the same situation as now.

| Window | Model P(over) | Actual over | Gap |
|---|---|---|---|
| Oct 22 to 26, 2024 (first 5 days) | 46.9% | 40.6% | -6.3 |
| Oct 27 to Nov 9, 2024 | 47.1% | 45.5% | -1.6 |
| Oct 21 to 25, 2025 (first 5 days) | 47.1% | 42.8% | -4.3 |
| Oct 26 to Nov 8, 2025 | 47.2% | 46.9% | -0.3 |
| Oct 20 to 23, 2026 (first 4 days) | 47.8% | 37.3% | -10.5 |

- The cold first week repeats in every October we have (about -4 to -6 points), and fades within two weeks. This year is colder than usual.
- Mechanism is unproven (defense ahead of offense early, new rosters, players still ramping up). It does not matter for the rule below, which is calendar-based.

### Proposal for AD to approve (NOT live)
Early-season discount on P(over), mirrored on P(under): about -5 points for the first 7 days of the regular season, about -1 point for days 8 to 21, none after. Test it first on one October fit and another October held out (2024 fit, 2025 test already points the same way). Until approved, the rule of thumb in NOTES.md stays: shade overs, prefer unders, for the first two weeks.

## Decision (pending AD approval)
- No model change yet. One week of data and one prior season is not enough to build a correction.
- Practical rule for now: treat overs as weaker than the model says for the first two weeks of the season, and prefer unders when the edge is similar.
- Re-run `python lab/overs_early_season.py 2026-10-20 <today>` in two weeks (around Nov 7). If the gap is still over 5 points, propose a temporary early-season over discount for AD to approve; if it closes, drop the idea and record that here.
- Experiment 3 answered the missing-data question: it repeats. See the proposal above.
