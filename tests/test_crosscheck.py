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
        # the wrong spike on 13.10, undone on 14.10, is one wrong close
        self.assertEqual(result.close_errors, [date(2026, 10, 13)])
        self.assertEqual(unexplained, [])
        self.assertIn(date(2026, 10, 16), explained)  # dividend: traded price fell, adjusted did not
        self.assertEqual(result.only_ours, [date(2026, 10, 15)])
        self.assertEqual(result.state, "fark var")

        text = crosscheck.format_report([result], "son 30 gün")
        self.assertIn("Hisseye özgü açıklanamayan fark 0 gün", text)
        self.assertIn("tek gün kapanış hatası (ertesi gün düzelen) 1", text)
        self.assertIn("yalnız Yahoo'da 1 gün: 15.10.2026", text)

    def test_gap_is_explained_only_by_a_recorded_corporate_action(self):
        # both sources are adjusted series: a one-sided gap is NOT assumed to be a dividend
        ours = frame([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
        theirs = frame([100.0, 101.0, 102.0, 98.0, 98.0 * 104 / 103, 98.0 * 105 / 103])

        unknown = crosscheck.compare("X.IS", ours, theirs)
        self.assertEqual(unknown.state, "fark var")
        self.assertEqual([d for d, *_ in unknown.unexplained], [date(2026, 10, 15)])

        recorded = crosscheck.compare("X.IS", ours, theirs, actions={date(2026, 10, 15)})
        self.assertEqual(recorded.state, "tutarlı")
        self.assertEqual(len(recorded.explained), 1)

    def test_unreachable_is_not_consistent(self):
        def broken(*a, **k):
            raise ConnectionError("kapalı")

        results = crosscheck.run(["THYAO.IS"], 30, today=date(2026, 10, 23), get=broken, bars=lambda s: frame([1.0]),
                                  sleep=lambda s: None)
        self.assertEqual([r.symbol for r in results], ["XU100.IS", "THYAO.IS"])
        self.assertEqual([r.state for r in results], ["kontrol edilemedi"] * 2)
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

    def test_benchmark_from_index_values(self):
        rows = [
            {"HGDG_TARIH": f"{d:02d}-10-2026", "HGDG_KAPANIS": 100.0 + d, "HGDG_MAX": 0, "HGDG_MIN": 0,
             "HGDG_AOF": 0, "HGDG_HACIM": 0, "END_DEGER": 1000.0 * (1.01 ** d)}
            for d in (12, 13, 14, 15, 16, 19)
        ]
        index = pd.bdate_range("2026-10-12", periods=6)
        stock = pd.DataFrame({"close": [100.0 + d for d in (12, 13, 14, 15, 16, 19)]}, index=index)
        bench = pd.DataFrame({"close": [1000.0 * (1.01 ** d) for d in (12, 13, 14, 15, 16, 19)]}, index=index)
        bench.iloc[3:] *= 0.96  # Yahoo's index misses a 4% move on 15.10

        results = crosscheck.run(["AAA.IS"], 30, today=date(2026, 10, 19), get=fake_get(rows),
                                 bars=lambda s: bench if s == "XU100.IS" else stock, sleep=lambda s: None)
        text = crosscheck.format_report(results, "test")

        self.assertIn("XU100 (İş Yatırım'ın BIST 100 değeriyle, 6 gün): 1 günde fark", text)
        self.assertIn("15.10.2026 Yahoo", text)
        self.assertIn(": 1 hisse |", text)  # the index is not counted as a stock

    def test_one_wrong_close_undone_next_day(self):
        theirs = frame([100.0, 90.0, 94.0, 95.0, 96.0, 97.0])  # real: -10% then +4.4%
        ours = theirs.copy()
        ours.iloc[1] = 96.0  # stored close taken before the drop, fixed the next day
        result = crosscheck.compare("GARAN.IS", ours, theirs)

        self.assertEqual(result.close_errors, [date(2026, 10, 13)])
        self.assertEqual(result.differences, [])
        self.assertEqual(result.state, "tutarlı")
        self.assertIn("tek gün kapanış hatası (ertesi gün düzelen) 1", crosscheck.format_report([result], "t"))

    def test_no_stored_prices(self):
        result = crosscheck.compare("KPOWR.IS", pd.DataFrame(), frame([1.0, 2.0, 3.0]))
        self.assertEqual(result.state, "kontrol edilemedi")
        self.assertIn("veri yok", result.error)

    def test_a_crashing_stock_does_not_stop_the_run(self):
        rows = [{"HGDG_TARIH": "12-10-2026", "HGDG_KAPANIS": 1.0, "HGDG_MAX": 1, "HGDG_MIN": 1,
                 "HGDG_AOF": 1, "HGDG_HACIM": 1}]

        def bars(symbol):
            if symbol == "BAD.IS":
                raise RuntimeError("bozuk")
            return frame([1.0])

        results = crosscheck.run(["BAD.IS", "OK.IS"], 30, today=date(2026, 10, 23), get=fake_get(rows),
                                 bars=bars, sleep=lambda s: None)
        self.assertEqual([r.symbol for r in results[1:]], ["BAD.IS", "OK.IS"])
        self.assertIn("karşılaştırma hatası", results[1].error)

    def test_source_down_stops_after_a_few_stocks(self):
        """İş Yatırım unreachable: 3 failed stocks in a row end the check instead of retrying every stock for hours."""

        calls = []

        def broken(*a, **k):
            calls.append(1)
            raise ConnectionError("zaman aşımı")

        symbols = [f"S{i}.IS" for i in range(100)]
        results = crosscheck.run(symbols, 30, today=date(2026, 10, 23), get=broken, bars=lambda s: frame([1.0]),
                                 sleep=lambda s: None)
        self.assertEqual(len(calls), crosscheck.SOURCE_DOWN_AFTER * crosscheck.RETRIES)
        self.assertEqual([r.symbol for r in results[1:]], symbols)  # every stock is still reported
        self.assertTrue(all(r.state == "kontrol edilemedi" for r in results))
        self.assertIn("ikinci kaynak yanıt vermiyor", results[-1].error)

    def test_one_failed_stock_does_not_stop_the_check(self):
        rows = [{"HGDG_TARIH": "12-10-2026", "HGDG_KAPANIS": 1.0, "HGDG_MAX": 1, "HGDG_MIN": 1,
                 "HGDG_AOF": 1, "HGDG_HACIM": 1}]
        ok = fake_get(rows)

        def flaky(url, params=None, **k):
            if params["hisse"] in ("A", "B"):
                raise ConnectionError("zaman aşımı")
            return ok(url, params, **k)

        results = crosscheck.run(["A.IS", "B.IS", "C.IS", "D.IS", "E.IS"], 30, today=date(2026, 10, 23), get=flaky,
                                 bars=lambda s: frame([1.0]), sleep=lambda s: None)
        self.assertEqual(len(ok.calls), 3)  # C, D, E were all asked
        self.assertNotIn("yanıt vermiyor", " ".join(r.error or "" for r in results))

    def test_inspect_shows_both_candles_around_the_day(self):
        """A flat O=H=L candle with the close outside: is our close right, or our high/low?"""

        rows = [
            {"HGDG_TARIH": "24-06-2022", "HGDG_KAPANIS": 7.00, "HGDG_MAX": 7.30, "HGDG_MIN": 6.90, "HGDG_AOF": 7.1,
             "HGDG_HACIM": 1e7},
            {"HGDG_TARIH": "27-06-2022", "HGDG_KAPANIS": 7.64, "HGDG_MAX": 7.70, "HGDG_MIN": 7.20, "HGDG_AOF": 7.5,
             "HGDG_HACIM": 2e7},
        ]
        index = pd.to_datetime(["2022-06-24", "2022-06-27"])
        ours = pd.DataFrame({"open": [7.0, 7.24], "high": [7.3, 7.24], "low": [6.9, 7.24], "close": [7.0, 7.64],
                             "volume": [1e6, 2e6]}, index=index)
        lines = crosscheck.inspect([("BIOEN.IS", date(2022, 6, 27))], get=fake_get(rows), bars=lambda s: ours,
                                   sleep=lambda s: None)
        text = "\n".join(lines)
        self.assertIn("BIOEN 27.06.2022", text)
        self.assertIn("kapanış aynı", text)  # 7.64 = 7.64: our close is right
        self.assertIn("bizde en yüksek/en düşük kapanışı kapsamıyor", text)
        self.assertIn("İş Yatırım  27.06.2022  —       7.70    7.20    7.64", text)

    def test_inspect_reports_a_different_close(self):
        rows = [{"HGDG_TARIH": "27-06-2022", "HGDG_KAPANIS": 5.70, "HGDG_MAX": 5.90, "HGDG_MIN": 5.60,
                 "HGDG_AOF": 5.8, "HGDG_HACIM": 1e7}]
        ours = pd.DataFrame({"open": [5.805], "high": [5.805], "low": [5.805], "close": [5.796], "volume": [1e6]},
                            index=pd.to_datetime(["2022-06-27"]))
        text = "\n".join(crosscheck.inspect([("BOBET.IS", date(2022, 6, 27))], get=fake_get(rows),
                                             bars=lambda s: ours, sleep=lambda s: None))
        self.assertIn("kapanış farklı (%+1.7)", text)

    def test_inspect_missing_day_shows_only_its_neighbourhood(self):
        """ADESE 08.02.2023 (cancelled session) is in neither source: show the days around it, not the whole history."""

        index = pd.bdate_range("2021-10-25", "2023-02-17")
        index = index[(index < "2023-02-08") | (index > "2023-02-14")]
        ours = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0}, index=index)
        lines = crosscheck.inspect([("ADESE.IS", date(2023, 2, 8))], get=fake_get([]), bars=lambda s: ours,
                                   sleep=lambda s: None)
        self.assertIn("o gün iki kaynakta da yok", lines[0])
        rows = [line for line in lines if line.startswith("  bizde")]
        self.assertEqual([r.split()[1] for r in rows], ["06.02.2023", "07.02.2023", "15.02.2023", "16.02.2023"])

    def test_inspect_survives_an_unreachable_source(self):
        def broken(*a, **k):
            raise ConnectionError("kapalı")

        text = "\n".join(crosscheck.inspect([("X.IS", date(2022, 6, 27))], get=broken, bars=lambda s: frame([1.0]),
                                             sleep=lambda s: None))
        self.assertIn("X 27.06.2022: ikinci kaynak alınamadı", text)

    def test_summary_for_the_accuracy_objective(self):
        ok = crosscheck.CrossCheck("A.IS", days=20)
        bad = crosscheck.CrossCheck("B.IS", days=20, differences=[(date(2026, 10, 20), 0.05, 0.01, False)])
        down = crosscheck.CrossCheck("C.IS", error="ConnectionError")
        index = crosscheck.CrossCheck("XU100.IS", days=20)
        crosscheck.format_report([index, ok, bad, down], "son 30 gün")  # marks market-wide days, as main does
        s = crosscheck.summary([index, ok, bad, down], date(2026, 10, 31))
        self.assertEqual(s["checked"], 2)  # stocks only; the unreachable one is not counted
        self.assertEqual(s["differing"], ["B"])
        self.assertEqual(s["unchecked"], ["C"])
        self.assertAlmostEqual(s["share"], 0.5)
        self.assertEqual(s["date"], "2026-10-31")

    def test_empty_second_source(self):
        result = crosscheck.compare("X.IS", frame([1.0, 2.0]), pd.DataFrame(columns=["close"]))
        self.assertEqual(result.state, "kontrol edilemedi")


if __name__ == "__main__":
    unittest.main()
