"""
K-80 (05.11.2026): the K-64 hourly forward test. Training sees only the frozen snapshot's events whose
label was known before HOLDOUT_START; the test sees only events from HOLDOUT_START up to the common end;
the K-64 rule (APPROVE, MIN_APPROVED, day bootstrap) is the frozen one; two downloads are combined by
the fixed table; a download failing the quality gate makes the result ÖLÇÜLEMEDİ.
"""

import unittest
from datetime import date, time
from unittest import mock

import numpy as np
import pandas as pd

from core.backtest.run import HOLDOUT_START
from core.ml import k64_forward as F
from core.ml import signal_filter as S

TZ = "Europe/Istanbul"
EDGE = HOLDOUT_START.tz_localize(TZ)


def rows(times, labels, ends=None):
    t = pd.DatetimeIndex(times).tz_localize(TZ) if pd.DatetimeIndex(times).tz is None else pd.DatetimeIndex(times)
    end = t + pd.Timedelta(days=2) if ends is None else pd.DatetimeIndex(ends).tz_localize(TZ)
    data = {f: np.linspace(0, 1, len(t)) for f in S.FEATURES}
    data.update(label=list(labels), label_end=end, symbol="AAA.IS", time=t, day=t.normalize())
    return pd.DataFrame(data)


class Fixed:
    """predict_proba returns the first feature (rsi column) as the probability."""

    def predict_proba(self, x):
        p = np.asarray(x)[:, 0]
        return np.column_stack([1 - p, p])


def session_frame(first: date, last: date, drop_last=0, drop_whole=(), zero=0) -> pd.DataFrame:
    from core.market.calendar import is_session_day, session_final

    stamps = []
    days = [d.date() for d in pd.bdate_range(first, last) if is_session_day(d.date())]
    for i, d in enumerate(days):
        if d in drop_whole:
            continue
        final = session_final(d)
        hours = [time(h, 30) for h in range(9, final.hour + 1)] if final.hour < 18 else \
            [time(h, 30) for h in range(9, 18)]
        if i < drop_last:
            hours = hours[:-1]
        stamps += [pd.Timestamp.combine(d, h) for h in hours]
    idx = pd.DatetimeIndex(stamps).tz_localize(TZ)
    vol = np.full(len(idx), 1000.0)
    vol[:zero] = 0
    return pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": vol}, index=idx)


class TrainTest(unittest.TestCase):
    def test_training_reads_nothing_from_the_holdout(self):
        seen = {}
        data = rows(["2026-10-01 10:30", "2026-10-29 10:30", "2026-10-30 10:30"], [1, 0, 1],
                    ends=["2026-10-02 10:30", "2026-10-30 17:30", "2026-11-03 10:30"])

        def fake_events(frames, x, y, members, before):
            seen.update(x=x, y=y, members=members, before=before)
            return data

        def make(train):
            seen["train"] = train
            return "model", {"max_depth": 4}

        with mock.patch.object(S, "events", fake_events):
            model, params, n = F.train_model({"AAA.IS": None}, make=make)
        self.assertEqual((seen["x"], seen["y"]), S.SPEC["saatlik"])
        self.assertIsNone(seen["members"])
        self.assertEqual(seen["before"], EDGE)
        self.assertEqual(n, 2)  # the event whose label ends after the edge is dropped
        self.assertTrue((seen["train"]["label_end"] < EDGE).all())
        self.assertEqual((model, params), ("model", {"max_depth": 4}))


class ForwardTest(unittest.TestCase):
    def run_forward(self, data, end=date(2027, 2, 2)):
        with mock.patch.object(S, "events", return_value=data) as ev:
            r = F.forward(Fixed(), {"AAA.IS": None}, end, {"max_depth": 4})
        return r, ev

    def test_only_events_inside_the_forward_window_count(self):
        data = rows(["2026-10-30 10:30", "2026-11-02 10:30", "2027-01-15 10:30", "2027-02-01 15:30"],
                    [1, 1, 0, 1],
                    ends=["2026-11-02 10:30", "2026-11-03 10:30", "2027-01-16 10:30", "2027-02-03 10:30"])
        r, ev = self.run_forward(data)
        self.assertEqual(r.events, 2)  # before the holdout: out; label ending after the common end: out
        self.assertEqual(ev.call_args.kwargs["before"], pd.Timestamp("2027-02-03").tz_localize(TZ))
        self.assertEqual(r.params, {"max_depth": 4})

    def test_k64_rule_with_frozen_constants(self):
        n = 200
        times = pd.date_range("2026-11-02 10:30", periods=n, freq="D")
        labels = ([1] * 3 + [0]) * (n // 4)
        data = rows(times, labels)
        data["rsi"] = np.where(np.arange(n) % 4 < 3, 0.9, 0.1)  # approve the 3-of-4 that hit
        r, _ = self.run_forward(data, end=date(2027, 12, 31))
        self.assertEqual(r.approved, 150)
        self.assertEqual(r.hits, 150)
        self.assertAlmostEqual(r.base_rate, 0.75)
        self.assertGreaterEqual(r.approved, S.MIN_APPROVED)
        self.assertTrue(r.passed, r.reason)

    def test_too_few_approvals_fail_like_k64(self):
        data = rows(pd.date_range("2026-11-02 10:30", periods=40, freq="D"), [1] * 40)
        data["rsi"] = 0.9
        r, _ = self.run_forward(data, end=date(2027, 12, 31))
        self.assertFalse(r.passed)
        self.assertIn(f"< {S.MIN_APPROVED}", r.reason)

    def test_threshold_is_the_frozen_approve(self):
        data = rows(pd.date_range("2026-11-02 10:30", periods=2, freq="D"), [1, 1])
        data["rsi"] = [S.APPROVE, S.APPROVE - 1e-9]
        r, _ = self.run_forward(data, end=date(2027, 12, 31))
        self.assertEqual(r.approved, 1)

    def test_no_events(self):
        r, _ = self.run_forward(rows([], []))
        self.assertEqual(r.events, 0)
        self.assertFalse(r.passed)


class QualityTest(unittest.TestCase):
    first, last = date(2026, 11, 2), date(2027, 2, 2)

    def test_complete_download_passes(self):
        q = F.quality({"A": session_frame(self.first, self.last)}, self.first, self.last)
        self.assertTrue(q.passed, q.reason)
        self.assertEqual((q.last_missing, q.short_sessions, q.empty_sessions, q.zero_volume), (0, 0, 0, 0))

    def test_each_threshold_fails_the_gate(self):
        n = len([d for d in pd.bdate_range(self.first, self.last)])
        bad = {
            "son mum": session_frame(self.first, self.last, drop_last=int(n * 0.10)),
            "mumsuz": session_frame(self.first, self.last, drop_whole=(date(2026, 11, 3),)),
            "hacmi 0": session_frame(self.first, self.last, zero=200),
        }
        for word, frame in bad.items():
            q = F.quality({"A": frame}, self.first, self.last)
            self.assertFalse(q.passed, word)
            self.assertIn(word, q.reason)

    def test_small_gaps_inside_the_limits_pass(self):
        q = F.quality({"A": session_frame(self.first, self.last, drop_last=2, zero=10)}, self.first, self.last)
        self.assertTrue(q.passed, q.reason)

    def test_zero_volume_opening_candle_does_not_close_the_gate(self):
        frame = session_frame(self.first, self.last)
        frame.loc[frame.index.time == time(9, 30), "volume"] = 0.0
        q = F.quality({"A": frame}, self.first, self.last)
        self.assertTrue(q.passed, q.reason)
        self.assertEqual((q.zero_volume, q.open_zero_volume), (0, 1))

    def test_zero_volume_in_other_hours_still_closes_the_gate(self):
        frame = session_frame(self.first, self.last)
        frame.loc[frame.index.time == time(12, 30), "volume"] = 0.0
        q = F.quality({"A": frame}, self.first, self.last)
        self.assertFalse(q.passed)
        self.assertIn("hacmi 0", q.reason)

    def test_half_day_last_candle_is_1130(self):
        from core.market.calendar import is_session_day, session_final

        halves = [d.date() for d in pd.bdate_range("2022-01-01", "2027-12-31")
                  if is_session_day(d.date()) and session_final(d.date()).hour < 18]
        if not halves:
            self.skipTest("no half day in the calendar")
        d = halves[0]
        q = F.quality({"A": session_frame(d, d)}, d, d)
        self.assertTrue(q.passed, q.reason)


class VerdictTest(unittest.TestCase):
    ok, bad = F.Quality(passed=True), F.Quality(passed=False)

    def test_table(self):
        yes, no = F.Result(passed=True), F.Result(passed=False)
        self.assertEqual(F.verdict(self.ok, yes, self.ok, yes), F.PASSED)
        self.assertEqual(F.verdict(self.ok, yes, self.ok, no), F.SENSITIVE)
        self.assertEqual(F.verdict(self.ok, no, self.ok, yes), F.SENSITIVE)
        self.assertEqual(F.verdict(self.ok, no, self.ok, no), F.FAILED)

    def test_reason_separates_a_small_sample_from_no_edge(self):
        few, many = F.Result(approved=13), F.Result(approved=60)
        self.assertIn("örneklem yetersiz", F.verdict_reason(F.FAILED, few, many))
        self.assertIn("ayırt edilemiyor", F.verdict_reason(F.FAILED, many, many))
        self.assertEqual(F.verdict_reason(F.PASSED, many, many), "")
        self.assertEqual(F.verdict_reason(F.UNMEASURED, None, many), "")

    def test_a_download_failing_the_gate_is_not_replaced(self):
        yes = F.Result(passed=True)
        self.assertEqual(F.verdict(self.bad, None, self.ok, yes), F.UNMEASURED)
        self.assertEqual(F.verdict(self.ok, yes, self.bad, None), F.UNMEASURED)

    def test_dates(self):
        self.assertEqual(F.check_dates(date(2027, 2, 3), date(2027, 2, 10), date(2027, 2, 2)), [])
        self.assertTrue(F.check_dates(date(2027, 2, 2), date(2027, 2, 10), date(2027, 2, 1)))
        self.assertTrue(F.check_dates(date(2027, 2, 3), date(2027, 2, 9), date(2027, 2, 2)))
        self.assertTrue(F.check_dates(date(2027, 2, 3), date(2027, 2, 10), date(2027, 2, 3)))


class MainTest(unittest.TestCase):
    def test_wrong_training_snapshot_or_dates_stop(self):
        import tempfile
        from contextlib import redirect_stdout
        from io import StringIO
        from pathlib import Path

        from core.analytics import provenance as P
        from tests.test_provenance import frames

        with tempfile.TemporaryDirectory() as tmp:
            P.freeze(frames(), Path(tmp) / "a", None)
            base = ["--egitim", str(Path(tmp) / "a"), "--test1", "x", "--test2", "y"]
            with redirect_stdout(StringIO()) as out:
                self.assertEqual(F.main([*base, "--indirme1", "2027-02-03", "--indirme2", "2027-02-05",
                                         "--son", "2027-02-02"]), 2)
                self.assertIn("tarih kuralı", out.getvalue())
                self.assertEqual(F.main([*base, "--indirme1", "2027-02-03", "--indirme2", "2027-02-10",
                                         "--son", "2027-02-02"]), 2)
                self.assertIn("A değil", out.getvalue())


if __name__ == "__main__":
    unittest.main()
