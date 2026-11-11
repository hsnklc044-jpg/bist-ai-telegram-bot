"""Borsa İstanbul official end-of-day prices (K, the user's 11.11.2026 decision). Written before the code.

The DataStore monthly files (data/inbox/bist) come in three header formats, found on 11.11 by reading all 467
files: the old system until 13.11.2015 (sessions, PAY KODU + SERI KODU, comma or point decimals), and the new
system (BISTECH) from 16.11.2015 with two header lines (Turkish, English), once with the midday session columns
until 09.2019 and once without. Headers are matched by name; an unknown header rejects the file with the reason.
Only ordinary shares (.E / series E) are kept. Prices before 1 January 2005 are in old lira (÷ 1 000 000).
The raw files are only read: never changed, moved or deleted."""

import os
import sqlite3
import unittest
from datetime import date, time
from pathlib import Path

import pytest

from core.official import prices

OLD_HEAD = ("TARIH;SEANS NO;PAZAR;PAY KODU;SERI KODU;MIN FIYAT;MAX FIYAT;ONCEKI KAPANIS FIYAT;KAPANIS FIYAT;AOF;"
            "ISLEM HACMI;ISLEM MIKTARI;SOZLESME SAYISI;SEANS SIRA NO;BAZ FIYAT;ALT LIMIT;UST LIMIT;MAX LOT;"
            "REFERANS  FIYAT;BSIT100 ENDEKS;ACILIS SEANSI FIYAT;ACILIS SEANSI ISLEM MIKTARI;"
            "ACILIS SEANSI SOZLESME SAYISI;GAOF;GRUP;BRUT TAKAS;PIYASA YAPICI KOD;ISLEM YONTEMI;"
            "KAPANIS SEANSI ISLEM MIKTARI;KAPANIS SEANSI ISLEM HACMI;TEK FIYAT ISLEM MIKTARI;"
            "TEK FIYAT SOZLESME SAYISI;KAPANIS SEANSI FIYATI;EN IYI ALIS FIYATI;EN IYI SATIS FIYATI")
OLD_HEAD_EN = "DATE;SESSION NO;MARKET;STOCK SYMBOL;STOCK SERIES"
NEW_HEAD = ("TARIH;ISLEM  KODU;BULTEN ADI;PAZAR GRUBU;PAZAR;YAPISAL BAZDA PIYASA ALT BOLUMU;ENSTRUMAN GRUBU;"
            "ENSTRUMAN TIPI;ENSTRUMAN SINIFI;ISLEM YONTEMI;PIYASA YAPICI;BIST 100 ENDEKS;BIST 30 ENDEKS;BRUT TAKAS;"
            "OZSERMAYE HALI;GECICI DURDURMA;ONCEKI KAPANIS FIYATI;ACILIS FIYATI;ACILIS SEANSI FIYATI;EN DUSUK FIYAT;"
            "EN YUKSEK FIYAT;KAPANIS FIYATI;KAPANIS SEANSI FIYATI;DEGISIM (%);BEKLEYEN EN IYI ALIS;"
            "BEKLEYEN EN IYI SATIS;A.O.F;TOPLAM ISLEM HACMI;TOPLAM ISLEM ADEDI;TOPLAM SOZLESME SAYISI;REFERANS FIYAT;"
            "ACILIS SEANSI ISLEM HACMI;ACILIS SEANSI ISLEM MIKTARI;ACILIS SEANSI SOZLESME SAYISI;"
            "KAPANIS SEANSI ISLEM HACMI;KAPANIS SEANSI ISLEM MIKTARI;KAPANIS SEANSI SOZLESME SAYISI;"
            "KAPANIS FIYATINDAN ISLEMLER ISLEM HACMI;KAPANIS FIYATINDAN ISLEMLER ISLEM MIKTARI;"
            "KAPANIS FIYATINDAN ISLEMLER SOZLESME SAYISI;EN DUSUK ACIGA SATIS FIYATI;EN YUKSEK ACIGA SATIS FIYATI;"
            "ACIGA SATIS A.O.F;ACIGA SATIS ISLEM HACMI;ACIGA SATIS ISLEM ADEDI;ACIGA SATIS SOZLESME SAYISI;"
            "OZEL ISLEM BILDIRIMI EN DUSUK FIYAT;OZEL ISLEM BILDIRIMI EN YUKSEK FIYAT;OZEL ISLEM BILDIRIMI A.O.F.;"
            "OZEL ISLEM BILDIRIMI ISLEM HACMI;OZEL ISLEM BILDIRIMI ISLEM ADEDI;OZEL ISLEM BILDIRIMI SOZLESME SAYISI")
NEW_HEAD_EN = "TRADE DATE;INSTRUMENT SERIES CODE;INSTRUMENT NAME"


def old_row(day, session, code, series="E", low="8", high="8.06", prev="7.97", close="8.02", value="1000",
            qty="100", bist100="E", opening="0"):
    cells = dict.fromkeys(OLD_HEAD.split(";"), "")
    cells.update({"TARIH": day, "SEANS NO": str(session), "PAZAR": "N", "PAY KODU": code, "SERI KODU": series,
                  "MIN FIYAT": low, "MAX FIYAT": high, "ONCEKI KAPANIS FIYAT": prev, "KAPANIS FIYAT": close,
                  "ISLEM HACMI": value, "ISLEM MIKTARI": qty, "BSIT100 ENDEKS": bist100,
                  "ACILIS SEANSI FIYAT": opening})
    return ";".join(cells[h] for h in OLD_HEAD.split(";"))


def new_row(day, code, opening="10", high="11", low="9", close="10.5", prev="10", value="5000", qty="500",
            bist100="1", bist30="0", corp=""):
    cells = dict.fromkeys(NEW_HEAD.split(";"), "0")
    cells.update({"TARIH": day, "ISLEM  KODU": code, "ACILIS FIYATI": opening, "EN YUKSEK FIYAT": high,
                  "EN DUSUK FIYAT": low, "KAPANIS FIYATI": close, "ONCEKI KAPANIS FIYATI": prev,
                  "TOPLAM ISLEM HACMI": value, "TOPLAM ISLEM ADEDI": qty, "BIST 100 ENDEKS": bist100,
                  "BIST 30 ENDEKS": bist30, "OZSERMAYE HALI": corp})
    return ";".join(cells[h] for h in NEW_HEAD.split(";"))


def write(folder: Path, name: str, lines: list[str], encoding="utf-8") -> Path:
    path = folder / name
    path.write_bytes(("\r\n".join(lines) + "\r\n").encode(encoding))
    return path


@pytest.fixture
def inbox(tmp_path):
    folder = tmp_path / "bist"
    folder.mkdir()
    return folder


@pytest.fixture(autouse=True)
def _db(tmp_path, monkeypatch):
    monkeypatch.setattr(prices, "OFFICIAL_DB", tmp_path / "official.db")


class NewSystemTest:
    def test_two_header_lines_and_only_ordinary_shares(self, inbox):
        path = write(inbox, "PP_GUNSONUFIYATHACIM.M.202610.csv", [
            NEW_HEAD, NEW_HEAD_EN + ";x",
            new_row("2026-10-01", "THYAO.E", close="300.25", bist100="1", bist30="1"),
            new_row("2026-10-01", "TBIPY.V"),
            new_row("2026-10-01", "1GXAA.C"),
            new_row("2026-10-01", "XYZ.F"),
        ])
        got = prices.read_file(path)
        assert got.rejected is None
        assert [(r.code, r.day) for r in got.rows] == [("THYAO", date(2026, 10, 1))]
        r = got.rows[0]
        assert (r.open, r.high, r.low, r.close, r.prev_close) == (10.0, 11.0, 9.0, 300.25, 10.0)
        assert (r.value, r.quantity, r.bist100, r.bist30) == (5000.0, 500.0, 1, 1)
        assert r.corp_action is None

    def test_the_exchange_corporate_action_code_is_kept(self, inbox):
        # as TUKAS's bonus split day 04.02.2025 ("03") and TSPOR's reduction and rights day 19.06.2025 ("01&04")
        path = write(inbox, "PP_GUNSONUFIYATHACIM.M.202502.csv", [
            NEW_HEAD, NEW_HEAD_EN, new_row("2025-02-04", "TUKAS.E", prev="6.23", close="2.04", corp="03"),
            new_row("2025-02-04", "TSPOR.E", corp="01&04"), new_row("2025-02-04", "THYAO.E", corp="0")])
        got = {r.code: r.corp_action for r in prices.read_file(path).rows}
        assert got == {"TUKAS": "03", "TSPOR": "01&04", "THYAO": None}
        prices.import_folder(inbox)
        with sqlite3.connect(prices.OFFICIAL_DB) as conn:
            stored = dict(conn.execute("SELECT code, corp_action FROM official_prices"))
        assert stored == {"TUKAS": "03", "TSPOR": "01&04", "THYAO": None}

    def test_the_2015_2019_header_with_midday_columns_is_matched_by_name(self, inbox):
        head = NEW_HEAD.replace("PAZAR GRUBU", "A_B_C_D GRUBU").replace(
            "ACILIS SEANSI FIYATI;EN DUSUK FIYAT;", "ACILIS SEANSI FIYATI;GUNORTASI SEANSI FIYATI;EN DUSUK FIYAT;", 1)
        cells = head.split(";")
        row = dict.fromkeys(cells, "0")
        row.update({"TARIH": "2016-03-01", "ISLEM  KODU": "GARAN.E", "KAPANIS FIYATI": "8.5", "ACILIS FIYATI": "8.4",
                    "EN YUKSEK FIYAT": "8.6", "EN DUSUK FIYAT": "8.3", "ONCEKI KAPANIS FIYATI": "8.4",
                    "TOPLAM ISLEM HACMI": ".5", "BIST 100 ENDEKS": "1"})
        path = write(inbox, "PP_GUNSONUFIYATHACIM.M.201603.csv", [head, NEW_HEAD_EN, ";".join(row[c] for c in cells)])
        got = prices.read_file(path)
        assert got.rejected is None
        assert got.rows[0].close == 8.5 and got.rows[0].value == 0.5 and got.rows[0].bist100 == 1


class OldSystemTest:
    def test_sessions_are_combined_into_one_day(self, inbox):
        path = write(inbox, "PP_GUNSONUFIYATHACIM.M.200806.csv", [
            OLD_HEAD, OLD_HEAD_EN,
            old_row("02.06.2008", 2, "THYAO", low="7,98", high="8,10", prev="8,02", close="8,00", value="200",
                    qty="20"),
            old_row("02.06.2008", 1, "THYAO", low="8", high="8,06", prev="7,97", close="8,02", value="100",
                    qty="10", opening="8,01"),
            old_row("02.06.2008", 1, "THYAO", series="B"),
        ])
        got = prices.read_file(path)
        assert got.rejected is None
        assert len(got.rows) == 1
        r = got.rows[0]
        assert r.code == "THYAO" and r.day == date(2008, 6, 2)
        assert r.close == 8.00  # the last session's close
        assert (r.low, r.high) == (7.98, 8.10)
        assert r.prev_close == 7.97  # before the first session
        assert (r.value, r.quantity) == (300.0, 30.0)
        assert r.open == 8.01
        assert r.bist100 == 1 and r.bist30 is None

    def test_no_opening_price_is_left_empty_never_made_up(self, inbox):
        path = write(inbox, "PP_GUNSONUFIYATHACIM.M.199801.csv", [
            OLD_HEAD, OLD_HEAD_EN, old_row("05.01.1998", 1, "THYAO", close="40500", bist100="")])
        r = prices.read_file(path).rows[0]
        assert r.open is None
        assert r.bist100 is None  # the flag is empty in the early files: membership unknown

    def test_before_2005_old_lira_and_old_shares_are_converted_without_a_jump(self, inbox):
        # as in the real files (THYAO 29.12.2004 close 7950; 03.01.2005 close 7,85 with previous close 7,95):
        # the old share in old lira; value in old lira; count of old shares (K-84)
        write(inbox, "PP_GUNSONUFIYATHACIM.M.200412.csv", [
            OLD_HEAD, OLD_HEAD_EN, old_row("29.12.2004", 1, "THYAO", low="7800", high="8000", prev="7800",
                                           close="7950", value="15900000000000", qty="2000000000")])
        write(inbox, "PP_GUNSONUFIYATHACIM.M.200501.csv", [
            OLD_HEAD, OLD_HEAD_EN, old_row("03.01.2005", 1, "THYAO", low="7,80", high="7,95", prev="7,95",
                                           close="7,85", value="15700000", qty="2000000")])
        dec = prices.read_file(inbox / "PP_GUNSONUFIYATHACIM.M.200412.csv").rows[0]
        jan = prices.read_file(inbox / "PP_GUNSONUFIYATHACIM.M.200501.csv").rows[0]
        assert dec.close == pytest.approx(7.95) and dec.low == pytest.approx(7.80)
        assert dec.value == pytest.approx(15_900_000.0)  # lira ÷ 1 000 000
        assert dec.quantity == pytest.approx(2_000_000.0)  # 1 000 old shares = 1 share
        assert dec.value / dec.quantity == pytest.approx(dec.close)  # the units agree
        assert jan.prev_close == pytest.approx(dec.close)  # no jump over the new year
        assert abs(jan.close / dec.close - 1) < 0.05

    def test_a_latin5_file_is_read(self, inbox):
        line = old_row("02.06.2008", 1, "THYAO").replace(";N;", ";İ;")
        path = write(inbox, "PP_GUNSONUFIYATHACIM.M.200806.csv", [OLD_HEAD, OLD_HEAD_EN, line], encoding="cp1254")
        assert prices.read_file(path).rows[0].code == "THYAO"


class RejectTest:
    def test_an_unknown_header_rejects_the_file_with_its_name(self, inbox):
        path = write(inbox, "PP_GUNSONUFIYATHACIM.M.202611.csv",
                     [NEW_HEAD + ";YENI ALAN", NEW_HEAD_EN, new_row("2026-11-02", "THYAO.E") + ";1"])
        got = prices.read_file(path)
        assert got.rows == []
        assert "YENI ALAN" in got.rejected

    def test_a_missing_field_rejects_the_file(self, inbox):
        head = NEW_HEAD.replace("KAPANIS FIYATI;KAPANIS SEANSI", "KAPANIS SEANSI")
        path = write(inbox, "PP_GUNSONUFIYATHACIM.M.202611.csv", [head, NEW_HEAD_EN])
        got = prices.read_file(path)
        assert "KAPANIS FIYATI" in got.rejected


class ImportTest:
    def test_the_folder_is_imported_once_and_never_changed(self, inbox):
        a = write(inbox, "PP_GUNSONUFIYATHACIM.M.202609.csv",
                  [NEW_HEAD, NEW_HEAD_EN, new_row("2026-09-30", "THYAO.E"), new_row("2026-09-30", "GARAN.E")])
        b = write(inbox, "PP_GUNSONUFIYATHACIM.M.202610.csv", [NEW_HEAD, NEW_HEAD_EN, new_row("2026-10-01", "THYAO.E")])
        before = {p.name: (p.read_bytes(), os.stat(p).st_mtime_ns) for p in (a, b)}
        first = prices.import_folder(inbox)
        assert (first.files, first.rows, first.rejected) == (2, 3, [])
        again = prices.import_folder(inbox)
        assert (again.files, again.rows) == (0, 0)  # only new files are read
        assert {p.name: (p.read_bytes(), os.stat(p).st_mtime_ns) for p in (a, b)} == before
        assert sorted(x.name for x in inbox.iterdir()) == sorted(before)
        with sqlite3.connect(prices.OFFICIAL_DB) as conn:
            assert conn.execute("SELECT COUNT(*) FROM official_prices").fetchone()[0] == 3

    def test_november_2015_halves_are_merged_and_an_overlap_is_reported(self, inbox):
        write(inbox, "BISTECH_Oncesi_PP_GUNSONUFIYATHACIM.M.201511.csv",
              [OLD_HEAD, OLD_HEAD_EN, old_row("13.11.2015", 1, "THYAO"), old_row("16.11.2015", 1, "GARAN")])
        write(inbox, "PP_GUNSONUFIYATHACIM.M.201511.csv",
              [NEW_HEAD, NEW_HEAD_EN, new_row("2015-11-16", "THYAO.E"), new_row("2015-11-16", "GARAN.E")])
        got = prices.import_folder(inbox)
        assert got.rows == 4
        assert got.overlaps == [("GARAN", date(2015, 11, 16))]

    def test_membership_comes_from_the_daily_flags(self, inbox):
        write(inbox, "PP_GUNSONUFIYATHACIM.M.202610.csv", [
            NEW_HEAD, NEW_HEAD_EN, new_row("2026-10-01", "THYAO.E", bist100="1", bist30="1"),
            new_row("2026-10-01", "ZZZZZ.E", bist100="0", bist30="0"), new_row("2026-10-01", "GARAN.E", bist30="0")])
        prices.import_folder(inbox)
        assert prices.members(date(2026, 10, 1), "bist100") == {"THYAO", "GARAN"}
        assert prices.members(date(2026, 10, 1), "bist30") == {"THYAO"}
        assert prices.members(date(2026, 10, 2), "bist100") == set()

    def test_a_rejected_file_is_reported_and_retried_after_it_changes(self, inbox):
        path = write(inbox, "PP_GUNSONUFIYATHACIM.M.202611.csv", [NEW_HEAD + ";YENI ALAN", NEW_HEAD_EN])
        got = prices.import_folder(inbox)
        assert got.rejected and "YENI ALAN" in got.rejected[0]
        assert prices.import_folder(inbox).rejected == []  # the same file is not re-read
        write(inbox, path.name, [NEW_HEAD, NEW_HEAD_EN, new_row("2026-11-02", "THYAO.E")])
        os.utime(path, ns=(os.stat(path).st_atime_ns, os.stat(path).st_mtime_ns + 10_000_000_000))
        assert prices.import_folder(inbox).rows == 1


class SafetyTest(unittest.TestCase):
    def test_the_inbox_never_reaches_git(self):
        self.assertIn("data/inbox/", Path(".gitignore").read_text(encoding="utf-8"))
        self.assertIn("data/*.db", Path(".gitignore").read_text(encoding="utf-8"))

    def test_the_heavy_import_runs_at_night_never_at_start_or_report_time(self):
        self.assertTrue(time(1, 0) <= prices.IMPORT_AT <= time(6, 0), prices.IMPORT_AT)

    def test_the_reader_never_writes_to_the_inbox(self):
        import inspect

        source = inspect.getsource(prices)
        for call in (".unlink(", ".rename(", "os.replace", "os.remove", "shutil.", "write_bytes(", "write_text("):
            self.assertNotIn(call, source)


# pytest collects plain classes named *Test only with the Test prefix; keep them explicit
TestNewSystem, TestOldSystem, TestReject, TestImport = NewSystemTest, OldSystemTest, RejectTest, ImportTest


class JobTest(unittest.TestCase):
    def test_a_quiet_night_sends_nothing_and_a_refusal_is_told(self):
        from bot import scheduler

        self.assertIsNone(scheduler.official_message(prices.ImportResult()))
        text = scheduler.official_message(prices.ImportResult(files=3, rows=10,
                                                              rejected=["PP_X.csv: bilinmeyen başlık"]))
        self.assertIn("2 dosya okundu", text)
        self.assertIn("PP_X.csv", text)
        self.assertLessEqual(len(text.splitlines()), 4)

    def test_the_job_runs_daily_at_the_import_time(self):
        from unittest import mock

        from bot import scheduler

        app = mock.Mock()
        self.assertTrue(scheduler.schedule_official_prices(app, chat_id=1))
        kwargs = app.job_queue.run_daily.call_args.kwargs
        self.assertEqual(kwargs["time"].replace(tzinfo=None), prices.IMPORT_AT)
        self.assertEqual(kwargs["name"], scheduler.OFFICIAL_JOB)

    def test_the_backup_takes_neither_the_raw_files_nor_the_rebuildable_database(self):
        from core import backup

        names = {Path(p).name for p in backup.PERSONAL_FILES}
        self.assertNotIn("official.db", names)
        self.assertFalse(any("inbox" in str(p) for p in backup.PERSONAL_FILES))
