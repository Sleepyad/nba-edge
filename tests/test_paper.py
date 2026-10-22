import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paper


class PaperTests(unittest.TestCase):
    def leg(self, status, odds=-110):
        return dict(status=status, odds=odds)

    def test_decimal_odds(self):
        self.assertAlmostEqual(paper.dec(-110), 1.9091, places=3)
        self.assertAlmostEqual(paper.dec(150), 2.5)

    def test_ticket_all_win(self):
        r = paper.ticket_result([self.leg("win"), self.leg("win")])
        self.assertAlmostEqual(r, 1.9091 ** 2 - 1, places=3)

    def test_ticket_one_loss_loses(self):
        self.assertEqual(paper.ticket_result([self.leg("win"), self.leg("lose")]), -1.0)

    def test_ticket_void_leg_dropped(self):
        r = paper.ticket_result([self.leg("win"), self.leg("void")])
        self.assertAlmostEqual(r, 0.9091, places=3)

    def test_ticket_pending(self):
        self.assertIsNone(paper.ticket_result([self.leg("win"), self.leg("pending")]))


if __name__ == "__main__":
    unittest.main()
