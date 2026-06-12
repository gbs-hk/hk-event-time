# Operations Runbook

This runbook explains how to diagnose and recover common production issues for Hong Kong Event Time. Use it when you are on call and need a repeatable checklist instead of guessing.

## Production References

- Production site: <https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/>
- Health endpoint: <https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/health>
- GitHub Actions: <https://github.com/gbs-hk/hk-event-time/actions>
- Azure App Service: `hk-event-time`
- Azure resource group: `hk-event-time`
- Alerting dashboard (Epic 2): TODO: add link when the team has configured Azure Monitor, UptimeRobot, Better Stack, or another alerting tool.
- Analytics dashboard (Epic 1): [HK Event Time Analytics Dashboard](https://portal.azure.com/#@acuhlmanngmail.onmicrosoft.com/resource/subscriptions/3a240a56-b0ac-4a39-91ad-03b8059cf63b/resourceGroups/hk-event-time/providers/microsoft.insights/workbooks/21b7a9d8-8e6b-4c5e-9c2e-0f4d7a1b8c21/workbook)

## Required Access

### Production deploy boundary

**All application code and App Service configuration changes go through GitHub**, not the Azure Portal or `az webapp` write commands:

1. Commit and **push to `main`** on [`gbs-hk/hk-event-time`](https://github.com/gbs-hk/hk-event-time) (no teacher approval or PR required; the team is responsible for the outcome).
2. [`.github/workflows/azure-deploy.yml`](../.github/workflows/azure-deploy.yml) deploys on every push to `main` via OIDC (build, app settings merge, zip deploy).

Optional: use a branch and PR for your own review, but that is not required.

Do not use Portal **Configuration**, `az webapp config appsettings set`, `az webapp deploy`, `az webapp restart`, or SCM publish for production changes.

### Students (`hk-event-time-student-agents`)

Entra group members in project **Contributors** on [Azure DevOps](https://dev.azure.com/gbs-hk/hk-event-time) with **Write** on the GitHub repo.

Azure RBAC on resource group `hk-event-time` (read + monitoring/performance **write only**):

| Role | Scope | Use for |
|------|-------|---------|
| Reader | Resource group | Read app config, list resources |
| Monitoring Reader | Resource group | View metrics and alert state |
| Monitoring Contributor | Resource group | Availability tests, alerts, action groups, diagnostic settings |
| Application Insights Component Contributor | `appinsights-hk-event-time` | Workbooks, dashboards, KQL |
| Load Test Owner | Resource group | Azure Load Testing resources and test runs |

Students **do not** have Website Contributor, Contributor, or Owner on the App Service or resource group.

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

Expected health response:

```json
{"status":"ok"}
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
- Body contains `{"status":"ok"}`

### Diagnose

Check the Flask route in `app/main.py`. The `/health` route should return:

```json
{"status":"ok"}
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
