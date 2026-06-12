import unittest
from unittest.mock import patch

from app.main import create_app


class HealthTests(unittest.TestCase):
    def test_health_reports_healthy_database(self):
        app = create_app()

        with app.test_client() as client:
            response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["database"]["status"], "ok")

    def test_health_reports_unhealthy_database(self):
        app = create_app()

        with patch("app.main.check_database_ready", return_value={"status": "down", "error": "OperationalError"}):
            with app.test_client() as client:
                response = client.get("/health")

        self.assertEqual(response.status_code, 503)
        payload = response.get_json()
        self.assertEqual(payload["status"], "down")
        self.assertEqual(payload["database"]["status"], "down")
        self.assertEqual(payload["database"]["error"], "OperationalError")


if __name__ == "__main__":
    unittest.main()
