"""Message style (A and B, the user's 11.11.2026 decision; docs/MESAJ_STILI.md). Written before the code.

Every user message answers three questions: is everything fine, what important changed, does the user need to do
something. First line the title and date in capitals, second line a status mark or score class and one sentence.
Turkish number format, a sign and one decimal on percentages, prices of 1.000 TL and over without decimals.
No internal code or developer term in a user message, never the words AL or SAT."""

import unittest
from datetime import date

from core.reports import style


class NumberTest(unittest.TestCase):
    def test_turkish_decimal_comma_and_thousands_point(self):
        self.assertEqual(style.number(1234567.891, 2), "1.234.567,89")
        self.assertEqual(style.number(0.5, 1), "0,5")
        self.assertEqual(style.number(-1234, 0), "-1.234")

    def test_percent_has_a_sign_and_one_decimal(self):
        self.assertEqual(style.percent(0.0123), "+1,2%")
        self.assertEqual(style.percent(-0.0456), "-4,6%")
        self.assertEqual(style.percent(0), "0,0%")

    def test_price_without_decimals_from_1000_tl(self):
        self.assertEqual(style.price(12249.04), "12.249 TL")
        self.assertEqual(style.price(1000), "1.000 TL")
        self.assertEqual(style.price(644.25), "644,25 TL")
        self.assertEqual(style.price(2.04), "2,04 TL")


class ScoreClassTest(unittest.TestCase):
    def test_the_five_classes_and_their_limits(self):
        cases = {100: ("🟢", "Güçlü"), 80: ("🟢", "Güçlü"), 79: ("🟢", "Olumlu"), 60: ("🟢", "Olumlu"),
                 59: ("🟡", "Karışık"), 40: ("🟡", "Karışık"), 39: ("🟠", "Zayıf"), 20: ("🟠", "Zayıf"),
                 19: ("🔴", "Çok zayıf"), 0: ("🔴", "Çok zayıf")}
        for score, expected in cases.items():
            self.assertEqual(style.score_class(score), expected, score)

    def test_no_class_without_a_score(self):
        self.assertIsNone(style.score_class(None))
        with self.assertRaises(ValueError):
            style.score_class(101)


class HeaderTest(unittest.TestCase):
    def test_title_and_date_in_capitals_then_the_status_line(self):
        self.assertEqual(style.header("Akşam raporu", date(2026, 11, 11), "✅", "Her şey yolunda."),
                         "AKŞAM RAPORU · 11.11.2026\n✅ Her şey yolunda.")

    def test_turkish_capitals(self):
        self.assertEqual(style.header("teknik tablo", date(2026, 11, 11)), "TEKNİK TABLO · 11.11.2026")


class CheckTest(unittest.TestCase):
    def test_internal_terms_and_buy_sell_words_are_found(self):
        text = ("ROBOT · 11.11.2026\n✅ v0.99.122 kuruldu, CI yeşil, SLO tamam (K-82, D14); SHA 475e074\n"
                "HTTP 502; logs/quantbist.log; ATR 2,1; CHARTER; AL sinyali; SAT")
        found = set(style.forbidden(text))
        for term in ("sürüm numarası", "CI", "SLO", "K-numarası", "D-numarası", "SHA", "HTTP hata adı", "dosya yolu",
                     "ATR", "CHARTER", "AL", "SAT"):
            self.assertIn(term, found)
        found = set(style.forbidden("python -m core.backup · .env'de BACKUP_DIR · OPERATIONS §7 · M30 kapalı"))
        for term in ("komut", "ayar dosyası", "belge bölümü", "model numarası"):
            self.assertIn(term, found)

    def test_ordinary_turkish_words_are_not_caught(self):
        for text in ("Salı günü alım fiyatı", "Satış tutarı", "Kalan süre", "ALARM · THYAO · 11.11.2026",
                     "Güncelleme sorunsuz kuruldu", "Sağlık kontrolü"):
            self.assertEqual(style.forbidden(text), [], text)

    def test_line_limits_per_kind(self):
        ok3 = "ROBOT · 11.11.2026\n✅ 2 güncelleme sorunsuz kuruldu\nYarın: endeks verisi"
        self.assertEqual(style.problems(ok3, "robot"), [])
        self.assertTrue(style.problems(ok3 + "\nfazla satır", "robot"))
        self.assertTrue(style.problems("\n".join(["x"] * 8), "gunluk"))
        self.assertEqual(style.problems("\n".join(["x"] * 6), "robot", sorun=True), [])
        self.assertTrue(style.problems("\n".join(["x"] * 5), "uyari"))

    def test_table_rows_are_at_most_32_characters(self):
        good = "BAŞLIK · 11.11.2026\n✅ ok\n<pre>🟢 THYAO   82  289,76  305,40</pre>"
        self.assertEqual(style.problems(good, "tablo"), [])
        bad = "BAŞLIK · 11.11.2026\n✅ ok\n<pre>" + "x" * 33 + "</pre>"
        self.assertTrue(any("32" in p for p in style.problems(bad, "tablo")))

    def test_only_status_and_score_emojis(self):
        self.assertEqual(style.problems("BAŞLIK · 11.11.2026\n✅ ok 🟢🟡🟠🔴⚠️❌", "uyari"), [])
        self.assertTrue(any("emoji" in p for p in style.problems("BAŞLIK · 11.11.2026\n🚀 ok", "uyari")))
        # the 10-box bars of /karne are allowed
        self.assertEqual(style.problems("BAŞLIK · 11.11.2026\n<pre>Trend █████░░░░░ 10/20</pre>", "tablo"), [])


class DocTest(unittest.TestCase):
    def test_the_style_document_has_the_rules_and_every_template(self):
        from pathlib import Path

        text = Path("docs/MESAJ_STILI.md").read_text(encoding="utf-8")
        for part in ("Her şey yolunda mı?", "Senden beklenen:", "AKŞAM RAPORU", "TARAMA ·", "🔔 ALARM",
                     "ROBOT ·", "Sistem sağlıklı", "❌ OLAY", "⚠️ SENİN İŞİN", "80–100", "Teknik göstergedir"):
            self.assertIn(part, text)
        self.assertIn("SMA (fiyat üstü)", text)  # the note that two scorecard rules are the same (I madde 0)


if __name__ == "__main__":
    unittest.main()
