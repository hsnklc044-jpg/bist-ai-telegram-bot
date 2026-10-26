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
            crosscheck.fetch_isyatirim("THYAO", date(2026, 10, 12), date(2026, 10, 14), get=fake_get(ok=False))


class CompareTest(unittest.TestCase):
    def test_scaled_but_consistent(self):
        # dividend-adjusted Yahoo closes: same returns, different level
        ours = frame([90.0, 90.9, 91.8, 92.7, 93.6])
        theirs = frame([100.0, 101.0, 102.0, 103.0, 104.0])
        result = crosscheck.compare("THYAO.IS", ours, theirs)
        self.assertEqual((result.state, result.days), ("tutarlı", 5))
        self.assertIn("karşılaştırılan 5 hisse-gün", crosscheck.format_report([result], 30))

    def test_wrong_day_missing_day_and_known_action(self):
        ours = frame([100.0, 108.0, 102.0, 103.0, 103.0, 104.0, 105.0])  # 13.10 wrong
        # traded price: 15.10 missing, 16.10 ex-dividend drop (Yahoo's adjusted series has none)
        theirs = frame([100.0, 101.0, 102.0, 103.0, 98.0, 98.0 * 104 / 103, 98.0 * 105 / 103])
        theirs = theirs.drop(pd.Timestamp("2026-10-15"))

        result = crosscheck.compare("THYAO.IS", ours, theirs, actions={date(2026, 10, 16)})
        days = [d for d, *_ in result.differences]
        self.assertIn(date(2026, 10, 13), days)
        self.assertEqual(result.only_ours, [date(2026, 10, 15)])
        self.assertTrue(any(known for *_, known in result.differences))
        self.assertEqual(result.state, "fark var")

        text = crosscheck.format_report([result], 30)
        self.assertIn("13.10 Yahoo", text)
        self.assertIn("kayıtlı şirket işlemi", text)
        self.assertIn("yalnız Yahoo'da: 15.10", text)

    def test_unreachable_is_not_consistent(self):
        def broken(*a, **k):
            raise ConnectionError("kapalı")

        results = crosscheck.run(["THYAO.IS"], 30, today=date(2026, 10, 23), get=broken, bars=lambda s: frame([1.0]))
        self.assertEqual(results[0].state, "kontrol edilemedi")
        self.assertIn("kontrol edilemedi 1", crosscheck.format_report(results, 30))

    def test_no_common_days_is_not_consistent(self):
        ours = frame([1.0, 2.0, 3.0], start="2026-09-01")
        theirs = frame([1.0, 2.0, 3.0], start="2026-10-12")
        result = crosscheck.compare("X.IS", ours, theirs)
        self.assertEqual(result.state, "kontrol edilemedi")
        self.assertIn("ortak gün 0", result.error)

    def test_empty_second_source(self):
        result = crosscheck.compare("X.IS", frame([1.0, 2.0]), pd.DataFrame(columns=["close"]))
        self.assertEqual(result.state, "kontrol edilemedi")


if __name__ == "__main__":
    unittest.main()
