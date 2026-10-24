#!/usr/bin/env python3
"""
nba_edge.py : your own NBA player database, prop pricer and bet log.

No dependencies (standard library only). Data comes from ESPN's public JSON feed, which works
from home, from servers and from GitHub Actions. Everything lives in one SQLite file
(default ~/nba_edge.db).

  python nba_edge.py sync                       # every player, every final game (first run backfills last season)
  python nba_edge.py sync --since 2025-10-01    # force a backfill from a date
  python nba_edge.py status
  python nba_edge.py player "Jokic" -n 10
  python nba_edge.py price "Nikola Jokic" ast 9.5 --odds -145 --opp OKC
  python nba_edge.py price "Shai Gilgeous-Alexander" pts 29.5 --min 32   # expect blowout minutes
  python nba_edge.py slip "Nikola Jokic:ast:over:9.5:-145" "Jared McCain:pts:over:10.5:-104"
  python nba_edge.py bet add --book bet365 --stake 10 --odds +450 --note "Thu SGP" \\
        --leg "Nikola Jokic:ast:over:9.5:-145:2026-10-22" \\
        --leg "Jared McCain:pts:over:10.5:-104:2026-10-22"
  python nba_edge.py sync                       # next morning
  python nba_edge.py settle                     # fills actuals, minutes, blowout flag
  python nba_edge.py report                     # record + autopsy of every miss
  python nba_edge.py calibrate                  # is the probability engine honest?

Repo plumbing (used by the GitHub Action):
  python nba_edge.py load data/game_log.csv     # CSV -> sqlite
  python nba_edge.py dump data/game_log.csv     # sqlite -> CSV (stable order, tiny diffs)
  python nba_edge.py export docs/data           # JSON for the dashboard

Dates are US Eastern game dates. Leg format  name:stat:side:line[:odds[:date]]  ("10+ assists" is over 9.5)
Stats: pts reb ast 3pm stl blk tov min fga pra pr pa ra
Non-player legs (ML, spread...) use any other stat word, e.g. "76ers:ml:win:0:-135:2026-10-22",
and get resolved by hand:  python nba_edge.py bet resolve LEG_ID win|loss|push|void
"""
import argparse
import concurrent.futures as cf
import bisect
import csv
import json
import math
import os
import random
import sqlite3
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone

DEFAULT_DB = os.path.expanduser("~/nba_edge.db")

STAT_COLS = {
    "pts": ["pts"], "reb": ["reb"], "ast": ["ast"], "3pm": ["fg3m"], "stl": ["stl"],
    "blk": ["blk"], "tov": ["tov"], "min": ["mins"], "fga": ["fga"],
    "pra": ["pts", "reb", "ast"], "pr": ["pts", "reb"], "pa": ["pts", "ast"], "ra": ["reb", "ast"],
}
ALIASES = {
    "points": "pts", "point": "pts", "rebounds": "reb", "rebs": "reb", "assists": "ast",
    "asts": "ast", "threes": "3pm", "3s": "3pm", "fg3m": "3pm", "steals": "stl",
    "blocks": "blk", "turnovers": "tov", "minutes": "min", "p+r+a": "pra",
}
BLOWOUT = 15  # |team margin| at or above this counts as a blowout
SHRINK = 0.92  # pull probabilities toward 50% (real stats are fatter-tailed than a bell curve)
HALFLIFE = 12.0  # games; recent games count double every 12 games back (tested out of sample)
PRIOR = 20.0  # pseudo-games of bell-curve belief blended with the raw hit rate (tested out of sample)
OPP_SHRINK = 150.0  # opponent adjustment is pulled hard toward 1.0
# Early-season discount on overs (lab experiment 3 in LAB.md). OFF until AD approves it: the first days of a season
# run cold (overs hit about 5 points less than priced in Oct 2024 and Oct 2025). Steps are (days since the season's
# first game, change to P(over)); P(under) moves the other way. EARLY_START overrides the auto-detected first game date.
EARLY_ON = False
EARLY_STEPS = [(7, -0.05), (21, -0.01)]
EARLY_START = None
USAGE_STRENGTH = 0.5  # share of the measured with/without effect that is applied (0.5 tested best out of sample)
BOOST_SHRINK = 20.0  # games-out pseudo-count: teammate splits are noisy, so pull them toward 1.0
ESPN = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
GAME_FIELDS = ["game_id", "game_date", "season", "season_type", "home", "away", "home_score", "away_score",
               "spread", "total", "open_spread", "open_total"]
LINE_FIELDS = ["game_id", "game_date", "home", "away", "captured", "spread", "total"]
SPREAD_EDGES = [3, 6, 9, 12, 15]  # |spread| buckets for the minutes effect
CTX_STATS = ["pts", "reb", "ast", "3pm", "stl", "blk", "tov", "pra", "pr", "pa", "ra"]
BOOST_STATS = ["pts", "reb", "ast", "3pm"]
COMBO = {"pra": ["pts", "reb", "ast"], "pr": ["pts", "reb"], "pa": ["pts", "ast"], "ra": ["reb", "ast"]}
GAME_COLS = ["player_id", "player", "pnorm", "team", "game_id", "game_date", "season", "season_type",
             "matchup", "home", "opp", "wl", "mins", "pts", "reb", "ast", "fg3m", "fg3a", "fgm", "fga",
             "ftm", "fta", "stl", "blk", "tov", "pf", "plus_minus", "starter"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS game_log(
  player_id INTEGER, player TEXT, pnorm TEXT, team TEXT, game_id TEXT, game_date TEXT,
  season TEXT, season_type TEXT, matchup TEXT, home INTEGER, opp TEXT, wl TEXT, mins REAL,
  pts REAL, reb REAL, ast REAL, fg3m REAL, fg3a REAL, fgm REAL, fga REAL, ftm REAL, fta REAL,
  stl REAL, blk REAL, tov REAL, pf REAL, plus_minus REAL, starter INTEGER,
  PRIMARY KEY (player_id, game_id));
CREATE INDEX IF NOT EXISTS ix_gl_player ON game_log(player_id, game_date);
CREATE INDEX IF NOT EXISTS ix_gl_pnorm ON game_log(pnorm);
CREATE INDEX IF NOT EXISTS ix_gl_game ON game_log(game_id);
CREATE TABLE IF NOT EXISTS games(
  game_id TEXT PRIMARY KEY, game_date TEXT, season TEXT, season_type TEXT, home TEXT, away TEXT,
  home_score REAL, away_score REAL, spread REAL, total REAL, open_spread REAL, open_total REAL);
CREATE TABLE IF NOT EXISTS lines(
  game_id TEXT, game_date TEXT, home TEXT, away TEXT, captured TEXT, spread REAL, total REAL,
  PRIMARY KEY (game_id, captured));
CREATE TABLE IF NOT EXISTS bets(
  id INTEGER PRIMARY KEY AUTOINCREMENT, placed_at TEXT, book TEXT, stake REAL, odds INTEGER,
  note TEXT, status TEXT DEFAULT 'pending', payout REAL DEFAULT 0, model_prob REAL);
CREATE TABLE IF NOT EXISTS legs(
  id INTEGER PRIMARY KEY AUTOINCREMENT, bet_id INTEGER, player TEXT, player_id INTEGER,
  stat TEXT, side TEXT, line REAL, odds INTEGER, game_date TEXT, label TEXT,
  model_prob REAL, mean_at_bet REAL, avg_min_at_bet REAL,
  result TEXT DEFAULT 'pending', actual REAL, minutes REAL, margin REAL, tags TEXT DEFAULT '');
"""


# ----------------------------------------------------------------------------- helpers
def die(msg):
    print("error: " + msg, file=sys.stderr)
    sys.exit(1)


def conn(path):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().replace(".", "").replace("'", "").replace("\u2019", "").replace("-", " ").strip()


def stat_key(s):
    s = s.lower().strip()
    return ALIASES.get(s, s)


def stat_expr(stat):
    return "(" + "+".join(STAT_COLS[stat]) + ")"


def row_value(r, stat):
    return sum(r[c] or 0 for c in STAT_COLS[stat])


def parse_odds(s):
    return int(float(str(s).strip().replace("+", "")))


def dec(odds):
    return 1 + odds / 100.0 if odds > 0 else 1 + 100.0 / abs(odds)


def to_american(d):
    return round((d - 1) * 100) if d >= 2 else round(-100 / (d - 1))


def fmt_odds(o):
    return ("+%d" % o) if o > 0 else str(o)


def current_season(today=None):
    today = today or date.today()
    y = today.year if today.month >= 10 else today.year - 1
    return "%d-%02d" % (y, (y + 1) % 100)


def prev_season(s):
    y = int(s[:4]) - 1
    return "%d-%02d" % (y, (y + 1) % 100)


def find_player(con, q):
    n = norm(q)
    rows = con.execute(
        "SELECT player_id, player, MAX(game_date) AS last, COUNT(*) AS g FROM game_log "
        "WHERE pnorm LIKE ? GROUP BY player_id ORDER BY last DESC", ("%" + n + "%",)).fetchall()
    if not rows:
        die("no player matching '%s'. Run `sync` first, or check the spelling." % q)
    exact = [r for r in rows if norm(r["player"]) == n]
    if len(exact) == 1:
        return exact[0]
    if len(rows) == 1:
        return rows[0]
    die("'%s' is ambiguous: %s" % (q, ", ".join(r["player"] for r in rows[:8])))


# ----------------------------------------------------------------------------- model
def phi(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def price_dist(xs, line, side, halflife=HALFLIFE, scale=1.0, prior=PRIOR, shrink=None):
    """xs newest first. Blend of recency-weighted normal and recency-weighted hit rate."""
    xs = [x * scale for x in xs]
    w = [0.5 ** (i / halflife) for i in range(len(xs))]
    sw = sum(w)
    mu = sum(a * b for a, b in zip(w, xs)) / sw
    var = sum(a * (b - mu) ** 2 for a, b in zip(w, xs)) / sw
    neff = sw * sw / sum(a * a for a in w)
    var *= neff / max(neff - 1.0, 1.0)
    sd = max(math.sqrt(var * (1 + 1.0 / neff)), 0.5)
    if float(line).is_integer():
        hi, lo = int(line) + 1, int(line) - 1
    else:
        hi, lo = math.floor(line) + 1, math.floor(line)
    n_over = 1 - phi((hi - 0.5 - mu) / sd)
    n_under = phi((lo + 0.5 - mu) / sd)
    n_push = max(0.0, 1 - n_over - n_under)
    e_over = sum(a for a, x in zip(w, xs) if x > line + 1e-9) / sw
    e_under = sum(a for a, x in zip(w, xs) if x < line - 1e-9) / sw
    e_push = max(0.0, 1 - e_over - e_under)
    p_over = (e_over * sw + prior * n_over) / (sw + prior)
    p_under = (e_under * sw + prior * n_under) / (sw + prior)
    p_push = (e_push * sw + prior * n_push) / (sw + prior)
    tot = p_over + p_under + p_push
    p_over, p_under, p_push = p_over / tot, p_under / tot, p_push / tot
    over = side == "over"
    p_win = p_over if over else p_under
    p_win = 0.5 + (SHRINK if shrink is None else shrink) * (p_win - 0.5)
    p_win = min(max(p_win, 0.02), 0.98)
    return dict(p_win=p_win, p_push=p_push, p_norm=n_over if over else n_under,
                p_emp=e_over if over else e_under, mu=mu, sd=sd, neff=neff)


def history(con, pid, stat, before=None, limit=40):
    q = ("SELECT %s AS v, mins, home, opp, game_date, starter, pts, reb, ast, fg3m, team FROM game_log "
         "WHERE player_id=? AND mins>=5" % stat_expr(stat))
    args = [pid]
    if before:
        q += " AND game_date<?"
        args.append(before)
    q += " ORDER BY game_date DESC, game_id DESC LIMIT ?"
    args.append(limit)
    return con.execute(q, args).fetchall()


def opp_seasons(con):
    """Regular seasons used for opponent adjustment: the latest, plus the one before while it is still early."""
    rows = con.execute("SELECT season, COUNT(DISTINCT game_id) g FROM game_log WHERE season_type='Regular Season' "
                       "GROUP BY season ORDER BY season DESC LIMIT 2").fetchall()
    if not rows:
        return []
    out = [rows[0]["season"]]
    if rows[0]["g"] < 100 and len(rows) > 1:
        out.append(rows[1]["season"])
    return out


def opp_factors(con, stat):
    """{team: (factor, n)} : how much each team's opponents beat their own averages, shrunk toward 1.0."""
    seasons = opp_seasons(con)
    if not seasons:
        return {}
    marks = ",".join("?" * len(seasons))
    expr = stat_expr(stat)
    where = "season_type='Regular Season' AND season IN (%s) AND mins>=15" % marks
    base = {r[0]: r[1] for r in con.execute(
        "SELECT player_id, AVG(%s) FROM game_log WHERE %s GROUP BY player_id" % (expr, where), seasons)}
    num, den, cnt = {}, {}, {}
    for r in con.execute("SELECT player_id, opp, %s AS v FROM game_log WHERE %s" % (expr, where), seasons):
        if r["player_id"] not in base:
            continue
        num[r["opp"]] = num.get(r["opp"], 0.0) + r["v"]
        den[r["opp"]] = den.get(r["opp"], 0.0) + base[r["player_id"]]
        cnt[r["opp"]] = cnt.get(r["opp"], 0) + 1
    out = {}
    for t in num:
        if den[t] > 0:
            out[t] = (1 + (num[t] / den[t] - 1) * cnt[t] / (cnt[t] + OPP_SHRINK), cnt[t])
    return out


def opp_factor(con, opp, stat):
    return opp_factors(con, stat).get(opp, (1.0, 0))


def spread_bucket(spread):
    a = abs(spread)
    return sum(1 for e in SPREAD_EDGES if a >= e)


def compute_ctx(con, before=None):
    """Learn from history how minutes depend on the point spread and how stats depend on the game total."""
    q = ("SELECT g.player_id pid, g.season, g.mins, g.starter, g.pts, g.reb, g.ast, g.fg3m, g.stl, g.blk, g.tov, "
         "m.spread, m.total, g.game_id FROM game_log g JOIN games m ON m.game_id = g.game_id "
         "WHERE g.season_type='Regular Season' AND g.mins>0 AND m.spread IS NOT NULL AND m.total IS NOT NULL")
    args = []
    if before:
        q += " AND g.game_date < ?"
        args.append(before)
    rows = con.execute(q, args).fetchall()
    if len(rows) < 2000:
        return None
    totals = {r["game_id"]: r["total"] for r in rows}
    t_mean = sum(totals.values()) / len(totals)
    agg_m, agg_s = {}, {}
    for r in rows:
        k = (r["pid"], r["season"])
        if r["mins"] >= 5:
            x = agg_m.setdefault(k, [0.0, 0])
            x[0] += r["mins"]
            x[1] += 1
        if r["mins"] >= 15:
            x = agg_s.setdefault(k, [[0.0] * len(CTX_STATS), 0])
            for i, st in enumerate(CTX_STATS):
                x[0][i] += row_value(r, st)
            x[1] += 1
    mins = {"starter": [[0.0, 0] for _ in range(len(SPREAD_EDGES) + 1)], "bench": [[0.0, 0] for _ in range(len(SPREAD_EDGES) + 1)]}
    sxy, sxx, cnt = [0.0] * len(CTX_STATS), [0.0] * len(CTX_STATS), [0] * len(CTX_STATS)
    for r in rows:
        k = (r["pid"], r["season"])
        am = agg_m.get(k)
        if am and am[1] >= 8 and am[0] / am[1] >= 10:
            cell = mins["starter" if r["starter"] else "bench"][spread_bucket(r["spread"])]
            cell[0] += r["mins"] / (am[0] / am[1])
            cell[1] += 1
        asx = agg_s.get(k)
        if r["mins"] >= 15 and asx and asx[1] >= 8:
            x = (r["total"] - t_mean) / t_mean
            for i, st in enumerate(CTX_STATS):
                avg = asx[0][i] / asx[1]
                if avg >= 2:
                    sxy[i] += x * (row_value(r, st) / avg - 1)
                    sxx[i] += x * x
                    cnt[i] += 1
    out_min = {}
    for role, cells in mins.items():
        tot_n = sum(c[1] for c in cells)
        overall = sum(c[0] for c in cells) / tot_n if tot_n else 1.0
        out_min[role] = []
        for c in cells:
            m = c[0] / c[1] if c[1] else overall
            m = overall + (m - overall) * c[1] / (c[1] + 300.0)
            out_min[role].append(round(m / overall, 4))
    slope = {}
    for i, st in enumerate(CTX_STATS):
        k = sxy[i] / sxx[i] if sxx[i] > 0 else 0.0
        slope[st] = round(k * cnt[i] / (cnt[i] + 3000.0), 4)
    return {"t_mean": round(t_mean, 2), "edges": SPREAD_EDGES, "min": out_min, "slope": slope, "n": len(rows)}


def compute_boost(con, before=None, k_shrink=BOOST_SHRINK, min_out=3):
    """With/without splits: how a player's stats change when a rotation teammate does not play.
    {player_id: {teammate_id: [n_games_out, r_pts, r_reb, r_ast, r_3pm]}} (ratios shrunk toward 1)."""
    seasons = [r[0] for r in con.execute("SELECT DISTINCT season FROM game_log ORDER BY season DESC LIMIT 2")]
    if not seasons:
        return {}
    q = ("SELECT player_id, team, game_id, game_date, mins, pts, reb, ast, fg3m FROM game_log "
         "WHERE season IN (%s)" % ",".join("?" * len(seasons)))
    args = list(seasons)
    if before:
        q += " AND game_date < ?"
        args.append(before)
    by_player, last = {}, {}
    first_with = {}
    for r in con.execute(q, args):
        by_player.setdefault(r["player_id"], {})[r["game_id"]] = r
        if r["player_id"] not in last or r["game_date"] >= last[r["player_id"]][0]:
            last[r["player_id"]] = (r["game_date"], r["team"])
        k = (r["player_id"], r["team"])
        if k not in first_with or r["game_date"] < first_with[k]:
            first_with[k] = r["game_date"]
    roster = {}
    for pid, (_, team) in last.items():
        rows = [r for r in by_player[pid].values() if r["team"] == team and r["mins"] >= 5]
        if len(rows) >= 8 and sum(r["mins"] for r in rows) / len(rows) >= 12:
            roster.setdefault(team, []).append((pid, sum(r["mins"] for r in rows) / len(rows)))
    cols = ["pts", "reb", "ast", "fg3m"]
    out = {}
    for team, plist in roster.items():
        for pid, _ in plist:
            prow = {g: r for g, r in by_player[pid].items() if r["team"] == team and r["mins"] >= 5}
            for yid, ymin in plist:
                if yid == pid or ymin < 20:
                    continue
                yg = by_player[yid]
                yfirst = first_with[(yid, team)]
                present = [r for g, r in prow.items() if g in yg and yg[g]["mins"] >= 5]
                absent = [r for g, r in prow.items() if (g not in yg or yg[g]["mins"] < 5) and r["game_date"] >= yfirst]
                if len(absent) < min_out or len(present) < 5:
                    continue
                arr = [len(absent)]
                for c in cols:
                    ma = sum(r[c] for r in absent) / len(absent)
                    mp = sum(r[c] for r in present) / len(present)
                    ratio = ma / mp if mp >= 0.5 else 1.0
                    ratio = 1 + (ratio - 1) * len(absent) / (len(absent) + k_shrink)
                    arr.append(round(min(max(ratio, 0.7), 1.5), 3))
                out.setdefault(pid, {})[yid] = arr
    return out


def ctx_factors(ctx, stat, starter, spread, total):
    fm, ft = 1.0, 1.0
    if ctx and spread is not None and ctx.get("min"):
        fm = ctx["min"]["starter" if starter else "bench"][spread_bucket(spread)]
    if ctx and total is not None and stat in ctx.get("slope", {}) and ctx.get("t_mean"):
        ft = min(max(1 + ctx["slope"][stat] * (total - ctx["t_mean"]) / ctx["t_mean"], 0.85), 1.15)
    return fm, ft


def stat_ratio(arr, stat, comp):
    """The with/without ratio for one stat (combos use the player's own mix of points, rebounds, assists),
    scaled by USAGE_STRENGTH because the raw splits overshoot."""
    if stat in BOOST_STATS:
        r = arr[1 + BOOST_STATS.index(stat)]
    elif stat in COMBO:
        comps = COMBO[stat]
        tot = sum(comp[c] for c in comps)
        r = sum(comp[c] * arr[1 + BOOST_STATS.index(c)] for c in comps) / tot if tot > 0 else 1.0
    else:
        r = 1.0
    return 1 + USAGE_STRENGTH * (r - 1)


def absent_fraction(dates, halflife, ydates, same=None):
    """Weighted share of the player's recent games (newest first) that teammate Y missed.
    Games played for a different team than today's count as 'Y was there' (no information)."""
    if not ydates:
        return 0.0
    d0, have = min(ydates), set(ydates)
    num = den = 0.0
    for i, d in enumerate(dates):
        w = 0.5 ** (i / halflife)
        den += w
        if d >= d0 and d not in have and (same is None or same[i]):
            num += w
    return num / den if den else 0.0


def usage_mult(entries, stat, comp):
    """entries: (ratio array, teammate is out tonight, share of recent games he missed).
    The recent average already contains his past absences, so divide those out, then add tonight's."""
    m = 1.0
    for arr, out_now, f in entries:
        r = stat_ratio(arr, stat, comp)
        m *= (r if out_now else 1.0) / (1 + f * (r - 1))
    return min(max(m, 0.7), 1.5)


def season_start(con, day):
    """First regular-season game date of the season containing `day` (YYYY-MM-DD), or EARLY_START if set."""
    if EARLY_START:
        return EARLY_START
    r = con.execute("SELECT MIN(game_date) FROM game_log WHERE season_type LIKE '%Regular%' AND season="
                    "(SELECT season FROM game_log WHERE season_type LIKE '%Regular%' AND game_date<=? "
                    "ORDER BY game_date DESC LIMIT 1)", (day,)).fetchone()
    return r[0] if r else None


def early_shift(con, day):
    """Change to P(over) for the early-season discount, 0 when it is off or the season is past day 21."""
    if not EARLY_ON:
        return 0.0
    start = season_start(con, day)
    if not start:
        return 0.0
    d = (date.fromisoformat(day) - date.fromisoformat(start)).days
    for lim, sh in EARLY_STEPS:
        if d < lim:
            return sh
    return 0.0


def predict(con, pid, stat, line, side, before=None, opp=None, exp_min=None, halflife=HALFLIFE,
            spread=None, total=None, outs=None, ctx=None, boost=None, shrink=None, prior=PRIOR, on_date=None):
    h = history(con, pid, stat, before)
    if len(h) < 5:
        return None
    xs = [r["v"] for r in h]
    ms = [r["mins"] for r in h]
    avg_min = sum(ms[:10]) / len(ms[:10])
    scale, notes = 1.0, []
    if opp and stat in CTX_STATS:  # same stats the dashboard has factors for
        f, n = opp_factor(con, opp, stat)
        scale *= f
        notes.append("opponent factor x%.3f (from %d player-games, shrunk)" % (f, n))
    starter = sum(1 for r in h[:5] if r["starter"]) >= 3
    fm, ft = ctx_factors(ctx, stat, starter, spread, total)
    if exp_min and avg_min > 0 and stat != "min":
        scale *= exp_min / avg_min
        notes.append("minutes scaled %.1f -> %.1f (your number)" % (avg_min, exp_min))
    elif fm != 1.0:
        scale *= fm
        notes.append("spread %+g: %s minutes x%.3f" % (spread, "starter" if starter else "bench", fm))
    if ft != 1.0:
        scale *= ft
        notes.append("game total %g: pace x%.3f" % (total, ft))
    if outs is not None and boost and boost.get(pid):
        comp = {c: sum(r[c if c != "3pm" else "fg3m"] for r in h[:10]) / len(h[:10]) for c in BOOST_STATS}
        dates = [r["game_date"] for r in h]
        same = [r["team"] == h[0]["team"] for r in h]
        entries = []
        for y, arr in boost[pid].items():
            q = "SELECT game_date FROM game_log WHERE player_id=? AND mins>=5"
            qa = [y]
            if before:
                q += " AND game_date<?"
                qa.append(before)
            yd = [r[0] for r in con.execute(q + " ORDER BY game_date DESC, game_id DESC LIMIT 40", qa)]
            entries.append((arr, y in outs, absent_fraction(dates, halflife, yd, same)))
        um = usage_mult(entries, stat, comp)
        if abs(um - 1) > 1e-9:
            scale *= um
            notes.append("teammates: %d out tonight, usage x%.3f (past absences removed from his average)" %
                         (sum(1 for e in entries if e[1]), um))
    res = price_dist(xs, line, side, halflife, scale, prior, shrink)
    sh = early_shift(con, on_date or before or et_today().isoformat())
    if sh:
        res["p_win"] = min(max(res["p_win"] + (sh if side == "over" else -sh), 0.02), 0.98)
        notes.append("early season: overs %+.0f points, unders %+.0f points (lab experiment 3)" % (sh * 100, -sh * 100))
    res.update(avg_min=avg_min, n=len(h), last=xs[:10], notes=notes)
    return res


def ev_per_dollar(p_win, p_push, odds):
    d = dec(odds)
    return p_win * (d - 1) - (1 - p_win - p_push)


def kelly(p_win, p_push, odds, frac=0.25, cap=0.05):
    b = dec(odds) - 1
    q = 1 - p_win - p_push
    k = (b * p_win - q) / b if b > 0 else 0
    return max(0.0, min(k * frac, cap))


# ----------------------------------------------------------------------------- commands
def cmd_init(args):
    conn(args.db)
    print("database ready: " + args.db)


class NotFound(Exception):
    """ESPN has no page for this game (a few playoff games never got a box score)."""


def http_json(url, tries=4):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "nba-edge/1.0 (personal stats project)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise NotFound(url)
            last = e
            time.sleep(1.5 * (i + 1))
        except Exception as e:  # network blip, bad json
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError("%s -> %s" % (url, last))


def et_today():
    """Today's date in US Eastern (fixed -5h is close enough; we always re-check the last 2 days)."""
    return (datetime.now(timezone.utc) - timedelta(hours=5)).date()


def num(x, default=0.0):
    try:
        return float(str(x).replace("+", ""))
    except (TypeError, ValueError):
        return default


def made_att(x):
    try:
        a, b = str(x).split("-")
        return float(a), float(b)
    except (ValueError, AttributeError):
        return 0.0, 0.0


def parse_line(x):
    """'-1.5' -> -1.5, 'o240.5' -> 240.5, 'EVEN'/'PK' -> 0."""
    if x is None:
        return None
    t = str(x).strip().lower()
    if t in ("even", "ev", "pk", "pick"):
        return 0.0
    try:
        return float(t.lstrip("ou"))
    except ValueError:
        return None


def game_lines(d):
    """Closing and opening spread (home team's view) and total from a game summary."""
    pcs = d.get("pickcenter") or []
    if not pcs:
        return None, None, None, None
    pc = pcs[0]
    ps = (pc.get("pointSpread") or {}).get("home") or {}
    tt = (pc.get("total") or {}).get("over") or {}
    spread = parse_line((ps.get("close") or {}).get("line"))
    open_spread = parse_line((ps.get("open") or {}).get("line"))
    total = parse_line((tt.get("close") or {}).get("line"))
    open_total = parse_line((tt.get("open") or {}).get("line"))
    if total is None:
        total = parse_line(pc.get("overUnder"))
    return spread, total, open_spread, open_total


def parse_summary(d, game_date):
    """One ESPN game summary -> (player rows, game row). ([], None) if the game is not final."""
    comp = d["header"]["competitions"][0]
    if comp["status"]["type"]["name"] != "STATUS_FINAL":
        return [], None
    info = d["header"].get("season", {})
    stype = info.get("type", 2)
    if stype not in (2, 3):
        return [], None
    year = int(info.get("year"))
    season = "%d-%02d" % (year - 1, year % 100)
    stype_name = "Regular Season" if stype == 2 else "Playoffs"
    teams = {}
    for c in comp["competitors"]:
        teams[str(c["team"]["id"])] = dict(abbr=c["team"]["abbreviation"], home=1 if c["homeAway"] == "home" else 0,
                                           win=bool(c.get("winner")), score=num(c.get("score")))
    gid = str(comp.get("id") or d["header"].get("id"))
    out = []
    for tb in d["boxscore"]["players"]:
        tid = str(tb["team"]["id"])
        if tid not in teams or not tb.get("statistics"):
            continue
        me = teams[tid]
        opp = [t["abbr"] for k, t in teams.items() if k != tid][0]
        st = tb["statistics"][0]
        keys = st["keys"]
        for a in st["athletes"]:
            if a.get("didNotPlay") or not a.get("stats"):
                continue
            m = dict(zip(keys, a["stats"]))
            mins = num(m.get("minutes"))
            if mins <= 0:
                continue
            fgm, fga = made_att(m.get("fieldGoalsMade-fieldGoalsAttempted"))
            tpm, tpa = made_att(m.get("threePointFieldGoalsMade-threePointFieldGoalsAttempted"))
            ftm, fta = made_att(m.get("freeThrowsMade-freeThrowsAttempted"))
            name = a["athlete"]["displayName"]
            matchup = "%s %s %s" % (me["abbr"], "vs." if me["home"] else "@", opp)
            out.append((int(a["athlete"]["id"]), name, norm(name), me["abbr"], gid, game_date.isoformat(),
                        season, stype_name, matchup, me["home"], opp,
                        "W" if me["win"] else "L", mins, num(m.get("points")), num(m.get("rebounds")),
                        num(m.get("assists")), tpm, tpa, fgm, fga, ftm, fta, num(m.get("steals")),
                        num(m.get("blocks")), num(m.get("turnovers")), num(m.get("fouls")),
                        num(m.get("plusMinus")), 1 if a.get("starter") else 0))
    home = next((t for t in teams.values() if t["home"]), None)
    away = next((t for t in teams.values() if not t["home"]), None)
    game = None
    if home and away:
        sp, tot, osp, otot = game_lines(d)
        game = (gid, game_date.isoformat(), season, stype_name, home["abbr"], away["abbr"], home["score"], away["score"],
                sp, tot, osp, otot)
    return out, game


def home_spread(odds):
    """Home team's spread from a scoreboard odds block (uses the favorite flag, so the sign is never ambiguous)."""
    sp = odds.get("spread")
    if sp is None:
        return None
    fav_home = (odds.get("homeTeamOdds") or {}).get("favorite")
    return 0.0 if sp == 0 else (-abs(sp) if fav_home else abs(sp))


def snapshot_lines(con):
    """Save today's and tomorrow's game lines. A row is only added when the spread or total moved."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    added = 0
    for d in (et_today(), et_today() + timedelta(days=1)):
        j = http_json("%s/scoreboard?dates=%s&limit=100" % (ESPN, d.strftime("%Y%m%d")))
        for e in j.get("events", []):
            if e["status"]["type"]["state"] != "pre":
                continue
            c = e["competitions"][0]
            odds = (c.get("odds") or [None])[0]
            if not odds:
                continue
            ab = {t["homeAway"]: t["team"]["abbreviation"] for t in c["competitors"]}
            row = (home_spread(odds), odds.get("overUnder"))
            last = con.execute("SELECT spread, total FROM lines WHERE game_id=? ORDER BY captured DESC LIMIT 1",
                               (str(e["id"]),)).fetchone()
            if last is None or (last["spread"], last["total"]) != row:
                con.execute("INSERT OR REPLACE INTO lines VALUES (?,?,?,?,?,?,?)",
                            (str(e["id"]), d.isoformat(), ab.get("home"), ab.get("away"), stamp, row[0], row[1]))
                added += 1
    con.commit()
    return added


def cmd_sync(args):
    con = conn(args.db)
    today = et_today()
    if args.since:
        start = date.fromisoformat(args.since)
    else:
        last = con.execute("SELECT MAX(game_date) FROM games").fetchone()[0] or \
            con.execute("SELECT MAX(game_date) FROM game_log").fetchone()[0]
        if last:
            start = date.fromisoformat(last) - timedelta(days=args.overlap)
        else:
            start = date(int(current_season()[:4]) - 1, 10, 1)
            print("empty database: backfilling from %s (use --since to change)" % start)
    end = date.fromisoformat(args.until) if args.until else today
    if start > end:
        die("--since is after the end date")
    known = {r[0] for r in con.execute("SELECT game_id FROM games")}
    days = [start + timedelta(n) for n in range((end - start).days + 1)]

    def day_events(day):
        j = http_json("%s/scoreboard?dates=%s&limit=100" % (ESPN, day.strftime("%Y%m%d")))
        return day, [e for e in j.get("events", [])
                     if e["status"]["type"]["name"] == "STATUS_FINAL" and e.get("season", {}).get("type") in (2, 3)]

    todo, failed = [], 0
    with cf.ThreadPoolExecutor(args.workers) as ex:
        for fut in [ex.submit(day_events, d) for d in days]:
            try:
                day, evs = fut.result()
            except Exception as e:
                failed += 1
                print("  scoreboard failed: %s" % e)
                continue
            todo += [(day, e["id"]) for e in evs if str(e["id"]) not in known]
    print("%d day(s) checked, %d new final game(s) to fetch" % (len(days), len(todo)))

    def one(item):
        day, eid = item
        return parse_summary(http_json("%s/summary?event=%s" % (ESPN, eid)), day)

    total, done, skipped = 0, 0, 0
    with cf.ThreadPoolExecutor(args.workers) as ex:
        futs = {ex.submit(one, it): it for it in todo}
        rows, games = [], []
        for fut in cf.as_completed(futs):
            done += 1
            try:
                r, g = fut.result()
                rows += r
                if g:
                    games.append(g)
            except NotFound:
                skipped += 1
            except Exception as e:
                failed += 1
                print("  game %s failed: %s" % (futs[fut][1], e))
            if len(rows) >= 2000 or done == len(futs):
                con.executemany("INSERT OR REPLACE INTO game_log VALUES (%s)" % ",".join("?" * len(GAME_COLS)), rows)
                con.executemany("INSERT OR REPLACE INTO games VALUES (%s)" % ",".join("?" * len(GAME_FIELDS)), games)
                con.commit()
                total += len(rows)
                rows, games = [], []
                print("  %d/%d games" % (done, len(futs)))
    if skipped:
        print("  %d game(s) skipped: ESPN publishes no box score for them" % skipped)
    if not args.no_lines:
        try:
            print("  game lines: %d new snapshot(s)" % snapshot_lines(con))
        except Exception as e:
            print("  could not snapshot game lines: %s" % e)
    print("done. %d player-games written to %s%s" % (total, args.db,
          ("  (%d request(s) failed, rerun to retry)" % failed) if failed else ""))
    if failed and not total:
        sys.exit(1)


TABLES = [("game_log", GAME_COLS, "game_date, game_id, player_id", "game_log.csv"),
          ("games", GAME_FIELDS, "game_date, game_id", "games.csv"),
          ("lines", LINE_FIELDS, "game_id, captured", "lines.csv")]


def cmd_dump(args):
    con = conn(args.db)
    os.makedirs(args.path, exist_ok=True)
    for table, cols, order, fname in TABLES:
        n = 0
        with open(os.path.join(args.path, fname), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(cols)
            for r in con.execute("SELECT %s FROM %s ORDER BY %s" % (",".join(cols), table, order)):
                w.writerow([("%g" % v) if isinstance(v, float) else v for v in tuple(r)])
                n += 1
        print("wrote %d rows to %s" % (n, os.path.join(args.path, fname)))


def cmd_load(args):
    con = conn(args.db)
    for table, cols, _, fname in TABLES:
        path = os.path.join(args.path, fname)
        if not os.path.exists(path):
            print("%s does not exist yet, skipping" % path)
            continue
        with open(path, newline="", encoding="utf-8") as f:
            data = [tuple((None if r[c] == "" else r[c]) for c in cols) for r in csv.DictReader(f)]
        con.executemany("INSERT OR REPLACE INTO %s VALUES (%s)" % (table, ",".join("?" * len(cols))), data)
        con.commit()
        print("loaded %d rows from %s" % (len(data), path))


LOG_FIELDS = ["date", "opp", "home", "min", "pts", "reb", "ast", "3pm", "stl", "blk", "tov", "fga", "starter", "margin", "team"]


def cmd_export(args):
    """JSON for the dashboard. Deterministic (no timestamps), so unchanged data means no git commit."""
    con = conn(args.db)
    os.makedirs(args.outdir, exist_ok=True)
    season = con.execute("SELECT MAX(season) FROM game_log").fetchone()[0]
    if not season:
        die("game_log is empty")
    pts = {}
    for r in con.execute("SELECT game_id, team, SUM(pts) p FROM game_log GROUP BY game_id, team"):
        pts.setdefault(r["game_id"], {})[r["team"]] = r["p"]

    def margin(gid, team):
        d = pts.get(gid, {})
        others = [v for k, v in d.items() if k != team]
        return int(d[team] - others[0]) if team in d and len(others) == 1 else None

    cutoff = (date.fromisoformat(con.execute("SELECT MAX(game_date) FROM game_log").fetchone()[0])
              - timedelta(days=args.active_days)).isoformat()
    active = [r["player_id"] for r in con.execute(
        "SELECT player_id FROM game_log GROUP BY player_id HAVING MAX(game_date) >= ?", (cutoff,))]
    players = []
    for pid in sorted(active):
        rows = con.execute(
            "SELECT * FROM game_log WHERE player_id=? AND mins>=5 ORDER BY game_date DESC, game_id DESC LIMIT ?",
            (pid, args.logs)).fetchall()
        if not rows:
            continue
        logs = [[r["game_date"], r["opp"], r["home"], round(r["mins"], 1), int(r["pts"]), int(r["reb"]), int(r["ast"]),
                 int(r["fg3m"]), int(r["stl"]), int(r["blk"]), int(r["tov"]), int(r["fga"]), r["starter"] or 0,
                 margin(r["game_id"], r["team"]), r["team"]] for r in rows]
        players.append({"id": pid, "n": rows[0]["player"], "p": rows[0]["pnorm"], "t": rows[0]["team"], "logs": logs})
    factors = {}
    for st in ("pts", "reb", "ast", "3pm", "stl", "blk", "tov", "pra", "pr", "pa", "ra"):
        factors[st] = {t: [round(f, 4), n] for t, (f, n) in sorted(opp_factors(con, st).items())}
    ctx = compute_ctx(con) or {}
    keep = {p["id"] for p in players}
    boost = {str(pid): {str(t): arr for t, arr in d.items() if t in keep}
             for pid, d in compute_boost(con).items() if pid in keep}
    boost = {k: v for k, v in boost.items() if v}
    n_rows = con.execute("SELECT COUNT(*) FROM game_log").fetchone()[0]
    n_games = con.execute("SELECT COUNT(DISTINCT game_id) FROM game_log").fetchone()[0]
    last = con.execute("SELECT MAX(game_date) FROM game_log").fetchone()[0]
    meta = {"season": season, "rows": n_rows, "games": n_games, "players": len(players), "last_game_date": last,
            "fields": LOG_FIELDS, "model": {"halflife": HALFLIFE, "prior": PRIOR, "shrink": SHRINK, "usage": USAGE_STRENGTH},
            "early": {"on": EARLY_ON, "steps": EARLY_STEPS, "start": EARLY_START or (con.execute(
                "SELECT MIN(game_date) FROM game_log WHERE season_type LIKE '%Regular%' AND season=?", (season,)).fetchone()[0])}}

    def put(name, obj):
        with open(os.path.join(args.outdir, name), "w", encoding="utf-8") as f:
            json.dump(obj, f, separators=(",", ":"), ensure_ascii=False, sort_keys=True)
            f.write("\n")
    put("players.json", players)
    put("opp.json", factors)
    put("ctx.json", ctx)
    put("boost.json", boost)
    put("meta.json", meta)
    print("exported %d players, %d games (last %s), %d boost tables to %s" % (len(players), n_games, last, len(boost), args.outdir))


def cmd_status(args):
    con = conn(args.db)
    rows = con.execute(
        "SELECT season, season_type, COUNT(*) g, COUNT(DISTINCT player_id) p, "
        "MIN(game_date) a, MAX(game_date) b FROM game_log GROUP BY season, season_type "
        "ORDER BY season").fetchall()
    if not rows:
        print("game_log is empty. Run `sync` (or `demo`).")
    for r in rows:
        print("%s %-14s %6d player-games  %4d players  %s to %s"
              % (r["season"], r["season_type"], r["g"], r["p"], r["a"], r["b"]))
    ng = con.execute("SELECT COUNT(*), SUM(spread IS NOT NULL) FROM games").fetchone()
    print("games with closing lines: %d of %d   line snapshots: %d" %
          (ng[1] or 0, ng[0], con.execute("SELECT COUNT(*) FROM lines").fetchone()[0]))
    nb = con.execute("SELECT COUNT(*), SUM(status='pending') FROM bets").fetchone()
    print("bets logged: %d (%d pending)" % (nb[0], nb[1] or 0))


def cmd_player(args):
    con = conn(args.db)
    p = find_player(con, args.name)
    rows = con.execute(
        "SELECT * FROM game_log WHERE player_id=? ORDER BY game_date DESC LIMIT ?",
        (p["player_id"], args.n)).fetchall()
    print("%s  (%d games in db)" % (p["player"], p["g"]))
    print("%-10s %-4s %-4s %5s %4s %4s %4s %4s %4s %4s %5s" %
          ("date", "tm", "opp", "min", "pts", "reb", "ast", "3pm", "stl", "blk", "+/-"))
    for r in rows:
        print("%-10s %-4s %-4s %5.1f %4.0f %4.0f %4.0f %4.0f %4.0f %4.0f %5.0f" %
              (r["game_date"], r["team"], ("" if r["home"] else "@") + r["opp"], r["mins"],
               r["pts"], r["reb"], r["ast"], r["fg3m"], r["stl"], r["blk"], r["plus_minus"] or 0))
    if rows:
        n = len(rows)
        avg = lambda c: sum(r[c] for r in rows) / n
        print("%-21s %5.1f %4.1f %4.1f %4.1f %4.1f %4.1f %4.1f" %
              ("avg last %d" % n, avg("mins"), avg("pts"), avg("reb"), avg("ast"),
               avg("fg3m"), avg("stl"), avg("blk")))


def show_price(name, stat, line, side, res, odds=None):
    print("%s  %s %s %s   (%d games used, %.1f effective)"
          % (name, stat.upper(), side, line, res["n"], res["neff"]))
    print("  recent mean %.1f  sd %.1f  avg minutes %.1f" % (res["mu"], res["sd"], res["avg_min"]))
    print("  last 10: " + " ".join("%g" % x for x in res["last"]))
    for note in res["notes"]:
        print("  " + note)
    print("  model P(win) %.1f%%   (normal %.1f%%, hit-rate %.1f%%)   push %.1f%%"
          % (res["p_win"] * 100, res["p_norm"] * 100, res["p_emp"] * 100, res["p_push"] * 100))
    if odds is not None:
        imp = 1 / dec(odds)
        ev = ev_per_dollar(res["p_win"], res["p_push"], odds)
        print("  at %s: book implies %.1f%%  edge %+.1f pts  EV %+.2f per $1  quarter-Kelly %.1f%% of bankroll"
              % (fmt_odds(odds), imp * 100, (res["p_win"] - imp) * 100, ev,
                 kelly(res["p_win"], res["p_push"], odds) * 100))


def team_of(con, pid):
    r = con.execute("SELECT team FROM game_log WHERE player_id=? ORDER BY game_date DESC, game_id DESC LIMIT 1", (pid,)).fetchone()
    return r["team"] if r else None


def live_context(con, pid):
    """Tonight's opponent, spread, total and the injury list for this player's team, straight from ESPN."""
    team = team_of(con, pid)
    out = dict(team=team, opp=None, spread=None, total=None, outs=[], doubtful=[], date=None)
    for d in (et_today(), et_today() + timedelta(days=1)):
        j = http_json("%s/scoreboard?dates=%s&limit=100" % (ESPN, d.strftime("%Y%m%d")))
        for e in j.get("events", []):
            c = e["competitions"][0]
            ab = {t["homeAway"]: t["team"]["abbreviation"] for t in c["competitors"]}
            if team in ab.values():
                out["opp"] = ab["away"] if ab["home"] == team else ab["home"]
                out["date"] = d.isoformat()
                odds = (c.get("odds") or [None])[0]
                if odds:
                    out["spread"], out["total"] = home_spread(odds), odds.get("overUnder")
                break
        if out["opp"]:
            break
    for t in http_json(ESPN + "/injuries").get("injuries", []):
        for e in t.get("injuries", []):
            a = e.get("athlete") or {}
            if (a.get("team") or {}).get("abbreviation") != team:
                continue
            r = con.execute("SELECT player_id FROM game_log WHERE pnorm=? ORDER BY game_date DESC LIMIT 1",
                            (norm(a.get("displayName", "")),)).fetchone()
            item = (r["player_id"] if r else None, a.get("displayName"), e.get("status"))
            if e.get("status") == "Out":
                out["outs"].append(item)
            else:
                out["doubtful"].append(item)
    return out


def cmd_price(args):
    con = conn(args.db)
    stat = stat_key(args.stat)
    if stat not in STAT_COLS:
        die("unknown stat '%s'. Use: %s" % (args.stat, " ".join(STAT_COLS)))
    side = "under" if args.side.lower().startswith("u") else "over"
    p = find_player(con, args.name)
    opp, spread, total = args.opp, args.spread, args.total
    outs = [find_player(con, n)["player_id"] for n in (args.out or [])] if (args.out or args.auto) else None
    if args.auto:
        lc = live_context(con, p["player_id"])
        if lc["opp"]:
            print("tonight: %s vs %s (%s)  spread %s  total %s" % (lc["team"], lc["opp"], lc["date"],
                  "n/a" if lc["spread"] is None else "%+g (home view)" % lc["spread"], lc["total"] or "n/a"))
            opp = opp or lc["opp"]
            spread = spread if spread is not None else lc["spread"]
            total = total if total is not None else lc["total"]
        else:
            print("no game found for %s today or tomorrow" % lc["team"])
        known = [i for i, _, _ in lc["outs"] if i]
        outs += [i for i in known if i != p["player_id"] and i not in outs]
        print("injury report, out: %s" % (", ".join(n for _, n, _ in lc["outs"]) or "none"))
        if lc["doubtful"]:
            print("injury report, not applied: %s" % ", ".join("%s (%s)" % (n, st) for _, n, st in lc["doubtful"]))
        if any(i == p["player_id"] for i, _, _ in lc["outs"]):
            print("WARNING: %s is listed OUT" % p["player"])
    ctx = compute_ctx(con) if (spread is not None or total is not None) else None
    boost = compute_boost(con) if outs is not None else None
    res = predict(con, p["player_id"], stat, args.line, side, opp=opp, exp_min=args.min, halflife=args.halflife,
                  spread=spread, total=total, outs=outs, ctx=ctx, boost=boost)
    if not res:
        die("not enough games for %s" % p["player"])
    show_price(p["player"], stat, args.line, side, res, parse_odds(args.odds) if args.odds else None)


def parse_leg(s):
    parts = [x.strip() for x in s.split(":")]
    if len(parts) < 4:
        die("bad leg '%s'. Format: name:stat:side:line[:odds[:date]]" % s)
    name, stat, side, line = parts[:4]
    odds = parse_odds(parts[4]) if len(parts) > 4 and parts[4] else None
    gdate = parts[5] if len(parts) > 5 and parts[5] else None
    stat = stat_key(stat)
    side = side.lower()
    if stat in STAT_COLS:
        side = "under" if side.startswith("u") else "over"
    return dict(name=name, stat=stat, side=side, line=float(line), odds=odds, date=gdate)


def price_leg(con, leg):
    """Returns (player_row, result) or (None, None) for manual legs."""
    if leg["stat"] not in STAT_COLS:
        return None, None
    p = find_player(con, leg["name"])
    res = predict(con, p["player_id"], leg["stat"], leg["line"], leg["side"], before=leg["date"])
    if not res:
        die("not enough games before %s for %s" % (leg["date"], p["player"]))
    return p, res


def cmd_slip(args):
    con = conn(args.db)
    joint, dsum = 1.0, 1.0
    modeled = True
    for s in args.legs:
        leg = parse_leg(s)
        p, res = price_leg(con, leg)
        if res is None:
            print("%s (%s): manual leg, not modeled\n" % (leg["name"], leg["stat"]))
            modeled = False
            continue
        show_price(p["player"], leg["stat"], leg["line"], leg["side"], res, leg["odds"])
        print()
        joint *= res["p_win"]
        if leg["odds"]:
            dsum *= dec(leg["odds"])
    if modeled:
        print("joint model P (independence assumed): %.1f%%  = 1 in %.1f" % (joint * 100, 1 / joint))
        if args.odds:
            d = dec(parse_odds(args.odds))
            print("slip pays %s; fair price for the model prob is %s; EV per $1 %+.2f"
                  % (args.odds, fmt_odds(to_american(1 / joint)), joint * (d - 1) - (1 - joint)))
        elif dsum > 1:
            print("legs multiplied pay %s (same-game builders reprice correlated legs lower)"
                  % fmt_odds(to_american(dsum)))
        print("note: legs from the same game are correlated, so the real joint P differs from this.")


def cmd_bet(args):
    con = conn(args.db)
    if args.bcmd == "add":
        legs = [parse_leg(s) for s in args.leg]
        if not legs:
            die("give at least one --leg")
        odds = parse_odds(args.odds)
        placed = args.date or date.today().isoformat()
        cur = con.execute("INSERT INTO bets(placed_at, book, stake, odds, note) VALUES (?,?,?,?,?)",
                          (placed, args.book, args.stake, odds, args.note or ""))
        bet_id = cur.lastrowid
        joint, all_modeled = 1.0, True
        for leg in legs:
            p, res = price_leg(con, leg)
            label = "%s %s %s %g" % (leg["name"], leg["stat"], leg["side"], leg["line"])
            if res:
                joint *= res["p_win"]
                con.execute(
                    "INSERT INTO legs(bet_id, player, player_id, stat, side, line, odds, game_date, label,"
                    " model_prob, mean_at_bet, avg_min_at_bet) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (bet_id, p["player"], p["player_id"], leg["stat"], leg["side"], leg["line"],
                     leg["odds"], leg["date"], label, res["p_win"], res["mu"], res["avg_min"]))
                print("  leg %-40s model %.1f%%  mean %.1f" % (label, res["p_win"] * 100, res["mu"]))
            else:
                all_modeled = False
                con.execute(
                    "INSERT INTO legs(bet_id, player, stat, side, line, odds, game_date, label)"
                    " VALUES (?,?,?,?,?,?,?,?)",
                    (bet_id, leg["name"], leg["stat"], leg["side"], leg["line"], leg["odds"],
                     leg["date"], label))
                print("  leg %-40s manual (resolve by hand)" % label)
        if all_modeled:
            con.execute("UPDATE bets SET model_prob=? WHERE id=?", (joint, bet_id))
            print("bet #%d logged. model joint P %.1f%% vs slip-implied %.1f%%"
                  % (bet_id, joint * 100, 100 / dec(odds)))
        else:
            print("bet #%d logged." % bet_id)
        con.commit()
    elif args.bcmd == "list":
        for b in con.execute("SELECT * FROM bets ORDER BY id DESC LIMIT ?", (args.n,)):
            print("#%d %s %s $%.2f at %s  %s  payout $%.2f  %s"
                  % (b["id"], b["placed_at"], b["book"], b["stake"], fmt_odds(b["odds"]),
                     b["status"], b["payout"], b["note"] or ""))
            for l in con.execute("SELECT * FROM legs WHERE bet_id=?", (b["id"],)):
                act = "" if l["actual"] is None else " actual %g" % l["actual"]
                print("     leg %d  %-42s %s%s" % (l["id"], l["label"], l["result"], act))
    elif args.bcmd == "cashout":
        n = con.execute("UPDATE bets SET status='cashout', payout=? WHERE id=?",
                        (args.amount, args.id)).rowcount
        con.commit()
        print("bet #%d cashed out for $%.2f" % (args.id, args.amount) if n else "no such bet")
    elif args.bcmd == "resolve":
        con.execute("UPDATE legs SET result=? WHERE id=?", (args.result, args.leg_id))
        con.commit()
        refresh_bets(con)
        print("leg %d marked %s" % (args.leg_id, args.result))
    elif args.bcmd == "tag":
        con.execute("UPDATE legs SET tags=trim(tags || ' ' || ?) WHERE id=?", (args.tag, args.leg_id))
        con.commit()
        print("tagged leg %d: %s" % (args.leg_id, args.tag))


def team_margin(con, game_id, team):
    rows = con.execute("SELECT team, SUM(pts) AS p FROM game_log WHERE game_id=? GROUP BY team",
                       (game_id,)).fetchall()
    d = {r["team"]: r["p"] for r in rows}
    if team in d and len(d) == 2:
        return d[team] - [v for k, v in d.items() if k != team][0]
    return None


def refresh_bets(con):
    for b in con.execute("SELECT * FROM bets WHERE status='pending'").fetchall():
        legs = con.execute("SELECT * FROM legs WHERE bet_id=?", (b["id"],)).fetchall()
        rs = [l["result"] for l in legs]
        if "loss" in rs:
            con.execute("UPDATE bets SET status='loss', payout=0 WHERE id=?", (b["id"],))
        elif rs and all(r in ("win", "push", "void") for r in rs):
            if all(r == "win" for r in rs):
                payout = b["stake"] * dec(b["odds"])
            else:
                kept = [l for l in legs if l["result"] == "win"]
                if kept and all(l["odds"] for l in kept):
                    d = 1.0
                    for l in kept:
                        d *= dec(l["odds"])
                    payout = b["stake"] * d
                else:
                    payout = b["stake"] * dec(b["odds"])
                print("  bet #%d had push/void legs: payout estimated, verify with your book" % b["id"])
            con.execute("UPDATE bets SET status='win', payout=? WHERE id=?", (payout, b["id"]))
    con.commit()


def cmd_settle(args):
    con = conn(args.db)
    legs = con.execute("SELECT * FROM legs WHERE result='pending'").fetchall()
    done = 0
    for l in legs:
        if l["stat"] not in STAT_COLS:
            continue
        if not l["game_date"]:
            print("  leg %d (%s): no date, cannot auto-settle" % (l["id"], l["label"]))
            continue
        r = con.execute("SELECT * FROM game_log WHERE player_id=? AND game_date=?",
                        (l["player_id"], l["game_date"])).fetchone()
        if not r:
            if args.void_dnp:
                con.execute("UPDATE legs SET result='void' WHERE id=?", (l["id"],))
                print("  leg %d (%s): no row on %s, marked void (DNP)" % (l["id"], l["label"], l["game_date"]))
                done += 1
            else:
                print("  leg %d (%s): no game row on %s yet (run sync, or add --void-dnp if he sat)"
                      % (l["id"], l["label"], l["game_date"]))
            continue
        actual = row_value(r, l["stat"])
        if abs(actual - l["line"]) < 1e-9:
            res = "push"
        elif (actual > l["line"]) == (l["side"] == "over"):
            res = "win"
        else:
            res = "loss"
        margin = team_margin(con, r["game_id"], r["team"])
        con.execute("UPDATE legs SET result=?, actual=?, minutes=?, margin=? WHERE id=?",
                    (res, actual, r["mins"], margin, l["id"]))
        print("  leg %d %-40s %s  actual %g, %.0f min, margin %s"
              % (l["id"], l["label"], res.upper(), actual, r["mins"],
                 "?" if margin is None else "%+d" % margin))
        done += 1
    con.commit()
    refresh_bets(con)
    print("settled %d leg(s)" % done)


def rec(sub):
    w = sum(1 for l in sub if l["result"] == "win")
    lo = sum(1 for l in sub if l["result"] == "loss")
    p = sum(1 for l in sub if l["result"] == "push")
    n = w + lo
    return "%d-%d%s  (%s)" % (w, lo, ("-%d" % p) if p else "", ("%.0f%%" % (100.0 * w / n)) if n else "n/a")


def cmd_report(args):
    con = conn(args.db)
    bets = con.execute("SELECT * FROM bets").fetchall()
    settled = [b for b in bets if b["status"] in ("win", "loss", "cashout")]
    staked = sum(b["stake"] for b in settled)
    back = sum(b["payout"] for b in settled)
    print("BETS  %d logged, %d settled, %d pending" %
          (len(bets), len(settled), sum(1 for b in bets if b["status"] == "pending")))
    if settled:
        print("  staked $%.2f  returned $%.2f  profit %+.2f  ROI %+.1f%%"
              % (staked, back, back - staked, 100 * (back - staked) / staked))
        print("  wins %d  losses %d  cashouts %d" % (
            sum(1 for b in settled if b["status"] == "win"),
            sum(1 for b in settled if b["status"] == "loss"),
            sum(1 for b in settled if b["status"] == "cashout")))
    legs = [dict(l) for l in con.execute(
        "SELECT * FROM legs WHERE result IN ('win','loss','push')").fetchall()]
    print("\nLEGS  %s" % rec(legs))
    if not legs:
        print("  nothing settled yet. Run `sync` then `settle`.")
        return
    groups = {}
    for l in legs:
        groups.setdefault("stat " + l["stat"], []).append(l)
        if l["stat"] in STAT_COLS:
            groups.setdefault("side " + l["side"], []).append(l)
        if l["odds"] is not None:
            b = "heavy fav (-150 or shorter)" if l["odds"] <= -150 else (
                "fav (-149 to -105)" if l["odds"] <= -105 else "even or plus money")
            groups.setdefault("price " + b, []).append(l)
        if l["margin"] is not None:
            groups.setdefault("blowout (|margin|>=%d)" % BLOWOUT if abs(l["margin"]) >= BLOWOUT
                              else "normal game", []).append(l)
    for k in sorted(groups):
        print("  %-34s %s" % (k, rec(groups[k])))
    modeled = [l for l in legs if l["model_prob"] is not None and l["result"] != "push"]
    if modeled:
        pred = sum(l["model_prob"] for l in modeled) / len(modeled)
        hit = sum(1 for l in modeled if l["result"] == "win") / len(modeled)
        brier = sum((l["model_prob"] - (1 if l["result"] == "win" else 0)) ** 2 for l in modeled) / len(modeled)
        print("\nMODEL  %d legs  predicted %.1f%%  actual %.1f%%  Brier %.3f (coin flip = 0.250)"
              % (len(modeled), pred * 100, hit * 100, brier))
    misses = [l for l in legs if l["result"] == "loss"]
    if misses:
        print("\nAUTOPSY OF MISSES")
        flags_count = {}
        for l in misses:
            flags = []
            if l["margin"] is not None and abs(l["margin"]) >= BLOWOUT:
                flags.append("BLOWOUT")
            if l["minutes"] is not None and l["avg_min_at_bet"] and l["minutes"] < 0.85 * l["avg_min_at_bet"]:
                flags.append("MINUTES SHORT")
            gap = abs((l["actual"] or 0) - l["line"])
            if gap <= 1.0:
                flags.append("BY ONE")
            if l["tags"]:
                flags.append("tags: " + l["tags"])
            for f in flags:
                flags_count[f.split(":")[0]] = flags_count.get(f.split(":")[0], 0) + 1
            print("  leg %d %s | %s %g, actual %g | %.0f min (avg %.0f) | margin %s | %s"
                  % (l["id"], l["game_date"] or "", l["label"], l["line"], l["actual"] or 0,
                     l["minutes"] or 0, l["avg_min_at_bet"] or 0,
                     "?" if l["margin"] is None else "%+d" % l["margin"],
                     ", ".join(flags) or "no flag, just variance"))
        print("  flag totals over %d misses: %s" % (len(misses), flags_count or "none"))
    book = [l for l in legs if l["model_prob"] is not None and l["odds"] is not None and l["result"] != "push"]
    if len(book) >= 10:
        yb = lambda l: 1 if l["result"] == "win" else 0
        bm = sum((l["model_prob"] - yb(l)) ** 2 for l in book) / len(book)
        bb = sum((1 / dec(l["odds"]) - yb(l)) ** 2 for l in book) / len(book)
        print("\nMODEL VS BOOK  %d legs with odds   Brier model %.3f vs book-implied %.3f  (lower wins; book number includes the vig)" % (len(book), bm, bb))
    print("\nWHAT THE MISSES SAY")
    if len(legs) < 30:
        print("  %d of 30 settled legs so far. Below that, any pattern is noise." % len(legs))
    else:
        for name, test in (("blowout", lambda l: l["margin"] is not None and abs(l["margin"]) >= BLOWOUT),
                           ("minutes short", lambda l: l["minutes"] is not None and l["avg_min_at_bet"] and l["minutes"] < 0.85 * l["avg_min_at_bet"])):
            fl = [l for l in legs if test(l) and l["result"] != "push"]
            ot = [l for l in legs if not test(l) and l["result"] != "push"]
            if len(fl) >= 8 and ot:
                lf = sum(1 for l in fl if l["result"] == "loss") / len(fl)
                lo_ = sum(1 for l in ot if l["result"] == "loss") / len(ot)
                verdict = "costs you: plan for it with --min, --spread or --out" if lf - lo_ > 0.15 else "no clear damage"
                print("  %-14s %d legs, %.0f%% lost vs %.0f%% otherwise: %s" % (name, len(fl), lf * 100, lo_ * 100, verdict))
            else:
                print("  %-14s only %d legs flagged, need 8" % (name, len(fl)))


def build_cases(con, split, sample, seed=1):
    """Out-of-sample test cases: player-games on or after `split`, priced only from earlier games."""
    by = {}
    for r in con.execute("SELECT * FROM game_log WHERE mins>=5 ORDER BY player_id, game_date, game_id"):
        by.setdefault(r["player_id"], []).append(r)
    info = {r["game_id"]: (r["spread"], r["total"]) for r in con.execute("SELECT game_id, spread, total FROM games")}
    played = {}
    for pid, lst in by.items():
        for r in lst:
            played.setdefault(r["game_id"], set()).add(pid)
    spots = [(pid, i) for pid, lst in by.items() for i in range(15, len(lst))
             if lst[i]["mins"] >= 15 and lst[i]["game_date"] >= split and lst[i]["season_type"] == "Regular Season"]
    random.seed(seed)
    if len(spots) > sample:
        spots = random.sample(spots, sample)
    return by, info, played, spots


def make_cases(by, info, played, spots, boost, stats=("pts", "reb", "ast", "3pm", "pra")):
    dates_by = {pid: [r["game_date"] for r in lst] for pid, lst in by.items()}
    cases = []
    for pid, i in spots:
        lst = by[pid]
        prior = lst[max(0, i - 40):i][::-1]
        row = lst[i]
        spread, total = info.get(row["game_id"], (None, None))
        starter = sum(1 for r in prior[:5] if r["starter"]) >= 3
        pdates = [r["game_date"] for r in prior]
        spot = {"entries": [], "f": {}, "pdates": pdates, "same": [r["team"] == prior[0]["team"] for r in prior]}
        for y, arr in (boost or {}).get(pid, {}).items():
            ds = dates_by.get(y, [])
            k = bisect.bisect_left(ds, row["game_date"])
            spot["entries"].append((arr, y not in played[row["game_id"]], ds[max(0, k - 40):k]))
        comp = {c: sum(r[c if c != "3pm" else "fg3m"] for r in prior[:10]) / len(prior[:10]) for c in BOOST_STATS}
        for st in stats:
            xs = [row_value(r, st) for r in prior]
            base = price_dist(xs, 0.5, "over")
            y = row_value(row, st)
            for k in (-0.75, -0.25, 0.25, 0.75):
                line = math.floor(base["mu"] + k * base["sd"]) + 0.5
                cases.append(dict(xs=xs, y=y, line=line, stat=st, starter=starter, spread=spread, total=total,
                                  spot=spot, comp=comp))
    return cases


def eval_cases(cases, ctx=None, use_ctx=False, use_boost=False, halflife=HALFLIFE, prior=PRIOR, shrink=None):
    obs = []
    for c in cases:
        scale = 1.0
        if use_ctx and ctx:
            fm, ft = ctx_factors(ctx, c["stat"], c["starter"], c["spread"], c["total"])
            scale *= fm * ft
        sp = c["spot"]
        if use_boost and sp["entries"]:
            if halflife not in sp["f"]:
                sp["f"][halflife] = [absent_fraction(sp["pdates"], halflife, yd, sp["same"]) for _, _, yd in sp["entries"]]
            ents = [(arr, out, f) for (arr, out, _), f in zip(sp["entries"], sp["f"][halflife])]
            scale *= usage_mult(ents, c["stat"], c["comp"])
        p = price_dist(c["xs"], c["line"], "over", halflife, scale, prior, shrink)["p_win"]
        obs.append((p, 1 if c["y"] > c["line"] else 0))
    return obs


def scores(obs):
    n = len(obs)
    brier = sum((p - y) ** 2 for p, y in obs) / n
    ll = -sum(math.log(min(max(p if y else 1 - p, 1e-6), 1)) for p, y in obs) / n
    return brier, ll


def pick_split(con, given):
    if given:
        return given
    dates = [r[0] for r in con.execute(
        "SELECT DISTINCT game_date FROM game_log WHERE season_type='Regular Season' ORDER BY game_date")]
    if len(dates) < 30:
        die("not enough data. Run `sync` first.")
    return dates[int(len(dates) * 0.6)]


def cmd_calibrate(args):
    con = conn(args.db)
    split = pick_split(con, args.split)
    ctx, boost = compute_ctx(con, before=split), compute_boost(con, before=split)
    by, info, played, spots = build_cases(con, split, args.sample)
    if not spots:
        die("no test games on or after %s" % split)
    cases = make_cases(by, info, played, spots, boost)
    print("out-of-sample test: context effects and teammate splits fitted on games BEFORE %s," % split)
    print("then %d predictions on %d player-games from that date on (each priced from earlier games only)\n" % (len(cases), len(spots)))
    variants = [("own history only", False, False), ("+ spread and game total", True, False),
                ("+ spread, total, teammates out", True, True)]
    print("%-34s %8s %9s" % ("model", "Brier", "log loss"))
    results = []
    for name, uc, ub in variants:
        if uc and not ctx:
            print("%-34s %s" % (name, "needs games with closing lines (run sync --since for a backfill)"))
            continue
        obs = eval_cases(cases, ctx, uc, ub)
        b, ll = scores(obs)
        results.append((name, obs))
        print("%-34s %8.4f %9.4f" % (name, b, ll))
    if len(results) > 1:
        full = results[-1][1]
        base = results[0][1]
        big = [i for i, c in enumerate(cases) if c["spread"] is not None and abs(c["spread"]) >= 10]
        outs = [i for i, c in enumerate(cases) if any(e[1] for e in c["spot"]["entries"])]
        for label, idx in (("big spread (10+) games", big), ("games with a teammate out", outs)):
            if len(idx) >= 200:
                b0 = scores([base[i] for i in idx])[0]
                b1 = scores([full[i] for i in idx])[0]
                print("  %-30s %5d cases   Brier %.4f -> %.4f" % (label, len(idx), b0, b1))
        obs = full
    else:
        obs = results[0][1]
    print("\npredicted    n     predicted   actual")
    for b in range(10):
        lo, hi = b / 10, (b + 1) / 10
        sub = [(p, y) for p, y in obs if lo <= p < hi or (b == 9 and p == 1.0)]
        if sub:
            print("%.1f-%.1f  %6d   %6.1f%%    %6.1f%%" % (
                lo, hi, len(sub), 100 * sum(p for p, _ in sub) / len(sub), 100 * sum(y for _, y in sub) / len(sub)))
    print("\nLower Brier and log loss are better; a coin flip scores 0.2500 and 0.6931.")
    print("This checks the engine against what actually happened. It does NOT prove an edge over the")
    print("book, because player prop lines are not in the data. Log real lines with `bet add` to test that.")


def cmd_tune(args):
    """Grid search of the model knobs on games after the split (everything priced from earlier games)."""
    con = conn(args.db)
    split = pick_split(con, args.split)
    ctx, boost = compute_ctx(con, before=split), compute_boost(con, before=split)
    by, info, played, spots = build_cases(con, split, args.sample, seed=7)
    cases = make_cases(by, info, played, spots, boost)
    full = bool(ctx)
    print("tuning on %d predictions (%d player-games from %s on), %s model\n" %
          (len(cases), len(spots), split, "full" if full else "own-history"))
    grid = []
    for hl in (8, 12, 16, 24):
        for pr in (4, 8, 12, 20):
            for sh in (0.85, 0.92, 1.0):
                b, ll = scores(eval_cases(cases, ctx, full, full, hl, pr, sh))
                grid.append((ll, b, hl, pr, sh))
    grid.sort()
    cur = scores(eval_cases(cases, ctx, full, full))
    print("current settings (halflife %g, prior %g, shrink %g): Brier %.4f, log loss %.4f" % (HALFLIFE, PRIOR, SHRINK, cur[0], cur[1]))
    print("\nbest by log loss:        halflife  prior  shrink    Brier  log loss")
    for ll, b, hl, pr, sh in grid[:5]:
        print("                         %8g  %5g  %6g  %7.4f  %8.4f" % (hl, pr, sh, b, ll))
    print("\nIf the best row beats the current one by more than about 0.0005 log loss, change HALFLIFE, PRIOR or")
    print("SHRINK at the top of nba_edge.py (and re-run `export` so the dashboard follows).")


def cmd_demo(args):
    """Fake league so you can try every command without internet. Not real players."""
    path = args.db
    if os.path.exists(path):
        os.remove(path)
    con = conn(path)
    random.seed(7)
    teams = ["T%02d" % i for i in range(1, 11)]
    mpgs = [34, 32, 30, 28, 26, 22, 18, 14, 10, 8]
    roster, pid = {}, 1000
    for t in teams:
        roster[t] = []
        for j in range(10):
            roster[t].append(dict(
                pid=pid, name="Demo %s Player%d" % (t, j + 1), mpg=mpgs[j],
                r_pts=random.uniform(0.35, 0.8), r_reb=random.uniform(0.1, 0.3),
                r_ast=random.uniform(0.05, 0.28), r_3=random.uniform(0.03, 0.1)))
            pid += 1
    strength = {t: random.gauss(0, 5) for t in teams}
    rows, games = [], []
    start = date(2026, 10, 20)
    for day in range(45):
        d = date.fromordinal(start.toordinal() + day).isoformat()
        order = teams[:]
        random.shuffle(order)
        for k in range(0, 10, 2):
            home, away = order[k], order[k + 1]
            target = strength[home] - strength[away] + 2 + random.gauss(0, 11)
            gid = "D%03d%d" % (day, k // 2)
            made = {}
            for t, opp, is_home in ((home, away, 1), (away, home, 0)):
                for j, p in enumerate(roster[t]):
                    mins = random.gauss(p["mpg"], 3)
                    if abs(target) > 16:
                        mins += -(abs(target) - 16) * 0.5 if j < 5 else (abs(target) - 16) * 0.4
                    mins = max(0.0, min(42.0, mins))
                    if mins < 5 or (j < 5 and random.random() < 0.08):  # bench cameos and starters resting
                        continue

                    def draw(rate, m=mins):
                        mu = rate * m
                        return max(0, round(random.gauss(mu, math.sqrt(max(mu, 0.3)) * 0.9)))
                    pts, reb, ast = draw(p["r_pts"]), draw(p["r_reb"]), draw(p["r_ast"])
                    tpm = draw(p["r_3"])
                    stl, blk, tov = draw(0.03), draw(0.025), draw(0.06)
                    matchup = "%s vs. %s" % (t, opp) if is_home else "%s @ %s" % (t, opp)
                    made.setdefault(t, 0)
                    made[t] += pts
                    rows.append([p["pid"], p["name"], norm(p["name"]), t, gid, d, "2026-27", "Regular Season",
                                 matchup, is_home, opp, None, round(mins, 1), pts, reb, ast, tpm,
                                 tpm * 2 + 1, round(pts / 2.2), round(pts / 1.1), pts // 5, pts // 4,
                                 stl, blk, tov, random.randint(0, 5), 0, 1 if j < 5 else 0])
            wl = {home: "W" if made[home] > made[away] else "L", away: "W" if made[away] > made[home] else "L"}
            sp = round(-(strength[home] - strength[away] + 2) * 2) / 2.0
            games.append((gid, d, "2026-27", "Regular Season", home, away, made[home], made[away], sp,
                          round((226 + random.gauss(0, 6)) * 2) / 2.0, sp, 226.0))
            for r in rows:
                if r[4] == gid:
                    r[11] = wl[r[3]]
    con.executemany("INSERT OR REPLACE INTO game_log VALUES (%s)" % ",".join("?" * len(GAME_COLS)), rows)
    con.executemany("INSERT OR REPLACE INTO games VALUES (%s)" % ",".join("?" * len(GAME_FIELDS)), games)
    con.commit()
    print("demo league written to %s: %d player-games, 100 fake players, %s to %s"
          % (path, len(rows), start.isoformat(), d))


def main():
    ap = argparse.ArgumentParser(description="NBA player database, prop pricer and bet log")
    ap.add_argument("--db", default=DEFAULT_DB, help="sqlite file (default %s)" % DEFAULT_DB)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init").set_defaults(fn=cmd_init)
    s = sub.add_parser("sync", help="download new final games from ESPN (first run backfills last season)")
    s.add_argument("--since", help="YYYY-MM-DD, force a backfill from this date")
    s.add_argument("--until", help="YYYY-MM-DD (default: today, US Eastern)")
    s.add_argument("--overlap", type=int, default=2, help="re-check this many days before the newest stored game")
    s.add_argument("--workers", type=int, default=6)
    s.add_argument("--no-lines", action="store_true", help="skip saving today's game lines")
    s.set_defaults(fn=cmd_sync)
    s = sub.add_parser("dump", help="write game_log.csv, games.csv and lines.csv into a folder")
    s.add_argument("path", help="folder, e.g. data")
    s.set_defaults(fn=cmd_dump)
    s = sub.add_parser("load", help="read the CSVs written by dump")
    s.add_argument("path", help="folder, e.g. data")
    s.set_defaults(fn=cmd_load)
    s = sub.add_parser("export", help="write dashboard JSON")
    s.add_argument("outdir")
    s.add_argument("--logs", type=int, default=40, help="games per player")
    s.add_argument("--active-days", type=int, default=200, help="only players who played within this many days of the newest game")
    s.set_defaults(fn=cmd_export)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    s = sub.add_parser("player")
    s.add_argument("name")
    s.add_argument("-n", type=int, default=10)
    s.set_defaults(fn=cmd_player)
    s = sub.add_parser("price", help="probability and EV for one prop")
    s.add_argument("name")
    s.add_argument("stat")
    s.add_argument("line", type=float)
    s.add_argument("--side", default="over")
    s.add_argument("--odds")
    s.add_argument("--opp", help="opponent code, e.g. OKC")
    s.add_argument("--min", type=float, help="expected minutes (overrides the automatic spread adjustment)")
    s.add_argument("--spread", type=float, help="game spread (either team's view); big spreads cut starters' minutes")
    s.add_argument("--total", type=float, help="game total; fast, high-scoring games lift counting stats")
    s.add_argument("--out", action="append", help="a teammate who is out (repeat for several)")
    s.add_argument("--auto", action="store_true", help="fetch tonight's opponent, spread, total and injuries from ESPN")
    s.add_argument("--halflife", type=float, default=HALFLIFE)
    s.set_defaults(fn=cmd_price)
    s = sub.add_parser("slip", help="price several legs together")
    s.add_argument("legs", nargs="+")
    s.add_argument("--odds", help="what the slip pays, e.g. +450")
    s.set_defaults(fn=cmd_slip)
    b = sub.add_parser("bet")
    bs = b.add_subparsers(dest="bcmd", required=True)
    a = bs.add_parser("add")
    a.add_argument("--book", default="bet365")
    a.add_argument("--stake", type=float, required=True)
    a.add_argument("--odds", required=True, help="slip odds, e.g. +450")
    a.add_argument("--leg", action="append", default=[])
    a.add_argument("--note")
    a.add_argument("--date", help="date placed (default today)")
    a = bs.add_parser("list")
    a.add_argument("-n", type=int, default=20)
    a = bs.add_parser("cashout")
    a.add_argument("id", type=int)
    a.add_argument("amount", type=float)
    a = bs.add_parser("resolve")
    a.add_argument("leg_id", type=int)
    a.add_argument("result", choices=["win", "loss", "push", "void"])
    a = bs.add_parser("tag")
    a.add_argument("leg_id", type=int)
    a.add_argument("tag")
    b.set_defaults(fn=cmd_bet)
    s = sub.add_parser("settle", help="fill in results from synced game logs")
    s.add_argument("--void-dnp", action="store_true")
    s.set_defaults(fn=cmd_settle)
    sub.add_parser("report").set_defaults(fn=cmd_report)
    s = sub.add_parser("calibrate", help="out-of-sample test of the whole model")
    s.add_argument("--sample", type=int, default=4000, help="player-games to test")
    s.add_argument("--split", help="YYYY-MM-DD: fit before, test from this date (default: 60%% through the data)")
    s.set_defaults(fn=cmd_calibrate)
    s = sub.add_parser("tune", help="grid search halflife, prior and shrink")
    s.add_argument("--sample", type=int, default=1500)
    s.add_argument("--split")
    s.set_defaults(fn=cmd_tune)
    sub.add_parser("demo", help="fake league for testing").set_defaults(fn=cmd_demo)
    args = ap.parse_args()
    if args.cmd == "demo" and args.db == DEFAULT_DB:
        args.db = os.path.expanduser("~/nba_edge_demo.db")
    args.fn(args)


if __name__ == "__main__":
    main()
