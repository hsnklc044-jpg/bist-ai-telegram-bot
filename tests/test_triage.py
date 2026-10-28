"""
Corporate action suspects with their evidence in one place (the SKBNK 19.10.2026 case, solved by
hand on 28.10): a price jump in our data, a KAP capital disclosure near it, and the second
source's own adjusted series. A proposal is written; nothing is applied.
"""

import unittest
from datetime import date

import pandas as pd

from core.market import triage
from core.market.kap import Finding

SUSPECT = {"symbol": "SKBNK.IS", "date": "2026-10-19", "change": -0.246, "kind": "sıçrama",
           "suggested_factor": 0.7542}
KAP = Finding("SKBNK.IS", "sermaye", date(2026, 10, 21), "Bedelli Sermaye Artırımına İlişkin Yeni Pay Alma "
              "Hakkı Kullanım Tarihleri", "https://www.kap.org.tr/tr/Bildirim/1685136", True)


def second(returns: dict[str, float]):
    """İş Yatırım stand-in: closes whose day-on-day change is `returns` on those days."""

    def fetch(code, start, end, **kwargs):
        days = pd.bdate_range(start, end)
        close, closes = 100.0, []
        for d in days:
            close *= 1 + returns.get(d.date().isoformat(), 0.0)
            closes.append(close)
        return pd.DataFrame({"close": closes}, index=days)

    return fetch


class TriageTest(unittest.TestCase):
    def test_both_kinds_of_evidence_give_a_proposed_row(self):
        (p,) = triage.triage([SUSPECT], [KAP], fetch=second({"2026-10-19": -0.031}))
        self.assertEqual(p.verdict, "güçlü")
        self.assertAlmostEqual(p.their_change, -0.031, places=3)
        self.assertEqual(p.kap, [KAP])
        self.assertEqual(p.row(), 'SKBNK.IS,2026-10-19,factor,,,0.7542,https://www.kap.org.tr/tr/Bildirim/1685136,'
                                  '"otomatik öneri 28.10 kanıtları: KAP sermaye bildirimi 21.10, İş Yatırım o gün -3.1%; '
                                  'eklemeden önce KAP metni okunur"'.replace("28.10", triage.today_text()))
        text = triage.format_proposals([p])
        self.assertIn("SKBNK 19.10.2026 -24.6%", text)
        self.assertIn("güçlü", text)
        self.assertIn("kap.yml detail: 1685136", text)
        self.assertIn("hiçbir şey otomatik uygulanmadı", text)

    def test_second_source_moving_the_same_way_is_no_corporate_action(self):
        (p,) = triage.triage([SUSPECT], [KAP], fetch=second({"2026-10-19": -0.24}))
        self.assertEqual(p.verdict, "zayıf")  # both sources fell: not a missing adjustment in ours
        self.assertIsNone(p.row())

    def test_no_kap_disclosure_or_second_source_down(self):
        (p,) = triage.triage([SUSPECT], [], fetch=second({"2026-10-19": -0.031}))
        self.assertEqual(p.verdict, "zayıf")

        def down(*args, **kwargs):
            raise ConnectionError("isyatirim down")

        (q,) = triage.triage([SUSPECT], [KAP], fetch=down)
        self.assertEqual(q.verdict, "zayıf")
        self.assertIsNone(q.their_change)
        self.assertIn("İş Yatırım: alınamadı", triage.format_proposals([q]))

    def test_kap_window_and_other_stocks(self):
        far = Finding("SKBNK.IS", "sermaye", date(2026, 6, 1), "eski", "x", True)
        other = Finding("THYAO.IS", "sermaye", date(2026, 10, 20), "başka", "y", False)
        dividend = Finding("SKBNK.IS", "temettü", date(2026, 10, 20), "kâr payı", "z", False)
        (p,) = triage.triage([SUSPECT], [far, other, dividend], fetch=second({"2026-10-19": -0.031}))
        self.assertEqual((p.kap, p.verdict), ([], "zayıf"))

    def test_nothing_to_triage(self):
        self.assertIn("şüphe yok", triage.format_proposals([]))


class CommandTest(unittest.TestCase):
    def test_main_asks_kap_only_when_there_is_a_suspect(self):
        import io
        from contextlib import redirect_stdout
        from unittest import mock

        from core.market import kap, quality

        for suspects, kap_calls in (([], 0), ([SUSPECT], 1)):
            with self.subTest(suspects=suspects), \
                    mock.patch.object(quality, "build_report", return_value=[]), \
                    mock.patch.object(quality, "recent_suspects", return_value=suspects), \
                    mock.patch("core.market.membership.ever_members", return_value=["SKBNK.IS"]), \
                    mock.patch.object(kap, "check", return_value=[KAP]) as asked, \
                    mock.patch.object(triage, "triage", return_value=[]), redirect_stdout(io.StringIO()):
                self.assertEqual(triage.main(["--days", "14"]), 0)
            self.assertEqual(asked.call_count, kap_calls)


if __name__ == "__main__":
    unittest.main()
