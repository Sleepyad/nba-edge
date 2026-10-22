# NBA Edge

> New session or new chat? Read [NOTES.md](NOTES.md) first. It has the current state, the model settings, test results and open items.

Claude's own paper-bet log lives in `paper.py` (imaginary money, public record).

Every NBA player's game log in one database, a prop pricer, a bet log that keeps a record of every miss,
and a live dashboard. Stats refresh on their own through GitHub Actions.

```
nba_edge.py            the whole engine: sync, pricing, bet log, report, calibration (standard library only)
data/                  game_log.csv (every player, every final game since last season), games.csv (final scores and
                       closing spread and total), lines.csv (pregame line snapshots, saved only when a line moves)
docs/                  the dashboard (GitHub Pages) and its JSON data
.github/workflows/     sync.yml pulls new games and deploys; tests.yml checks JS and Python agree
tests/                 proves the dashboard's model and the CLI's model give the same numbers
```

## Dashboard

Open the Pages site. It has three parts:

- **Today's games**: live scores from ESPN, refreshed every 15 seconds while a game is on.
- **Price a prop**: pick a player, stat, line and odds. Tonight's spread and total fill in by themselves, and the injury
  report shows tick boxes for his teammates (Out is ticked, Day-To-Day is not). You get the model's chance, the book's
  implied chance, edge, expected value, quarter-Kelly size, and the last 15 games drawn against your line.
- **Slip tracker**: add legs and watch them update during the games (`needs 3 more`, `HIT (locked)`, `BUSTED`,
  `WON`, `LOST`). The slip is stored in your browser only. Press *Copy log command* to get the CLI line that
  logs it to your private database.

## Command line

Needs Python 3.9 or newer. On Windows use `py` instead of `python`.

```
python nba_edge.py sync                    # first run backfills last season (about 2 minutes)
python nba_edge.py price "Nikola Jokic" ast 9.5 --odds -145 --opp OKC
python nba_edge.py price "Nikola Jokic" ast 9.5 --odds -145 --auto       # pulls tonight's opponent, spread, total and injuries from ESPN
python nba_edge.py price "Shai Gilgeous-Alexander" pts 29.5 --min 32      # plan for blowout minutes
python nba_edge.py price "Jared McCain" pts 10.5 --out "Embiid" --spread -8 --total 236
python nba_edge.py slip "Nikola Jokic:ast:over:9.5:-145" "Jared McCain:pts:over:10.5:-104" --odds +260
python nba_edge.py bet add --book bet365 --stake 10 --odds +450 --note "Thu SGP" \
      --leg "Nikola Jokic:ast:over:9.5:-145:2026-10-22" --leg "Jared McCain:pts:over:10.5:-104:2026-10-22"
python nba_edge.py sync && python nba_edge.py settle    # next morning: fills actuals, minutes, margin
python nba_edge.py report                               # record by stat, side, price, blowout, plus an autopsy of every miss
python nba_edge.py calibrate                            # out-of-sample test of the whole model
python nba_edge.py tune                                 # grid search of the memory settings
```

Your bets live in `~/nba_edge.db` on your computer. They are never committed to the repo.
Leg format is `name:stat:side:line[:odds[:date]]` (dates are US Eastern). "10+ assists" means over 9.5.
Stats: `pts reb ast 3pm stl blk tov min fga pra pr pa ra`. Moneyline or spread legs can be logged with any
other stat word and resolved by hand: `bet resolve LEG_ID win|loss|push|void`.

## How the model works

1. Take a player's last 40 games (minutes 5 or more), newest first, and weight them so a game counts half as much every 12 games back.
2. Blend the weighted hit rate against the line with a bell curve fitted to the same games (the curve counts as 20 games, so it carries most of the weight).
3. Scale for the opponent (how much that team's opponents beat their own averages, pulled hard toward 1.0).
4. **Teammates out:** from past games, measure how a player's points, rebounds, assists and threes change when each rotation teammate sits. Half of that measured effect is applied, and the part of his recent average that came from earlier absences is removed first, so a long injury is not counted twice.
5. **Spread and total (optional):** a big spread trims starters' minutes a little, a high total lifts counting stats a little. Both are learned from the closing lines of past games.
6. Pull the answer 8% toward 50%, because real stats have fatter tails than a bell curve.

`calibrate` fits steps 4 and 5 on games before a cutoff date, then prices 100,000 lines on games after it, using only information that existed before each game. It reports Brier and log loss for the model with and without each piece. On the 2025-26 season (cutoff Jan 31):

| model | log loss |
| --- | --- |
| own history only | 0.5970 |
| + spread and game total | 0.5968 |
| + teammates out | 0.5953 |

For reference, the first version of the settings (half-life 8, curve weight 4) scored about 0.603, so retuning with `tune` gave the biggest gain. Spread and total barely move the needle, which is why they are optional inputs. Teammate injuries help a little, mostly in games where someone important sits.

This tests the engine against what happened, not against a sportsbook, because player prop lines are not in any free data. The only way to learn whether you beat the book is to log real lines with `bet add` and read `report` (it prints model vs book once there are 10 legs with odds, and what your misses have in common once there are 30 settled legs).

## Setting up the repo

1. Make the repo **public**. It holds only public box scores and code, and GitHub Pages on a private repo needs a paid plan.
2. *Settings > Pages > Source*: **GitHub Actions**.
3. *Settings > Actions > General > Workflow permissions*: **Read and write permissions**.
4. *Actions > sync-and-deploy > Run workflow* once. After that it runs every 30 minutes in the evening and night
   (UTC 17:00 to 06:59), and only commits when there is a new final game.

## Things to know

- The data source is ESPN's unofficial public JSON feed. It is free and works from cloud servers, but ESPN can change it
  without notice. (stats.nba.com blocks cloud servers, which is why it is not used.)
- ESPN published no box score for 4 playoff games from spring 2026. They are skipped and reported on each backfill.
- GitHub's scheduler can run a few minutes late. Live scores in the dashboard come straight from ESPN in your browser,
  so they do not wait for the Action.
- Same-game legs are correlated. The slip's joint chance multiplies legs as if independent, so treat it as a rough guide.
