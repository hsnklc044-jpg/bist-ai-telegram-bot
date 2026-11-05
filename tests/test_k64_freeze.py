"""
K-64 frozen for the 03.02.2027 forward test (user's approval 05.11.2026). The source of every part
the K-64 measurement and the live /tara ai model depend on, and the package lock, are hashed here.
A change to any of them turns CI red, so it cannot slip in while other work goes on.

The hashes may be updated ONLY with the user's explicit approval, recorded in DECISIONS with the
reason; never to make CI green. Line endings do not count (a Windows checkout is CRLF).
"""

import ast
import hashlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FROZEN_AT = "c598008 (v0.99.90)"

PARTS = {
    "core/ml/signal_filter.py": ("SPEC", "APPROVE", "FEATURES", "OUTER_CHUNKS", "INNER_CHUNKS", "MIN_APPROVED",
                                 "BOOTSTRAP", "features", "labels", "events", "_purged_folds", "fit", "evaluate",
                                 "_bootstrap", "decide", "text", "fit_live", "load_live", "model_file"),
    "core/analytics/dip_study.py": ("GAP", "events", "day_bootstrap"),
    "core/market/extended.py": "*",
    "core/market/limits.py": ("LIMIT_MOVE", "TOLERANCE", "EDGE", "limit_up"),
    "core/backtest/run.py": ("HOLDOUT_START",),
    "core/market/hourly.py": ("ISTANBUL", "COLUMNS", "clean", "_split", "load_hourly"),
}

FROZEN = {
    "core/analytics/dip_study.py:GAP": "f1f0e2ff49320786",
    "core/analytics/dip_study.py:day_bootstrap": "85eb05a7e7e5ace6",
    "core/analytics/dip_study.py:events": "9ca82ef4cfff821c",
    "core/backtest/run.py:HOLDOUT_START": "c1e9814af4874ffa",
    "core/market/extended.py:BB_NEAR": "9da45d1c9f107dab",
    "core/market/extended.py:REQUIRED": "604c48bca40676df",
    "core/market/extended.py:RSI_LOW": "cae9fc238e149fd0",
    "core/market/extended.py:STOCH_LOW": "8909225864a4db40",
    "core/market/extended.py:__all__": "0e0e584c6d0c9c82",
    "core/market/extended.py:add_indicators": "183643a3a925f2c2",
    "core/market/extended.py:logger": "7b9c6b7b5d6b393f",
    "core/market/extended.py:scan": "61f3cd4a8bc6c9de",
    "core/market/extended.py:trigger_mask": "7f27c5364469b406",
    "core/market/hourly.py:COLUMNS": "8eb8577591bd76b7",
    "core/market/hourly.py:ISTANBUL": "e0da36f4f9359270",
    "core/market/hourly.py:_split": "6ca88fc415ac49ed",
    "core/market/hourly.py:clean": "80050dbf0293ad82",
    "core/market/hourly.py:load_hourly": "dfc67691c5cb2688",
    "core/market/limits.py:EDGE": "020e5a4448da9a8c",
    "core/market/limits.py:LIMIT_MOVE": "7dfcb0ee5371e059",
    "core/market/limits.py:TOLERANCE": "7ab3a79550a31b4a",
    "core/market/limits.py:limit_up": "4cb9013a9d9cca18",
    "core/ml/signal_filter.py:APPROVE": "e1964d5fb8d67e22",
    "core/ml/signal_filter.py:BOOTSTRAP": "c5cd7774ee8ee1b5",
    "core/ml/signal_filter.py:FEATURES": "414eb1dc328dd7e4",
    "core/ml/signal_filter.py:INNER_CHUNKS": "be20c68c871e0108",
    "core/ml/signal_filter.py:MIN_APPROVED": "61f888a01bebab79",
    "core/ml/signal_filter.py:OUTER_CHUNKS": "e2d9a376c6a9c06b",
    "core/ml/signal_filter.py:SPEC": "f349ee8e033c368c",
    "core/ml/signal_filter.py:_bootstrap": "14a33b927b43e4ac",
    "core/ml/signal_filter.py:_purged_folds": "27f6e369677f6b2a",
    "core/ml/signal_filter.py:decide": "d0eca20a4458291f",
    "core/ml/signal_filter.py:evaluate": "edac138e3c82a196",
    "core/ml/signal_filter.py:events": "28a13a10fefeed9d",
    "core/ml/signal_filter.py:features": "cc407c9b28ef77e4",
    "core/ml/signal_filter.py:fit": "9e161ac93f0ae835",
    "core/ml/signal_filter.py:fit_live": "4ccc8c04de569c08",
    "core/ml/signal_filter.py:labels": "84bd116fda98cb7d",
    "core/ml/signal_filter.py:load_live": "3611d9a980b6e36b",
    "core/ml/signal_filter.py:model_file": "34efe3abbe11c293",
    "core/ml/signal_filter.py:text": "e2b6a56c409f2748",
    "requirements.lock": "9b4cec2e2372fcd1",
}


def _source(text: str, node) -> str:
    return (ast.get_source_segment(text, node) or "").replace("\r\n", "\n")


def parts(path: str, names) -> dict[str, str]:
    text = (ROOT / path).read_text(encoding="utf-8").replace("\r\n", "\n")
    out = {}
    for node in ast.parse(text).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            key = [node.name]
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            key = [t.id for t in targets if isinstance(t, ast.Name)]
        else:
            continue
        for k in key:
            if names == "*" or k in names:
                out[k] = hashlib.sha256(_source(text, node).encode("utf-8")).hexdigest()[:16]
    return out


def lock_digest() -> str:
    lines = [ln.strip() for ln in (ROOT / "requirements.lock").read_text(encoding="utf-8").splitlines()]
    body = "\n".join(ln for ln in lines if ln and not ln.startswith("#"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def current() -> dict[str, str]:
    found = {f"{path}:{name}": h for path, names in PARTS.items() for name, h in parts(path, names).items()}
    found["requirements.lock"] = lock_digest()
    return found


class FrozenTest(unittest.TestCase):
    def test_line_endings_do_not_count(self):
        import tempfile
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            for path in [*PARTS, "requirements.lock"]:
                target = Path(tmp) / path
                target.parent.mkdir(parents=True, exist_ok=True)
                raw = (ROOT / path).read_bytes().replace(b"\r\n", b"\n")
                target.write_bytes(raw.replace(b"\n", b"\r\n"))
            with mock.patch(f"{__name__}.ROOT", Path(tmp)):
                self.assertEqual(current(), FROZEN)

    def test_k64_is_unchanged(self):
        now = current()
        changed = sorted(k for k in FROZEN if now.get(k) != FROZEN[k])
        added = sorted(k for k in now if k not in FROZEN)
        self.assertEqual((changed, added), ([], []),
                         "K-64 is frozen for the 03.02.2027 forward test; a change needs the user's approval")

    def test_every_listed_part_exists(self):
        now = current()
        for path, names in PARTS.items():
            if names == "*":
                continue
            for name in names:
                self.assertIn(f"{path}:{name}", now, name)


if __name__ == "__main__":
    unittest.main()
