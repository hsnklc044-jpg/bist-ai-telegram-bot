"""
Talimat C (DECISIONS K-51): nominal / real (TÜFE) / USD / cash returns. Every number here can be
checked by hand, and a CPI value is never visible before the day after TÜİK published it.
"""

import tempfile
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

from core.market import macro

CPI_HEADER = "period,monthly_pct,annual_pct,published,published_note\n"


class Files(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def cpi(self, *rows):
        path = self.dir / "cpi.csv"
        path.write_text("# yorum\n" + CPI_HEADER + "".join(rows), encoding="utf-8")
        return macro.load_cpi(path)


class CpiTest(Files):
    def test_known_only_from_the_day_after_publication(self):
        cpi = self.cpi("2026-08,2.00,30.0,2026-09-03,x\n", "2026-09,1.00,29.0,2026-10-05,x\n")
        self.assertEqual(macro.cpi_known(cpi, date(2026, 10, 5)).period, "2026-08")  # published 10:00 that day
        self.assertEqual(macro.cpi_known(cpi, date(2026, 10, 6)).period, "2026-09")
        self.assertIsNone(macro.cpi_known(cpi, date(2026, 9, 3)))  # nothing known yet

    def test_chained_index(self):
        cpi = self.cpi("2026-08,2.00,30.0,2026-09-03,x\n", "2026-09,1.00,29.0,2026-10-05,x\n")
        a = macro.cpi_known(cpi, date(2026, 9, 10))
        b = macro.cpi_known(cpi, date(2026, 10, 10))
        self.assertAlmostEqual(b.index / a.index, 1.01)

    def test_real_return_by_hand(self):
        cpi = self.cpi("2026-08,2.00,30.0,2026-09-03,x\n", "2026-09,1.00,29.0,2026-10-05,x\n")
        # nominal +5% while known CPI rose 1%: real = 1.05 / 1.01 - 1
        real = macro.real_return(0.05, date(2026, 9, 10), date(2026, 10, 10), cpi)
        self.assertAlmostEqual(real, 1.05 / 1.01 - 1)
        # inside one month nothing new is published: real equals nominal (no estimate)
        self.assertAlmostEqual(macro.real_return(0.05, date(2026, 9, 10), date(2026, 9, 30), cpi), 0.05)
        self.assertIsNone(macro.real_return(0.05, date(2026, 8, 1), date(2026, 9, 30), cpi))  # start unknown

    def test_one_year_by_hand(self):
        rows = [f"2025-{m:02d},1.00,0,2025-{m + 1:02d}-03,x\n" for m in range(1, 12)]
        rows += ["2025-12,1.00,0,2026-01-05,x\n"]
        cpi = self.cpi(*rows)
        # 12 months of +1% from the start (Jan known) to the end (Dec known): 1.01 ** 11
        real = macro.real_return(0.20, date(2025, 2, 10), date(2026, 1, 10), cpi)
        self.assertAlmostEqual(real, 1.20 / 1.01 ** 11 - 1)

    def test_repository_file(self):
        cpi = macro.load_cpi()
        self.assertGreaterEqual(len(cpi), 60)
        self.assertTrue((cpi["published"] > cpi.index.map(lambda p: pd.Timestamp(p + "-28"))).all())
        # the chained 12 months match TÜİK's published annual change (parse check), within rounding
        for period in ("2023-12", "2024-12", "2025-12", "2026-09"):
            with self.subTest(period=period):
                i = cpi.index.get_loc(period)
                chained = (1 + cpi["monthly_pct"].iloc[i - 11:i + 1] / 100).prod() - 1
                self.assertAlmostEqual(chained * 100, cpi["annual_pct"].iloc[i], delta=0.15)
        self.assertEqual(cpi.loc["2022-04", "published"], pd.Timestamp("2022-05-05"))  # bayram
        self.assertEqual(cpi.loc["2026-05", "published"], pd.Timestamp("2026-06-05"))

    def test_bad_rows_refused(self):
        with self.assertRaises(ValueError):
            self.cpi("2026-08,2.00,30.0,2026-08-15,x\n")  # published before the month ended


BULLETIN = """<?xml version="1.0" encoding="UTF-8"?>
<Tarih_Date Tarih="27.10.2026" Date="10/27/2026" Bulten_No="2026/203">
<Currency CrossOrder="0" Kod="USD" CurrencyCode="USD"><Unit>1</Unit><ForexBuying>49.6997</ForexBuying>
<ForexSelling>49.7892</ForexSelling></Currency>
<Currency CrossOrder="1" Kod="EUR" CurrencyCode="EUR"><Unit>1</Unit><ForexBuying>57.1</ForexBuying></Currency>
</Tarih_Date>"""


class Response:
    def __init__(self, status, text=""):
        self.status_code, self.content = status, text.encode("utf-8")


class UsdTest(Files):
    def test_bulletin(self):
        self.assertEqual(macro.parse_bulletin(BULLETIN.encode("utf-8")), (date(2026, 10, 27), 49.6997))

    def test_url(self):
        self.assertEqual(macro.bulletin_url(date(2022, 1, 3)), "https://www.tcmb.gov.tr/kurlar/202201/03012022.xml")

    def test_fill_cache_only_missing_weekdays(self):
        path = self.dir / "usdtry.csv"
        asked = []

        def get(url, **_):
            asked.append(url)
            if url.endswith("28102026.xml"):
                return Response(404)  # half day: no bulletin
            return Response(200, BULLETIN.replace("27.10.2026", "26.10.2026" if "26102026" in url else "27.10.2026"))

        added = macro.update_usdtry(date(2026, 10, 24), date(2026, 10, 28), path=path, get=get, sleep=lambda s: None)
        self.assertEqual(added, 3)  # 26, 27, 28 (the 404 is remembered too); 24-25 is a weekend
        self.assertEqual(len(asked), 3)
        rates = macro.load_usdtry(path)
        self.assertEqual(list(rates.index.date), [date(2026, 10, 26), date(2026, 10, 27)])
        macro.update_usdtry(date(2026, 10, 24), date(2026, 10, 28), path=path, get=get, sleep=lambda s: None)
        self.assertEqual(len(asked), 3)  # nothing is asked twice

    def test_cap(self):
        path = self.dir / "usdtry.csv"
        added = macro.update_usdtry(date(2026, 10, 1), date(2026, 10, 28), path=path, limit=2,
                                    get=lambda url, **_: Response(404), sleep=lambda s: None)
        self.assertEqual(added, 2)

    def test_time_budget_keeps_what_was_fetched(self):
        # the weekly research must never run out of time on this step (29.10.2026: ~1,6 s per bulletin)
        path = self.dir / "usdtry.csv"
        clock = iter([0, *range(0, 1000, 10)])  # the start, then each request "takes" 10 seconds
        added = macro.update_usdtry(date(2026, 10, 1), date(2026, 10, 28), path=path, budget=25,
                                    get=lambda url, **_: Response(404), sleep=lambda s: None,
                                    clock=lambda: next(clock))
        self.assertEqual(added, 3)  # 0, 10, 20 s: the fourth would start after the budget
        self.assertEqual(len(macro._cache(path)), 3)  # and they are saved

    def test_progress_is_saved_in_chunks(self):
        path = self.dir / "usdtry.csv"
        seen = []

        def get(url, **_):
            seen.append(len(macro._cache(path)))
            return Response(404)

        macro.update_usdtry(date(2026, 1, 1), date(2026, 6, 30), path=path, get=get, sleep=lambda s: None)
        self.assertIn(macro.SAVE_EVERY, seen)  # written to disk while still running

    def test_network_error_is_not_remembered(self):
        path = self.dir / "usdtry.csv"

        def get(url, **_):
            raise OSError("offline")

        self.assertEqual(macro.update_usdtry(date(2026, 10, 26), date(2026, 10, 27), path=path, get=get,
                                             sleep=lambda s: None), 0)
        self.assertFalse(path.exists() and macro.load_usdtry(path).size)

    def test_a_stale_rate_is_never_used(self):
        # research 29.10.2026: a half-filled cache made the END rate months old (USD +383% instead of ~+56%)
        rates = pd.Series([13.42, 18.70], index=pd.to_datetime(["2022-01-03", "2023-02-28"]))
        self.assertIsNone(macro.usd_on(rates, date(2026, 10, 27)))
        self.assertIsNone(macro.usd_return(4.788, date(2022, 1, 3), date(2026, 10, 27), rates))
        self.assertEqual(macro.usd_on(rates, date(2023, 3, 9)), 18.70)  # a 9-day holiday gap is still fine
        self.assertIsNone(macro.usd_on(rates, date(2023, 3, 13)))

    def test_usd_return_by_hand(self):
        rates = pd.Series([40.0, 44.0], index=pd.to_datetime(["2026-01-02", "2026-06-01"]))
        # +21% in TL while USD/TRY rose 10%: in USD 1.21 / 1.10 - 1 = +10%
        self.assertAlmostEqual(macro.usd_return(0.21, date(2026, 1, 2), date(2026, 6, 3), rates), 0.10)
        self.assertIsNone(macro.usd_return(0.21, date(2025, 12, 1), date(2026, 6, 3), rates))


class FourBasisTest(Files):
    def test_line(self):
        cpi = self.cpi("2026-08,2.00,30.0,2026-09-03,x\n", "2026-09,1.00,29.0,2026-10-05,x\n")
        rates = pd.Series([40.0, 44.0], index=pd.to_datetime(["2026-09-10", "2026-10-10"]))

        class Cash:
            def growth(self, prev_day, day):
                from core.backtest.cash import CashGrowth

                return CashGrowth(1.03)

        result = macro.four_basis(0.10, date(2026, 9, 10), date(2026, 10, 10), cpi=cpi, usd=rates, cash=Cash())
        self.assertAlmostEqual(result.real, 1.10 / 1.01 - 1)
        self.assertAlmostEqual(result.usd, 1.10 / 1.10 - 1)
        self.assertAlmostEqual(result.cash, 1.10 / 1.03 - 1)
        line = result.line()
        self.assertIn("nominal +%10,0", line)
        self.assertIn("reel +%8,9", line)
        self.assertIn("TÜFE 09.2026'ya kadar, tahmin yok", line)
        self.assertIn("USD +%0,0", line)
        self.assertIn("nakde göre +%6,8", line)

    def test_unknown_parts_say_so(self):
        result = macro.four_basis(0.10, date(2026, 9, 10), date(2026, 10, 10), cpi=macro.load_cpi(self.dir / "x.csv"),
                                  usd=pd.Series(dtype=float), cash=None)
        self.assertIsNone(result.real)
        self.assertIn("reel: TÜFE yok", result.line())
        self.assertIn("USD: kur yok", result.line())

    def test_cash_series_that_starts_later_says_so(self):
        class Cash:
            def growth(self, prev_day, day):
                from core.backtest.cash import CashGrowth

                return CashGrowth(1.5, missing_days=10)

        result = macro.four_basis(0.10, date(2022, 1, 3), date(2026, 10, 27), cpi=macro.load_cpi(),
                                  usd=pd.Series(dtype=float), cash=Cash())
        self.assertIsNone(result.cash)
        self.assertIn("nakde göre: faiz serisi dönemin başını kapsamıyor", result.line())


TCMB_PAGE = """<html><body><table><tr><td>Ay-Yıl</td></tr>
<tr><td>10-2026</td><td>28.10</td><td>2.10</td></tr>
<tr><td>09-2026</td><td>29.73</td><td>1.84</td></tr></table></body></html>"""


class CpiUpdateTest(Files):
    def test_parse_page(self):
        self.assertEqual(macro.parse_cpi_page(TCMB_PAGE.encode("utf-8")),
                         [("2026-10", 2.10, 28.10), ("2026-09", 1.84, 29.73)])

    def test_new_month_is_dated_the_day_it_was_first_seen(self):
        repo = self.dir / "cpi.csv"
        repo.write_text(CPI_HEADER + "2026-09,1.84,29.73,2026-10-05,x\n", encoding="utf-8")
        local = self.dir / "cpi_local.csv"
        get = lambda url, **_: Response(200, TCMB_PAGE)  # noqa: E731
        self.assertFalse(macro.update_cpi(date(2026, 11, 2), repo, local, get=get))  # not due before the 3rd
        self.assertTrue(macro.update_cpi(date(2026, 11, 4), repo, local, get=get))
        cpi = macro.load_cpi(repo, local)
        self.assertEqual(cpi.loc["2026-10", "published"], pd.Timestamp("2026-11-04"))  # never earlier than seen
        self.assertEqual(macro.cpi_known(cpi, date(2026, 11, 4)).period, "2026-09")
        self.assertEqual(macro.cpi_known(cpi, date(2026, 11, 5)).period, "2026-10")
        self.assertFalse(macro.update_cpi(date(2026, 11, 5), repo, local, get=get))  # already have it

    def test_repo_row_wins_and_offline_is_quiet(self):
        repo = self.dir / "cpi.csv"
        repo.write_text(CPI_HEADER + "2026-09,1.84,29.73,2026-10-05,x\n", encoding="utf-8")
        local = self.dir / "cpi_local.csv"

        def offline(url, **_):
            raise OSError("offline")

        self.assertFalse(macro.update_cpi(date(2026, 11, 4), repo, local, get=offline))
        self.assertFalse(local.exists())


class CommandTest(Files):
    def test_both_ends_are_filled_first(self):
        from unittest import mock

        calls = []

        def fake(start, end, **kwargs):
            calls.append((start, end))
            return 0

        with mock.patch.object(macro, "update_usdtry", side_effect=fake), \
                mock.patch.object(macro, "freshness", return_value=("ok", "x")):
            macro.main(["--usd", "2021-12-01", "--budget", "100"])
        today = date.today()
        self.assertEqual(calls[0], (today - pd.Timedelta(days=14).to_pytimedelta(), today))  # the newest days
        self.assertEqual(calls[1], (date(2021, 12, 1), date(2021, 12, 15)))  # the period's start
        self.assertEqual(calls[2], (date(2021, 12, 1), today))  # then everything else


class SecondSourceTest(Files):
    def test_difference_by_hand(self):
        tcmb = pd.Series([40.0, 41.0, 42.0], index=pd.to_datetime(["2026-10-26", "2026-10-27", "2026-10-28"]))
        yahoo = pd.DataFrame({"close": [40.2, 41.0, 42.84]},
                             index=pd.to_datetime(["2026-10-26", "2026-10-27", "2026-10-29"]))
        out = macro.second_source_check(tcmb, today=date(2026, 10, 29),
                                        fetch=lambda symbols, start: {"USDTRY=X": yahoo})
        self.assertEqual(out["days"], 2)  # only the days both have
        self.assertAlmostEqual(out["max_diff_pct"], 0.5)  # 40.2 / 40 - 1
        self.assertEqual(out["day"], "2026-10-27")

    def test_unavailable(self):
        tcmb = pd.Series([40.0], index=pd.to_datetime(["2026-10-26"]))
        self.assertIsNone(macro.second_source_check(tcmb, today=date(2026, 10, 29), fetch=lambda s, start: {}))

        def broken(symbols, start):
            raise OSError("offline")

        self.assertIsNone(macro.second_source_check(tcmb, today=date(2026, 10, 29), fetch=broken))

    def test_freshness_shows_and_warns(self):
        cpi = self.cpi("2026-09,1.84,29.7,2026-10-05,x\n")
        rates = pd.Series([49.7], index=pd.to_datetime(["2026-10-27"]))
        ok = {"day": "2026-10-27", "days": 5, "max_diff_pct": 0.3}
        state, text = macro.freshness(date(2026, 10, 28), cpi, rates, second=ok)
        self.assertEqual(state, "ok")
        self.assertIn("Yahoo farkı en çok %0,3", text)
        state, text = macro.freshness(date(2026, 10, 28), cpi, rates, second={**ok, "max_diff_pct": 1.4})
        self.assertEqual(state, "warn")
        self.assertIn("%1,4", text)


class FreshnessTest(Files):
    def test_states(self):
        cpi = self.cpi("2026-09,1.84,29.7,2026-10-05,x\n")
        rates = pd.Series([49.7], index=pd.to_datetime(["2026-10-27"]))
        self.assertEqual(macro.freshness(date(2026, 10, 28), cpi, rates)[0], "ok")
        state, text = macro.freshness(date(2026, 11, 9), cpi, rates)  # October's figure is out by 03.11
        self.assertEqual(state, "warn")
        self.assertIn("10.2026 verisi eklenmedi", text)
        self.assertEqual(macro.freshness(date(2026, 10, 28), cpi, pd.Series(dtype=float))[0], "warn")
        self.assertEqual(macro.freshness(date(2026, 10, 28), macro.load_cpi(self.dir / "yok.csv"), rates)[0], "unknown")

    def test_health_line_and_gitignore(self):
        from core.config.paths import ROOT_DIR
        from core.reports import health

        names = [c.name for c in health.health_checks(online=False)]
        self.assertIn("Makro veri", names)
        ignored = (ROOT_DIR / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("data/macro/usdtry.csv", ignored)
        self.assertIn("data/macro/cpi_local.csv", ignored)


if __name__ == "__main__":
    unittest.main()
