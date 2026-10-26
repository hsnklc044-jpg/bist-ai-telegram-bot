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

    def test_panel_template_renders(self):
        from jinja2 import Environment, FileSystemLoader

        from core.config.paths import WEB_TEMPLATES_DIR

        env = Environment(loader=FileSystemLoader(str(WEB_TEMPLATES_DIR)), autoescape=True)
        html = env.get_template("dashboard.html").render(
            dashboard=self.dashboard, portfolio_source="işlem defteri (sanal hesap)"
        )

        self.assertIn(self.dashboard.decision.action, html)
        self.assertNotIn("MarketRegimeType.", html)
        self.assertIn("getiri tahmin gücü bulunmadı", html)
        self.assertIn("Portföy kaynağı: işlem defteri (sanal hesap)", html)


class WebPanelTest(unittest.TestCase):
    """FastAPI panel end to end (needs fastapi + httpx, installed from requirements.lock)."""

    def test_routes(self):
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("fastapi not installed")

        from core import __version__
        from core.web.app import app

        client = TestClient(app)
        with offline_market():
            self.assertEqual(client.get("/health").json()["version"], __version__)
            page = client.get("/dashboard")
            css = client.get("/static/css/style.css")
            root = client.get("/", follow_redirects=False)

        self.assertEqual(page.status_code, 200)
        self.assertIn("QuantBIST özet", page.text)
        self.assertIn("Piyasa", page.text)
        self.assertIn("Sanal hesap", page.text)
        self.assertIn("AL/SAT önerisi vermez", page.text)
        self.assertEqual(css.status_code, 200)
        self.assertEqual(root.headers["location"], "/dashboard")
