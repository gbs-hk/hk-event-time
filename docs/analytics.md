# Analytics Dashboard

This page documents the student analytics dashboard for Azure DevOps item `#21`.

The app emits privacy-minimal analytics events through `POST /api/analytics/events`. Frontend events use the `HKET.*` namespace and are logged as structured `analytics.event` traces. The payload includes an anonymous browser-session id, the route path, and allowlisted properties only. It does not send names, emails, raw search text, ticket URLs, map URLs, cookies, or secrets.

## Open Dashboard

Open the shared Azure Workbook: [HK Event Time Analytics Dashboard](https://portal.azure.com/#@acuhlmanngmail.onmicrosoft.com/resource/subscriptions/3a240a56-b0ac-4a39-91ad-03b8059cf63b/resourceGroups/hk-event-time/providers/microsoft.insights/workbooks/21b7a9d8-8e6b-4c5e-9c2e-0f4d7a1b8c21/workbook).

If the deep link does not open directly, go to Azure Portal -> Application Insights `appinsights-hk-event-time` -> Workbooks -> `HK Event Time Analytics Dashboard`.

## Event Names

| Event | Purpose | Fields |
| --- | --- | --- |
| `HKET.session.started` | Count browser sessions | `route` |
| `HKET.route.viewed` | Count route views | `route` |
| `HKET.calendar.view_changed` | Compare month/week/day use | `view_type` |
| `HKET.calendar.results_loaded` | Understand event availability in the current view | `view_type`, `result_count`, `category_count`, `has_query` |
| `HKET.category_filter.changed` | Measure filter usage | `category_count`, `selected_all` |
| `HKET.search.changed` | Measure search usage without storing the query | `has_query`, `search_length` |
| `HKET.day_events.opened` | Measure day drill-down usage | `result_count` |
| `HKET.event_details.opened` | Measure event detail interest | `event_category`, `event_source` |
| `HKET.scrape_refresh.clicked` | Measure manual refresh attempts | `source` |
| `HKET.api_events.failed` | Client-side signal that calendar event loading failed | `view_type` |

## Workbook Tiles

The shared workbook already contains the required 7-day tiles. The KQL below documents each tile so the dashboard can be audited or recreated if needed.

### Sessions

```kusto
AppTraces
| where TimeGenerated > ago(7d)
| where Message has "analytics.event"
| extend payload = parse_json(extract(@"\{.*\}", 0, Message))
| where tostring(payload.event_name) == "HKET.session.started"
| summarize sessions = dcount(tostring(payload.session_id)) by bin(TimeGenerated, 1d)
| order by TimeGenerated asc
```

### Top Routes

```kusto
AppTraces
| where TimeGenerated > ago(7d)
| where Message has "analytics.event"
| extend payload = parse_json(extract(@"\{.*\}", 0, Message))
| where tostring(payload.event_name) == "HKET.route.viewed"
| summarize route_views = count(), sessions = dcount(tostring(payload.session_id)) by route = tostring(payload.route)
| order by route_views desc
```

### `/api/events` Error Rate

Use the `AppRequests` table when Application Insights request collection is enabled:

```kusto
AppRequests
| where TimeGenerated > ago(7d)
| where Name has "/api/events" or Url has "/api/events"
| summarize total = count(),
            failed = countif(Success == false or toint(ResultCode) >= 500)
          by bin(TimeGenerated, 1h)
| extend error_rate = iff(total == 0, 0.0, todouble(failed) / todouble(total))
| order by TimeGenerated asc
```

If request collection is unavailable, use the client-side failure signal as a fallback:

```kusto
AppTraces
| where TimeGenerated > ago(7d)
| where Message has "analytics.event"
| extend payload = parse_json(extract(@"\{.*\}", 0, Message))
| where tostring(payload.event_name) == "HKET.api_events.failed"
| summarize client_failures = count() by bin(TimeGenerated, 1h)
| order by TimeGenerated asc
```

If `/api/events` error rate spikes, follow the site/API diagnosis steps in [operations.md](operations.md#site-down).

### `HKET.*` Events

```kusto
AppTraces
| where TimeGenerated > ago(7d)
| where Message has "analytics.event"
| extend payload = parse_json(extract(@"\{.*\}", 0, Message))
| where tostring(payload.event_name) startswith "HKET."
| summarize events = count(),
            sessions = dcount(tostring(payload.session_id))
          by event_name = tostring(payload.event_name)
| order by events desc
```

### Event Detail Interest

```kusto
AppTraces
| where TimeGenerated > ago(7d)
| where Message has "analytics.event"
| extend payload = parse_json(extract(@"\{.*\}", 0, Message))
| where tostring(payload.event_name) == "HKET.event_details.opened"
| summarize opens = count()
          by category = tostring(payload.properties.event_category),
             source = tostring(payload.properties.event_source)
| order by opens desc
```

## Product Insight And Follow-Up

Insight: before this change, the project had operational scrape visibility but no user analytics, so the team could not tell whether users actually used filters, search, day drill-downs, or event detail cards. That made product decisions about the calendar UI mostly opinion-based.

Decision: instrument privacy-minimal `HKET.*` events first and use a 7-day dashboard before changing the UI again. The most important product signal is `HKET.event_details.opened` by category/source, because it tells us which event types users show enough interest in to open details.

Follow-up: after 7 days of production traffic, review the workbook. If `HKET.category_filter.changed` and `HKET.search.changed` are low, keep the menu simple and prioritize event data quality. If they are high, improve filter/search discoverability and add a saved default view. If `/api/events` error rate spikes, use the linked operations runbook before interpreting product analytics.
