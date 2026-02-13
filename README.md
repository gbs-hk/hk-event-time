# HK Event Discovery

Local-first event discovery system for Hong Kong with:
- Python FastAPI backend + scraping pipeline
- PostgreSQL storage via SQLAlchemy/Alembic
- Next.js calendar frontend with color-coded categories

## Project structure

- `backend/`: API, models, migration scripts, and source scrapers
- `frontend/`: calendar UI, filters, and event detail drawer

## Backend setup

1. Create a Postgres database (default expected: `hk_events`).
2. Install dependencies:
   - `pip install -r backend/requirements.txt`
3. Configure environment (copy from `.env.example` as needed).
4. Run migrations:
   - `cd backend`
   - `alembic upgrade head`
5. Start API:
   - `uvicorn app.main:app --reload --port 8000`
6. Run scraper once:
   - `python scripts/run_scrape.py`
7. Optional scheduler mode:
   - `python scripts/run_scrape.py --mode scheduler`

## Frontend setup

1. Install dependencies:
   - `cd frontend`
   - `npm install`
2. Start frontend:
   - `npm run dev`
3. Open `http://localhost:3000`

The frontend calls backend API at `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000/api`).
