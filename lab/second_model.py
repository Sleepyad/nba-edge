#!/usr/bin/env python3
"""Lab experiment 5: "Model B", a context layer on top of the live model, plus team-result correlation.

Part 1 (SGP correlation): for every player-game (22+ minutes) at a proxy line (last-10 average rounded to x.5), how
often does the player go over when his team wins vs loses? This is what a "player over + team ML" same-game parlay
really bets on.
Part 2 (Model B): only pregame, numeric versions of the "story" signals:
  usage_trend  = last-5 average of (fga + 0.44 fta + tov) vs the 35 games before that  ("he is carrying the offense")
  min_trend    = last-5 average minutes vs the 35 games before that
  team_form    = his team's win rate over its last 10 games
A logistic recalibration of Model A's probability plus these features is fitted on one block of days and scored on a
later block (log loss, lower is better). If Model B does not beat Model A out of sample, the story signals do not go in.
Usage: python lab/second_model.py [TRAIN_END]      (default 2026-02-15; games after it are the test set)
Reads only. Needs numpy.
"""
import os
import sys
import math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
import nba_edge as N

STATS = ("pts", "reb", "ast", "pra")
MIN_LINE = {"pts": 9.5, "reb": 4.5, "ast": 3.5, "pra": 15.5}


def usage(r):
    return r["fga"] + 0.44 * r["fta"] + r["tov"]


def build(con):
    rows = con.execute("SELECT player_id, team, game_date, game_id, wl FROM game_log WHERE mins>=22 "
                       "AND season_type LIKE '%Regular%' ORDER BY game_date").fetchall()
    # team results by date for team_form
    tg = {}
    for r in con.execute("SELECT DISTINCT team, game_date, game_id, wl FROM game_log WHERE season_type LIKE '%Regular%'"):
        tg.setdefault(r["team"], []).append((r["game_date"], r["game_id"], r["wl"]))
    for t in tg:
        tg[t].sort()
    out = []
    for r in rows:
        pid, d = r["player_id"], r["game_date"]
        hist = con.execute("SELECT mins, fga, fta, tov FROM game_log WHERE player_id=? AND mins>=5 AND game_date<? "
                           "ORDER BY game_date DESC, game_id DESC LIMIT 40", (pid, d)).fetchall()
        if len(hist) < 20:
            continue
        u5 = np.mean([usage(x) for x in hist[:5]])
        u35 = np.mean([usage(x) for x in hist[5:]])
        m5 = np.mean([x["mins"] for x in hist[:5]])
        m35 = np.mean([x["mins"] for x in hist[5:]])
        prev = [x for x in tg[r["team"]] if x[0] < d][-10:]
        if len(prev) < 5:
            continue
        form = sum(1 for x in prev if x[2] == "W") / len(prev)
        for stat in STATS:
            h = N.history(con, pid, stat, d, 10)
            if len(h) < 8:
                continue
            line = round(sum(x["v"] for x in h) / len(h) - 0.5) + 0.5
            if line < MIN_LINE[stat]:
                continue
            p = N.predict(con, pid, stat, line, "over", before=d)
            if not p:
                continue
            a = con.execute("SELECT %s AS v FROM game_log WHERE player_id=? AND game_date=? AND game_id=?" % N.stat_expr(stat),
                            (pid, d, r["game_id"])).fetchone()["v"]
            if a == line:
                continue
            out.append(dict(date=d, gid=r["game_id"], team=r["team"], stat=stat, pa=p["p_win"], y=1.0 if a > line else 0.0, win=1.0 if r["wl"] == "W" else 0.0,
                            ut=u5 / max(u35, 1e-6) - 1, mt=m5 / max(m35, 1e-6) - 1, form=form))
    return out


def logloss(p, y):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def fit_logit(X, y, l2=1.0, iters=50):
    w = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-X @ w))
        g = X.T @ (p - y) + l2 * np.r_[0, w[1:]]
        H = (X * (p * (1 - p))[:, None]).T @ X + l2 * np.eye(X.shape[1])
        w -= np.linalg.solve(H, g)
    return w


def main():
    cut = sys.argv[1] if len(sys.argv) > 1 else "2026-02-15"
    con = N.conn(os.environ.get("NBA_DB", N.DEFAULT_DB))
    data = build(con)
    print("player-games priced: %d" % len(data))

    print("\nPART 1: over rate when his team wins vs loses (proxy lines)")
    for stat in STATS + ("ALL",):
        d = [x for x in data if stat == "ALL" or x["stat"] == stat]
        w = [x["y"] for x in d if x["win"]]
        l = [x["y"] for x in d if not x["win"]]
        pa = np.mean([x["pa"] for x in d])
        print("  %-4s n=%5d  model %4.1f%%  over|team W %4.1f%% (n=%d)  over|team L %4.1f%% (n=%d)  gap %+.1f"
              % (stat, len(d), pa * 100, np.mean(w) * 100, len(w), np.mean(l) * 100, len(l), (np.mean(w) - np.mean(l)) * 100))

    print("\nPART 2: Model B vs Model A, train up to %s, test after" % cut)
    tr = [x for x in data if x["date"] <= cut]
    te = [x for x in data if x["date"] > cut]
    if len(tr) < 500 or len(te) < 500:
        print("  not enough data for the split")
        return

    def mat(d, feats):
        pa = np.clip(np.array([x["pa"] for x in d]), 0.02, 0.98)
        cols = [np.ones(len(d)), np.log(pa / (1 - pa))] + [np.array([x[f] for x in d]) for f in feats]
        return np.column_stack(cols)

    ytr = np.array([x["y"] for x in tr])
    yte = np.array([x["y"] for x in te])
    pa_te = np.array([x["pa"] for x in te])
    print("  train n=%d  test n=%d" % (len(tr), len(te)))
    print("  Model A raw                  test log loss %.4f" % logloss(pa_te, yte))
    for name, feats in [("A recalibrated only", []), ("B + usage trend", ["ut"]), ("B + minutes trend", ["mt"]),
                        ("B + team form", ["form"]), ("B all three", ["ut", "mt", "form"])]:
        w = fit_logit(mat(tr, feats), ytr)
        p = 1 / (1 + np.exp(-mat(te, feats) @ w))
        print("  %-28s test log loss %.4f   weights %s" % (name, logloss(p, yte), np.round(w, 3).tolist()))
    print("  (a real gain would be about 0.001 or more; smaller is noise)")


if __name__ == "__main__":
    main()
