import unittest
from datetime import date

from signal_check import flip_email, month_ends, states


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

    def test_flip_email_names_both_accounts(self):
        subject, body = flip_email(("2026-08", -0.005, False), ("2026-09", 0.012, True))
        self.assertIn("RSP", subject)
        self.assertIn("sell SPY, buy RSP", body)
        self.assertIn("Sell nothing", body)


if __name__ == "__main__":
    unittest.main()
