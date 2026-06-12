from __future__ import annotations

from datetime import UTC, datetime
import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)


def parse_connection_string(value: str) -> dict[str, str]:
    parts: dict[str, str] = {}
    for item in value.split(";"):
        if "=" not in item:
            continue
        key, raw_value = item.split("=", 1)
        parts[key.strip()] = raw_value.strip()
    return parts


def application_insights_config() -> tuple[str, str] | None:
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
    parts = parse_connection_string(connection_string)
    instrumentation_key = parts.get("InstrumentationKey") or os.getenv("APPINSIGHTS_INSTRUMENTATIONKEY", "")
    ingestion_endpoint = parts.get("IngestionEndpoint", "https://dc.services.visualstudio.com/")

    if not instrumentation_key:
        return None
    return instrumentation_key, ingestion_endpoint.rstrip("/")


def track_event(event_name: str, properties: dict[str, Any]) -> bool:
    config = application_insights_config()
    if config is None:
        return False

    instrumentation_key, ingestion_endpoint = config
    string_properties: dict[str, str] = {}
    measurements: dict[str, float] = {}

    for key, value in properties.items():
        if isinstance(value, bool):
            string_properties[key] = str(value).lower()
        elif isinstance(value, int | float):
            measurements[key] = float(value)
        elif value is not None:
            string_properties[key] = str(value)

    envelope = {
        "name": "Microsoft.ApplicationInsights.Event",
        "time": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "iKey": instrumentation_key,
        "data": {
            "baseType": "EventData",
            "baseData": {
                "ver": 2,
                "name": event_name,
                "properties": string_properties,
                "measurements": measurements,
            },
        },
    }

    try:
        response = requests.post(f"{ingestion_endpoint}/v2/track", json=[envelope], timeout=2)
        response.raise_for_status()
        return True
    except requests.RequestException as exc:
        logger.warning("analytics.appinsights.failed %s", exc.__class__.__name__)
        return False
