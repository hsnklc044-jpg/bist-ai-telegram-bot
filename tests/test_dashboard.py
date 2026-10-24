import unittest

from tests.helpers import offline_market


class DashboardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from core.dashboard.service import get_dashboard

        with offline_market():
            cls.dashboard = get_dashboard()

    def test_dashboard_is_complete(self):
        d = self.dashboard

        self.assertTrue(d.ready)
        self.assertIsNotNone(d.committee)
        self.assertEqual(d.decision.committee, d.committee)
        self.assertTrue(0 <= d.decision.ai_score <= 100)

    def test_optimizer_names_positions(self):
        opt = self.dashboard.portfolio.optimization

        self.assertEqual(opt.best_symbol, opt.largest_position)
        self.assertEqual(opt.worst_symbol, opt.smallest_position)
        self.assertNotEqual(opt.best_symbol, "-")

    def test_reports_and_exports(self):
        from core.export.service import export_report
        from core.reports import generate_summary_report

        self.assertIn("QUANTBIST SUMMARY", generate_summary_report(self.dashboard))

        for fmt in ("txt", "markdown", "html", "json"):
            with self.subTest(fmt=fmt):
                self.assertTrue(export_report(self.dashboard, fmt))

    def test_flask_template_renders(self):
        from app import app

        with app.test_request_context():
            from flask import render_template

            html = render_template("dashboard.html", dashboard=self.dashboard)

        self.assertIn(self.dashboard.decision.action, html)
        self.assertNotIn("MarketRegimeType.", html)


class DashboardWithoutDataTest(unittest.TestCase):
    def test_flask_returns_503(self):
        from app import app
        from tests.helpers import FakeProvider

        with offline_market(FakeProvider(fail=True)):
            response = app.test_client().get("/")

        self.assertEqual(response.status_code, 503)
