# Hong Kong Event Time

Event discovery app for Hong Kong with source-prioritized scraping, quality scoring, calendar and mobile list views, and per-source debug diagnostics.

## What changed
- Scraping now defaults to a curated priority set of 5 sources instead of treating every source equally.
- Each event gets a `quality_score`; low-confidence, generic, archive-like, duplicate, and stale rows are rejected before import.
- Manual scrapes run through a background queue with progress polling, per-source timeout, retry, and failure isolation.
- The UI now shows scrape health, source counts, imported/rejected totals, richer event details, empty-state actions, and a mobile-friendly list mode.
- Debug output includes raw fetched counts plus kept/rejected samples and reject reasons per source.

## Setup
```bash
cd /Users/leozille/Downloads/hk-event-time
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

Open [http://127.0.0.1:5050](http://127.0.0.1:5050)

## Key endpoints
- `GET /api/categories`
- `GET /api/events?start=<ISO>&end=<ISO>&category=music&free=1&district=central`
- `POST /api/scrape-now`
- `GET /api/scrape-status`
- `GET /api/debug/sources`

## Runtime config
Use `.env` for product settings:
- `SCRAPE_SOURCE_MODE=priority|all|lkf_nightlife`
- `SCRAPE_MIN_QUALITY_SCORE`
- `SCRAPE_SOURCE_TIMEOUT_SECONDS`
- `SCRAPE_RETRY_COUNT`
- `CACHE_TTL_SECONDS`
- `DATABASE_URL`

## Deployment baseline
- App server: `gunicorn wsgi:app --bind 0.0.0.0:5050 --workers 2 --threads 4`
- Reverse proxy: nginx or Caddy in front of Gunicorn
- Database: SQLite is still supported for local/dev, Postgres is the intended next production step
- Monitoring: use the scrape history/debug endpoints and source-level logs as the initial health surface

## Current limitations
- Some sources are JS-heavy or bot-protected, so even curated source scrapers can still return partial data.
- There is no Postgres migration layer yet; the app still relies on SQLAlchemy `create_all`.
- The in-process queue is good enough for one instance, but not a distributed worker setup.
