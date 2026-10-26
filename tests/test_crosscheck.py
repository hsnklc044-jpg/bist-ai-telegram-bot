import unittest
from datetime import date

import pandas as pd

from core.market import crosscheck


def frame(closes, start="2026-10-12"):
    index = pd.bdate_range(start, periods=len(closes))
    return pd.DataFrame({"close": closes}, index=index, dtype=float)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def fake_get(rows=None, ok=True):
    calls = []

    def get(url, params=None, headers=None, timeout=None):
        calls.append(params)
        return FakeResponse({"ok": ok, "errorDescription": None if ok else "bozuk", "value": rows or []})

    get.calls = calls
    return get


ROWS = [  # unsorted, as the service returns them
    {"HGDG_TARIH": "14-10-2026", "HGDG_KAPANIS": 102.0, "HGDG_MAX": 103, "HGDG_MIN": 100, "HGDG_AOF": 101.5, "HGDG_HACIM": 1e9},
    {"HGDG_TARIH": "12-10-2026", "HGDG_KAPANIS": 100.0, "HGDG_MAX": 101, "HGDG_MIN": 99, "HGDG_AOF": 100.2, "HGDG_HACIM": 1e9},
    {"HGDG_TARIH": "13-10-2026", "HGDG_KAPANIS": 101.0, "HGDG_MAX": 102, "HGDG_MIN": 99, "HGDG_AOF": 100.8, "HGDG_HACIM": 1e9},
]


class FetchTest(unittest.TestCase):
    def test_parses_and_sorts(self):
        get = fake_get(ROWS)
        df = crosscheck.fetch_isyatirim("THYAO", date(2026, 10, 12), date(2026, 10, 14), get=get)

        self.assertEqual(list(df["close"]), [100.0, 101.0, 102.0])
        self.assertEqual(get.calls[0], {"hisse": "THYAO", "startdate": "12-10-2026", "enddate": "14-10-2026"})

    def test_service_error_raises(self):
        with self.assertRaises(ValueError):
            crosscheck.fetch_isyatirim("THYAO", date(2026, 10, 12), date(2026, 10, 14), get=fake_get(ok=False),
                                      sleep=lambda s: None)


class CompareTest(unittest.TestCase):
    def test_scaled_but_consistent(self):
        # dividend-adjusted Yahoo closes: same returns, different level
        ours = frame([90.0, 90.9, 91.8, 92.7, 93.6])
        theirs = frame([100.0, 101.0, 102.0, 103.0, 104.0])
        result = crosscheck.compare("THYAO.IS", ours, theirs)
        self.assertEqual((result.state, result.days), ("tutarlı", 5))
        self.assertIn("karşılaştırılan 5 hisse-gün", crosscheck.format_report([result], "son 30 gün"))

    def test_wrong_day_missing_day_and_known_action(self):
        ours = frame([100.0, 108.0, 102.0, 103.0, 103.0, 104.0, 105.0])  # 13.10 wrong
        # traded price: 15.10 missing, 16.10 ex-dividend drop (Yahoo's adjusted series has none)
        theirs = frame([100.0, 101.0, 102.0, 103.0, 98.0, 98.0 * 104 / 103, 98.0 * 105 / 103])
        theirs = theirs.drop(pd.Timestamp("2026-10-15"))

        result = crosscheck.compare("THYAO.IS", ours, theirs, actions={date(2026, 10, 16)})
        unexplained = [d for d, *_ in result.unexplained]
        explained = [d for d, *_ in result.explained]
        # the wrong spike (13.10, up) is caught on the day it reverses (14.10, down)
        self.assertEqual(unexplained, [date(2026, 10, 14)])
        self.assertIn(date(2026, 10, 16), explained)  # dividend: traded price fell, adjusted did not
        self.assertEqual(result.only_ours, [date(2026, 10, 15)])
        self.assertEqual(result.state, "fark var")

        text = crosscheck.format_report([result], "son 30 gün")
        self.assertIn("Hisseye özgü açıklanamayan fark 1 gün", text)
        self.assertIn("14.10.2026 Yahoo", text)
        self.assertIn("yalnız Yahoo'da 1 gün: 15.10.2026", text)

    def test_dividend_only_is_consistent(self):
        ours = frame([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
        theirs = frame([100.0, 101.0, 102.0, 98.0, 98.0 * 104 / 103, 98.0 * 105 / 103])
        result = crosscheck.compare("X.IS", ours, theirs)
        self.assertEqual(result.state, "tutarlı")
        self.assertEqual(len(result.explained), 1)

    def test_unreachable_is_not_consistent(self):
        def broken(*a, **k):
            raise ConnectionError("kapalı")

        results = crosscheck.run(["THYAO.IS"], 30, today=date(2026, 10, 23), get=broken, bars=lambda s: frame([1.0]),
                                  sleep=lambda s: None)
        self.assertEqual(results[0].state, "kontrol edilemedi")
        self.assertIn("kontrol edilemedi 1", crosscheck.format_report(results, "son 30 gün"))

    def test_no_common_days_is_not_consistent(self):
        ours = frame([1.0, 2.0, 3.0], start="2026-09-01")
        theirs = frame([1.0, 2.0, 3.0], start="2026-10-12")
        result = crosscheck.compare("X.IS", ours, theirs)
        self.assertEqual(result.state, "kontrol edilemedi")
        self.assertIn("ortak gün 0", result.error)

    def test_market_wide_days_are_separated(self):
        theirs = frame([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
        ours = theirs.copy()
        ours.iloc[3:] *= 0.97  # every stock 3% lower from the 4th day: a source-level issue
        results = [crosscheck.compare(f"S{i}.IS", ours, theirs) for i in range(5)]
        odd = ours.copy()
        odd.iloc[4:] *= 0.9  # one stock also has its own error
        results.append(crosscheck.compare("ODD.IS", odd, theirs))

        text = crosscheck.format_report(results, "test")
        self.assertIn("15.10.2026: 6 hisse", text)
        self.assertEqual([r.state for r in results[:5]], ["tutarlı"] * 5)
        self.assertEqual(results[5].state, "fark var")
        self.assertIn("ODD: 16.10.2026", text)

    def test_long_range_in_yearly_pieces_with_retry(self):
        calls, failures = [], [1]

        def get(url, params=None, headers=None, timeout=None):
            calls.append((params["startdate"], params["enddate"]))
            if failures:
                failures.pop()
                raise TimeoutError("yavaş")
            return FakeResponse({"ok": True, "value": []})

        crosscheck.fetch_isyatirim("THYAO", date(2022, 1, 1), date(2024, 6, 30), get=get, sleep=lambda s: None)
        starts = [c[0] for c in calls]
        self.assertEqual(starts[0], starts[1])  # the timed-out piece was retried
        self.assertEqual(len(set(starts)), 3)  # 2.5 years -> 3 pieces
        self.assertEqual(calls[-1][1], "30-06-2024")

    def test_empty_second_source(self):
        result = crosscheck.compare("X.IS", frame([1.0, 2.0]), pd.DataFrame(columns=["close"]))
        self.assertEqual(result.state, "kontrol edilemedi")


if __name__ == "__main__":
    unittest.main()
