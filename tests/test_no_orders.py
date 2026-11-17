"""K-54 / K-93: no code sends a real order. The paper books stay offline; no broker or exchange SDK is
imported or required; the only HTTP POST in the code is the KAP disclosure search (a read query)."""

import ast
import tomllib
import unittest
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [p for d in ("core", "bot", "scripts") for p in (ROOT / d).rglob("*.py")]

# broker, exchange and trading-terminal SDKs (lowercase top-level module / distribution names)
FORBIDDEN = {
    "ccxt", "alpaca", "alpaca_trade_api", "alpaca_py", "ib_insync", "ib_async", "ibapi", "algolab", "matriks",
    "midas", "binance", "python_binance", "oandapyv20", "metatrader5", "kiteconnect", "robin_stocks",
    "tradingview_ta", "tvdatafeed", "backtrader_ib", "fxcmpy", "xtb", "pyalgotrade",
}
POST_ALLOWED = {"core/market/kap.py"}  # KAP disclosure search: POST with a query body, reads only
PAPER_BOOKS = ("core/ledger/paper.py", "core/signals/store.py", "core/ledger/book.py", "core/ledger/service.py")
NETWORK = {"httpx", "requests", "urllib", "socket", "http", "aiohttp", "websocket", "websockets", "telegram"}


def _tree(path):
    with warnings.catch_warnings():  # old escape sequences in docstrings are not this test's subject
        warnings.simplefilter("ignore")
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _imports(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (a.name.split(".")[0].lower() for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            yield node.module.split(".")[0].lower()


def _rel(path):
    return path.relative_to(ROOT).as_posix()


class NoOrdersTest(unittest.TestCase):
    def test_sources_found(self):
        self.assertGreater(len(SOURCES), 50)

    def test_no_broker_sdk_imported(self):
        bad = [(_rel(p), m) for p in SOURCES for m in _imports(_tree(p)) if m in FORBIDDEN]
        self.assertEqual(bad, [])

    def test_no_broker_sdk_required(self):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        deps = list(project.get("dependencies", []))
        for extra in project.get("optional-dependencies", {}).values():
            deps += extra
        lock = ROOT / "requirements.lock"
        if lock.exists():
            deps += [ln for ln in lock.read_text(encoding="utf-8").splitlines() if ln and not ln.startswith("#")]
        names = {d.split("==")[0].split(">")[0].split("<")[0].split("[")[0].split(";")[0].strip().lower()
                 .replace("-", "_") for d in deps}
        self.assertEqual(names & FORBIDDEN, set())

    def test_http_post_only_where_allowed(self):
        posts = set()
        for p in SOURCES:
            for node in ast.walk(_tree(p)):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr in ("post", "put", "patch") and _rel(p) not in POST_ALLOWED
                        and not (isinstance(node.func.value, ast.Name) and node.func.value.id in ("ax", "plt"))):
                    posts.add(f"{_rel(p)}:{node.lineno}")
        self.assertEqual(posts, set())

    def test_no_order_endpoint_in_urls(self):
        bad = []
        for p in SOURCES:
            for node in ast.walk(_tree(p)):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    s = node.value.lower()
                    if s.startswith(("http://", "https://", "wss://")) and any(
                            w in s for w in ("/order", "/trade", "/emir", "/position")):
                        bad.append(f"{_rel(p)}:{node.lineno}")
        self.assertEqual(bad, [])

    def test_paper_books_are_offline(self):
        for rel in PAPER_BOOKS:
            path = ROOT / rel
            if not path.exists():
                continue
            used = set(_imports(_tree(path))) & NETWORK
            self.assertEqual(used, set(), rel)

    def test_paper_books_say_no_order(self):
        self.assertIn("No order ever reaches a broker", (ROOT / "core/ledger/paper.py").read_text(encoding="utf-8"))
        self.assertIn("emir oluşturulmaz", (ROOT / "core/signals/store.py").read_text(encoding="utf-8"))

    def test_scanner_catches_a_planted_order(self):
        planted = ast.parse("import ccxt\nhttpx.post('https://api.example.com/v1/orders', json={})\n")
        self.assertIn("ccxt", set(_imports(planted)))
        calls = [n for n in ast.walk(planted) if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "post"]
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
