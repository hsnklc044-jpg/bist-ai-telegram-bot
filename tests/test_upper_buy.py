"""/uzun_ust: the user's saved upper buy price (append-only CSV) and its use by /uzun."""

import asyncio
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from core.infrastructure.exceptions import PersonalFileError
from core.market import upper_buy as U
from core.market.calendar import ISTANBUL
from tests.test_long_model import breakout_frame

NOW = datetime(2026, 11, 10, 17, 0, tzinfo=ISTANBUL)


class StoreTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "upper_buy.csv"

    def run_words(self, *words):
        return U.command_text(list(words), path=self.path, now=NOW)

    def test_set_read_and_list(self):
        self.assertIn("Kayıtlı üst alım fiyatı yok", self.run_words())
        message = self.run_words("THYAO", "250")
        self.assertIn("THYAO üst alım fiyatı 250,00 TL olarak kaydedildi", message)
        self.assertEqual(U.latest("THYAO.IS", self.path), 250.0)
        listing = self.run_words()
        self.assertIn("THYAO: 250,00 TL (kayıt 10.11.2026)", listing)
        self.assertIn("öneri değildir", listing)

    def test_the_last_row_wins_and_the_file_only_grows(self):
        self.run_words("THYAO", "250")
        first = self.path.read_bytes()
        message = self.run_words("thyao", "260,5")
        self.assertIn("(önceki: 250,00)", message)
        self.assertEqual(U.latest("THYAO.IS", self.path), 260.5)
        self.assertTrue(self.path.read_bytes().startswith(first))  # nothing rewritten
        self.assertEqual([r[1] for r in U.history(self.path)], ["THYAO.IS", "THYAO.IS"])

    def test_clear_closes_the_record_and_keeps_the_history(self):
        self.run_words("THYAO", "250")
        self.assertIn("kaydı kapatıldı", self.run_words("THYAO", "sil"))
        self.assertIsNone(U.latest("THYAO.IS", self.path))
        self.assertEqual(len(U.history(self.path)), 2)
        self.assertIn("kayıtlı üst alım fiyatı yok", self.run_words("THYAO", "sil"))
        self.assertEqual(len(U.history(self.path)), 2)  # clearing nothing writes nothing

    def test_number_formats(self):
        for raw, expected in (("250", 250.0), ("250,5", 250.5), ("250.5", 250.5), ("1.250,50", 1250.5)):
            self.run_words("AKBNK", raw)
            self.assertEqual(U.latest("AKBNK", self.path), expected, raw)

    def test_typing_slips_are_refused_and_nothing_is_written(self):
        for raw in ("0", "-5", "abc", "nan", "inf", "2000000"):
            with self.subTest(raw), self.assertRaises(ValueError):
                self.run_words("THYAO", raw)
        self.assertFalse(self.path.exists())

    def test_usage_and_a_bad_symbol(self):
        self.assertIn("Kullanım", self.run_words("THYAO"))
        self.assertIn("Kullanım", self.run_words("A", "1", "2"))
        with self.assertRaises(ValueError):
            self.run_words("!!", "250")

    def test_a_broken_row_names_its_line(self):
        self.path.write_text("at,symbol,price,note\n2026-11-10T10:00:00,THYAO.IS,250,\n"
                             "2026-11-10T11:00:00,GARAN.IS,abc,\n", encoding="utf-8")
        with self.assertRaisesRegex(PersonalFileError, "3. satır"):
            U.load(self.path)
        self.path.write_text("at,symbol,price,note\n2026-11-10T10:00:00,THYAO.IS,-1,\n", encoding="utf-8")
        with self.assertRaisesRegex(PersonalFileError, "sıfırdan büyük"):
            U.load(self.path)

    def test_an_empty_file_is_said_not_ignored(self):
        self.path.write_bytes(b"")
        with self.assertRaises(PersonalFileError):
            self.run_words()

    def test_backed_up_health_checked_and_not_in_git(self):
        from core import backup
        from core.config.paths import ROOT_DIR, UPPER_BUY_FILE
        from core.reports import health

        self.assertIn(UPPER_BUY_FILE, backup.PERSONAL_FILES)
        self.assertIn(UPPER_BUY_FILE, health.SCHEMAS)
        self.assertIn("data/upper_buy.csv", (ROOT_DIR / ".gitignore").read_text(encoding="utf-8"))
        self.run_words("THYAO", "250")
        made = backup.create_backup([self.path], target=self.path.parent / "yedek")
        self.assertIn("upper_buy.csv", made.files)


class LongModelTest(unittest.TestCase):
    def text(self, upper=None, saved_price=None, error=None):
        from bot import analysis

        patches = [mock.patch("core.reports.daily.adjusted_bars", return_value=breakout_frame()),
                   mock.patch("core.market.upper_buy.latest", return_value=saved_price, side_effect=error)]
        with patches[0], patches[1]:
            return analysis._long_text("THYAO.IS", upper)

    def test_a_saved_price_is_used_and_marked(self):
        text = self.text(saved_price=1e9)
        self.assertIn("Karar: Giriş adayı", text)
        self.assertIn("(kayıtlı)", text)
        self.assertIn("Kayıtlı fiyatı değiştirmek için: /uzun_ust THYAO", text)

    def test_the_price_in_the_command_wins_over_the_saved_one(self):
        text = self.text(upper=1e9, saved_price=1.0)
        self.assertIn("Karar: Giriş adayı", text)
        self.assertNotIn("(kayıtlı)", text)

    def test_no_saved_price_keeps_the_rule_that_nothing_is_a_candidate(self):
        text = self.text()
        self.assertIn("Karar: İzle", text)
        self.assertIn("üst alım fiyatı girilmedi", text)
        self.assertIn("/uzun_ust THYAO FİYAT", text)

    def test_an_unreadable_saved_file_is_said_and_the_card_still_comes(self):
        text = self.text(error=PersonalFileError(Path("upper_buy.csv"), "3. satır: fiyat sayı değil"))
        self.assertIn("Kayıtlı üst alım fiyatları okunamadı", text)
        self.assertIn("Teknik puan:", text)
        self.assertIn("Karar: İzle", text)


class CommandTest(unittest.TestCase):
    def run_command(self, args, path):
        from bot import analysis
        from tests.test_screen_telegram import fake_update

        sent = []
        with mock.patch.object(U, "FILE", path):
            asyncio.run(analysis.upper_cmd(fake_update(sent), SimpleNamespace(args=args)))
        return sent[0][0]

    def test_registered_and_documented(self):
        from bot.handlers import COMMANDS, MENU
        from bot.start import HELP_TEXT

        self.assertIn("uzun_ust", dict(COMMANDS))
        self.assertIn("uzun_ust", dict(MENU))
        self.assertIn("/uzun_ust THYAO 250", HELP_TEXT)

    def test_the_command_end_to_end_and_its_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "upper_buy.csv"
            self.assertIn("kaydedildi", self.run_command(["THYAO", "250"], path))
            self.assertIn("THYAO: 250,00 TL", self.run_command([], path))
            self.assertIn("Fiyat sayı olmalı", self.run_command(["THYAO", "abc"], path))
            path.write_text("at,symbol,price,note\nx,THYAO.IS,abc,\n", encoding="utf-8")
            self.assertIn("fiyat sayı değil", self.run_command([], path))
            with mock.patch("core.market.upper_buy.command_text", side_effect=OSError("disk")):
                self.assertIn("kaydedilemedi", self.run_command(["THYAO", "250"], path))


if __name__ == "__main__":
    unittest.main()
