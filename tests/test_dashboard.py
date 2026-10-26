import unittest

from tests.helpers import offline_market


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
            root = client.get("/", follow_redirects=False)

        self.assertEqual(page.status_code, 200)
        self.assertIn("QuantBIST özet", page.text)
        self.assertIn("Piyasa", page.text)
        self.assertIn("Sanal hesap", page.text)
        self.assertIn("AL/SAT önerisi vermez", page.text)
        self.assertEqual(root.headers["location"], "/dashboard")
