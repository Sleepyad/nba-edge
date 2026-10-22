# NBA Edge: project notes for a new session (updated Oct 22, 2026, evening)

Read this first. Owner: AD (Sleepyad). Personal project, free, not a business. Friends may get shown how to build their own later.
Working style: casual, concise, direct, no em dashes, match his language (English or French), no heavy caveats, never repeat an instruction he already gave, check what he actually sees before giving click-by-click steps. The repo and Pages site are public; bets must never be committed.

## Links
- Repo: https://github.com/Sleepyad/nba-edge (public, branch main)
- Live dashboard: https://sleepyad.github.io/nba-edge/ (GitHub Pages, source = GitHub Actions)
- Claude Project: Gamble 101 (holds a copy of these notes as claude/nba-edge-handoff.md)

## What is built
- `nba_edge.py`: one file, standard library only, Python 3.9+. SQLite at ~/nba_edge.db on AD's PC (his bets live only there).
  - `sync` (ESPN public JSON, every player's box score for every final game, plus final score and closing spread/total per game; first run backfills last season; saves pregame line snapshots only when a line moves), `status`, `player`
  - `price NAME STAT LINE [--odds --opp --min --spread --total --out NAME --auto]`; `--auto` pulls tonight's opponent, spread, total and injuries from ESPN
  - `slip`, `bet add|list|cashout|resolve|tag`, `settle`, `report` (record by stat/side/price/blowout, autopsy of each miss, model vs book once 10 legs have odds, "what the misses say" once 30 settled legs)
  - `calibrate` (fit before a split date, test after, Brier and log loss per model variant), `tune` (grid of halflife, prior, shrink), `load DIR`, `dump DIR`, `export DIR`, `demo` (fake league for testing)
- `docs/index.html`: dashboard. Live scores (15 s while games run), prop pricer (auto-fills tonight's spread/total, ESPN injury report with tick boxes for teammates), slip tracker that updates legs live (needs N more, HIT, BUSTED, WON, LOST), "Copy log command" button that prints the `bet add` line. Slip is stored in the browser only.
- `data/`: `game_log.csv` (every player, every final game since 2025-26), `games.csv` (scores, closing and opening spread/total, 1074 of 1330 games have lines), `lines.csv` (pregame snapshots). `docs/data/*.json`: dashboard exports (players, opp, ctx, boost, meta).
- GitHub Actions: `sync-and-deploy` (cron every 30 min, UTC 17:00 to 06:59; loads data, syncs, dumps, exports, commits only if something changed, then deploys Pages; also runs on push to main and manually with an optional backfill date) and `tests` (JS and Python probabilities must match within 0.002).

## The model (constants at the top of nba_edge.py, mirrored in docs/data/meta.json)
HALFLIFE 12 games, PRIOR 20 (bell curve counts as 20 games vs the raw hit rate), SHRINK 0.92 toward 50%, OPP_SHRINK 150, USAGE_STRENGTH 0.5, BOOST_SHRINK 20.
1. Last 40 games with minutes >= 5, recency weighted. 2. Blend weighted hit rate with a bell curve. 3. Opponent factor. 4. Teammate-out usage: with/without ratios (pts, reb, ast, 3pm) per rotation teammate, half strength, and the share of his recent games that teammate missed is divided out so long injuries are not double counted (games for a previous team are ignored). 5. Optional spread (starter/bench minutes by |spread| bucket) and total (pace slope). 6. Shrink.
Out-of-sample result (fit before 2026-01-31, 100,000 predictions after): log loss 0.5970 own history only, 0.5968 plus spread/total, 0.5953 plus teammates out. First version scored about 0.603, so retuning gave the biggest gain. Spread and total barely help, so they stay optional. This tests against outcomes, NOT against a sportsbook: no free player prop lines exist.
Python (`predict`) and JavaScript (`predict` in docs/index.html) must stay identical. Change one, change the other, run `python -m unittest discover tests`.

## Facts and limits
- Data source is ESPN's unofficial feed (stats.nba.com blocks cloud servers). It can change without notice. 4 spring 2026 playoff games have no box score and are skipped.
- The sandbox cannot create GitHub repos; the repo was made by AD. A session needs `add_repo` (push access) to commit.
- GitHub's scheduler can run late. Live scores in the browser come straight from ESPN and do not wait for the Action.
- Same-game legs are correlated; the slip's joint chance assumes independence.
- Untested so far: the Action committing newly finished games on its own (first real test is the night of Oct 22), and anything against real prop lines.

## Open items and ideas
1. Check tonight (Oct 22) that a "data: sync" commit appeared after Cavs-76ers and Nuggets-Thunder finished; if not, read the failed run in the Actions tab.
2. AD runs `python nba_edge.py sync` once on his home PC to build his private bet database, then logs bets with `bet add` (or the dashboard's copy button), `settle` after games, `report`.
3. Log real book lines with every bet so a model-vs-book comparison becomes possible; read grouped results only with 30+ legs.
4. Not built: a short notes/index file for cheaper future sessions (this file is the start of it) and smaller data files. AD said efficiency work is fine but the site comes first.
5. Possible next modeling ideas: pace by team, rest/back-to-back, starter confirmation near tip, closing-line value tracking from lines.csv.

## Betting history (for context, not for the repo's data)
- Oct 20: $10 five-leg Thunder-Spurs parlay lost (Wemby rebounds under; single-narrative stacking, a Holmgren minutes guess, small-sample SGA assists).
- Oct 21: $10 parlay cashed out for $85.40, then a second ticket with Garland and Hachimura overs died in a Clippers blowout; he cashed out near $80 for about +$75 total. Lesson: be careful with favorite starters' overs in games that can become blowouts.
- Oct 22 advice: 76ers ML plus Maxey O22.5 pts; Jokic 10+ assists plus McCain O10.5 pts; SGA O29.5 optional. After the upgrade the model priced Jokic 10+ ast at -145 about fair (56.9% vs 59.2% implied) and SGA O29.5 at -115 below fair. Results not yet logged.
- Platforms: bet365 (main), Underdog Fantasy. A $10-to-$10k ladder only if two picks are really solid. Likes prices around -110 to -220, maybe one +100, with reasons and sources, and clean put-in / take-off checklists.
