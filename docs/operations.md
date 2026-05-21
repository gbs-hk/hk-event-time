# Operations Runbook

This runbook explains how to diagnose and recover common production issues for Hong Kong Event Time. Use it when you are on call and need a repeatable checklist instead of guessing.

## Production References

- Production site: <https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/>
- Health endpoint: <https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/health>
- GitHub Actions: <https://github.com/gbs-hk/hk-event-time/actions>
- Azure App Service: `hk-event-time`
- Azure resource group: `hk-event-time`
- Alerting dashboard (Epic 2): TODO: add link when the team has configured Azure Monitor, UptimeRobot, Better Stack, or another alerting tool.
- Analytics dashboard (Epic 1): TODO: add link when user analytics are implemented.

## Required Access

- GitHub access to `gbs-hk/hk-event-time`.
- Azure access to the `hk-event-time` App Service or help from someone who has it.
- Azure CLI installed locally.
- Authenticated Azure CLI session:

```bash
az login
```

## Fast Checks

Use these before making changes.

```bash
curl -i https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/
curl -i https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/health
curl -i "https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/api/events?start=2026-05-01T00:00:00%2B08:00&end=2026-06-01T00:00:00%2B08:00"
```

Check Azure app configuration and logs:

```bash
az webapp config show --name hk-event-time --resource-group hk-event-time
az webapp config appsettings list --name hk-event-time --resource-group hk-event-time
az webapp log tail --name hk-event-time --resource-group hk-event-time
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

Then inspect Azure logs:

```bash
az webapp log tail --name hk-event-time --resource-group hk-event-time
```

Look for startup errors such as:

- missing Python package;
- Gunicorn startup failure;
- database path or permission error;
- wrong port or startup command;
- uncaught exception during Flask app startup.

### Recovery

Restart the Azure App Service:

```bash
az webapp restart --name hk-event-time --resource-group hk-event-time
```

If the latest deploy introduced the outage, use the rollback section below.

### Escalate When

- You do not have Azure permission to inspect logs or restart the app.
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

Inspect Azure logs for scheduler or scraper errors:

```bash
az webapp log tail --name hk-event-time --resource-group hk-event-time
```

### Recovery

- Run a manual scrape.
- Restart the app if the scheduler appears stuck:

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
