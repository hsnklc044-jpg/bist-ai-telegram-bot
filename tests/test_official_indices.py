"""Borsa İstanbul official end-of-day index files (K madde 8, the user's 11.11.2026 decision). Written before the code.

data/inbox/bist_endeks/YYYYMM/: until 10.2015 (and the first half of 11.2015) one file per month with sessions,
price and return index on one row (dates 04.01.2010); from 11.2015 files with a title, an empty line and a
"Türkçe / English" header (dates 01/10/2026), UTF-16 from 12.2015, the return index as its own row
(XU100_CFNNTLTL, type "Getiri"), leveraged and risk control files beside them (not read). Index points lost two
zeros on 01.07.2020 in these files (30.06.2020 XU100 116.524,78; 01.07.2020 1.153,15; the request said 27.07.2020,
which would divide 01–24.07 twice) and on 02.01.1997 (27.12.1996 97.588,81; 02.01.1997 988,93). Index points did not change on 01.01.2005; lira values did (÷ 1 000 000)."""

import unittest
from datetime import date, datetime

import pandas as pd
import pytest

from core.market.calendar import ISTANBUL
from core.official import compare, indices, prices

OLD_HEAD = ("TARIH;SEANS NO;ENDEKS KODU;FIYAT ENDEKSI BOLEN DEGERI;GETIRI ENDEKSI BOLEN DEGERI;"
            "FIYAT ENDEKSI KAPANIS DEGERI;FIYAT ENDEKSI MINIMUM DEGERI;FIYAT ENDEKSI MAXIMUM DEGERI;"
            "GETIRI ENDEKSI KAPANIS DEGERI;FIYAT ENDEKSI ACILIS SEANSI DEGERI;ISLEM HACMI;ISLEM MIKTARI")
OLD_EN = "DATE;SESSION NO;INDEX CODE;PRICE INDEX DIVISOR"
NEW_HEAD = ("Tarih / Date;Endeks Kodu / Index Code;Endeksler / Index Names In Turkish;"
            "Endekslerin İngilizce İsimleri / Index Names In English;Endeks Türü / Index Type;Bölen / Divisor;"
            "Kapanış Değeri / Closing Value;En Düşük / Lowest Value;En Yüksek / Highest Value;"
            "İşlem Hacmi / Traded Value;İşlem Miktarı / Traded Volume")


def write(folder, name, lines, encoding="utf-8"):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_bytes(("\r\n".join(lines) + "\r\n").encode(encoding))
    return path


def new_row(day, code, close, kind="Fiyat", low=None, high=None, value="1000"):
    return f"{day};{code};BIST 100;BIST 100;{kind};2.5;{close};{low or close};{high or close};{value};10"


@pytest.fixture
def inbox(tmp_path):
    return tmp_path / "bist_endeks"


@pytest.fixture(autouse=True)
def _db(tmp_path, monkeypatch):
    monkeypatch.setattr(prices, "OFFICIAL_DB", tmp_path / "official.db")
    monkeypatch.setattr(compare, "REPORT_DIR", tmp_path)


class TestNewFormat:
    def test_title_lines_utf16_and_the_return_index_row(self, inbox):
        path = write(inbox / "202610", "PP_GUNSONUENDEKS_M.csv", [
            "Günsonu Endeks - Aylık", "", NEW_HEAD,
            new_row("01/10/2026", "XU100", "12249.04", low="11936.19", high="12363.77", value="188579487373.42"),
            new_row("01/10/2026", "XU100_CFNNTLTL", "30000.5", kind="Getiri"),
            new_row("01/10/2026", "XU100_BID", "12249.04"),
            new_row("01/10/2026", "XU030", "13000"),
            new_row("01/10/2026", "XYZ99", "5"),
        ], encoding="utf-16")
        got = indices.read_file(path)
        assert got.rejected is None
        rows = {r.code: r for r in got.rows}
        assert set(rows) == {"XU100", "XU030"}
        x = rows["XU100"]
        assert (x.day, x.close, x.low, x.high, x.return_close) == (date(2026, 10, 1), 12249.04, 11936.19, 12363.77,
                                                                    30000.5)
        assert x.value == 188579487373.42

    def test_points_before_july_2020_lose_two_zeros_without_a_jump(self, inbox):
        june = indices.read_file(write(inbox / "202006", "PP_GUNSONUENDEKS_M.csv", [
            "Günsonu Endeks - Aylık", "", NEW_HEAD, new_row("30/06/2020", "XU100", "116524.78")], encoding="utf-16"))
        july = indices.read_file(write(inbox / "202007", "PP_GUNSONUENDEKS_M.csv", [
            "Günsonu Endeks - Aylık", "", NEW_HEAD, new_row("01/07/2020", "XU100", "1153.15")], encoding="utf-16"))
        assert june.rows[0].close == pytest.approx(1165.2478)
        assert abs(july.rows[0].close / june.rows[0].close - 1) < 0.02

    def test_the_leveraged_and_risk_control_files_are_not_read(self, inbox):
        write(inbox / "202610", "PP_KALDIRACLIENDEKSLER_M.csv", ["x"], encoding="utf-16")
        write(inbox / "202610", "PP_RISKKONTROLENDEKSLERI_M.csv", ["x"], encoding="utf-16")
        got = indices.import_folder(inbox)
        assert (got.files, got.rejected) == (0, [])

    def test_an_unknown_header_rejects_the_file(self, inbox):
        path = write(inbox / "202611", "PP_GUNSONUENDEKS_M.csv",
                     ["t", "", NEW_HEAD + ";Yeni Alan / New Field"], encoding="utf-16")
        assert "YENI ALAN" in indices.read_file(path).rejected


class TestOldFormat:
    def test_sessions_and_the_return_index_column(self, inbox):
        path = write(inbox / "201001", "PP_GUNSONUENDEKSHACIM.M.201001.csv", [
            OLD_HEAD, OLD_EN,
            "04.01.2010;2;XU100;1999495.8981;1517789.8893;53368.16;52425.84;53368.16;70305.79;52559.85;1237818297.05;455498906",
            "04.01.2010;1;XU100;1999495.8981;1517789.8893;52490.47;52410.14;53299.43;69149.55;52818.57;1005216408.01;396478182",
        ])
        r = indices.read_file(path).rows[0]
        assert r.day == date(2010, 1, 4)
        assert r.close == pytest.approx(533.6816)  # last session, two zeros dropped (before 01.07.2020)
        assert (r.low, r.high) == (pytest.approx(524.1014), pytest.approx(533.6816))
        assert r.return_close == pytest.approx(703.0579)
        assert r.value == pytest.approx(1005216408.01 + 1237818297.05)

    def test_index_points_do_not_jump_over_2005_but_lira_values_are_converted(self, inbox):
        dec = indices.read_file(write(inbox / "200412", "PP_GUNSONUENDEKSHACIM.M.200412.csv", [
            OLD_HEAD, OLD_EN, "29.12.2004;2;XU100;1;1;24971.68;24839.21;25106.19;29102.25;;5000000000000;1"])).rows[0]
        jan = indices.read_file(write(inbox / "200501", "PP_GUNSONUENDEKSHACIM.M.200501.csv", [
            OLD_HEAD, OLD_EN, "03.01.2005;2;XU100;1;1;25445.15;25258.88;25508.11;29654.03;;5000000;1"])).rows[0]
        assert abs(jan.close / dec.close - 1) < 0.05
        assert dec.value == pytest.approx(5_000_000.0)


class TestRescaling:
    def test_the_1997_rebase_is_followed_too(self, inbox):
        before = indices.read_file(write(inbox / "199612", "PP_GUNSONUENDEKSHACIM.M.199612.csv", [
            OLD_HEAD, OLD_EN, "27.12.1996;2;XU100;0;0;97588.81;96328.7629;97588.8059;96728.56;;;"])).rows[0]
        after = indices.read_file(write(inbox / "199701", "PP_GUNSONUENDEKSHACIM.M.199701.csv", [
            OLD_HEAD, OLD_EN, "02.01.1997;2;XU100;5;5;994.87;986.25;994.87;994.87;;;"])).rows[0]
        assert before.close == pytest.approx(9.758881)  # ÷ 100 (1997) ÷ 100 (2020)
        assert after.close == pytest.approx(9.9487)
        assert abs(after.close / before.close - 1) < 0.05


class TestImport:
    def test_imported_once_into_its_own_table(self, inbox):
        write(inbox / "202610", "PP_GUNSONUENDEKS_M.csv",
              ["t", "", NEW_HEAD, new_row("01/10/2026", "XU100", "12249.04")], encoding="utf-16")
        assert indices.import_folder(inbox).rows == 1
        assert indices.import_folder(inbox).files == 0
        assert indices.series("XU100").to_dict() == {pd.Timestamp("2026-10-01"): 12249.04}

    def test_the_txt_file_of_february_2016_is_read_too(self, inbox):
        write(inbox / "201602", "PP_GUNSONUENDEKSHACIM.M.201602.txt",
              ["t", "", NEW_HEAD.replace("Endekslerin İngilizce İsimleri / Index Names In English;", ""),
               "01/02/2016;XU100;BIST 100;Fiyat;2.5;72000;71000;72500;1;1"], encoding="utf-16")
        assert indices.import_folder(inbox).rows == 1


class YahooIndexTest(unittest.TestCase):
    def test_xu100_is_checked_against_yahoo_for_the_closed_month(self):
        days = pd.bdate_range("2026-10-01", "2026-10-30")
        values = [10000 * (1.003 ** i) for i in range(len(days))]
        with prices._connect() as conn:
            indices._schema(conn)
            conn.executemany("INSERT INTO official_indices (code, date, close, low, high, return_close, value, file) "
                             "VALUES ('XU100', ?, ?, ?, ?, NULL, 1, 'f')",
                             [(d.date().isoformat(), v, v, v) for d, v in zip(days, values)])
        yahoo = list(values)
        yahoo[5:] = [v * 1.03 for v in yahoo[5:]]

        def bars(symbol):
            return pd.DataFrame({"close": yahoo}, index=days)

        line = compare.yahoo_index_check(datetime(2026, 11, 11, 3, tzinfo=ISTANBUL), bars=bars)
        self.assertIn("XU100", line)
        self.assertIn("1 günde fark", line)
        self.assertIn("08.10.2026", (compare.REPORT_DIR / "resmi_xu100_2026-10.txt").read_text(encoding="utf-8"))


class JobTest(unittest.TestCase):
    def test_the_night_job_imports_the_indices_and_checks_xu100(self):
        import inspect

        from bot import scheduler

        source = inspect.getsource(scheduler.official_prices_job)
        self.assertIn("indices.import_folder", source)
        self.assertIn("compare.yahoo_index_check", source)
