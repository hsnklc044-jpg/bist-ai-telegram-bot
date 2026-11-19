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
        full = m.load_changes(full_history=True)
        sizes = m.check_sizes(full, stable=set())
        self.assertEqual(set(sizes.values()), {m.INDEX_SIZE - len(m.load_stable(full_history=True))})


class CommittedStableListTest(unittest.TestCase):
    def test_membership_is_100_on_every_date(self):
        for full in (False, True):
            events = m.load_changes(full_history=full)
            stable = m.load_stable(full_history=full)
            self.assertEqual(len(stable), 47 if full else 50)
            self.assertEqual(set(m.check_sizes(events, stable).values()), {m.INDEX_SIZE})

    def test_sizes_cover_the_day_before_the_first_change(self):
        events = m.load_changes(full_history=True)
        first = min(d for ev in events.values() for d, _ in ev)
        self.assertEqual(first, D("2020-10-01"))
        sizes = m.check_sizes(events, m.load_stable(full_history=True))
        self.assertIn(D("2020-09-30"), sizes)
        self.assertIn(D("2021-04-01"), sizes)

    def test_q4_2020_sise_merger(self):
        # 14118: TRKCM, ANACM, SODA left on 01.10.2020 (ÅiÅŸecam merger); AKSGY came in
        before = m.members_on(D("2020-09-30"), full_history=True)
        after = m.members_on(D("2020-10-01"), full_history=True)
        self.assertTrue({"TRKCM", "ANACM", "SODA"} <= before)
        self.assertFalse({"TRKCM", "ANACM", "SODA"} & after)
        self.assertIn("AKSGY", after - before)

    def test_off_cycle_change_june_2021(self):
        # KAP 942442 (15.06.2021): BAGFS to Yakin Izleme Pazari, ECZYT (1st reserve) in from 16.06.2021
        before = m.members_on(D("2021-06-15"), full_history=True)
        after = m.members_on(D("2021-06-16"), full_history=True)
        self.assertIn("BAGFS", before - after)
        self.assertIn("ECZYT", after - before)

    def test_off_cycle_change_june_2026(self):
        events = m.load_changes()
        stable = m.load_stable()
        self.assertIn("KONTR", m.members_on(D("2026-06-17"), events, stable))
        self.assertNotIn("KONTR", m.members_on(D("2026-06-18"), events, stable))
        self.assertIn("BERA", m.members_on(D("2026-06-18"), events, stable))


OLD = Path(__file__).parent / "fixtures" / "bist100_2022"


class DefaultEqualsOldFilesTest(unittest.TestCase):
    """Rows before COVERAGE_START are opt-in: by default every result equals the 2022-04 files."""

    def setUp(self):
        self.old_events = m.load_changes(OLD / "bist100_changes.csv")
        self.old_stable = m.load_stable(OLD / "bist100_stable.csv", changes_path=OLD / "bist100_changes.csv")

    def test_coverage_start(self):
        self.assertEqual(m.COVERAGE_START, D("2022-04-01"))

    def test_ever_members(self):
        old = m.ever_members(self.old_events, self.old_stable)
        self.assertEqual(len(old), 202)
        self.assertEqual(m.ever_members(), old)
        self.assertGreater(len(m.ever_members(full_history=True)), 202)

    def test_members_on(self):
        for day in ("2020-06-01", "2021-06-01", "2022-03-31", "2022-04-01", "2024-01-02", "2026-11-02"):
            with self.subTest(day=day):
                self.assertEqual(m.members_on(D(day)), m.members_on(D(day), self.old_events, self.old_stable))

    def test_loaders_and_panel(self):
        self.assertEqual(m.load_changes(), self.old_events)
        self.assertEqual(m.load_stable(), self.old_stable)
        idx = pd.DatetimeIndex(["2021-06-01", "2022-03-31", "2022-04-01", "2026-11-02"])
        symbols = ["ENKAI.IS", "BAGFS.IS", "ECZYT.IS", "AKSGY.IS", "ARASE.IS"]
        pd.testing.assert_frame_equal(
            m.membership_panel(idx, symbols), m.membership_panel(idx, symbols, self.old_events, self.old_stable)
        )

    def test_full_history_differs_before_coverage(self):
        self.assertNotIn("ENKAI", m.members_on(D("2021-06-01"), full_history=True))
        self.assertIn("ENKAI", m.members_on(D("2021-06-01")))


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
