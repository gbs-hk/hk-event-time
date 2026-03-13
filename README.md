# Automated Event Discovery and Color-Coded Calendar (Hong Kong)

This project scans configured Hong Kong event sources, categorizes events automatically, and displays them in a filterable color-coded calendar.

## Features
- Automatic scraping pipeline (manual trigger + daily scheduler)
- Multi-strategy scraping:
  - JSON-LD Event schema extraction
  - Generic event-card extraction on listing pages
  - Event-link discovery + detail-page JSON-LD extraction
- Event normalization and deduplication via stable `external_id`
- Auto categorization:
  - Music / Concert
  - Party / Club
  - Sports
  - Food & Dining
  - Culture / Theater
  - Networking / Business
- Color-coded calendar with month/week/day views
- Clickable event details modal with map, tickets, and discount info
- Optional discount hint extraction from source text

## Tech Stack
- Backend: Flask + SQLAlchemy + APScheduler
- Database: SQLite
- Frontend: FullCalendar + vanilla JS

## Setup
```bash
cd /Users/ezrabohm/Desktop/Python\ GBS/hk-event-calendar
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Open: `http://127.0.0.1:5050`

## API Endpoints
- `GET /api/categories`
- `GET /api/events?start=<ISO>&end=<ISO>&category=music&category=sports`
- `POST /api/scrape-now`
- `GET /api/debug/sources` (current upcoming events grouped by source)
- `GET /api/debug/sources?run=1` (runs scrape now and returns per-source diagnostics)

## Config
- `SCHEDULE_HOUR_UTC`: daily scrape hour in UTC
- `SCRAPE_TIMEOUT_SECONDS`: per-request timeout
- `SCRAPE_MAX_DETAIL_PAGES_PER_SOURCE`: detail pages to follow per source (default: `12`)
- `SCRAPE_INCLUDE_SAMPLE=1`: optionally include sample seed events
- `SCRAPE_SOURCE_MODE`: `lkf_nightlife` (default) or `all`
- `SCRAPE_FOCUS_CATEGORIES`: comma list (default: `party,music`)

## Current Sources
Configured in `/Users/ezrabohm/Desktop/Python GBS/hk-event-calendar/app/scrapers/sources.py`, including:
- discoverhongkong.com
- hongkongcheapo.com/events
- timeout.com/hong-kong
- brandhk.gov.hk
- meetup.com/cities/hk/hong_kong
- eventbrite.com (HK pages)
- internations.org/hong-kong-expats
- letseventhk.com
- lcsd.gov.hk
- hkcc.gov.hk
- hkculturalcentre.gov.hk
- hkcec.com/en/event-calendar
- partnernet.hktb.com events page
- lankwaifong.com
- cassiohk.com
- dragon-i.com.hk
- trilogyhk.com
- zeus-lkf.com
- omahk.com
- boomeranghk.com
- maggiechoos.com/hongkong
- theironfairies.com/hong-kong
- saharalkf.com
- qing.hk
- chinabarhk.com
- hongkongpubcrawl.com
- shuffle.hk

## Important Limitations
- Some sites are JS-rendered, login-gated, or bot-protected; those may return partial or zero data with plain HTTP scraping.
- For those sources, next step is a source-specific scraper (or browser automation) with explicit selectors/API usage.
- Always follow each website's terms and robots policies.
