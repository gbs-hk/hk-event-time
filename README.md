# HK Event Discovery

A web app that scrapes Hong Kong event websites, stores the events in a
database, and displays them on a calendar in your browser.

## Architecture overview

The project has three parts that talk to each other in a straight line:

```
Event websites ──(scrape HTML)──> Backend API ──(save/read)──> Database
                                       ^
                                       |
                                  (HTTP requests)
                                       |
                                   Frontend
                                  (your browser)
```

```mermaid
flowchart LR
  subgraph scraping [1 - Scraping]
    Sites["Event Websites<br/>(Klook, Time Out, ...)"]
    Scraper["Scraper<br/>Python + BeautifulSoup"]
  end

  subgraph backend_group [2 - Backend]
    API["FastAPI Server<br/>(REST API)"]
    DB[("PostgreSQL<br/>Database")]
  end

  subgraph frontend_group [3 - Frontend]
    Next["Next.js App<br/>(React)"]
    Browser["Your Browser"]
  end

  Sites -->|"download HTML"| Scraper
  Scraper -->|"write events"| DB
  API -->|"read events"| DB
  Next -->|"GET /api/events"| API
  Browser -->|"renders page"| Next
```

**How data flows through the system:**

1. The **scraper** visits event websites, reads their HTML, and pulls out event
   details (title, date, location, link).
2. Those events are **saved to PostgreSQL** so they survive restarts.
3. The **FastAPI backend** exposes REST endpoints so the frontend can ask
   "give me all events" or "give me only music events".
4. The **Next.js frontend** calls those endpoints, gets JSON back, and renders
   the events on a FullCalendar widget in your browser.

## Concepts you will learn

| Concept | Where in the code | What it means |
|---|---|---|
| REST API | `backend/app/api/events.py` | A standard way for programs to talk over HTTP (GET, POST, ...) |
| ORM (Object-Relational Mapping) | `backend/app/models.py` | Python classes that map to database tables -- no raw SQL needed |
| Web Scraping | `backend/app/sources/` | Downloading a web page and extracting structured data from its HTML |
| React Components | `frontend/src/components/` | Reusable UI building blocks (Calendar, EventDrawer) |
| React State (hooks) | `frontend/src/app/page.tsx` | `useState` and `useEffect` manage what the page shows and when it updates |
| Client-Server Architecture | `frontend/src/lib/api.ts` | The browser (client) sends HTTP requests to the backend (server) |
| SQL Database | `docker-compose.yml` | PostgreSQL stores rows of events, categories, and sources in tables |
| Containers (Docker) | `docker-compose.yml` | Docker runs the database in an isolated box so you skip OS-specific setup |

## Folder map

```
hk-event-time/
├── backend/                          # Everything that runs on the server
│   ├── app/
│   │   ├── main.py                   # Entry point -- creates the FastAPI server
│   │   ├── config.py                 # Reads settings from .env file
│   │   ├── database.py               # Connects Python to PostgreSQL via SQLAlchemy
│   │   ├── models.py                 # Defines database tables as Python classes
│   │   ├── schemas.py                # Shapes of JSON the API returns (Pydantic)
│   │   ├── categories.py             # List of event categories (music, sports, ...)
│   │   ├── categorize.py             # Assigns a category to an event by keywords
│   │   ├── scrape.py                 # Orchestrates all scrapers, saves results to DB
│   │   ├── api/
│   │   │   └── events.py             # HTTP endpoints the frontend calls
│   │   └── sources/                  # One file per website we scrape
│   │       ├── common.py             # Shared helpers (fetch HTML, parse dates)
│   │       ├── types.py              # RawEvent dataclass
│   │       ├── klook_hk.py           # Klook Hong Kong scraper
│   │       ├── timeout_hk.py         # Time Out Hong Kong scraper
│   │       ├── eventbrite_hk.py      # Eventbrite Hong Kong scraper
│   │       ├── meetup_hk.py          # Meetup Hong Kong scraper
│   │       ├── hktb.py               # HK Tourism Board scraper
│   │       └── ticketflap.py         # Ticketflap scraper
│   ├── scripts/
│   │   ├── init_db.py                # Run once to create database tables
│   │   └── run_scrape.py             # Run once or on a schedule to scrape events
│   └── requirements.txt              # Python dependencies
│
├── frontend/                         # Everything that runs in the browser
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx            # Root HTML wrapper
│   │   │   ├── page.tsx              # Main page -- state, filters, calendar
│   │   │   └── globals.css           # Global styles
│   │   ├── components/
│   │   │   ├── Calendar.tsx          # FullCalendar wrapper (month/week/day views)
│   │   │   └── EventDrawer.tsx       # Side panel showing event details
│   │   ├── lib/
│   │   │   ├── api.ts                # Functions that call the backend API
│   │   │   └── categories.ts         # Helper to pick category colors
│   │   └── types/
│   │       └── event.ts              # TypeScript type definitions
│   └── package.json                  # Node.js dependencies
│
├── docker-compose.yml                # Runs PostgreSQL in a Docker container
├── .env.example                      # Template for environment variables
└── .gitignore                        # Files git should ignore
```

## What you need installed

| Tool | Why |
|---|---|
| Python 3.11+ | Runs the backend and scraper |
| Node.js 20+ | Runs the frontend dev server |
| Docker | Runs the PostgreSQL database |

> **WSL users:** install Node via [nvm](https://github.com/nvm-sh/nvm) inside
> Linux (`curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash`,
> then `nvm install --lts`).

---

## Quick start

Run every command from the project root unless noted otherwise.

### 1. Create `.env`

```bash
cp .env.example .env          # Linux / macOS
# or
Copy-Item .env.example .env   # Windows PowerShell
```

You usually do not need to edit this file for local development.

### 2. Start the database

```bash
docker compose up -d db
```

### 3. Set up the backend

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
cd backend
python scripts/init_db.py      # creates tables in the database
```

### 4. Run the backend API

Stay in `backend/`:

```bash
uvicorn app.main:app --reload --port 8000
```

Leave this terminal open. Visit http://localhost:8000/docs to see the auto-generated API documentation.

### 5. Run the frontend

Open a **new terminal**:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 -- you should see the calendar.

### 6. Scrape events

Open a **third terminal**, activate the venv, then from `backend/`:

```bash
python scripts/run_scrape.py
```

Refresh the browser -- events should appear on the calendar.

---

## Daily workflow

1. `docker compose up -d db`
2. Activate your Python venv
3. Terminal 1 (from `backend/`): `uvicorn app.main:app --reload --port 8000`
4. Terminal 2 (from `frontend/`): `npm run dev`
5. Terminal 3 (from `backend/`): `python scripts/run_scrape.py` whenever you want fresh events

---

## Auto deploy to Azure (simple view)

When you push code to `main`, GitHub Actions deploys your app to Azure automatically.

```mermaid
flowchart LR
  localCode[Your code on laptop] -->|git push main| githubRepo[GitHub repository]
  githubRepo --> deployWorkflow[Deploy workflow]
  deployWorkflow --> azureWebApp[Azure Web App hk-event-time]
  azureWebApp --> healthWorkflow[Post-deploy health check workflow]
  healthWorkflow --> result{Health check pass?}
  result -->|Yes| green[Deployment is healthy]
  result -->|No| red[Workflow fails so you catch issues fast]
```

### What runs on each push

1. `.github/workflows/azure-deploy.yml` runs on every push to `main`.
2. It deploys the latest commit to Azure Web App `hk-event-time`.
3. `.github/workflows/post-deploy-healthcheck.yml` runs after deploy and probes:
   - `/`
   - `/api/events?start=...&end=...`
4. If either probe fails, the health-check workflow fails.

### Required GitHub secrets (one-time setup)

In your GitHub repo settings, add:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

These are used by OIDC login in the deploy workflow.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'app'` | Make sure you run backend commands from inside `backend/` |
| Frontend shows no events | Run the scraper at least once, and check both servers are running |
| Database connection error | Check Docker is running: `docker ps`. Check `.env` exists |

---

## Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+psycopg2://postgres:postgres@localhost:5432/hk_events` |
| `BACKEND_CORS_ORIGINS` | Which URLs can call the API | `http://localhost:3000` |
| `NEXT_PUBLIC_API_BASE_URL` | Where the frontend finds the API | `http://localhost:8000/api` |
