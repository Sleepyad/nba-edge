#!/usr/bin/env python3
"""Lab experiment 2: does the league-wide miss persist from day to day?

Each day, compute (actual over rate - model P(over)) for points props at a last-10-average line. If the previous
7 days' miss predicts the next day's miss, a 'league drift' correction (shrunk) would help; if not, the early-season
gap is noise and no correction should go in.
Usage: python lab/league_drift.py [START] [END]
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import nba_edge as N


def main():
    start = sys.argv[1] if len(sys.argv) > 1 else "2025-11-01"
    end = sys.argv[2] if len(sys.argv) > 2 else "2026-04-12"
    con = N.conn(os.environ.get("NBA_DB", N.DEFAULT_DB))
    days = [r["d"] for r in con.execute("SELECT DISTINCT game_date d FROM game_log WHERE game_date>=? AND game_date<=? "
                                         "AND season_type LIKE '%Regular%' ORDER BY d", (start, end))]
    resid = {}
    for d in days:
        rows = con.execute("SELECT player_id FROM game_log WHERE game_date=? AND mins>=22", (d,)).fetchall()
        diffs = []
        for r in rows:
            h = N.history(con, r["player_id"], "pts", d, 10)
            if len(h) < 8:
                continue
            line = round(sum(x["v"] for x in h) / len(h) - 0.5) + 0.5
            if line < 9.5:
                continue
            p = N.predict(con, r["player_id"], "pts", line, "over", before=d)
            if not p:
                continue
            a = con.execute("SELECT pts v FROM game_log WHERE player_id=? AND game_date=?", (r["player_id"], d)).fetchone()["v"]
            diffs.append((1.0 if a > line else 0.0) - p["p_win"])
        if len(diffs) >= 15:
            resid[d] = sum(diffs) / len(diffs)
    ds = sorted(resid)
    xs, ys = [], []
    for i, d in enumerate(ds):
        prev = [resid[x] for x in ds[max(0, i - 7):i]]
        if len(prev) >= 4:
            xs.append(sum(prev) / len(prev))
            ys.append(resid[d])
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    vx = sum((a - mx) ** 2 for a in xs)
    vy = sum((b - my) ** 2 for b in ys)
    corr = cov / (vx * vy) ** 0.5
    print("days used: %d   mean daily miss %+.1f pts of probability   sd of daily miss %.1f" % (len(ds), 100 * sum(resid.values()) / len(ds), 100 * (sum((v - sum(resid.values()) / len(ds)) ** 2 for v in resid.values()) / len(ds)) ** 0.5))
    print("correlation between the previous 7 days' miss and the next day's miss: %+.2f  (n=%d)" % (corr, n))
    print("slope: %+.2f" % (cov / vx))


if __name__ == "__main__":
    main()
