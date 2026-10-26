import json
import pathlib
import tempfile
import unittest
from unittest import mock

from core.watchlist import repository, service


class WatchlistTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.file = pathlib.Path(self.tmp.name) / "watchlist.json"
        patcher = mock.patch.object(repository, "WATCHLIST_FILE", self.file)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_normalize_symbol(self):
        self.assertEqual(service.normalize_symbol(" eregl "), "EREGL.IS")
        self.assertEqual(service.normalize_symbol("THYAO.IS"), "THYAO.IS")

        for bad in ("", "A", "THY AO", "../etc", "X" * 11):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                service.normalize_symbol(bad)

    def test_add_and_remove(self):
        self.assertEqual(service.add_symbol(42, "eregl"), "EREGL.IS")
        service.add_symbol(42, "EREGL")
        service.add_symbol(42, "thyao")

        self.assertEqual(service.get_watchlist(42), ["EREGL.IS", "THYAO.IS"])
        self.assertEqual(json.loads(self.file.read_text(encoding="utf-8"))["42"], ["EREGL.IS", "THYAO.IS"])

        self.assertTrue(service.remove_symbol(42, "eregl"))
        self.assertFalse(service.remove_symbol(42, "eregl"))
        self.assertEqual(service.get_watchlist(42), ["THYAO.IS"])

    def test_users_are_separate(self):
        service.add_symbol(1, "EREGL")

        self.assertEqual(service.get_watchlist(2), [])

    def test_size_limit(self):
        with mock.patch.object(service, "MAX_WATCHLIST_SIZE", 2):
            service.add_symbol(1, "AAA")
            service.add_symbol(1, "BBB")

            with self.assertRaises(ValueError):
                service.add_symbol(1, "CCC")
