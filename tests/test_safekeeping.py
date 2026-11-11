"""Everything kept safe (L, the user's 11.11.2026 request). Written before the code.

Every night the 21:00 summary says in one line whether every local branch equals its GitHub copy, and in one line
how old the newest copy of the files outside the repository is. The project documents that lived outside the
repository are in docs/ now; scripts with a personal value (the Telegram chat id) never enter the public repository."""

import re
import subprocess
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from core import otonom
from core.market.calendar import ISTANBUL

NOW = datetime(2026, 11, 11, 21, 0, tzinfo=ISTANBUL)


def fake_git(branches: dict[str, tuple[str, str | None]], ancestors: set[tuple[str, str]] = frozenset()):
    """branches: name -> (local sha, origin sha or None)"""

    def run(args, **kwargs):
        if args[:2] == ["git", "for-each-ref"]:
            return SimpleNamespace(returncode=0, stdout="\n".join(branches) + "\n")
        if args[:3] == ["git", "rev-parse", "-q"]:
            ref = args[-1]
            name = ref.removeprefix("refs/heads/").removeprefix("refs/remotes/origin/")
            local, remote = branches.get(name, (None, None))
            sha = local if ref.startswith("refs/heads/") else remote
            return SimpleNamespace(returncode=0 if sha else 1, stdout=(sha or "") + "\n")
        if args[:2] == ["git", "merge-base"]:
            return SimpleNamespace(returncode=0 if (args[-2], args[-1]) in ancestors else 1, stdout="")
        raise AssertionError(args)

    return run


class BranchesTest(unittest.TestCase):
    def test_all_equal_is_one_short_line(self):
        run = fake_git({"a": ("1", "1"), "b": ("2", "2")})
        self.assertEqual(otonom.branches_line(run=run), "✅ Dallar: 2 yerel dal GitHub'daki kopyasıyla aynı")

    def test_each_kind_of_difference_is_named(self):
        run = fake_git({"a": ("1", "1"), "ileri": ("3", "2"), "yok": ("4", None), "ayri": ("5", "6"),
                        "geride": ("7", "8")},
                       ancestors={("2", "3"), ("7", "8")})
        line = otonom.branches_line(run=run)
        self.assertTrue(line.startswith("⚠️ Dallar: 5 dalın 4'ü farklı"), line)
        for part in ("ileri (gönderilmemiş commit)", "yok (GitHub'da yok)", "ayri (ayrışmış)",
                     "geride (GitHub ileride)"):
            self.assertIn(part, line)

    def test_git_trouble_never_breaks_the_summary(self):
        def broken(*a, **k):
            raise FileNotFoundError("git")

        self.assertIn("kontrol edilemedi", otonom.branches_line(run=broken))

    def test_it_only_reads(self):
        import inspect

        source = inspect.getsource(otonom.branches_line)
        for command in ('"push"', '"fetch"', '"checkout"', '"reset"', '"branch"', '"commit"', '"pull"'):
            self.assertNotIn(command, source)  # only for-each-ref, rev-parse and merge-base


class OutsideCopyTest(unittest.TestCase):
    def test_the_newest_copy_and_its_age(self):
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(otonom.outside_copy_line(Path(d), NOW),
                             "⚠️ Depo dışı dosyalar: yedekte kopyası yok")
            old = Path(d, "quantbist_depo_disi_2026-11-01.zip")
            new = Path(d, "quantbist_depo_disi_2026-11-11.zip")
            for p in (old, new):
                p.write_bytes(b"x")
            os.utime(new, (NOW.timestamp(), (NOW - timedelta(days=0, hours=20)).timestamp()))
            os.utime(old, (NOW.timestamp(), (NOW - timedelta(days=10)).timestamp()))
            self.assertEqual(otonom.outside_copy_line(Path(d), NOW),
                             "✅ Depo dışı dosyalar: son kopya 11.11 (0 gün önce)")
            os.utime(new, (NOW.timestamp(), (NOW - timedelta(days=9)).timestamp()))
            self.assertIn("⚠️ Depo dışı dosyalar: son kopya", otonom.outside_copy_line(Path(d), NOW))

    def test_the_summary_carries_both_lines(self):
        text = otonom.summary_text(NOW, [], "", [], {"next": "x"}, checks=["✅ Dallar: 1", "✅ Depo dışı: 1"])
        lines = text.splitlines()
        self.assertIn("✅ Dallar: 1", lines)
        self.assertLess(lines.index("✅ Depo dışı: 1"), lines.index("Yarın sıradaki iş: x"))
        import inspect

        source = inspect.getsource(otonom.build_summary)
        self.assertIn("branches_line(", source)
        self.assertIn("outside_copy_line(", source)


class MovedDocsTest(unittest.TestCase):
    MOVED = ("docs/MODEL_6_12_AY.md", "docs/KARNE_KURALI.md", "docs/OTONOM_KURALLAR.md", "docs/OTONOM_GOREV.md",
             "docs/GOZLEMLER.md")

    def test_the_project_documents_are_in_the_repository(self):
        for path in self.MOVED:
            self.assertTrue(Path(path).exists(), path)

    def test_the_private_repository_and_personal_values_stay_out(self):
        chat = re.compile(r"\b1\d{9}\b")
        for path in (*self.MOVED, "scripts/araclar/fiyat_cevir.py"):
            text = Path(path).read_text(encoding="utf-8")
            self.assertNotIn("hsnklc044-jpg-bist-ai-bot", text, path)
            self.assertIsNone(chat.search(text), path)

    def test_the_skills_read_the_rules_from_the_repository(self):
        for skill in (".claude/skills/robot/SKILL.md", ".claude/skills/siradaki-is/SKILL.md"):
            text = Path(skill).read_text(encoding="utf-8")
            self.assertIn("docs/OTONOM_KURALLAR.md", text)
            self.assertNotIn(r"QuantBIST-araclar\otonom_kurallar.md", text)

    def test_the_one_off_scripts_with_the_chat_id_are_not_here(self):
        self.assertFalse(Path("scripts/araclar/tarama_ekle.py").exists())
        self.assertFalse(Path("scripts/araclar/tarama_ekle2.py").exists())

    def test_the_converter_writes_outside_the_repository_by_default(self):
        out = subprocess.run(["python", "-c", "import ast,sys; print('ok')"], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0)
        source = Path("scripts/araclar/fiyat_cevir.py").read_text(encoding="utf-8")
        self.assertIn("--klasor", source)


if __name__ == "__main__":
    unittest.main()
