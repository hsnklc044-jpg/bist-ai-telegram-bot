"""#8 (K-113 Dalga 2): strategy config files with a hash.

All configs here are made-up test inputs; none is a real strategy and nothing is run on market data.
"""

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from core.research import strategy_config as sc

ROOT = Path(__file__).resolve().parents[1]

TOML_A = """
ad = "deneme"
surum = "1"
evren = "BIST100"
olusturma_tarihi = 2026-11-19

[parametreler]
pencere = 20
esik = 0.5
yontem = "ortalama"

[maliyet]
komisyon_bps = 10.0
kayma_bps = 5.0
"""

# same content, keys in a different order
TOML_B = """
evren = "BIST100"
surum = "1"
olusturma_tarihi = 2026-11-19
ad = "deneme"

[maliyet]
kayma_bps = 5.0
komisyon_bps = 10.0

[parametreler]
yontem = "ortalama"
esik = 0.5
pencere = 20
"""


def _write(text: str, name: str) -> Path:
    folder = Path(tempfile.mkdtemp())
    path = folder / name
    path.write_text(text, encoding="utf-8")
    return path


def _valid() -> dict:
    return {
        "ad": "deneme", "surum": "1", "evren": "BIST100", "olusturma_tarihi": date(2026, 11, 19),
        "parametreler": {"pencere": 20, "esik": 0.5}, "maliyet": {"komisyon_bps": 10.0},
    }


class HashTest(unittest.TestCase):
    def test_key_order_does_not_change_the_hash(self):
        a = sc.load(_write(TOML_A, "a.toml"))
        b = sc.load(_write(TOML_B, "b.toml"))
        self.assertEqual(sc.config_hash(a), sc.config_hash(b))
        self.assertEqual(sc.canonical(a), sc.canonical(b))

    def test_toml_and_json_with_the_same_content_have_the_same_hash(self):
        a = sc.load(_write(TOML_A, "a.toml"))
        data = dict(a, olusturma_tarihi=a["olusturma_tarihi"].isoformat())
        j = sc.load(_write(json.dumps(data), "a.json"))
        self.assertEqual(sc.config_hash(a), sc.config_hash(j))

    def test_any_parameter_change_changes_the_hash(self):
        base = sc.config_hash(sc.validate(_valid()))
        changed = _valid()
        changed["parametreler"]["pencere"] = 21
        self.assertNotEqual(base, sc.config_hash(sc.validate(changed)))
        cost = _valid()
        cost["maliyet"]["komisyon_bps"] = 10.5
        self.assertNotEqual(base, sc.config_hash(sc.validate(cost)))
        version = _valid()
        version["surum"] = "2"
        self.assertNotEqual(base, sc.config_hash(sc.validate(version)))

    def test_hash_is_sha256_hex(self):
        h = sc.config_hash(sc.validate(_valid()))
        self.assertEqual(len(h), 64)
        int(h, 16)

    def test_int_and_float_are_different_values(self):
        a, b = _valid(), _valid()
        b["parametreler"]["pencere"] = 20.0
        self.assertNotEqual(sc.config_hash(sc.validate(a)), sc.config_hash(sc.validate(b)))


class ValidateTest(unittest.TestCase):
    def assertRefused(self, data, text):
        with self.assertRaises(sc.StrategyConfigError) as ctx:
            sc.validate(data)
        self.assertIn(text, str(ctx.exception))

    def test_missing_field_is_refused(self):
        data = _valid()
        del data["evren"]
        self.assertRefused(data, "evren")

    def test_unknown_field_is_refused(self):
        data = _valid()
        data["parametre"] = {}
        self.assertRefused(data, "parametre")

    def test_wrong_types_are_refused(self):
        data = _valid()
        data["parametreler"] = [1, 2]
        self.assertRefused(data, "parametreler")
        data = _valid()
        data["olusturma_tarihi"] = "19.11.2026"
        self.assertRefused(data, "olusturma_tarihi")
        data = _valid()
        data["ad"] = "  "
        self.assertRefused(data, "ad")

    def test_non_finite_and_odd_values_are_refused(self):
        data = _valid()
        data["parametreler"]["esik"] = float("nan")
        self.assertRefused(data, "esik")
        data = _valid()
        data["maliyet"]["komisyon_bps"] = -1.0
        self.assertRefused(data, "komisyon_bps")
        data = _valid()
        data["parametreler"]["zaman"] = object()
        self.assertRefused(data, "zaman")

    def test_bad_file_is_refused_with_its_name(self):
        path = _write("ad = ", "bozuk.toml")
        with self.assertRaises(sc.StrategyConfigError) as ctx:
            sc.load(path)
        self.assertIn("bozuk.toml", str(ctx.exception))
        with self.assertRaises(sc.StrategyConfigError):
            sc.load(_write("{}", "x.yaml"))

    def test_validate_does_not_change_the_input(self):
        data = _valid()
        sc.validate(data)
        self.assertEqual(data, _valid())


class ExampleTest(unittest.TestCase):
    def test_example_config_is_valid_and_marked_as_example(self):
        cfg = sc.load(ROOT / "config" / "strategies" / "ornek.toml")
        self.assertIs(cfg.get("ornek"), True)
        self.assertIn("ÖRNEK", cfg["aciklama"])
        self.assertEqual(len(sc.config_hash(cfg)), 64)


if __name__ == "__main__":
    unittest.main()
