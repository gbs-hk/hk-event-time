# Quiz Prep Cards

Use these for active recall. Each answer points to the code path to verify.

1. **What is the project in one sentence?**  
   A Flask app that collects Hong Kong events, stores them, and serves a calendar UI. See [`README.md`](../README.md) and [`app/main.py`](../app/main.py).

2. **What stack should contributors keep?**  
   A single Flask stack: `app/`, `templates/`, `static/`, `run.py`, and `wsgi.py`. See [`AGENTS.md`](../AGENTS.md).

3. **Where is the Flask app created?**  
   `create_app()` in [`app/main.py`](../app/main.py).

4. **Which route renders the main page?**  
   `GET /` returns `templates/index.html` from [`app/main.py`](../app/main.py).

5. **Which route returns event data to the browser?**  
   `GET /api/events` in [`app/main.py`](../app/main.py).

6. **How does `/api/events` handle time zones?**  
   It parses `start` and `end`, assumes Hong Kong time for naive values, converts to UTC, then returns Hong Kong ISO strings. See `parse_request_datetime_to_utc()` and `utc_naive_to_hk_iso()` in [`app/main.py`](../app/main.py).

7. **Where are event rows queried?**  
   `query_events()` in [`app/services.py`](../app/services.py) filters by UTC start/end and optional categories.

8. **Where is the database model defined?**  
   The `Event` SQLAlchemy model is in [`app/models.py`](../app/models.py).

9. **How is the database session configured?**  
   [`app/database.py`](../app/database.py) builds the SQLAlchemy engine and `SessionLocal`.

10. **How does the health check work?**  
    `GET /health` calls `check_database_ready()` and returns `200` when DB status is `ok`, otherwise `503`. See [`app/main.py`](../app/main.py) and [`app/database.py`](../app/database.py).

11. **Which route can manually trigger scraping?**  
    `POST /api/scrape-now` calls `run_scrape()` in [`app/main.py`](../app/main.py).

12. **Which route helps debug sources?**  
    `GET /api/debug/sources` returns source mode, focus categories, upcoming counts, and optionally a detailed scrape run. See [`app/main.py`](../app/main.py).

13. **Where is scrape orchestration implemented?**  
    `run_scrape_detailed()` in [`app/services.py`](../app/services.py).

14. **What happens to duplicate events during scraping?**  
    `run_scrape_detailed()` tracks semantic keys and skips duplicates before upserting. See [`app/services.py`](../app/services.py).

15. **Where is category inference defined?**  
    `infer_category()` and `CATEGORY_DEFINITIONS` live in [`app/categories.py`](../app/categories.py).

16. **How does the API expose category metadata?**  
    `GET /api/categories` returns `categories_for_api()` from [`app/categories.py`](../app/categories.py), routed in [`app/main.py`](../app/main.py).

17. **Where are scraper source lists built?**  
    `build_scrapers()` in [`app/scrapers/sources.py`](../app/scrapers/sources.py).

18. **What is `ScrapedEvent`?**  
    The normalized scraper output type before database storage. See [`app/scrapers/base.py`](../app/scrapers/base.py).

19. **What keeps the production scrape running daily?**  
    APScheduler in [`app/scheduler.py`](../app/scheduler.py), started from `create_app()` in [`app/main.py`](../app/main.py).

20. **Why does the scheduler avoid starting twice locally?**  
    `start_scheduler()` only runs outside local debug parent processes by checking `FLASK_ENV` and `WERKZEUG_RUN_MAIN`. See [`app/scheduler.py`](../app/scheduler.py).

21. **Where are runtime settings read from?**  
    Environment variables in [`app/config.py`](../app/config.py), including database URL, scraper timeout, source mode, and schedule hour.

22. **How are PostgreSQL URLs normalized?**  
    `Config.normalized_database_url()` converts `postgres://` or plain `postgresql://` to `postgresql+psycopg://`. See [`app/config.py`](../app/config.py).

23. **Where is the frontend behavior?**  
    Calendar/list behavior is in [`static/app.js`](../static/app.js), with markup in [`templates/index.html`](../templates/index.html).

24. **How does deployment happen?**  
    Pushes to `main` run [`.github/workflows/azure-deploy.yml`](../.github/workflows/azure-deploy.yml), deploying `wsgi:app` to Azure App Service.

25. **What should be checked before marking a task done?**  
    Pull latest `main`, run relevant tests, avoid secrets, consider analytics/PII and a11y when touched, then record the work item ID. See [`AGENTS.md`](../AGENTS.md) and [`.github/pull_request_template.md`](../.github/pull_request_template.md).

Teacher review note: students should pick any five cards, open the linked files, and confirm the answer still matches the code before assessment.
