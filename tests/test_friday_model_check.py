"""
The Friday model check runs by itself (user's request 05.11.2026: no commands to run by hand). After the
Friday refit the daily job runs scripts/kart_modeli_kontrol.py and sends its output to Telegram, so the
user sees "SONUÇ: DOĞRULANDI" (or not) without opening PowerShell. A failing check never stops the job.
"""

import unittest
from datetime import date
from unittest import mock

from core.reports import daily


class FridayCheckTest(unittest.TestCase):
    def test_friday_refit_sends_the_check_output(self):
        from core.ml import signal_filter as S

        sent = []

        def fake_main():
            print("SONUÇ: DOĞRULANDI")
            return 0

        with mock.patch.object(S, "_daily", return_value=({}, None)), \
                mock.patch.object(S, "fit_live", return_value=812), \
                mock.patch.object(daily, "_model_check_main", return_value=fake_main):
            daily._refit_signal_model(date(2026, 11, 6), sent.append)
        self.assertEqual(len(sent), 1)
        self.assertIn("Cuma model kontrolü", sent[0])
        self.assertIn("SONUÇ: DOĞRULANDI", sent[0])

    def test_not_friday_sends_nothing(self):
        sent = []
        daily._refit_signal_model(date(2026, 11, 5), sent.append)
        self.assertEqual(sent, [])

    def test_a_crashing_check_is_reported_not_raised(self):
        from core.ml import signal_filter as S

        sent = []

        def broken():
            raise RuntimeError("okunamadı")

        with mock.patch.object(S, "_daily", return_value=({}, None)), \
                mock.patch.object(S, "fit_live", return_value=812), \
                mock.patch.object(daily, "_model_check_main", return_value=broken):
            daily._refit_signal_model(date(2026, 11, 6), sent.append)
        self.assertIn("DOĞRULANAMADI", sent[0])
        self.assertIn("okunamadı", sent[0])

    def test_the_real_script_is_found(self):
        main = daily._model_check_main()
        self.assertTrue(callable(main))


if __name__ == "__main__":
    unittest.main()
