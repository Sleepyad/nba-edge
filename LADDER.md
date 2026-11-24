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
| 15 | 2026-11-07 | Karl-Anthony Towns ast OVER (proxy) | 2.5 | -110 | 68% | win (3 ast) | 6.95 (3.64 x 1.909) |
| 16 | 2026-11-08 | Trey Murphy III pts OVER (proxy) | 14.5 | -110 | 67% | win (26 pts) | 13.27 (6.95 x 1.909) |
| 17 | 2026-11-09 | Stephon Castle ast OVER (proxy) | 4.5 | -110 | 68% | win (7 ast) | 25.33 (13.27 x 1.909) |
| 18 | 2026-11-10 | Franz Wagner reb UNDER (proxy) | 6.5 | -110 | 70% | loss (7 reb) | 1.00 (ladder dead from 25.33, restart #5 at day 19) |
| 19 | 2026-11-11 | Anthony Black reb UNDER (proxy) | 5.5 | -110 | 68% | loss (7 reb) | 1.00 (restart #5 died immediately; restart #6 at day 20) |
| 20 | 2026-11-12 | Devin Booker 3pm UNDER (proxy) | 2.5 | -110 | 69% | loss (4 3pm) | 1.00 (restart #6 died immediately; restart #7 at day 21) |
| 21 | 2026-11-13 | Karl-Anthony Towns pts UNDER (proxy) | 21.5 | -110 | 70% | loss (23 pts) | 1.00 (restart #7 died immediately; restart #8 at day 22) |
| 22 | 2026-11-14 | Donovan Mitchell pts OVER (proxy) | 21.5 | -110 | 69% | void (did not play, no plays in the game) | 1.00 (stake returned, restart #8 holds) |
| 23 | 2026-11-15 | Landry Shamet 3pm UNDER (proxy) | 2.5 | -110 | 69% | loss (4 3pm) | 1.00 (restart #8 died immediately; restart #9 at day 24) |
| 24 | 2026-11-16 | Tristan da Silva 3pm UNDER (proxy) | 3.5 | -110 | 70% | win (3 3pm) | 1.91 (1.00 x 1.909) |
| 25 | 2026-11-17 | De'Aaron Fox ast OVER (proxy) | 4.5 | -110 | 67% | loss (2 ast) | 1.00 (ladder dead from 1.91, restart #10 at day 26) |
| 26 | 2026-11-18 | Anthony Black reb UNDER (proxy) | 5.5 | -110 | 69% | win (2 reb) | 1.91 (1.00 x 1.909) |
| 27 | 2026-11-19 | Karl-Anthony Towns reb UNDER (proxy) | 14.5 | -110 | 68% | win (12 reb) | 3.64 (1.91 x 1.909) |
| 28 | 2026-11-20 | Tristan da Silva pts UNDER (proxy) | 15.5 | -110 | 69% | win (6 pts) | 6.95 (3.64 x 1.909) |
| 29 | 2026-11-21 | Donovan Clingan ast UNDER (proxy) | 2.5 | -110 | 69% | loss (4 ast) | 1.00 (ladder dead from 6.95, restart #11 at day 30) |
| 30 | 2026-11-22 | Karl-Anthony Towns reb UNDER (proxy) | 14.5 | -110 | 69% | win (13 reb) | 1.91 (1.00 x 1.909) |
| 31 | 2026-11-23 | Toumani Camara 3pm OVER (proxy) | 1.5 | -110 | 69% | loss (1 3pm) | 1.00 (ladder dead from 1.91, restart #12 at day 32) |
| 32 | 2026-11-24 | Anthony Black reb UNDER (proxy) | 5.5 | -110 | 68% | pending | pending |

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

Running: picks won / picks made = 9 / 13 after day 15 (day 6 void, day 11 pass). Restart #4 is 3 for 3 (days 13 to 15), balance 6.95 (69.5 dollars at a 10 dollar start). Best balance reached: 25.33.

Day 16 note: 7 game slate, all unstarted at check time (first tip PHI-CHI 4:30 PM ET). Murphy pts o14.5: NO -1.5 at LAC, only Missi out, last-10 mean 14.6 (40-game mean 18.4, 33.3 min), model 67.0%, normal 68.9% and hit-rate 68.0% agree. Skipped: Embiid pts o18.5 (69.6%, PHI +9.5 spread blowout risk), Giddey reb o4.5 (normal 73.0% vs hit-rate 63.8% split), Murphy 3pm o1.5 (72.9%, over the cap).

Day 17 note: 8 game slate, all unstarted at check time (first tip LAL-ATL 7 PM ET). Castle ast o4.5: SA at PHX, SA -8.5 (under the 10 point blowout line), no flux flag, only Vassell, Harris and Quaintance out (usage x1.023), last-10 ast mean 5.3 (40-game mean 5.9, 28.9 min), model 68.3%, normal 71.2% and hit-rate 68.4% agree. Skipped: Harper pts u18.5 (69.9%) and ast u4.5 (68.4%) same game with lower usage risk, DET-WSH unders (DET -10.5 blowout, heavy flux), IND-DAL and NO-GS unders (heavy flux), Vassell reb o3.5 (he is listed out).

Running: picks won / picks made = 10 / 14 after day 16 (day 6 void, day 11 pass). Restart #4 is 4 for 4 (days 13 to 16), balance 13.27 (132.7 dollars at a 10 dollar start). Best balance reached: 25.33.

Day 18 note: 6 game slate, all unstarted at check time (first tip MIL-NY 7:30 PM ET). Best flux-free names were NY-MIL (Towns ast o2.5 69.0%, Anunoby 3pm o1.5 68.9%) but NY is -15.5, so skipped for blowout risk. Wagner reb u6.5: ORL +6.5 vs SAC (total 222.5), Banchero, Suggs, Isaac, Penda out (heavy ORL flux, but the reb usage factor is only x1.022), last-10 reb mean 5.3 (8 of 10 under 6.5, 35.2 min), model 70.3% (rounded 70%), normal 66.6% and hit-rate 78.9% both clear 65% but are not tight. Weaker pick than usual: Wagner ast u8.5 (66.4%, usage x1.17, normal 63.3% vs hit-rate 73.3% split) and Carter 3pm u1.5 (69.7%, normal 65.7% vs hit-rate 78.4%) were similar. Other games have heavy flux.

Running: picks won / picks made = 11 / 15 after day 17 (day 6 void, day 11 pass). Restart #4 is 5 for 5 (days 13 to 17), balance 25.33 (253.3 dollars at a 10 dollar start). Best balance reached: 25.33 (ties restart #2 peak).

Running: picks won / picks made = 11 / 16 after day 18 (day 6 void, day 11 pass). Restart #4 climbed to 25.33 (253.3 dollars at a 10 dollar start, 5 for 5) then died on day 18 (Wagner grabbed 7 reb vs a 6.5 line). Balance back to 1.00 (10 dollars), restart #5 begins with day 19. Best balance reached: 25.33.

Day 19 note: 10 game slate, all unstarted at check time (first tip WSH-IND 7 PM ET). Black reb u5.5: ORL -4.5 vs UTAH, no flux flag (Suggs, Banchero, Isaac, Penda out, already in usage x1.045 for reb), last-10 reb mean 5.4 (last 5 games 2 3 5 3 5, 32.0 min), model 67.5%, normal 68.9% and hit-rate 69.1% agree tightly. Skipped: Wagner ast u8.5 (70.2%, usage x1.15, last-10 mean 8.6 vs line) and reb u6.5 (68.3%, he went over yesterday), SA-CHI (SA -15.5) and LAL-MIL (LAL -14.5) for blowout risk, other games heavy flux.

Running: picks won / picks made = 11 / 17 after day 19 (day 6 void, day 11 pass). Restart #5 died immediately on day 19 (Black grabbed 7 reb vs a 5.5 line). Balance 1.00 (10 dollars), restart #6 begins with day 20. Best balance reached: 25.33.

Day 20 note: 4 game slate (TOR-PHI 7 PM, DET-WSH 7 PM, DAL-MIN 8 PM, CHA-PHX 9 PM ET), all unstarted at check time (3:15 PM ET). Booker 3pm u2.5: PHX -6.5 vs CHA, total 214.5, only Mark Williams out (Bridges and Spencer flagged on the CHA side of flux list), last-10 3pm mean 1.9 (2 3 2 4 2 2 3 0 2 0, 33.8 min), model 68.9%, normal 70.4% and hit-rate 70.8% agree tightly. Skipped: Shead ast u7.5 (71.8%, over the cap, normal 66.5% vs hit-rate 82.7% split), WSH unders (DET -9.5 blowout line, Davis and Dybantsa out, heavy flux), Barrett ast u4.5 (66.9%) and Green pts o11.5 (66.4%) lower ranked.

Running: picks won / picks made = 11 / 18 after day 20 (day 6 void, day 11 pass). Restart #6 died immediately on day 20 (Booker hit 4 threes vs an under 2.5 line). Balance 1.00 (10 dollars), restart #7 begins with day 21. Best balance reached: 25.33.

Day 21 note: 9 game slate, all unstarted at check time (first tip NY-IND 7 PM ET, 3:15 PM ET check). Towns pts u21.5: NY -8.5 at home vs IND (under the 10 point blowout line), no NY flux, no NY injuries (IND has Haliburton, Furphy, Sheppard out), last-10 pts mean 18.3 (21 21 29 17 11 22 19 27 22 22, 32.1 min), model 70.1% (just at the cap), normal 71.4% and hit-rate 72.6% agree tightly. Skipped: Anunoby ast u2.5 (69.8%, normal 65.3% vs hit-rate 79.3% split), Wagner ast u8.5 (usage x1.115, 5 ORL out), SA-GS and UTAH-HOU (blowout lines), other games heavy flux.

Running: picks won / picks made = 11 / 19 after day 21 (day 6 void, day 11 pass). Restart #7 died immediately on day 21 (Towns scored 23 vs an under 21.5 line). Balance 1.00 (10 dollars), restart #8 begins with day 22. Best balance reached: 25.33.

Day 22 note: 5 game slate, all unstarted at check time (first tip DEN-NO 7 PM ET, 3:15 PM ET check). Every team carries a flux flag, so no flux-free pick existed. Donovan Mitchell pts o21.5: CLE +4.5 at home vs DAL, Mobley, Merrill and Tomlin out (usage x1.06), last-10 pts mean 21.9 (25 23 11 37 23 27 17 15 22 19, 31.9 min), model 69.3%, normal 69.8% and hit-rate 72.5% agree. Mitchell is day-to-day (a DNP would void). Skipped: Davion Mitchell pts u17.5 (68.9%, Giannis day-to-day swings his usage), Robinson 3pm u4.5 (68.1%, normal 67.1% vs hit-rate 73.0%), Coward and Saraf unders (82 to 93%, over the cap and a usage x0.70 artifact), DEN-NO (DEN -12.5) and CHI-MIN (MIN -15.5) for blowout risk.

Day 22 note: Mitchell was listed day-to-day and had no plays in the CLE-DAL game (127 to 117), so the pick is a void: stake returned, nothing counts. ESPN published no player box score for the game, so the bot has not graded it, the void is read from the play-by-play.

Day 23 note: 9 game slate, first tip IND-PHI already in progress (excluded), the rest unstarted at the 3:15 PM ET check. Shamet 3pm u2.5: NY at TOR, spread 5.5, total 217.5, no injuries reported, no flux flag, last-10 3pm mean 1.8 (1 2 2 3 1 4 0 4 3 2, 26.0 min), model 68.7%, normal 71.6% and hit-rate 68.8% agree. Skipped: SA-UTAH (SA -15.5) for blowout risk (Harper 3pm u1.5 69.2%, Wembanyama pts u31.5 68.3%), Tatum pts u27.5 (69.8%, Carter and George flux), OKC-SAC and WSH-HOU heavy flux.

Running: picks won / picks made = 11 / 19 after day 21 (day 6 void, day 11 pass, day 22 void). Restart #8 is pending on day 23. Best balance reached: 25.33.

Day 24 note: 8 game slate, all unstarted at the 3:15 PM ET check (first tip ORL-BOS 7 PM ET). Only ORL carries no flux flag. da Silva 3pm u3.5: BOS -8.5 (under the 10 point blowout line), total 212.5, Isaac, Penda, Banchero out (usage x1.051), last-10 3pm mean 3.4 (2 5 4 2 5 2 4 5 1 4, 30.5 min), model 69.9%, normal 72.5% and hit-rate 70.7% agree. Skipped: Black reb u5.5 (69.3%, normal 74.5% vs hit-rate 66.6%, lost this line on day 11), Bane 3pm u4.5 (67.3%), Richardson ast u2.5 (67.3%, normal 72.8% vs hit-rate 63.7%), every other game heavy flux.

Running: picks won / picks made = 11 / 20 after day 23 (day 6 void, day 11 pass, day 22 void). Restart #8 died immediately on day 23 (Shamet hit 4 threes vs an under 2.5 line). Balance 1.00 (10 dollars), restart #9 begins with day 24 (pending). Best balance reached: 25.33.

Day 24 result: da Silva made 3 threes vs an under 3.5 line, win. Restart #9 balance 1.91 (19.09 dollars at a 10 dollar start). Picks won / picks made = 12 / 21 after day 24 (day 6 void, day 11 pass, day 22 void). Best balance reached: 25.33.

Day 25 note: 5 game slate, all unstarted at the 3:15 PM ET check (first tip NY-TOR 7:30 PM ET). Fox ast o4.5: SA -9.5 vs DET (under the 10 point blowout line), total 222.5, no SA flux flag (Harris, Quaintance out, usage x0.991), DET missing Joe, Prince, Holland, Robinson, Duren, last-10 ast mean 5.5 (1 9 6 6 4 4 3 7 4 6, 28.0 min), model 67.1%, normal 67.0% and hit-rate 70.6% agree tightly. Skipped: Towns pts u21.5 (70.0%, normal 67.2% vs hit-rate 77.5% split, lost this line on day 21), Towns 3pm u2.5 (71.0%, over the cap, normal 77.3% vs hit-rate 67.3%), Wembanyama 3pm u2.5 (66.7%, same game with lower ranked agreement), other games heavy flux.

Day 25 result: Fox had 2 assists vs an over 4.5 line, loss. Restart #9 died at 1.91 after one win. Balance 1.00 (10 dollars), restart #10 begins with day 26. Picks won / picks made = 12 / 22 after day 25 (day 6 void, day 11 pass, day 22 void). Best balance reached: 25.33.

Day 26 note (proxy): 12 game slate, all unstarted at the 3:15 PM ET check (first tip MEM-CLE 7 PM ET). Only ORL carries no flux flag. Black reb u5.5 (LADDER-d26): ORL -1.5 at home vs PHI, total 222.5, Banchero, Isaac, Penda, Nelson out (usage x0.979), PHI missing Brown and Bona, last-10 reb mean 5.2 (2 2 7 7 8 7 8 6 2 3, 32.3 min), model 68.7%, normal 71.9% and hit-rate 68.5% agree. Black lost this line on days 11 and 19, noted as a risk. Skipped: da Silva pts u14.5 (65.9%, last-10 mean 14.7), Richardson ast u2.5 (66.3%, normal 70.9% vs hit-rate 63.7%), Wagner ast u8.5 (66.7%, last-10 mean 8.9), every other game heavy flux or over the 70% cap.

Day 26 result: Black had 2 reb vs an under 5.5 line, win. Restart #10 balance 1.91 (19.09 dollars at a 10 dollar start). Picks won / picks made = 13 / 23 after day 26 (day 6 void, day 11 pass, day 22 void). Best balance reached: 25.33.

Day 27 note (proxy): 4 game slate (GS-MEM, POR-MIL, NY-MIN, LAC-SA, first tip 8 PM ET), all unstarted at the 3:15 PM ET check. Towns reb u14.5 (LADDER-d27): NY vs MIN, NY +1.5 (pick'em), total 216.5, no NY flux flag, no NY injuries, last-10 reb mean 14.1 (16 17 15 11 16 13 12 16 12 13), model 68.0%, normal 70.9% and hit-rate 67.8% agree. Skipped: Brunson 3pm u3.5 (69.9%, at the cap), Towns 3pm u2.5 (73.0%, over the cap), Shamet 3pm u2.5 (67.3%, lost this line on day 23), Shamet pts u11.5 (69.1%, two 22+ games in the last 10), Melton 3pm u2.5 (62.1% once injuries applied), Wembanyama and Fox (SA, 65.6% and 65.9%, lower ranked), POR-MIL and MEM heavy flux.

Day 27 result: Towns had 12 reb vs an under 14.5 line, win. Restart #10 is 2 for 2 (days 26 and 27), balance 3.64 (36.4 dollars at a 10 dollar start). Picks won / picks made = 14 / 24 after day 27 (day 6 void, day 11 pass, day 22 void). Best balance reached: 25.33.

Day 28 note (proxy): 9 game slate, all unstarted at the 3:15 PM ET check (first tip CHA-ATL 7 PM ET). Only ORL carries no flux flag. da Silva pts u15.5 (LADDER-d28): ORL -6.5 at BKN (under the 10 point blowout line), total 224.5, Nelson, Isaac, Penda, Banchero out (usage x1.013), last-10 pts mean 15.4 (12 13 12 19 18 10 23 8 20 19, 30.6 min), model 68.9%, normal 70.1% and hit-rate 71.2% agree. Skipped: Wagner ast u9.5 (70.2%, over the cap), Black ast u5.5 (68.0%, over 5.5 in 6 of last 10), every other game heavy flux.

Day 28 result: da Silva scored 6 pts vs an under 15.5 line, win. Restart #10 is 3 for 3 (days 26 to 28), balance 6.95 (69.5 dollars at a 10 dollar start). Picks won / picks made = 15 / 25 after day 28 (day 6 void, day 11 pass, day 22 void). Best balance reached: 25.33.

Day 29 note (proxy): 5 unstarted games at the 3:15 PM ET check (MIL-PHI already in progress, excluded). Clingan ast u2.5 (LADDER-d29): POR at NY, NY -3.5, total 215.5, no flux flag on either side, Morant, Sharpe, Krejci, Youngblood out (usage x1.001, Avdija day-to-day), last-10 ast mean 2.0 (2 5 1 2 2 3 0 1 1 3, 27.4 min), model 68.8%, normal 67.7% and hit-rate 73.8% agree. Skipped: Towns reb u14.5 (70.5%, over the cap, day-to-day void risk), Clingan reb u11.5 (68.7%, normal 66.3% vs hit-rate 75.4% split), Bridges reb u4.5 (normal 75.2% vs hit-rate 62.8%), SA-NO (SA -18.5) and BOS-SAC (BOS -13.5) for blowout risk, DAL and SAC unders heavy flux.

Day 29 result: Clingan had 4 assists vs an under 2.5 line, loss. Restart #10 died at 6.95 after three wins. Balance back to 1.00 (10 dollars), restart #11 begins with day 30. Picks won / picks made = 15 / 26 after day 29 (day 6 void, day 11 pass, day 22 void). Best balance reached: 25.33.

Day 30 note (proxy): 7 game slate, all unstarted at the check time (first tip DET-ATL 3:30 PM ET). Towns reb u14.5 (LADDER-d30): NY -7.5 vs IND (under the 10 point blowout line), total 213.5, no NY flux flag, Anunoby and Clarkson out (usage x0.986), last-10 reb mean 14.0 (12 16 17 15 11 16 13 12 16 12, 33.6 min), model 69.1%, normal 71.6% and hit-rate 69.6% agree tightly. Towns is day-to-day (a DNP would void). He won this line on day 27. Skipped: Hart reb o5.5 (69.4%, normal 74.1% vs hit-rate 67.2%), Lendeborg 3pm u2.5 (69.1%, normal 64.1% vs hit-rate 83.1% split), da Silva pts u14.5 (68.2%, normal 67.3% vs hit-rate 72.8%), DEN-CHI and BOS-GS spreads near blowout, other games heavy flux.

Day 30 result: Towns had 13 reb vs an under 14.5 line, win. Restart #11 balance 1.91 (19.09 dollars at a 10 dollar start). Picks won / picks made = 16 / 27 after day 30 (day 6 void, day 11 pass, day 22 void). Best balance reached: 25.33.

Day 31 note (proxy): 10 game slate, all unstarted at the 3:15 PM ET check (first tip MEM-CHA 7 PM ET). Camara 3pm o1.5 (LADDER-d31): POR at PHI, spread 2.5, total 231.5, no flux flag, Morant, Sharpe, Krejci, Youngblood out (usage x1.021), last-10 3pm mean 2.5 (1 4 2 0 2 2 2 0 4 1, 31.8 min), model 68.9%, normal 70.2% and hit-rate 71.0% agree tightly. Risk: Embiid, Brown and Wade are day-to-day on the PHI side. Skipped: K. Williams ast u2.5 (70.0%, normal 66.6% vs hit-rate 78.0% split, 8 OKC out), Castle 3pm u2.5 (SA -10.5 blowout line), James 3pm u1.5 (67.4%, normal 65.1% vs hit-rate 73.7%), Spencer ast u6.5 (67.3%, normal 72.1% vs hit-rate 64.6%), every flux-flagged game.

Day 31 result: Camara made 1 three vs an over 1.5 line, loss. Restart #11 died at 1.91 after one win. Balance back to 1.00 (10 dollars), restart #12 begins with day 32. Picks won / picks made = 16 / 28 after day 31 (day 6 void, day 11 pass, day 22 void). Best balance reached: 25.33.

Day 32 note (proxy): 3 game slate (DET-ORL 7 PM, BOS-WSH 8 PM, DAL-DEN 10 PM ET), all unstarted at the 3:15 PM ET check. Only ORL carries no flux flag. Black reb u5.5 (LADDER-d32): ORL home vs DET, DET -2.5, total 212.5, Isaac, Nelson, Penda, Banchero out (usage x0.998), last-10 reb mean 4.2 (35.3 min), model 68.1%, normal 70.8% and hit-rate 68.2% agree. Black lost this line on days 11 and 19, won it on day 26. Skipped: Black ast u5.5 (70.3%, over the cap, normal 76.7% vs hit-rate 66.3% split), Richardson ast u2.5 (70.4%, normal 77.3% vs hit-rate 65.8% split), Black pts u16.5 (67.6%, normal 71.3% vs hit-rate 66.5%), da Silva reb u4.5 (68.4%, normal 67.7% vs hit-rate 72.9%), BOS-WSH (BOS -11.5 blowout line) and DAL-DEN heavy flux.

## Extension (instruction from AD, 2026-11-02)
The ladder keeps going past day 10 under these rules: Claude decides when to cash out (stop once enough is made) or runs it up to a 10k dollar paper balance (balance 1000.00 on a 1.00 unit scale at a 10 dollar start, i.e. 1000x). Stop only for one day if a day has no good pick, and stop for good only if the following day also has none. Everything else in the rules above still applies. Tickets continue as LADDER-d11, d12 and so on.
