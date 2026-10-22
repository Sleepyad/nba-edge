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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import nba_edge as ne  # noqa: E402


class Parity(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_js_matches_python(self):
        tmp = tempfile.mkdtemp()
        try:
            db = os.path.join(tmp, "demo.db")
            ap = type("A", (), {"db": db})()
            ne.cmd_demo(ap)
            ex = type("A", (), {"db": db, "outdir": os.path.join(tmp, "out"), "logs": 40, "active_days": 200})()
            ne.cmd_export(ex)
            con = ne.conn(db)
            random.seed(3)
            players = [r["player_id"] for r in con.execute("SELECT DISTINCT player_id FROM game_log")]
            teams = sorted({r["opp"] for r in con.execute("SELECT DISTINCT opp FROM game_log")})
            cases = []
            for _ in range(250):
                pid = random.choice(players)
                stat = random.choice(["pts", "reb", "ast", "3pm", "pra", "pr", "stl"])
                mu = con.execute("SELECT AVG(%s) FROM game_log WHERE player_id=? AND mins>=5" % ne.stat_expr(stat), (pid,)).fetchone()[0] or 1
                line = round(mu) + random.choice([-1, -0.5, 0, 0.5, 1.5])
                cases.append(dict(player_id=pid, stat=stat, line=max(line, 0.5), side=random.choice(["over", "under"]),
                                  opp=random.choice(teams + [""]), exp_min=random.choice([None, None, 20, 32])))
            cf = os.path.join(tmp, "cases.json")
            json.dump(cases, open(cf, "w"))
            js = json.loads(subprocess.check_output(["node", os.path.join(ROOT, "tests", "parity.js"), ex.outdir, cf]))
            worst = 0.0
            for c, j in zip(cases, js):
                py = ne.predict(con, c["player_id"], c["stat"], c["line"], c["side"], opp=c["opp"] or None, exp_min=c["exp_min"])
                self.assertEqual(py is None, j is None, c)
                if py:
                    worst = max(worst, abs(py["p_win"] - j["pWin"]), abs(py["p_push"] - j["pPush"]))
                    self.assertAlmostEqual(py["mu"], j["mu"], delta=1e-3 * max(1.0, py["mu"]), msg=str(c))  # export rounds minutes to 0.1
            self.assertLess(worst, 1e-3, "JS and Python probabilities drifted apart")
            print("worst probability difference JS vs Python: %.2e over %d cases" % (worst, len(cases)))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
