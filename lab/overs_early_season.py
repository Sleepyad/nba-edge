#!/usr/bin/env python3
"""Lab experiment 1: do overs run cold early in a season?

Question: in the first days of a season the paper log shows overs hitting far less often than the model said.
Is that a real bias or noise? For every player-game in a window, price the player from EARLIER games only (no
opponent/teammate context, so this isolates the base model), at a line equal to his last-10 average rounded to x.5,
and compare the model's average P(over) with how often the over actually hit.

Usage: python lab/overs_early_season.py START END   (ET dates, e.g. 2026-10-20 2026-10-24)
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import nba_edge as N

MIN_LINE = {"pts": 9.5, "reb": 3.5, "ast": 2.5, "3pm": 1.5}


def run(con, start, end):
    rows = con.execute("SELECT player_id, game_date, mins FROM game_log WHERE game_date>=? AND game_date<=? AND mins>=15",
                       (start, end)).fetchall()
    res = {s: [] for s in MIN_LINE}
    for r in rows:
        for stat in MIN_LINE:
            h = N.history(con, r["player_id"], stat, r["game_date"], 10)
            if len(h) < 5:
                continue
            line = round(sum(x["v"] for x in h) / len(h) - 0.5) + 0.5
            if line < MIN_LINE[stat]:
                continue
            p = N.predict(con, r["player_id"], stat, line, "over", before=r["game_date"])
            if not p:
                continue
            actual = con.execute("SELECT %s AS v FROM game_log WHERE player_id=? AND game_date=?" % N.stat_expr(stat),
                                 (r["player_id"], r["game_date"])).fetchone()["v"]
            res[stat].append((p["p_win"], 1.0 if actual > line else 0.0, actual - line))
    return res


def main():
    start, end = sys.argv[1], sys.argv[2]
    con = N.conn(os.environ.get("NBA_DB", N.DEFAULT_DB))
    res = run(con, start, end)
    allr = [x for v in res.values() for x in v]
    print("window %s to %s" % (start, end))
    for k, v in list(res.items()) + [("ALL", allr)]:
        if not v:
            continue
        n = len(v)
        pm = sum(x[0] for x in v) / n
        ar = sum(x[1] for x in v) / n
        gap = sum(x[2] for x in v) / n
        se = (ar * (1 - ar) / n) ** 0.5
        print("  %-4s n=%4d  model P(over) %5.1f%%  actual over %5.1f%% (+/- %.1f)  avg actual minus line %+.2f"
              % (k, n, pm * 100, ar * 100, se * 100, gap))


if __name__ == "__main__":
    main()
