import tempfile
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

from core.market import membership as m

D = date.fromisoformat


class RealChangeLogTest(unittest.TestCase):
    """The committed change log must be internally consistent."""

    def test_alternates_and_has_sources(self):
        events = m.load_changes()  # raises on a missing source or a repeated add/remove
        self.assertGreater(len(events), 100)

    def test_changing_part_has_constant_size(self):
        events = m.load_changes()
        sizes = m.check_sizes(events, stable=set())
        self.assertEqual(set(sizes.values()), {m.INDEX_SIZE - len(m.load_stable())})


class CommittedStableListTest(unittest.TestCase):
    def test_membership_is_100_on_every_date(self):
        events = m.load_changes()
        stable = m.load_stable()
        self.assertEqual(len(stable), 47)
        self.assertEqual(set(m.check_sizes(events, stable).values()), {m.INDEX_SIZE})

    def test_sizes_cover_the_day_before_the_first_change(self):
        events = m.load_changes()
        first = min(d for ev in events.values() for d, _ in ev)
        self.assertEqual(first, D("2020-10-01"))
        sizes = m.check_sizes(events, m.load_stable())
        self.assertIn(D("2020-09-30"), sizes)
        self.assertIn(D("2021-04-01"), sizes)

    def test_q4_2020_sise_merger(self):
        # 14118: TRKCM, ANACM, SODA left on 01.10.2020 (Şişecam merger); AKSGY came in
        events = m.load_changes()
        stable = m.load_stable()
        before = m.members_on(D("2020-09-30"), events, stable)
        after = m.members_on(D("2020-10-01"), events, stable)
        self.assertTrue({"TRKCM", "ANACM", "SODA"} <= before)
        self.assertFalse({"TRKCM", "ANACM", "SODA"} & after)
        self.assertIn("AKSGY", after - before)

    def test_off_cycle_change_june_2026(self):
        events = m.load_changes()
        stable = m.load_stable()
        self.assertIn("KONTR", m.members_on(D("2026-06-17"), events, stable))
        self.assertNotIn("KONTR", m.members_on(D("2026-06-18"), events, stable))
        self.assertIn("BERA", m.members_on(D("2026-06-18"), events, stable))


class SyntheticTest(unittest.TestCase):
    def setUp(self):
        self.events = {
            "AAA": [(D("2023-01-02"), "add")],
            "BBB": [(D("2023-01-02"), "remove")],
            "CCC": [(D("2023-01-02"), "add"), (D("2024-01-02"), "remove")],
            "DDD": [(D("2024-01-02"), "add")],
        }

    def test_members_on(self):
        stable = {"STB"}
        self.assertEqual(m.members_on(D("2022-06-01"), self.events, stable), {"STB", "BBB"})
        self.assertEqual(m.members_on(D("2023-06-01"), self.events, stable), {"STB", "AAA", "CCC"})
        self.assertEqual(m.members_on(D("2024-06-01"), self.events, stable), {"STB", "AAA", "DDD"})

    def test_panel(self):
        idx = pd.DatetimeIndex(["2022-12-30", "2023-01-02", "2024-01-02"])
        panel = m.membership_panel(idx, ["AAA.IS", "BBB.IS", "STB.IS", "XXX.IS"], self.events, {"STB"})
        self.assertEqual(panel["AAA.IS"].tolist(), [False, True, True])
        self.assertEqual(panel["BBB.IS"].tolist(), [True, False, False])
        self.assertEqual(panel["STB.IS"].tolist(), [True, True, True])
        self.assertFalse(panel["XXX.IS"].any())

    def test_repeated_action_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.csv"
            path.write_text(
                "effective_date,symbol,action,source\n2023-01-02,AAA,add,x\n2024-01-02,AAA,add,x\n",
                encoding="utf-8",
            )
            with self.assertRaises(m.MembershipError):
                m.load_changes(path)

    def test_alias(self):
        self.assertEqual(m._code("KOZAL.IS"), "TRALT")
        self.assertEqual(m._code("eforc"), "EFOR")


class StableFromCurrentTest(unittest.TestCase):
    def test_wrong_list_is_refused(self):
        events = m.load_changes()
        dynamic = m.dynamic_members(events, D("2026-10-23"))
        stable_guess = [f"S{i:03d}" for i in range(m.INDEX_SIZE - len(dynamic))]
        good = sorted(dynamic) + stable_guess
        stable = m.stable_from_current(good, events, D("2026-10-23"))
        self.assertEqual(len(stable), len(stable_guess))
        # a list missing a current dynamic member, or containing a removed stock, is refused
        broken = good[1:] + ["SKBNK"]  # SKBNK left the index on 2026-10-01
        with self.assertRaises(m.MembershipError):
            m.stable_from_current(broken, events, D("2026-10-23"))
        with self.assertRaises(m.MembershipError):
            m.stable_from_current(good[:-1], events, D("2026-10-23"))


if __name__ == "__main__":
    unittest.main()
