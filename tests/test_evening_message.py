"""The evening report and price alarms in the message style (H, the user's 11.11.2026 decision). Written before the code.

AKŞAM RAPORU · date; a status line; BIST 100 value and change; "Piyasa": the class of the share of stocks above
their 50-day average; the paper account (value, today, since the start, real); "Senden beklenen:" only when
something is expected; "/summary". At most seven lines (the data trust note is a system line on its own). The full
report is built and kept as before (/rapor_tekrar). Every crossed price alarm is its own message."""

import unittest
from datetime import date

from core.alerts.levels import Alarm, Hit
from core.reports import daily, style

DAY = date(2026, 11, 10)
FACTS = {"xu100": (11662.0, -0.0043), "breadth": 15.0,
         "paper": {"total": 100531.0, "day": 0.0004, "start": 0.005, "real": -0.020}}


class ShortReportTest(unittest.TestCase):
    def test_a_quiet_day(self):
        text = daily.short_report(DAY, FACTS, problems=[], expect=None)
        self.assertEqual(text.splitlines(), [
            "AKŞAM RAPORU · 10.11.2026",
            "✅ Rapor tamam, sorun yok.",
            "BIST 100: 11.662 (-0,4%)",
            "Piyasa: 🔴 Çok zayıf (trenddeki hisse %15)",
            "Sanal hesap: 100.531 TL · bugün 0,0% · başlangıçtan +0,5% · reel -2,0%",
            "/summary",
        ])
        self.assertEqual(style.problems(text, "gunluk"), [])

    def test_problems_and_what_is_expected(self):
        text = daily.short_report(DAY, FACTS, problems=["Yedek alınamadı", "2 risk uyarısı"],
                                  expect="geçen ayın borsa fiyat ve endeks dosyalarını indir")
        lines = text.splitlines()
        self.assertEqual(lines[1], "⚠️ 2 konu: Yedek alınamadı; 2 risk uyarısı")
        self.assertEqual(lines[-2], "Senden beklenen: geçen ayın borsa fiyat ve endeks dosyalarını indir")
        self.assertLessEqual(len(lines), 7)
        self.assertEqual(style.problems(text, "gunluk", sorun=True), [])

    def test_missing_facts_are_left_out_not_made_up(self):
        text = daily.short_report(DAY, {}, problems=[], expect=None)
        self.assertEqual(text.splitlines(), ["AKŞAM RAPORU · 10.11.2026", "✅ Rapor tamam, sorun yok.", "/summary"])

    def test_the_market_class_follows_the_score_classes(self):
        for share, label in ((85, "🟢 Güçlü"), (65, "🟢 Olumlu"), (45, "🟡 Karışık"), (25, "🟠 Zayıf")):
            text = daily.short_report(DAY, {"breadth": share}, problems=[], expect=None)
            self.assertIn(f"Piyasa: {label} (trenddeki hisse %{share})", text)

    def test_the_data_note_is_a_system_line_not_counted(self):
        from core.market import trust

        text = trust.with_note(daily.short_report(DAY, FACTS, problems=["x"], expect="y"), trust.Trust(3, "Yahoo"))
        self.assertEqual(style.problems(text, "gunluk", sorun=True), [])


class AlarmTest(unittest.TestCase):
    def test_one_message_per_alarm(self):
        hits = [Hit(Alarm(3, "THYAO.IS", "below", 290.0), 289.76), Hit(Alarm(4, "SISE.IS", "above", 40.0), 41.2)]
        messages = daily.alarm_messages(DAY, hits)
        self.assertEqual(messages[0].splitlines(), ["🔔 ALARM · THYAO · 10.11.2026",
                                                    "Kapanış 289,76 TL · koşul: 290,00 TL altı", "/alarm"])
        self.assertIn("koşul: 40,00 TL üstü", messages[1])
        for m in messages:
            self.assertEqual(style.problems(m, "uyari"), [])


class WiringTest(unittest.TestCase):
    def test_the_short_report_is_sent_and_the_full_text_kept(self):
        import inspect

        source = inspect.getsource(daily._run_locked)
        self.assertIn("short_report(", source)
        self.assertIn("_keep_report_text(result.day, result.text)", source)
        self.assertIn("alarm_messages(", source)


if __name__ == "__main__":
    unittest.main()
