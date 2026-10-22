#!/usr/bin/env python3
"""Claude's paper-trading log for nba-edge. Imaginary money, real record.

Why it exists: AD logs his own bets (private, in his own database). This file keeps a SEPARATE public log
of picks the model and Claude make, so we can see how they do, miss by miss, and compare line moves.

Two sources of bets:
  rule    picked automatically by a fixed rule each day (no human judgment, so it is an honest baseline)
  claude  picked by Claude with a written reason (so we can test whether judgment adds anything)
  book    a real sportsbook line AD gave us, priced by the model

Until real prop lines are available, "rule" bets use a PROXY LINE: the player's last-10-game average rounded
to the nearest x.5, which is roughly where books anchor. That tests whether the model's extra inputs
(40-game weighting, opponent, teammates out, spread, total) beat plain recent form. It does NOT test the book.

Data (committed, append-friendly): data/paper_bets.csv, data/fair_lines.csv
Commands: snapshot, auto, bet, settle, report, moves
"""
import argparse
import csv
import math
import os
import sys
from datetime import date, timedelta

import nba_edge as N

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("PAPER_DIR", os.path.join(HERE, "data"))
BETS = os.path.join(DATA, "paper_bets.csv")
FAIR = os.path.join(DATA, "fair_lines.csv")
BET_COLS = ["id", "placed", "game_date", "ticket", "source", "player_id", "player", "team", "opp", "stat",
            "side", "line", "odds", "model_p", "reason", "status", "actual"]
FAIR_COLS = ["captured", "game_date", "player_id", "player", "team", "opp", "stat", "line", "p_over", "flux"]
STATS = ("pts", "reb", "ast", "3pm")
THRESH = 0.57       # model confidence needed for an automatic pick
CAP = 0.68          # above this the real book would price it heavily, so a flat -110 would flatter the model
MIN_LINE = {"pts": 9.5, "reb": 3.5, "ast": 2.5, "3pm": 1.5}  # smaller lines are not real prop markets
MAX_SINGLES = 6
STAKE = 1.0         # units
ODDS = -110


# ----------------------------------------------------------------------------- csv helpers
def read_csv(path, cols):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path, cols, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def dec(odds):
    odds = int(odds)
    return 1 + (odds / 100.0 if odds > 0 else 100.0 / -odds)


# ----------------------------------------------------------------------------- tonight's slate
def slate(day):
    """Games on this ET date: [{home, away, spread, total, state, ids:{abbr:teamid}}]"""
    j = N.http_json("%s/scoreboard?dates=%s&limit=100" % (N.ESPN, day.strftime("%Y%m%d")))
    out = []
    for e in j.get("events", []):
        c = e["competitions"][0]
        t = {x["homeAway"]: x["team"] for x in c["competitors"]}
        odds = (c.get("odds") or [None])[0]
        out.append(dict(home=t["home"]["abbreviation"], away=t["away"]["abbreviation"],
                        ids={t["home"]["abbreviation"]: t["home"]["id"], t["away"]["abbreviation"]: t["away"]["id"]},
                        spread=N.home_spread(odds) if odds else None, total=odds.get("overUnder") if odds else None,
                        state=e["status"]["type"]["state"]))
    return out


def roster_names(team_id):
    j = N.http_json("%s/teams/%s/roster" % (N.ESPN, team_id))
    return [a["displayName"] for a in j.get("athletes", [])]


def injury_map():
    m = {}
    for t in N.http_json(N.ESPN + "/injuries").get("injuries", []):
        for e in t.get("injuries", []):
            a = e.get("athlete") or {}
            ab = (a.get("team") or {}).get("abbreviation")
            m.setdefault(ab, []).append((N.norm(a.get("displayName", "")), e.get("status")))
    return m


def pid_of(con, name):
    r = con.execute("SELECT player_id FROM game_log WHERE pnorm=? ORDER BY game_date DESC LIMIT 1", (N.norm(name),)).fetchone()
    return r["player_id"] if r else None


def team_pool(con, abbr, team_id, inj):
    """Rostered players for a team, split into regulars and newcomers (changed teams recently)."""
    regulars, newcomers = [], []
    out_ids = []
    for nm in roster_names(team_id):
        pid = pid_of(con, nm)
        if not pid:
            continue
        status = dict(inj.get(abbr, [])).get(N.norm(nm))
        if status == "Out":
            out_ids.append(pid)
            continue
        m10 = con.execute("SELECT AVG(mins) a FROM (SELECT mins FROM game_log WHERE player_id=? AND mins>=5 "
                          "ORDER BY game_date DESC LIMIT 10)", (pid,)).fetchone()["a"] or 0
        with_team = con.execute("SELECT COUNT(*) c FROM game_log WHERE player_id=? AND team=? AND mins>=5",
                                (pid, abbr)).fetchone()["c"]
        item = (m10, pid, nm, with_team, status)
        if m10 >= 20 and with_team < 15:
            newcomers.append(item)
        elif m10 >= 20:
            regulars.append(item)
    regulars.sort(reverse=True)
    return regulars[:7], newcomers, out_ids


def proxy_line(con, pid, stat):
    h = N.history(con, pid, stat, None, 10)
    if len(h) < 5:
        return None
    mean = sum(r["v"] for r in h) / len(h)
    return round(mean - 0.5) + 0.5


def build_rows(con, day, only_pre=True):
    ctx, boost = N.compute_ctx(con), N.compute_boost(con)
    inj = injury_map()
    rows = []
    for g in slate(day):
        if only_pre and g["state"] != "pre":
            continue
        for abbr, opp in ((g["home"], g["away"]), (g["away"], g["home"])):
            regs, news, out_ids = team_pool(con, abbr, g["ids"][abbr], inj)
            flux = ",".join(n[2] for n in news)
            for m10, pid, nm, wt, st in regs:
                for stat in STATS:
                    line = proxy_line(con, pid, stat)
                    if line is None or line < MIN_LINE[stat]:
                        continue
                    r = N.predict(con, pid, stat, line, "over", opp=opp, spread=g["spread"], total=g["total"],
                                  outs=[o for o in out_ids if o != pid], ctx=ctx, boost=boost)
                    if not r:
                        continue
                    rows.append(dict(captured=date.today().isoformat(), game_date=day.isoformat(), player_id=pid,
                                     player=nm, team=abbr, opp=opp, stat=stat, line=line,
                                     p_over=round(r["p_win"], 4), flux=flux))
    return rows


# ----------------------------------------------------------------------------- commands
def cmd_snapshot(args):
    con = N.conn(args.db)
    day = date.fromisoformat(args.date) if args.date else N.et_today()
    rows = build_rows(con, day)
    old = [r for r in read_csv(FAIR, FAIR_COLS) if not (r["captured"] == date.today().isoformat() and r["game_date"] == day.isoformat())]
    write_csv(FAIR, FAIR_COLS, old + rows)
    print("snapshot: %d model lines for %s" % (len(rows), day))


def next_id(bets):
    return max([int(b["id"]) for b in bets] + [0]) + 1


def cmd_auto(args):
    con = N.conn(args.db)
    day = date.fromisoformat(args.date) if args.date else N.et_today()
    bets = read_csv(BETS, BET_COLS)
    if any(b["source"] == "rule" and b["game_date"] == day.isoformat() for b in bets):
        print("rule picks for %s already logged" % day)
        return
    rows = [r for r in build_rows(con, day) if not r["flux"]]
    picks = []
    for r in rows:
        p = float(r["p_over"])
        side, conf = ("over", p) if p >= 0.5 else ("under", 1 - p)
        if THRESH <= conf <= CAP:
            picks.append((conf, side, r))
    picks.sort(key=lambda x: -x[0])
    seen, chosen = set(), []
    for conf, side, r in picks:
        k = (r["player_id"], r["stat"])
        if k in seen:
            continue
        if sum(1 for c in chosen if c[2]["player_id"] == r["player_id"]) >= 1:  # one stat per player
            continue
        seen.add(k)
        chosen.append((conf, side, r))
        if len(chosen) >= MAX_SINGLES:
            break
    if not chosen:
        print("no pick cleared %.0f%% for %s (flux teams skipped)" % (THRESH * 100, day))
        return
    i = next_id(bets)
    ticket = "R-%s" % day
    for rank, (conf, side, r) in enumerate(chosen):
        bets.append(dict(id=i, placed=date.today().isoformat(), game_date=day.isoformat(),
                         ticket=ticket if rank < 3 else "", source="rule", player_id=r["player_id"], player=r["player"],
                         team=r["team"], opp=r["opp"], stat=r["stat"], side=side, line=r["line"], odds=ODDS,
                         model_p=round(conf, 4), reason="auto: model %.0f%% vs proxy line" % (conf * 100),
                         status="pending", actual=""))
        i += 1
        print("%-22s %-3s %-5s %s %s  model %.1f%%%s" % (r["player"], r["stat"], side, r["line"], r["opp"], conf * 100,
                                                     "  [in parlay]" if rank < 3 else ""))
    write_csv(BETS, BET_COLS, bets)
    cmd_snapshot(args)


def cmd_bet(args):
    con = N.conn(args.db)
    stat = N.stat_key(args.stat)
    p = N.find_player(con, args.name)
    pid = p["player_id"]
    side = "under" if args.side.lower().startswith("u") else "over"
    lc = N.live_context(con, pid)
    res = N.predict(con, pid, stat, args.line, side, opp=lc["opp"], spread=lc["spread"], total=lc["total"],
                    outs=[i for i, _, _ in lc["outs"] if i and i != pid], ctx=N.compute_ctx(con), boost=N.compute_boost(con))
    if not res:
        N.die("not enough games for %s" % p["player"])
    bets = read_csv(BETS, BET_COLS)
    bets.append(dict(id=next_id(bets), placed=date.today().isoformat(), game_date=args.date or lc["date"] or N.et_today().isoformat(),
                     ticket=args.ticket or "", source=args.source, player_id=pid, player=p["player"], team=lc["team"],
                     opp=lc["opp"] or "", stat=stat, side=side, line=args.line, odds=args.odds,
                     model_p=round(res["p_win"], 4), reason=args.reason or "", status="pending", actual=""))
    write_csv(BETS, BET_COLS, bets)
    print("logged #%s: %s %s %s %s  model %.1f%%  (%s)" % (bets[-1]["id"], p["player"], stat, side, args.line, res["p_win"] * 100, args.source))


def cmd_settle(args):
    con = N.conn(args.db)
    bets = read_csv(BETS, BET_COLS)
    today = N.et_today()
    n = 0
    for b in bets:
        if b["status"] != "pending":
            continue
        row = con.execute("SELECT %s AS v, mins FROM game_log WHERE player_id=? AND game_date=?" % N.stat_expr(b["stat"]),
                          (b["player_id"], b["game_date"])).fetchone()
        if not row:
            if date.fromisoformat(b["game_date"]) < today - timedelta(days=2):
                b["status"], n = "void", n + 1  # never played, or no box score
            continue
        v, line = row["v"], float(b["line"])
        b["actual"] = v
        if v == line:
            b["status"] = "push"
        elif (v > line) == (b["side"] == "over"):
            b["status"] = "win"
        else:
            b["status"] = "lose"
        n += 1
    write_csv(BETS, BET_COLS, bets)
    print("settled %d bet(s); %d still pending" % (n, sum(1 for b in bets if b["status"] == "pending")))


def ticket_result(legs):
    live = [l for l in legs if l["status"] in ("win", "lose", "push", "void")]
    if any(l["status"] == "pending" for l in legs):
        return None
    if any(l["status"] == "lose" for l in legs):
        return -STAKE
    ws = [l for l in legs if l["status"] == "win"]
    if not ws:
        return 0.0
    return STAKE * (math.prod(dec(l["odds"]) for l in ws) - 1)


def cmd_report(args):
    bets = read_csv(BETS, BET_COLS)
    done = [b for b in bets if b["status"] in ("win", "lose")]
    print("paper bets: %d logged, %d settled, %d pending\n" % (len(bets), len(done), sum(1 for b in bets if b["status"] == "pending")))
    if not done:
        return

    def block(title, key):
        groups = {}
        for b in done:
            groups.setdefault(key(b), []).append(b)
        print(title)
        for k, g in sorted(groups.items()):
            w = sum(1 for b in g if b["status"] == "win")
            exp = sum(float(b["model_p"]) for b in g) / len(g)
            units = sum((dec(b["odds"]) - 1) if b["status"] == "win" else -1 for b in g)
            print("  %-10s %3d bets  won %5.1f%%  model said %5.1f%%  units %+.2f" % (k, len(g), 100.0 * w / len(g), exp * 100, units))
        print()

    block("by source", lambda b: b["source"])
    block("by side", lambda b: b["side"])
    block("by stat", lambda b: b["stat"])
    block("by confidence", lambda b: "%d-%d%%" % (int(float(b["model_p"]) * 20) * 5, int(float(b["model_p"]) * 20) * 5 + 5))
    tk = {}
    for b in bets:
        if b["ticket"]:
            tk.setdefault(b["ticket"], []).append(b)
    if tk:
        print("tickets")
        for t, legs in sorted(tk.items()):
            r = ticket_result(legs)
            print("  %-14s %d legs  %s" % (t, len(legs), "pending" if r is None else "%+.2f units" % r))
        print()
    misses = [b for b in done if b["status"] == "lose"][-8:]
    if misses:
        print("recent misses")
        for b in misses:
            print("  %s %s %s %s %s: got %s (model %.0f%%)  %s" % (b["game_date"], b["player"], b["stat"], b["side"], b["line"],
                                                                 b["actual"], float(b["model_p"]) * 100, b["reason"]))
    print("\nThis is the model against a proxy line, not a sportsbook. Read groups only with 30+ bets.")


def cmd_moves(args):
    rows = read_csv(FAIR, FAIR_COLS)
    caps = sorted({r["captured"] for r in rows})
    if len(caps) < 2:
        print("need two snapshot days to compare; have %d" % len(caps))
        return
    a, b = caps[-2], caps[-1]
    old = {(r["player_id"], r["stat"]): r for r in rows if r["captured"] == a}
    out = []
    for r in rows:
        if r["captured"] != b:
            continue
        o = old.get((r["player_id"], r["stat"]))
        if o and o["line"] != r["line"]:
            out.append((float(r["line"]) - float(o["line"]), r, o))
    out.sort(key=lambda x: -abs(x[0]))
    print("proxy-line moves %s -> %s" % (a, b))
    for d, r, o in out[:20]:
        print("  %-22s %-3s %5s -> %5s  (%+.1f)" % (r["player"], r["stat"], o["line"], r["line"], d))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=N.DEFAULT_DB)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("snapshot", "auto"):
        s = sub.add_parser(name)
        s.add_argument("--date", help="ET game date YYYY-MM-DD (default today)")
    s = sub.add_parser("bet")
    s.add_argument("name")
    s.add_argument("stat")
    s.add_argument("side")
    s.add_argument("line", type=float)
    s.add_argument("--odds", type=int, default=ODDS)
    s.add_argument("--reason", default="")
    s.add_argument("--ticket", default="")
    s.add_argument("--source", default="claude", choices=["claude", "book", "rule"])
    s.add_argument("--date")
    sub.add_parser("settle")
    sub.add_parser("report")
    sub.add_parser("moves")
    args = ap.parse_args()
    {"snapshot": cmd_snapshot, "auto": cmd_auto, "bet": cmd_bet, "settle": cmd_settle,
     "report": cmd_report, "moves": cmd_moves}[args.cmd](args)


if __name__ == "__main__":
    main()
