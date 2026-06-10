# Operations Runbook

This runbook explains how to diagnose and recover common production issues for Hong Kong Event Time. Use it when you are on call and need a repeatable checklist instead of guessing.

## Production References

- Production site: <https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/>
- Health endpoint: <https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/health>
- GitHub Actions: <https://github.com/gbs-hk/hk-event-time/actions>
- Azure App Service: `hk-event-time`
- Azure resource group: `hk-event-time`
- Alerting dashboard (Epic 2): TODO: add link when the team has configured Azure Monitor, UptimeRobot, Better Stack, or another alerting tool.
- Analytics dashboard (Epic 1): [analytics workbook queries and product decision](analytics.md).

## Required Access

### Production deploy boundary

**All application code and App Service configuration changes go through GitHub**, not the Azure Portal or `az webapp` write commands:

1. Commit and **push to `main`** on [`gbs-hk/hk-event-time`](https://github.com/gbs-hk/hk-event-time) (no teacher approval or PR required; the team is responsible for the outcome).
2. [`.github/workflows/azure-deploy.yml`](../.github/workflows/azure-deploy.yml) deploys on every push to `main` via OIDC (build, app settings merge, zip deploy).

Optional: use a branch and PR for your own review, but that is not required.

Do not use Portal or `az` for routine **application** deploys (zip/SCM/restart). Students may use Portal **Configuration** for observability-related app settings when needed for backlog work; code changes still go through GitHub → Actions.

### Students (`hk-event-time-student-agents`)

Entra group members need **three** layers (see [student-entitlements.md](student-entitlements.md)):

1. **Entra group** `hk-event-time-student-agents` (Azure RBAC below).
2. **Azure DevOps** project **Contributors**, **hk-event-time Team**, and **Build Administrators** (per-user; the Entra group is not synced into DevOps).
3. **GitHub** **Write** on [`gbs-hk/hk-event-time`](https://github.com/gbs-hk/hk-event-time).

Azure RBAC for Entra group `hk-event-time-student-agents`:

| Role | Scope | Use for |
|------|-------|---------|
| Reader | Subscription | See subscription in portal filters; list resources |
| Reader | Resource group | Read resources |
| Website Contributor | Resource group + App Service `hk-event-time` | App settings (e.g. `APPLICATIONINSIGHTS_CONNECTION_STRING` for Epic 15.1); portal config — routine **code** deploy still via GitHub |
| Monitoring Reader | Resource group | View metrics and alert state |
| Monitoring Contributor | Resource group + `appinsights-hk-event-time` | Availability tests, alerts, action groups, diagnostics (stories **2.2**, **2.3**) |
| Monitoring Metrics Publisher | App Service `hk-event-time` | Custom metrics from the app (after students add instrumentation) |
| Application Insights Component Contributor | `appinsights-hk-event-time` | Metric/log alert rules, workbooks, dashboards (story **2.3**) |
| Log Analytics Reader | `ws-3a240a56-southeasta` (linked workspace) | Run KQL in Logs and in alert query text (story **2.3**) |
| Log Analytics Contributor | Workspace + resource group | Create/edit log-based alert rules (story **2.3**) |
| Load Test Owner | Resource group | Azure Load Testing resources and test runs (Epic 16) |

**Students:** portal bookmarks in [student-azure-access.md](student-azure-access.md); boards at [work item 14](https://dev.azure.com/gbs-hk/hk-event-time/_workitems/edit/14) and the [Epics board](https://dev.azure.com/gbs-hk/hk-event-time/_boards/board/t/hk-event-time%20Team/Epics).

**Teachers:** after adding someone to the Entra group, run (Owner on subscription + DevOps admin):

```bash
bash scripts/apply-student-entitlements.sh
```

Or confirm IAM in Portal → **hk-event-time** → **Access control (IAM)** → filter `hk-event-time-student-agents`, and add the new email to DevOps/GitHub per [student-entitlements.md](student-entitlements.md).

Students **do not** have Contributor or Owner on the subscription; production **application** deploy remains GitHub Actions on push to `main`.

### Teachers / platform owners

Contributor (or equivalent) on the App Service or resource group for `az webapp restart`, log stream, and emergency app settings changes outside the pipeline.

### Everyone

- Azure CLI installed locally.
- Authenticated session: `az login`
- GitHub access to `gbs-hk/hk-event-time` (students: Write, including push to `main`; deploy secrets stay in Actions).

## Fast Checks

Use these before making changes. **All roles** can run the `curl` probes.

```bash
curl -i https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/
curl -i https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/health
curl -i "https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/api/events?start=2026-05-01T00:00:00%2B08:00&end=2026-06-01T00:00:00%2B08:00"
```

**Students:** inspect app settings read-only; use Application Insights / Log Analytics for logs and metrics.

```bash
az webapp config show --name hk-event-time --resource-group hk-event-time
az webapp config appsettings list --name hk-event-time --resource-group hk-event-time
```

**Teachers only** (live log stream and restart):

```bash
az webapp log tail --name hk-event-time --resource-group hk-event-time
az webapp restart --name hk-event-time --resource-group hk-event-time
```

## 1. Site Down

### Symptoms

- The production URL does not load.
- Browser shows `503`, `Application Error`, timeout, or connection errors.
- GitHub Actions post-deploy healthcheck fails.

### First Checks

```bash
curl -i https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/
curl -i https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/health
```

Expected healthy response:

```json
{"database":{"status":"ok"},"status":"ok"}
```

### Diagnose

Open the latest GitHub Actions run:

<https://github.com/gbs-hk/hk-event-time/actions>

Then inspect logs (**teachers:** `az webapp log tail`; **students:** Application Insights → Logs / Failures for `hk-event-time`):

```bash
# Teachers only
az webapp log tail --name hk-event-time --resource-group hk-event-time
```

Look for startup errors such as:

- missing Python package;
- Gunicorn startup failure;
- database path or permission error;
- wrong port or startup command;
- uncaught exception during Flask app startup.

### Recovery

**Teachers only** — restart the Azure App Service:

```bash
az webapp restart --name hk-event-time --resource-group hk-event-time
```

**Students:** escalate to a teacher for restart; if the latest deploy introduced the outage, use the rollback section (`git revert` and push to `main`).

### Escalate When

- You need a teacher to restart the app or change app settings outside the deploy workflow.
- The app still fails after restart and the logs show an Azure platform or permission issue.

## 2. Health Degraded

### Symptoms

- The site may load, but `/health` fails.
- The post-deploy healthcheck fails at the health step.
- Azure or an external monitor reports the app as unhealthy.

### First Checks

```bash
curl -i https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/health
```

Healthy result:

- HTTP status `200`
- Body contains top-level `"status":"ok"`
- Body contains database `"status":"ok"`

Unhealthy database result:

- HTTP status `503`
- Body contains top-level `"status":"down"`
- Body contains database `"status":"down"`

Example unhealthy response:

```json
{"database":{"error":"OperationalError","status":"down"},"status":"down"}
```

### Diagnose

Check the Flask route in `app/main.py`. The `/health` route calls the database readiness check from `app/database.py`.

The healthy response should return:

```json
{"database":{"status":"ok"},"status":"ok"}
```

Check Azure app settings:

```bash
az webapp config appsettings list --name hk-event-time --resource-group hk-event-time
```

Important settings include:

- `FLASK_ENV=production`
- `DATABASE_URL=sqlite:////home/data/events.db`
- `PORT=8000`
- `WEBSITES_PORT=8000`
- `WEBSITE_WARMUP_PATH=/health`
- `WEBSITE_WARMUP_STATUSES=200`

### Recovery

If `/health` fails because the app is not running, follow the Site Down section. If `/health` was changed in code, restore the simple route behavior and deploy again.

## 3. Empty Calendar

### Symptoms

- The site loads.
- Calendar UI is visible.
- No events appear for the selected date range.

### First Checks

Check whether the events API returns data:

```bash
curl -i "https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/api/events?start=2026-05-01T00:00:00%2B08:00&end=2026-06-01T00:00:00%2B08:00"
```

Check source diagnostics:

```bash
curl -i "https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/api/debug/sources"
```

Run detailed diagnostics if needed:

```bash
curl -i "https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/api/debug/sources?run=1"
```

### Diagnose

- If `/api/events` returns events, the issue is likely frontend filtering or rendering.
- If `/api/events` returns an empty list but `/api/debug/sources` shows upcoming events, check query dates and category filters.
- If `/api/debug/sources?run=1` shows failed or empty sources, inspect the scraper errors and source websites.
- If only non-focused categories are being fetched, check `SCRAPE_FOCUS_CATEGORIES`.

### Recovery

Trigger a manual scrape:

```bash
curl -X POST https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/api/scrape-now
```

Then query events again:

```bash
curl -i "https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/api/events?start=2026-05-01T00:00:00%2B08:00&end=2026-06-01T00:00:00%2B08:00"
```

If the scrape still produces no useful events, review `app/scrapers/sources.py`, `app/services.py`, and the source diagnostics output.

## 4. Stale Scrape

### Symptoms

- The calendar shows old events.
- New events do not appear after waiting for the scheduled scrape.
- Source diagnostics show outdated or unchanged event counts.

### First Checks

Check upcoming source counts:

```bash
curl -i "https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/api/debug/sources"
```

Run a scrape manually:

```bash
curl -X POST https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/api/scrape-now
```

Check detailed scrape output:

```bash
curl -i "https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/api/debug/sources?run=1"
```

### Diagnose

Check these code paths:

- `app/scheduler.py` starts the daily scrape job.
- `app/services.py` runs `run_scrape()` and `run_scrape_detailed()`.
- `app/scrapers/sources.py` decides which scrapers are active.
- `app/config.py` controls `SCHEDULE_HOUR_UTC`, `SCRAPE_SOURCE_MODE`, and `SCRAPE_FOCUS_CATEGORIES`.

Inspect logs for scheduler or scraper errors (teachers: log tail; students: Application Insights).

```bash
# Teachers only
az webapp log tail --name hk-event-time --resource-group hk-event-time
```

Structured scrape completion logs include:

- `event`: `scrape.run.finished`
- `scrape.events_persisted`: events inserted or updated in that run
- `failed_sources`: source count that raised errors
- `empty_sources`: source count that returned no usable events
- `sources_total`: configured source count for the run
- `duration_ms`: run duration
- `success`: whether all sources completed without exceptions

Application Insights / Log Analytics KQL for recent scrape outcomes:

```kusto
traces
| where message has "scrape.run.finished"
| extend payload = parse_json(extract(@"\{.*\}", 0, message))
| project timestamp,
          events_persisted = toint(payload["scrape.events_persisted"]),
          failed_sources = toint(payload.failed_sources),
          empty_sources = toint(payload.empty_sources),
          sources_total = toint(payload.sources_total),
          duration_ms = toint(payload.duration_ms),
          success = tostring(payload.success)
| order by timestamp desc
```

Recommended alerts:

- No successful scrape in 36h: alert when the KQL above filtered to `success == "true"` has zero rows in the last 36 hours.
- Zero events for 2 consecutive runs: alert when the two most recent `scrape.run.finished` rows both have `events_persisted == 0`.

### Recovery

- Run a manual scrape.
- **Teachers only** — restart the app if the scheduler appears stuck:

```bash
az webapp restart --name hk-event-time --resource-group hk-event-time
```

- If sources changed their HTML and scrapers fail, update the affected scraper and release through the normal GitHub Actions deployment.

## 5. Deploy Rollback

### Symptoms

- A recent commit deployed successfully but broke production behavior.
- Healthcheck or manual smoke tests fail after a release.
- The latest GitHub Actions run corresponds to the broken behavior.

### Preferred Rollback: Revert the Bad Commit

Use `git revert` so the team history stays intact.

```bash
git log --oneline
git revert <bad-commit-sha>
git push origin main
```

GitHub Actions will deploy the revert commit automatically.

### Verify Rollback

After the workflow finishes, check:

```bash
curl -i https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/
curl -i https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/health
curl -i "https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/api/events?start=2026-05-01T00:00:00%2B08:00&end=2026-06-01T00:00:00%2B08:00"
```

Also confirm the GitHub Actions deploy and post-deploy healthcheck are green:

<https://github.com/gbs-hk/hk-event-time/actions>

### Avoid

Do not use `git reset --hard` plus force push on the shared `main` branch unless the team explicitly agrees. It rewrites shared history and makes recovery harder.

## Release Smoke Test

After any recovery or rollback, run this checklist:

1. Run local tests:

```bash
python -m unittest discover -s tests
```

2. Start the app locally:

```bash
python run.py
```

3. Push the fix or revert.
4. Confirm GitHub Actions deployment is green.
5. Confirm the public URL loads.
6. Confirm `/health` returns `{"status":"ok"}`.
7. Confirm `/api/events` returns a valid JSON response for a real date range.
