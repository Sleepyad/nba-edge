# NBA Edge

Every NBA player's game log in one database, a prop pricer, a bet log that keeps a record of every miss,
and a live dashboard. Stats refresh on their own through GitHub Actions.

```
nba_edge.py            the whole engine: sync, pricing, bet log, report, calibration (standard library only)
data/game_log.csv      every player, every final game since last season (grows by itself)
docs/                  the dashboard (GitHub Pages) and its JSON data
.github/workflows/     sync.yml pulls new games and deploys; tests.yml checks JS and Python agree
tests/                 proves the dashboard's model and the CLI's model give the same numbers
```

## Dashboard

Open the Pages site. It has three parts:

- **Today's games**: live scores from ESPN, refreshed every 15 seconds while a game is on.
- **Price a prop**: pick a player, stat, line and odds. You get the model's chance, the book's implied chance, edge,
  expected value, quarter-Kelly size, and the last 15 games drawn against your line.
- **Slip tracker**: add legs and watch them update during the games (`needs 3 more`, `HIT (locked)`, `BUSTED`,
  `WON`, `LOST`). The slip is stored in your browser only. Press *Copy log command* to get the CLI line that
  logs it to your private database.

## Command line

Needs Python 3.9 or newer. On Windows use `py` instead of `python`.

```
python nba_edge.py sync                    # first run backfills last season (about 2 minutes)
python nba_edge.py price "Nikola Jokic" ast 9.5 --odds -145 --opp OKC
python nba_edge.py price "Shai Gilgeous-Alexander" pts 29.5 --min 32      # plan for blowout minutes
python nba_edge.py slip "Nikola Jokic:ast:over:9.5:-145" "Jared McCain:pts:over:10.5:-104" --odds +260
python nba_edge.py bet add --book bet365 --stake 10 --odds +450 --note "Thu SGP" \
      --leg "Nikola Jokic:ast:over:9.5:-145:2026-10-22" --leg "Jared McCain:pts:over:10.5:-104:2026-10-22"
python nba_edge.py sync && python nba_edge.py settle    # next morning: fills actuals, minutes, margin
python nba_edge.py report                               # record by stat, side, price, blowout, plus an autopsy of every miss
python nba_edge.py calibrate                            # is the probability engine honest?
```

Your bets live in `~/nba_edge.db` on your computer. They are never committed to the repo.
Leg format is `name:stat:side:line[:odds[:date]]` (dates are US Eastern). "10+ assists" means over 9.5.
Stats: `pts reb ast 3pm stl blk tov min fga pra pr pa ra`. Moneyline or spread legs can be logged with any
other stat word and resolved by hand: `bet resolve LEG_ID win|loss|push|void`.

## How the model works

1. Take a player's last 40 games (minutes 5 or more), newest first.
2. Weight them so a game counts half as much every 8 games back.
3. Blend the weighted hit rate against the line with a bell curve fitted to the same games (the curve counts as 4 games).
4. Scale for the opponent (how much that team's opponents beat their own averages, pulled hard toward 1.0) and
   for expected minutes if you give them.
5. Pull the answer 8% toward 50%, because real stats have fatter tails than a bell curve.

`calibrate` replays history one game at a time using only earlier games and checks that "60%" really happens about
60% of the time. It tests the engine against a player's own history. It does not prove an edge over a sportsbook,
because the books' lines are not in the data. The only way to learn that is to log real lines with `bet add` and read
`report` once each group has 30 or more legs.

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
