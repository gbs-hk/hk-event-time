import json
import logging
import unittest

from app.main import create_app


class AnalyticsTests(unittest.TestCase):
    def test_analytics_logger_allows_info_events(self):
        self.assertTrue(logging.getLogger("app.main").isEnabledFor(logging.INFO))

    def test_accepts_hket_event_and_logs_sanitized_payload(self):
        app = create_app()

        with self.assertLogs("app.main", level=logging.INFO) as logs:
            with app.test_client() as client:
                response = client.post(
                    "/api/analytics/events",
                    json={
                        "event_name": "HKET.search.changed",
                        "session_id": "session_123456",
                        "route": "/?ignored=true",
                        "properties": {
                            "has_query": True,
                            "search_length": 5,
                            "raw_query": "secret search text",
                        },
                    },
                )

        self.assertEqual(response.status_code, 202)
        payload = json.loads(logs.output[0].split("analytics.event ", 1)[1])
        self.assertEqual(payload["event_name"], "HKET.search.changed")
        self.assertEqual(payload["session_id"], "session_123456")
        self.assertEqual(payload["route"], "/")
        self.assertEqual(payload["properties"], {"has_query": True, "search_length": 5})

    def test_rejects_non_hket_event_names(self):
        app = create_app()

        with app.test_client() as client:
            response = client.post(
                "/api/analytics/events",
                json={
                    "event_name": "Other.search.changed",
                    "session_id": "session_123456",
                },
            )

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
