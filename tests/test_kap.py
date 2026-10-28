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
        self.assertIn("     1  Kar Payı", text)
        self.assertIn("stockCodes örnekleri: ['THYAO']", text)
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


class DetailTest(unittest.TestCase):
    """A disclosure's own text, so a corporate action is verified from KAP itself (SKBNK 19.10 vs 22.10)."""

    PAGE = (b"<html><head><script>var x = 1;</script><style>p{}</style></head><body>"
            b"<nav>Menu Bildirim Sorgulari</nav><p>G\xc3\xb6nderim Tarihi 21.10.2026</p>"
            b"<h1>Bedelli Sermaye Art\xc4\xb1r\xc4\xb1m\xc4\xb1</h1><table><tr><td>Hak Kullan\xc4\xb1m Ba\xc5\x9flang\xc4\xb1\xc3\xa7"
            b"</td><td>22.10.2026</td></tr></table>"
            b'<script id="__NEXT_DATA__" type="application/json">{"props":{"rightsStart":"2026-10-22"}}</script>'
            b"</body></html>")

    def test_visible_text_and_embedded_data(self):
        asked = []

        def get(url):
            asked.append(url)
            return self.PAGE

        text = kap.detail(1685136, get=get)
        self.assertEqual(asked, ["https://www.kap.org.tr/tr/Bildirim/1685136"])
        self.assertIn("Hak Kullanım Başlangıç 22.10.2026", text)
        self.assertNotIn("var x", text)
        self.assertNotIn("Menu", text)  # the text starts at the disclosure itself
        self.assertIn('"rightsStart":"2026-10-22"', text)

    def test_failure_is_reported_not_raised(self):
        def down(url):
            raise ConnectionError("KAP down")

        self.assertIn("alınamadı: ConnectionError", kap.detail(1, get=down))

    def test_command_line(self):
        import io
        from contextlib import redirect_stdout
        from unittest import mock

        out = io.StringIO()
        with mock.patch.object(kap, "detail", side_effect=lambda i: f"metin {i}"), redirect_stdout(out):
            self.assertEqual(kap.main(["--detail", "11,22"]), 0)
        self.assertIn("metin 11", out.getvalue())
        self.assertIn("metin 22", out.getvalue())


if __name__ == "__main__":
    unittest.main()


CAPITAL = "Sermaye Artırımı - Azaltımı İşlemlerine İlişkin Bildirim"
DIVIDEND = "Kar Payı Dağıtım İşlemlerine İlişkin Bildirim"


def item(codes, subject, when="20.10.2026 18:00:00", index=1500000, summary="özet"):
    return {"stockCodes": codes, "subject": subject, "publishDate": when, "disclosureIndex": index, "summary": summary}


class CorporateActionCheckTest(unittest.TestCase):
    def actions(self, *rows):
        from core.market.corrections import CorporateAction

        return [CorporateAction(symbol=s, ex_date=d, factor=1.0, note="", kind="factor", ratio=None, price=1.0, source="")
                for s, d in rows]

    def check(self, items, actions=()):
        def post(url, body):
            return items if body["fromDate"] == "2026-10-14" else []

        return kap.check(TODAY, ["THYAO.IS", "BIMAS.IS", "OYYAT.IS"], list(actions), days=14, post=post)

    def test_unrecorded_capital_action_in_our_universe_is_listed_with_its_link(self):
        found = self.check([item("THYAO", CAPITAL, index=1511111, summary="%100 bedelsiz"),
                            item("ZZZZZ", CAPITAL)])  # not in our universe
        self.assertEqual([(f.symbol, f.kind, f.recorded) for f in found], [("THYAO.IS", "sermaye", False)])
        self.assertIn("kap.org.tr/tr/Bildirim/1511111", found[0].link)
        self.assertIn("%100 bedelsiz", found[0].summary)

    def test_a_recorded_action_near_the_announcement_counts_as_recorded(self):
        found = self.check([item("THYAO", CAPITAL)], actions=self.actions(("THYAO.IS", date(2026, 11, 20))))
        self.assertTrue(found[0].recorded)
        old = self.check([item("THYAO", CAPITAL)], actions=self.actions(("THYAO.IS", date(2025, 1, 2))))  # an older, other action
        self.assertFalse(old[0].recorded)

    def test_private_placement_needs_no_price_adjustment(self):
        """First real run 27.10: HEKTS "Tahsisli Sermaye Artırımı" was flagged as unrecorded; a private
        placement gives existing holders no rights, so prices need no adjustment and no row is expected."""
        found = self.check([item("THYAO", CAPITAL, summary="Tahsisli Sermaye Artırımında Payların Satışının Tamamlanması")])
        self.assertTrue(found[0].recorded)
        self.assertIn("düzeltme gerekmez", kap.format_findings(found, TODAY, 14))

    def test_dividends_are_information_and_several_codes_are_split(self):
        found = self.check([item("OYA, OYYAT", DIVIDEND), item("BIMAS", "Payların Geri Alınmasına İlişkin Bildirim")])
        self.assertEqual([(f.symbol, f.kind) for f in found], [("OYYAT.IS", "temettü")])

    def test_text(self):
        found = self.check([item("THYAO", CAPITAL), item("BIMAS", DIVIDEND)])
        text = kap.format_findings(found, TODAY, 14)
        self.assertIn("THYAO", text)
        self.assertIn("corporate_actions.csv'de yok", text)
        self.assertIn("temettü", text)
        self.assertIn("hiçbir şey kendiliğinden uygulanmaz", text)
        self.assertIn("bildirim yok", kap.format_findings([], TODAY, 14))


class DaysCommandTest(unittest.TestCase):
    def test_days_uses_the_universe_and_recorded_actions(self):
        import io
        from contextlib import redirect_stdout
        from unittest import mock

        out = io.StringIO()
        with mock.patch.object(kap, "check", return_value=[]) as check, \
                mock.patch("core.market.universe.load_universe", return_value=["THYAO.IS"]), \
                mock.patch("core.market.corrections.load_corporate_actions", return_value=[]), \
                redirect_stdout(out):
            self.assertEqual(kap.main(["--days", "14"]), 0)
        self.assertEqual(check.call_args.args[1:3], (["THYAO.IS"], []))
        self.assertEqual(check.call_args.kwargs["problems"], [])
        self.assertIn("bildirim yok", out.getvalue())


class UnexpectedAnswerTest(unittest.TestCase):
    """Öz-denetim 3, Ö10: one odd answer from KAP must not lose the whole weekly check."""

    def test_non_list_answer_and_odd_dates_are_skipped_not_fatal(self):
        def post(url, body):
            if body["fromDate"] == "2026-10-14":
                return {"error": "rate limited"}
            return [item("THYAO", CAPITAL, when="27/10/2026"), item("BIMAS", CAPITAL, when="22.10.2026 10:00:00")]

        problems = []
        found = kap.check(TODAY, ["THYAO.IS", "BIMAS.IS"], [], days=14, post=post, problems=problems)
        self.assertEqual([f.symbol for f in found], ["BIMAS.IS"])
        self.assertEqual(len(problems), 2)
        self.assertIn("14.10–20.10 arası okunamadı", problems[0])
        self.assertIn("⚠️ Eksik kontrol", kap.format_findings(found, TODAY, 14, problems))
