# Hong Kong Event Calendar

This project scrapes selected Hong Kong event sources, classifies events automatically, and shows them in a filterable calendar with direct links to maps, tickets, and offers.

## Features

- Automated scraping pipeline with manual refresh and scheduled runs
- Multi-strategy scraping support:
  - JSON-LD event extraction
  - Generic event-card extraction
  - Event-link discovery and detail-page parsing
- Automatic categorization for music, party, sports, food, culture, networking, and other
- Color-coded calendar with month, week, and day views
- Event detail modal with location, organizer, ticket, and discount links
- Source debug endpoint for scrape diagnostics

## Requirements

- Python 3.10 or newer
- `git`

## Clone and install

```bash
git clone https://github.com/gbs-hk/hk-event-time.git
cd hk-event-time
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows activation:

```bash
.venv\Scripts\activate
```

## Run the app

```bash
python run.py
```

Open [http://127.0.0.1:5050](http://127.0.0.1:5050)

If port `5050` is already in use:

```bash
PORT=5051 python run.py
```

## Common commands

Refresh dependencies:

```bash
pip install -r requirements.txt
```

Run tests:

```bash
python -m unittest discover -s tests -v
```

## Configuration

The app can be configured with environment variables:

- `PORT`: web server port, default `5050`
- `SCHEDULE_HOUR_UTC`: daily scheduled scrape hour in UTC
- `SCRAPE_TIMEOUT_SECONDS`: per-request scrape timeout
- `SCRAPE_MAX_DETAIL_PAGES_PER_SOURCE`: detail pages followed per source, default `12`
- `SCRAPE_INCLUDE_SAMPLE`: set to `1` to include sample demo events
- `SCRAPE_SOURCE_MODE`: `lkf_nightlife` or `all`
- `SCRAPE_FOCUS_CATEGORIES`: comma-separated categories, default `party,music`

Example:

```bash
SCRAPE_SOURCE_MODE=all SCRAPE_FOCUS_CATEGORIES=party,music,food python run.py
```

## API endpoints

- `GET /api/categories`
- `GET /api/events?start=<ISO>&end=<ISO>&category=music&category=party`
- `POST /api/scrape-now`
- `GET /api/debug/sources`
- `GET /api/debug/sources?run=1`

## Project structure

- `app/`: Flask app, models, services, scheduler, and scrapers
- `static/`: frontend JavaScript and CSS
- `templates/`: HTML templates
- `tests/`: test suite

## Current scraping notes

Configured sources include general Hong Kong event sites plus Lan Kwai Fong and nightlife-related sources. Some sites are JavaScript-rendered, login-gated, or bot-protected, so plain HTTP scraping may return partial or zero results. For those sources, the next step is a source-specific scraper or browser-based automation.

Always make sure your use of scraped websites follows their terms and robots policies.
