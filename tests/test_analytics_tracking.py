import os
import unittest
from unittest.mock import Mock, patch

from app.analytics import application_insights_config, parse_connection_string, track_event


class AnalyticsTrackingTests(unittest.TestCase):
    def test_parses_application_insights_connection_string(self):
        parts = parse_connection_string(
            "InstrumentationKey=abc;IngestionEndpoint=https://example.test/;ApplicationId=app"
        )

        self.assertEqual(parts["InstrumentationKey"], "abc")
        self.assertEqual(parts["IngestionEndpoint"], "https://example.test/")

    def test_config_prefers_connection_string(self):
        with patch.dict(
            os.environ,
            {
                "APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=abc;IngestionEndpoint=https://example.test/",
                "APPINSIGHTS_INSTRUMENTATIONKEY": "fallback",
            },
        ):
            self.assertEqual(application_insights_config(), ("abc", "https://example.test"))

    @patch("app.analytics.requests.post")
    def test_track_event_posts_custom_event_envelope(self, post):
        response = Mock()
        response.raise_for_status.return_value = None
        post.return_value = response

        with patch.dict(
            os.environ,
            {"APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=abc;IngestionEndpoint=https://example.test/"},
        ):
            self.assertTrue(
                track_event(
                    "HKET.route.viewed",
                    {"session_id": "session123", "route": "/", "result_count": 3, "has_query": False},
                )
            )

        post.assert_called_once()
        url = post.call_args.args[0]
        envelope = post.call_args.kwargs["json"][0]
        self.assertEqual(url, "https://example.test/v2/track")
        self.assertEqual(envelope["iKey"], "abc")
        self.assertEqual(envelope["data"]["baseData"]["name"], "HKET.route.viewed")
        self.assertEqual(envelope["data"]["baseData"]["properties"]["session_id"], "session123")
        self.assertEqual(envelope["data"]["baseData"]["properties"]["has_query"], "false")
        self.assertEqual(envelope["data"]["baseData"]["measurements"]["result_count"], 3.0)


if __name__ == "__main__":
    unittest.main()
