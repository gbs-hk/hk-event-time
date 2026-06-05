# Quiz Prep Cards

Use these for exam-style active recall. Every answer includes a real route, file, workflow, or doc path so the answer can be checked against the project instead of staying hand-wavy.

## Project Overview

1. **What is this project in one sentence?**  
   It is a Flask web app that collects Hong Kong event data from external sources, stores it in a database, and shows it in a calendar interface. Code path: [`README.md`](../README.md), [`app/main.py`](../app/main.py), [`templates/index.html`](../templates/index.html).

2. **Why is it more than just a website?**  
   It has several connected parts: frontend UI, backend API, database, scrapers, scheduler, GitHub deployment, Azure hosting, and Azure DevOps task tracking. The simple mental model is: sources -> scrapers -> database -> API -> calendar UI. Code path: [`docs/mental-model.md`](mental-model.md), [`app/scheduler.py`](../app/scheduler.py), [`.github/workflows/azure-deploy.yml`](../.github/workflows/azure-deploy.yml).

3. **How does event data flow through the system?**  
   Scrapers fetch raw event data, normalize it into a shared event shape, the service layer filters and stores it, and the frontend loads it through API endpoints. Code path: [`app/scrapers/base.py`](../app/scrapers/base.py), [`app/services.py`](../app/services.py), route `GET /api/events` in [`app/main.py`](../app/main.py).

4. **Why should the app not scrape live for every user request?**  
   Live scraping would make users wait for external websites. It is better that scraping runs in the background, saves data in the database, and the user-facing calendar loads quickly from stored data. Code path: scheduled scrape in [`app/scheduler.py`](../app/scheduler.py), manual route `POST /api/scrape-now` and read route `GET /api/events` in [`app/main.py`](../app/main.py).

5. **Why is the database important?**  
   It separates data collection from user browsing. The scraper can write events when it runs, while users can read already stored events quickly from the calendar API. Code path: [`app/models.py`](../app/models.py), [`app/database.py`](../app/database.py), `upsert_event()` and `query_events()` in [`app/services.py`](../app/services.py).

6. **Why do categories and timezones matter?**  
   Categories make messy event data easier to browse, and timezone handling prevents Hong Kong events from appearing on the wrong day or time. Code path: [`app/categories.py`](../app/categories.py), route `GET /api/categories` in [`app/main.py`](../app/main.py), [`tests/test_main_timezones.py`](../tests/test_main_timezones.py).

7. **How is the app deployed?**  
   Code changes are pushed to GitHub, GitHub Actions deploys the Flask app, and Azure App Service hosts it publicly. Code path: [`.github/workflows/azure-deploy.yml`](../.github/workflows/azure-deploy.yml), [`wsgi.py`](../wsgi.py), [`startup.sh`](../startup.sh).

8. **What is Azure DevOps used for?**  
   Azure DevOps is used for project management: tasks, backlog, board columns, ownership, and marking work as done after implementation and verification. Code path: Azure DevOps notes in [`AGENTS.md`](../AGENTS.md), student access docs in [`docs/student-azure-access.md`](student-azure-access.md), operations notes in [`docs/operations.md`](operations.md).

9. **What is the role of `README.md`?**  
   `README.md` explains the project for humans: what it does, how to run it, important environment variables, API endpoints, tests, and deployment notes. Code path: [`README.md`](../README.md), config values in [`app/config.py`](../app/config.py).

10. **What is the role of `AGENTS.md`?**  
    `AGENTS.md` gives AI coding agents project-specific rules, such as keeping the Flask architecture, using tests, avoiding secrets, and including Azure DevOps work item IDs in commits. Code path: [`AGENTS.md`](../AGENTS.md).

## AI And Critical Review

11. **How did AI help in this project?**  
    AI can help write code, debug errors, explain architecture, review risks, and suggest tests. The important point is that AI should assist understanding, not replace it. Code path: AI rules and review expectations in [`AGENTS.md`](../AGENTS.md), example review targets in [`docs/mental-model.md`](mental-model.md).

12. **What is a critical agent review?**  
    It means asking an AI agent to review the codebase like a senior engineer: find risks, missing tests, reliability problems, accessibility issues, deployment risks, and scalability limits before changing code. Code path: review routes in [`app/main.py`](../app/main.py), scraper reliability in [`app/services.py`](../app/services.py), a11y docs in [`docs/a11y.md`](a11y.md).

13. **What is a good prompt for reviewing this app?**  
    Ask the agent to focus on scraping reliability, sync vs async blocking, database scalability, observability, accessibility, user analytics, code quality, and Azure deployment risks. Also ask it to list the biggest risks first instead of rewriting everything. Code path: scraper flow in [`app/services.py`](../app/services.py), database config in [`app/database.py`](../app/database.py), deploy workflow in [`.github/workflows/azure-deploy.yml`](../.github/workflows/azure-deploy.yml).

14. **Why should AI answers be verified?**  
    AI can be wrong or miss project-specific context. Good use means asking questions, reading the referenced files, running tests, and understanding why a change matters before accepting it. Code path: test suite in [`tests/`](../tests), contribution rules in [`AGENTS.md`](../AGENTS.md).

## Observability, Monitoring, Alerting

15. **What does observability mean here?**  
    Observability means being able to understand what the app is doing when something goes wrong: whether the website is down, the scraper failed, a source returned zero events, or the database/API is slow. Code path: route `GET /health` in [`app/main.py`](../app/main.py), scrape logs in [`app/services.py`](../app/services.py), runbook in [`docs/operations.md`](operations.md).

16. **What is the difference between logs, metrics, and traces?**  
    Logs are timestamped events like "scrape finished". Metrics are numbers over time like duration, error rate, or events persisted. Traces show the path of one request through frontend, API, and database. Code path: `scrape.run.finished` log in [`app/services.py`](../app/services.py), KQL examples in [`docs/operations.md`](operations.md).

17. **Which scraper logs and metrics matter most?**  
    Important fields are `scrape.events_persisted`, `failed_sources`, `empty_sources`, `sources_total`, `duration_ms`, and `success`. They help detect stale calendar data and broken sources. Code path: [`app/services.py`](../app/services.py), [`tests/test_scrape_observability.py`](../tests/test_scrape_observability.py), [`docs/operations.md`](operations.md).

18. **What alerts make sense for this app?**  
    Alert if there is no successful scrape in 36 hours, if two scrape runs in a row persist zero events, or if the public website becomes unavailable. Code path: alert guidance in [`docs/operations.md`](operations.md), health route `GET /health` in [`app/main.py`](../app/main.py).

19. **What should not be logged?**  
    Do not log passwords, API keys, secrets, sensitive cookies, or unnecessary personal data. Logs should help debugging without creating privacy or security problems. Code path: secret guidance in [`AGENTS.md`](../AGENTS.md), config/env handling in [`app/config.py`](../app/config.py).

## Scalability

20. **What does scalability mean for this project?**  
    It means the app can handle more users, more event sources, more events, and more frequent scraping without becoming slow or unreliable. Code path: source list in [`app/scrapers/sources.py`](../app/scrapers/sources.py), database access in [`app/services.py`](../app/services.py), config in [`app/config.py`](../app/config.py).

21. **Why is synchronous scraping a scalability risk?**  
    The current scraping flow calls sources one after another. If one website is slow, the scraper waits. With many sources, total scrape time grows and one blocking source can slow the whole scrape. Code path: `for scraper in build_scrapers()` inside `run_scrape_detailed()` in [`app/services.py`](../app/services.py).

22. **Why could async or background jobs help scraping?**  
    Scraping is often I/O-bound because the app waits for network responses. Async requests, queues, workers, retries, rate limits, and timeouts can make scraping faster and more reliable, but they also add complexity. Code path: scheduled background scrape in [`app/scheduler.py`](../app/scheduler.py), scraper timeout config in [`app/config.py`](../app/config.py), source fetching in [`app/scrapers/html_event_scraper.py`](../app/scrapers/html_event_scraper.py).

23. **Why is SQLite different from PostgreSQL?**  
    SQLite is simple and good for local development, but it is file-based and weaker for concurrent production writes. PostgreSQL is better for production because it handles concurrency, larger datasets, and cloud deployment patterns more robustly. Code path: `DATABASE_URL` and PostgreSQL normalization in [`app/config.py`](../app/config.py), engine setup in [`app/database.py`](../app/database.py), config tests in [`tests/test_config.py`](../tests/test_config.py).

## A11y, Analytics, Quality

24. **What is A11y and why does it matter for a calendar app?**  
    A11y means accessibility. A calendar is very visual, so events should also be usable with keyboard navigation, screen readers, clear labels, semantic buttons, and good contrast. Code path: [`templates/index.html`](../templates/index.html), [`static/app.js`](../static/app.js), [`static/styles.css`](../static/styles.css), [`docs/a11y.md`](a11y.md).

25. **What is the difference between observability and user analytics?**  
    Observability is for developers and operations: is the app healthy, fast, and reliable? User analytics is for product decisions: which views, filters, or events do users interact with? Analytics should be minimal and privacy-friendly. Code path: observability in [`docs/operations.md`](operations.md), analytics/privacy rule in [`AGENTS.md`](../AGENTS.md).

26. **Is user analytics implemented already?**  
    Not yet. The operations docs still mark the analytics dashboard as a TODO, and `AGENTS.md` says any analytics change must avoid unnecessary personal data and document new event names or fields. Code path: [`docs/operations.md`](operations.md), [`AGENTS.md`](../AGENTS.md).

27. **What does code quality mean in this project?**  
    Code quality means understandable structure, clear names, tests, error handling, deduplication, configuration through environment variables, no secrets in Git, and separation between frontend, backend, scraper, and database code. Code path: [`tests/`](../tests), [`app/services.py`](../app/services.py), [`app/scrapers/`](../app/scrapers).

28. **Why is deduplication important for event scraping?**  
    The scraper may find the same event repeatedly. Deduplication prevents the same concert, market, or meetup from being stored many times and cluttering the calendar. Code path: semantic key handling in [`app/services.py`](../app/services.py), `make_semantic_key()` in [`app/scrapers/html_event_scraper.py`](../app/scrapers/html_event_scraper.py).

29. **What should be tested before a task is done?**  
    Run the relevant local tests, check the changed behavior, consider accessibility/privacy impact if UI or analytics changed, and only then mark the Azure DevOps item done. Code path: [`tests/`](../tests), [`docs/a11y.md`](a11y.md), [`AGENTS.md`](../AGENTS.md).

30. **Strong final exam answer:**  
    This project is not just a simple website. It is a small production-like system: scrapers collect external Hong Kong event data, the backend normalizes and stores it, and the frontend displays it in a calendar. The main engineering challenges are reliability because sources can fail, scalability because synchronous scraping can block, and maintainability because many people work on the same repo. GitHub manages code, Azure hosts the app, Azure DevOps tracks work, and AI helps with coding and review as long as we verify its suggestions. A more production-ready version would improve observability, alerts, async/background scraping, and possibly move from SQLite to PostgreSQL. Code path: [`README.md`](../README.md), [`docs/mental-model.md`](mental-model.md), [`app/services.py`](../app/services.py), [`docs/operations.md`](operations.md).

Teacher review note: pick any five cards, explain them in your own words, then open the linked files to prove the answer still matches the project.
