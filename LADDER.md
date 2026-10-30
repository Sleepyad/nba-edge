# 10-day paper ladder (started Sat 2026-10-24, review Wed 2026-11-03)

Goal: measure the real hit rate of ONE best pick per day on a real bet365 line, and see how far a roll-over ladder gets.

## Rules
- One pick per day, single leg, real bet365 line (AD sends it) or the model's proxy line if none was sent (marked "proxy").
- Minimum model confidence 65%, cap 70% (above that the model is usually fooled by a small sample).
- Prefer teams without rotation newcomers (no flux flag), no big blowout risk, healthy minutes. If nothing qualifies, take the best available and say so.
- Never flip a pick if the line moves: take it or pass (pass counts as no pick, the ladder holds).
- Stake is a paper 1.00 unit. Win: whole balance rolls to the next day at the pick's odds. Loss: ladder is dead, restart the next day at 1.00 (count restarts).
- Every pick is logged in data/paper_bets.csv with ticket LADDER-dNN and graded by the bot.
- Also record the plain hit rate (picks won / picks made). That is the number that matters, the ladder is just the story.

## Log
| Day | Date | Pick | Line | Odds | Model % | Result | Balance |
|---|---|---|---|---|---|---|---|
| 1 | 2026-10-24 | Zion Williamson pts OVER | 18.5 | -112 | 69% | loss (17 pts) | 1.00 |
| 2 | 2026-10-25 | Wendell Carter Jr. ast UNDER (proxy) | 2.5 | -110 | 68% | win (2 ast) | 1.91 (1.00 x 1.909) |
| 3 | 2026-10-26 | Jock Landale ast UNDER (proxy) | 2.5 | -110 | 65% | loss (4 ast) | 1.00 (ladder dead, restart #2 at day 4) |
| 4 | 2026-10-27 | OG Anunoby ast UNDER (proxy) | 2.5 | -110 | 68% | win (2 ast) | 1.91 (1.00 x 1.909) |
| 5 | 2026-10-28 | Karl-Anthony Towns ast OVER (proxy) | 2.5 | -110 | 68% | win (5 ast) | 3.64 (1.91 x 1.909) |
| 6 | 2026-10-29 | Dejounte Murray ast UNDER (proxy) | 7.5 | -110 | 70% | void (did not play, no stat line) | 3.64 (stake returned, ladder holds) |
| 7 | 2026-10-30 | Jalen Brunson ast OVER (proxy) | 4.5 | -110 | 68% | pending | 3.64 |

Running: picks won / picks made = 3 / 5 after day 6 (day 6 void, does not count), day 7 pending. Ladder restart #2 started day 4 and is alive at 3.64 after two straight wins (days 4 and 5).

Day 6 note: all three games today (ATL-CLE, MEM-POR, SAC-NO) have flux flags, so no flux-free pick existed. NO was the lightest flux. Model 69.5% is rounded to 70% in the table.

Day 7 note: NY-PHI is a 1.5 point spread, NY has no flux flag (only Alvarado out). Brunson averages 6.2 ast over the last 10 (36.9 min) against a 4.5 line; model 67.8%. The ORL-TOR unders were skipped because of heavy ORL injuries (flux).
