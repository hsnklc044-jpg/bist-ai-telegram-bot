"""KAP endpoints (core/market/kap.py) without the network: fakes answer for KAP."""

import unittest
from datetime import date

from core.market import kap

TODAY = date(2026, 10, 27)


class ProbeTest(unittest.TestCase):
    def test_reports_shapes_and_survives_failures(self):
        calls = []

        def get(url):
            calls.append(url)
            if url.endswith("/DG/IGS"):
                raise ConnectionError("kapalı")
            return [{"subjectOid": "abc", "subject": "Sermaye Artırımı"}]

        def post(url, body):
            calls.append((url, body["disclosureClass"], body["fromDate"], body["toDate"]))
            return [{"stockCodes": "THYAO", "subject": "Kar Payı", "publishDate": "27.10.26 18:00"}]

        text = kap.probe(TODAY, get=get, post=post)
        self.assertIn("[ODA] konu sayısı: 1", text)
        self.assertIn("Sermaye Artırımı", text)
        self.assertIn("[DG] konular alınamadı: ConnectionError", text)
        self.assertIn("alanlar: ['publishDate', 'stockCodes', 'subject']", text)
        self.assertIn((f"{kap.BASE}/disclosure/members/byCriteria", "ODA", "2026-10-20", "2026-10-27"), calls)

    def test_criteria_asks_every_company(self):
        body = kap._criteria(date(2026, 10, 1), TODAY, "ODA", ["abc"])
        self.assertEqual(body["mkkMemberOidList"], [])
        self.assertEqual(body["subjectList"], ["abc"])


class HttpAndCommandTest(unittest.TestCase):
    def test_http_wrapper_sends_json_and_raises_on_errors(self):
        from types import SimpleNamespace
        from unittest import mock

        seen = []

        def fake(method):
            def call(url, json=None, headers=None, timeout=None):
                seen.append((method, url, json, timeout))
                return SimpleNamespace(raise_for_status=lambda: None, json=lambda: [1])
            return call

        with mock.patch("requests.get", fake("get")), mock.patch("requests.post", fake("post")):
            self.assertEqual(kap._http("get")("u"), [1])
            self.assertEqual(kap._http("post")("u", {"a": 1}), [1])
        self.assertEqual(seen, [("get", "u", None, kap.TIMEOUT), ("post", "u", {"a": 1}, kap.TIMEOUT)])

    def test_command(self):
        import io
        from contextlib import redirect_stdout
        from unittest import mock

        out = io.StringIO()
        with mock.patch.object(kap, "probe", return_value="deneme çıktısı"), redirect_stdout(out):
            self.assertEqual(kap.main(["--probe"]), 0)
        self.assertIn("deneme çıktısı", out.getvalue())
        with redirect_stdout(io.StringIO()):
            self.assertEqual(kap.main([]), 2)


if __name__ == "__main__":
    unittest.main()
