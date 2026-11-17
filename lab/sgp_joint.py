#!/usr/bin/env python3
"""Lab experiment 6: price "player over + team moneyline" same-game legs jointly instead of independently.

Method: team win chance w from the closing spread (normal, sd SD). A stat's over chance splits as
P(over) = w*a + (1-w)*b with a - b = GAP[stat] (fitted on games up to TRAIN_END). Given the live model's pA:
b = pA - w*GAP, a = b + GAP. Then P(over and team wins) = w*a, P(over and team loses) = (1-w)*b.
Scored against the independent version (pA*w, pA*(1-w)) by log loss on games after TRAIN_END that have a closing spread.
Usage: python lab/sgp_joint.py [TRAIN_END]   (needs numpy; reads only)
"""
import os, sys, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import nba_edge as N
import second_model as S

SDS = (10, 12, 14, 16, 18, 20)


def phi(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def main():
    cut = sys.argv[1] if len(sys.argv) > 1 else "2026-02-15"
    con = N.conn(os.environ.get("NBA_DB", N.DEFAULT_DB))
    sp = {r["game_id"]: (r["home"], r["spread"]) for r in con.execute("SELECT game_id, home, spread FROM games WHERE spread IS NOT NULL")}
    data = [x for x in S.build(con) if x["gid"] in sp]
    for x in data:
        home, s = sp[x["gid"]]
        x["s"] = s if x["team"] == home else -s        # spread from the player's team view (negative = favorite)
    print("player-games with a closing spread: %d" % len(data))
    tr = [x for x in data if x["date"] <= cut]
    te = [x for x in data if x["date"] > cut]
    # pick SD by team-win log loss on train
    best = None
    for sd in SDS:
        ll = S.logloss(np.array([phi(-x["s"] / sd) for x in tr]), np.array([x["win"] for x in tr]))
        print("  SD %d: team-win log loss %.4f" % (sd, ll))
        if best is None or ll < best[0]:
            best = (ll, sd)
    sd = best[1]
    print("using SD %d" % sd)
    gap = {}
    for stat in S.STATS:
        d = [x for x in tr if x["stat"] == stat]
        gap[stat] = np.mean([x["y"] for x in d if x["win"]]) - np.mean([x["y"] for x in d if not x["win"]])
    print("gap by stat (train):", {k: round(float(v), 3) for k, v in gap.items()})
    res = {"indep": [], "joint": []}
    ev = {"indep": [], "joint": []}
    for x in te:
        w = phi(-x["s"] / sd)
        pa = min(max(x["pa"], 0.02), 0.98)
        b = min(max(pa - w * gap[x["stat"]], 0.01), 0.97)
        a = min(b + gap[x["stat"]], 0.99)
        y_win = x["y"] * x["win"]
        y_lose = x["y"] * (1 - x["win"])
        for k, (pw, pl) in (("indep", (pa * w, pa * (1 - w))), ("joint", (w * a, (1 - w) * b))):
            ev[k].append((pw, y_win))
            ev[k].append((pl, y_lose))
    print("\nTEST after %s: %d player-games, %d events (over&team wins, over&team loses)" % (cut, len(te), len(ev["indep"])))
    for k in ("indep", "joint"):
        p = np.array([e[0] for e in ev[k]]); y = np.array([e[1] for e in ev[k]])
        print("  %-6s log loss %.4f   avg predicted %.3f   actual %.3f" % (k, S.logloss(p, y), p.mean(), y.mean()))
    # calibration by bucket for the case that matters: over AND opposing/own side result
    for k in ("indep", "joint"):
        p = np.array([e[0] for e in ev[k]]); y = np.array([e[1] for e in ev[k]])
        print("  %s calibration (predicted -> actual):" % k, end=" ")
        qs = np.quantile(p, [0, .25, .5, .75, 1])
        for i in range(4):
            m = (p >= qs[i]) & (p <= qs[i + 1])
            print("%.2f->%.2f" % (p[m].mean(), y[m].mean()), end="  ")
        print()


if __name__ == "__main__":
    main()
