import unittest
from datetime import date

from render import chart_rows, flip_html, run_length
from signal_check import BAND, CAP, EQUAL, flip_email, month_ends, states


def series(monthly_returns: list[float]) -> dict[str, float]:
    out, v = {}, 100.0
    for i, r in enumerate(monthly_returns):
        v *= 1 + r
        out[f"{2010 + i // 12}-{i % 12 + 1:02d}"] = v
    return out


class Signal(unittest.TestCase):
    def test_month_ends_takes_last_close_and_drops_current_month(self):
        daily = [("2026-07-30", 1.0), ("2026-07-31", 2.0), ("2026-08-29", 3.0), ("2026-09-02", 4.0)]
        self.assertEqual(month_ends(daily, date(2026, 9, 3)), {"2026-07": 2.0, "2026-08": 3.0})

    def test_band_holds_state_inside_one_point(self):
        cap = series([0.01] * 40)
        # equal leads by a hair, then trails by a hair: never past the band
        eq = series([0.01] * 12 + [0.0105] * 6 + [0.0095] * 22)
        hist = states(cap, eq)
        self.assertTrue(all(s == hist[0][2] for _, _, s in hist))

    def test_flips_past_the_band_both_ways(self):
        cap = series([0.01] * 48)
        eq = series([0.0] * 12 + [0.03] * 12 + [0.0] * 24)
        seq = [s for _, _, s in states(cap, eq)]
        self.assertEqual(seq[0], False)
        self.assertIn(True, seq)
        self.assertEqual(seq[-1], False)
        flips = sum(a != b for a, b in zip(seq, seq[1:]))
        self.assertEqual(flips, 2)

    def test_flip_email_switches_ira_and_leaves_taxable(self):
        subject, body, _ = flip_email(("2026-08", -0.005, False), ("2026-09", 0.012, True))
        self.assertIn("RSP", subject)
        self.assertIn("sell SPY, buy RSP", body)
        self.assertIn("Taxable:               nothing. Stay in SPY", body)


class Render(unittest.TestCase):
    def hist(self):
        cap, eq = series([0.01] * 48), series([0.0] * 12 + [0.03] * 12 + [0.0] * 24)
        return states(cap, eq)

    def test_run_length_counts_back_to_the_last_flip(self):
        held, began = run_length(self.hist())
        self.assertGreater(held, 0)
        self.assertRegex(began, r"^\d{4}-\d{2}$")

    def test_chart_bars_stay_inside_their_half(self):
        rows = chart_rows(self.hist())
        self.assertEqual(len(rows), 36)
        for r in rows:
            self.assertEqual(r["width"] + r["pad"], r["half"])
            self.assertGreaterEqual(r["width"], 2)
        self.assertNotEqual(rows[-1]["label"], "")

    def test_html_carries_both_actions_and_no_script(self):
        hist = self.hist()
        html = flip_html(hist[-2], hist[-1], hist, CAP, EQUAL, BAND)
        self.assertIn("IRA", html)
        self.assertIn(f"buy <b>{CAP if not hist[-1][2] else EQUAL}</b>", html)
        self.assertIn("do nothing", html)
        self.assertNotIn("<script", html)
        self.assertNotIn("{{", html)


if __name__ == "__main__":
    unittest.main()
