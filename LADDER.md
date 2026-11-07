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
| 7 | 2026-10-30 | Jalen Brunson ast OVER (proxy) | 4.5 | -110 | 68% | win (6 ast) | 6.95 (3.64 x 1.909) |
| 8 | 2026-10-31 | James Harden ast OVER (proxy) | 4.5 | -110 | 68% | win (7 ast) | 13.27 (6.95 x 1.909) |
| 9 | 2026-11-01 | Scottie Barnes reb UNDER (proxy) | 7.5 | -110 | 68% | win (6 reb) | 25.33 (13.27 x 1.909) |
| 10 | 2026-11-02 | Scottie Barnes reb UNDER (proxy) | 7.5 | -110 | 68% | loss (15 reb) | 1.00 (ladder dead from 25.33, restart #3 at next pick) |
| 11 | 2026-11-03 | no pick (no NBA games today) | - | - | - | pass | 1.00 |
| 12 | 2026-11-04 | Derik Queen pts UNDER (proxy) | 15.5 | -110 | 69% | loss (20 pts) | 1.00 (ladder dead, restart #3 only reached 1.00; restart #4 at day 13) |
| 13 | 2026-11-05 | Oso Ighodaro ast UNDER (proxy) | 4.5 | -110 | 68% | win (1 ast) | 1.91 (1.00 x 1.909) |
| 14 | 2026-11-06 | Dejounte Murray ast UNDER (proxy) | 6.5 | -110 | 69% | win (4 ast) | 3.64 (1.91 x 1.909) |
| 15 | 2026-11-07 | Karl-Anthony Towns ast OVER (proxy) | 2.5 | -110 | 68% | pending | 3.64 (staked, restart #4) |

Running: picks won / picks made = 6 / 9 after day 10 (day 6 void, day 11 pass, neither counts). Restart #2 (day 4) climbed to 25.33 (253 dollars at a 10 dollar start) then died on day 10 (Barnes grabbed 15 reb vs a 7.5 line). Balance is back to 1.00 (10 dollars), restart #3 begins at the next pick. Best balance reached: 25.33.

Day 6 note: all three games today (ATL-CLE, MEM-POR, SAC-NO) have flux flags, so no flux-free pick existed. NO was the lightest flux. Model 69.5% is rounded to 70% in the table.

Day 7 note: NY-PHI is a 1.5 point spread, NY has no flux flag (only Alvarado out). Brunson averages 6.2 ast over the last 10 (36.9 min) against a 4.5 line; model 67.8%. The ORL-TOR unders were skipped because of heavy ORL injuries (flux).

Day 8 note: SA-MIN had the only flux-free players but SA is a 12.5 point favourite (blowout risk), so skipped. CLE at MIL: MIL favoured by 9.5, CLE has only Tyson out. Harden averages 6.3 ast over the last 10 (35.5 min) against a 4.5 line; model 68.0%. CHA-PHI picks skipped (Knueppel, White out, heavy flux).

Day 9 note: BOS-ORL tips 3:30 PM, ORL picks skipped (Banchero and Suggs out, usage should rise against the model's 0.9 factor). BKN-IND and LAC-GS skipped (heavy flux, Curry and Green out). TOR-LAL spread is 2.5, Leonard has been out since Oct 29. Barnes averages 6.0 reb over the last 10 (36.2 min) against a 7.5 line; model 68.4%, 71% hit rate over 40 games.

Day 10 note: 15 game slate. NY-BKN (NY -14.5) and SA-UTAH (SA -15.5) skipped for blowout risk, even though KAT ast over 2.5 (69.5%) and Castle pts over 14.5 (69.1%) priced well. Wagner reb u6.5 skipped because the normal model (61%) and hit-rate model (81%) disagree widely. Barnes reb u7.5 again: TOR +5.5 at LAC, no new flux, last-10 mean 6.1 (36.3 min), model 68.3%, both methods agree (67.7% and 72.6%).

Day 11 note: ESPN scoreboard for 2026-11-03 has no games (next slate is 2026-11-04, first tip 7 PM ET), so there was nothing to pick. This is the first no-pick day; if 2026-11-04 also has no good pick the ladder stops for good.

Day 12 note: 14 game slate (first tip 7 PM ET). The only flux-free players were SA-DAL (SA -11.5, blowout risk), skipped. Queen pts u15.5: NO-UTAH spread 4.5, only Julian Reese flagged, Poole and Missi out long-term, Trey Murphy day-to-day (model 68.7% even if he sits), last-10 mean 15.9, model 69.1%, normal 69.4% and hit-rate 72.5% agree. Barrett ast u4.5 (68.3%) ranked lower because normal 74.5% and hit-rate 64.2% disagree. Pass-day streak reset: day 11 was a no-game pass, day 12 has a pick.

Running: picks won / picks made = 6 / 10 after day 12 (day 6 void, day 11 pass). Restart #3 died immediately on day 12 (Queen scored 20 vs a 15.5 line). Balance 1.00 (10 dollars), restart #4 begins with day 13. Best balance reached: 25.33.

Day 13 note: only 2 games tonight (ORL-PHX 9 PM ET, MIA-GS 10 PM ET). Ighodaro ast u4.5: PHX -1.5, last-10 mean 3.3 (24.6 min), model 68.1%, normal 71.9% and hit-rate 66.8% agree. PHX has some flux (Bridges, Kennard, Spencer flagged), MIA-GS has GS -6.5 and heavy MIA flux. Wagner reb u6.5 (72.4%) skipped: over the 70% cap and normal 67.5% vs hit-rate 82.9% split.

Running: picks won / picks made = 7 / 11 after day 13 (day 6 void, day 11 pass). Restart #4 won day 13 (Ighodaro 1 ast vs 4.5), balance 1.91 (19.09 dollars at a 10 dollar start). Best balance reached: 25.33.

Day 14 note: 9 game slate (first tip 7 PM ET). SA-SAC skipped (SA -17.5, blowout). Murray ast u6.5: NO-MIN spread 3.5, NO only Missi out long-term (Reese flagged), MIN without Edwards, DiVincenzo and Shannon, last-10 mean 6.4 (effective 5.6, 31.7 min), 7 of 10 unders, model 68.7%, normal 65.7% and hit-rate 78.3% agree. Barrett ast u4.5 (68.2%) skipped because Barnes is day-to-day, Fears pts u18.5 (68.3%) skipped for 36 pt outlier games, Bey reb o3.5 (70.0%) at the cap.

Running: picks won / picks made = 8 / 12 after day 14 (day 6 void, day 11 pass). Restart #4 is 2 for 2 (days 13 and 14), balance 3.64 (36.4 dollars at a 10 dollar start). Best balance reached: 25.33.

Day 15 note: 7 game slate, all unstarted at check time (first tip DEN-IND 5 PM ET). Towns ast o2.5: NY at CLE spread 5.5, only Hart out for NY, last-10 mean 2.8 (40-game mean 3.8, 29.9 min), model 67.7%, normal 69.5% and hit-rate 68.9% agree. Wagner ast u7.5 (67.6%) skipped: ORL has Banchero, Suggs, Bane, Isaac out (heavy flux) and normal 62.7% vs hit-rate 77.1% disagree.

## Extension (instruction from AD, 2026-11-02)
The ladder keeps going past day 10 under these rules: Claude decides when to cash out (stop once enough is made) or runs it up to a 10k dollar paper balance (balance 1000.00 on a 1.00 unit scale at a 10 dollar start, i.e. 1000x). Stop only for one day if a day has no good pick, and stop for good only if the following day also has none. Everything else in the rules above still applies. Tickets continue as LADDER-d11, d12 and so on.
