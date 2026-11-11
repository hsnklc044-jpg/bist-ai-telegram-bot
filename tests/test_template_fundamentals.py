"""Templates with their fundamental conditions and three subscriptions closed (E madde 2–4, the user's 11.11.2026
decision). Written before the code. The personal subscription file is never changed."""

import tempfile
import unittest
from pathlib import Path

from core.screen import fields, subscriptions, templates
from core.screen.language import parse


class SubscriptionTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "subs.csv"
        self.path.write_text("at,chat,name,action\n"
                             "2026-11-05T10:00:00,1,bist100_aday,abone\n"
                             "2026-11-05T10:00:00,1,bist30_aday,abone\n"
                             "2026-11-05T10:00:00,1,bist100_trend,abone\n"
                             "2026-11-05T10:00:00,1,bist100_kirilim,abone\n"
                             "2026-11-05T10:00:00,1,bist100_geri_cekilme,abone\n", encoding="utf-8")

    def test_three_are_closed_and_the_file_stays(self):
        before = self.path.read_bytes()
        self.assertEqual(sorted(subscriptions.active(self.path)), ["bist100_geri_cekilme", "bist100_kirilim"])
        self.assertEqual(subscriptions.closed(self.path), ["bist100_aday", "bist100_trend", "bist30_aday"])
        self.assertIn("Kapatılan", subscriptions.list_text(self.path))
        self.assertEqual(self.path.read_bytes(), before)

    def test_subscribing_again_later_works(self):
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write("2026-11-20T10:00:00,1,bist100_trend,abone\n")
        self.assertIn("bist100_trend", subscriptions.active(self.path))


class TemplateTest(unittest.TestCase):
    def test_the_new_template_and_its_rank_field(self):
        t = templates.TEMPLATES["deger_kalite_trend"]
        query = parse(t.criteria)
        self.assertIn("pd_dd_sira", query.fields)
        self.assertEqual(fields.RANKED["pd_dd_sira"], "pd_dd")
        self.assertIn("henüz ölçülmedi", templates.list_text(cards={}))

    def test_known_thresholds_are_back_and_unknown_ones_named(self):
        self.assertIn("piyasa_degeri>2", templates.TEMPLATES["teknik_temel_ema"].criteria)
        self.assertIn("piyasa_degeri>10", templates.TEMPLATES["tek_tus_trend"].criteria)
        self.assertIn("fso<1", templates.TEMPLATES["bebek_teknik"].criteria)
        for name in ("teknik_temel_ema", "basit_teknik", "basit_teknik_3g"):
            self.assertIn("kullanıcıdan bekleniyor", templates.TEMPLATES[name].skipped)


if __name__ == "__main__":
    unittest.main()
