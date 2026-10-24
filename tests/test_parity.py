"""The dashboard (JavaScript) and the CLI (Python) must give the same probabilities.
Run:  python -m unittest discover tests
"""
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import nba_edge as ne  # noqa: E402


class Parity(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_js_matches_python(self):
        tmp = tempfile.mkdtemp()
        try:
            db = os.path.join(tmp, "demo.db")
            ne.cmd_demo(type("A", (), {"db": db})())
            ex = type("A", (), {"db": db, "outdir": os.path.join(tmp, "out"), "logs": 40, "active_days": 200})()
            ne.cmd_export(ex)
            con = ne.conn(db)
            ctx, boost = ne.compute_ctx(con), ne.compute_boost(con)
            self.assertTrue(ctx, "demo data should be enough to fit the context effects")
            self.assertTrue(boost, "demo data should produce teammate splits")
            random.seed(3)
            players = [r["player_id"] for r in con.execute("SELECT DISTINCT player_id FROM game_log")]
            teams = sorted({r["opp"] for r in con.execute("SELECT DISTINCT opp FROM game_log")})
            cases = []
            for _ in range(400):
                pid = random.choice(players)
                stat = random.choice(["pts", "reb", "ast", "3pm", "pra", "pr", "pa", "ra", "stl", "min"])
                mu = con.execute("SELECT AVG(%s) FROM game_log WHERE player_id=? AND mins>=5" % ne.stat_expr(stat), (pid,)).fetchone()[0] or 1
                mates = list(boost.get(pid, {}))
                mode = random.choice(["none", "empty", "some"])
                outs = None if mode == "none" else ([] if mode == "empty" or not mates else random.sample(mates, random.randint(1, min(2, len(mates)))))
                cases.append(dict(player_id=pid, stat=stat, line=max(round(mu) + random.choice([-1, -0.5, 0, 0.5, 1.5]), 0.5),
                                  side=random.choice(["over", "under"]), opp=random.choice(teams + [""]),
                                  exp_min=random.choice([None, None, 20, 32]),
                                  spread=random.choice([None, -11.5, -2, 4.5, 14]), total=random.choice([None, 214.5, 238]), outs=outs))
            first = con.execute("SELECT MIN(game_date) FROM game_log").fetchone()[0]
            offsets = [-2, 0, 3, 6, 7, 10, 20, 21, 40]
            for c in cases:
                c["on_date"] = (date.fromisoformat(first) + timedelta(days=random.choice(offsets))).isoformat()
            ne.EARLY_ON, ne.EARLY_START = True, first
            mp = os.path.join(ex.outdir, "meta.json")
            meta = json.load(open(mp))
            meta["early"] = {"on": True, "steps": ne.EARLY_STEPS, "start": first}
            json.dump(meta, open(mp, "w"))
            cf = os.path.join(tmp, "cases.json")
            json.dump(cases, open(cf, "w"))
            js = json.loads(subprocess.check_output(["node", os.path.join(ROOT, "tests", "parity.js"), ex.outdir, cf]))
            worst, with_outs = 0.0, 0
            for c, j in zip(cases, js):
                py = ne.predict(con, c["player_id"], c["stat"], c["line"], c["side"], opp=c["opp"] or None, exp_min=c["exp_min"],
                                spread=c["spread"], total=c["total"], outs=c["outs"], ctx=ctx, boost=boost, on_date=c["on_date"])
                self.assertEqual(py is None, j is None, c)
                if py:
                    with_outs += bool(c["outs"])
                    worst = max(worst, abs(py["p_win"] - j["pWin"]), abs(py["p_push"] - j["pPush"]))
                    self.assertAlmostEqual(py["mu"], j["mu"], delta=2e-3 * max(1.0, py["mu"]), msg=str(c))  # export rounds minutes to 0.1
            self.assertGreater(with_outs, 20, "test should exercise the teammate-out path")
            self.assertLess(worst, 2e-3, "JS and Python probabilities drifted apart")
            print("worst probability difference JS vs Python: %.2e over %d cases (%d with teammates out)" % (worst, len(cases), with_outs))
        finally:
            ne.EARLY_ON, ne.EARLY_START = False, None
            shutil.rmtree(tmp, ignore_errors=True)

    def test_early_season_switch(self):
        tmp = tempfile.mkdtemp()
        try:
            db = os.path.join(tmp, "demo.db")
            ne.cmd_demo(type("A", (), {"db": db})())
            con = ne.conn(db)
            first = con.execute("SELECT MIN(game_date) FROM game_log").fetchone()[0]
            pid = con.execute("SELECT player_id FROM game_log LIMIT 1").fetchone()[0]
            day = lambda n: (date.fromisoformat(first) + timedelta(days=n)).isoformat()
            off = ne.predict(con, pid, "pts", 12.5, "over", on_date=day(1))["p_win"]
            offu = ne.predict(con, pid, "pts", 12.5, "under", on_date=day(1))["p_win"]
            try:
                ne.EARLY_ON, ne.EARLY_START = True, first
                self.assertAlmostEqual(ne.predict(con, pid, "pts", 12.5, "over", on_date=day(1))["p_win"], off - 0.05, places=6)
                self.assertAlmostEqual(ne.predict(con, pid, "pts", 12.5, "under", on_date=day(1))["p_win"], offu + 0.05, places=6)
                self.assertAlmostEqual(ne.predict(con, pid, "pts", 12.5, "over", on_date=day(10))["p_win"],
                                       ne.predict(con, pid, "pts", 12.5, "over", on_date=day(60))["p_win"] - 0.01, places=6)
            finally:
                ne.EARLY_ON, ne.EARLY_START = False, None
            self.assertAlmostEqual(ne.predict(con, pid, "pts", 12.5, "over", on_date=day(1))["p_win"], off, places=9)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
