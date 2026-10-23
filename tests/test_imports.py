import importlib
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class ImportTest(unittest.TestCase):
    def test_every_module_imports(self):
        failures = []

        for path in sorted(ROOT.glob("*/**/*.py")):
            if path.parts[len(ROOT.parts)] not in ("core", "bot"):
                continue

            module = ".".join(path.relative_to(ROOT).with_suffix("").parts)
            module = module.removesuffix(".__init__")

            try:
                importlib.import_module(module)
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{module}: {type(exc).__name__}: {exc}")

        self.assertEqual(failures, [])

    def test_entry_points_import(self):
        for module in ("app", "main", "core.web.app"):
            importlib.import_module(module)
