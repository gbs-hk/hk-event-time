"""Entry point of the backend API server.

FastAPI is a Python web framework.  This file creates the app, configures
which frontend URLs are allowed to call it (CORS), and registers the API
routes defined in app/api/events.py.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.events import router as events_router
from app.config import settings

app = FastAPI(title="HK Event Discovery API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(events_router, prefix="/api")

frontend_out_dir = Path(__file__).resolve().parent / "frontend_out"


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    index_file = frontend_out_dir / "index.html"
    if index_file.exists():
        return index_file.read_text(encoding="utf-8")

    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Hong Kong Event Discovery</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 0; background: #f9fafb; color: #111827; }
    main { max-width: 1100px; margin: 0 auto; padding: 1.5rem; }
    .header { display: flex; justify-content: space-between; align-items: center; gap: 1rem; }
    .chip-wrap { display: flex; gap: 0.5rem; flex-wrap: wrap; margin: 1rem 0; }
    .chip { border-radius: 999px; border: 1px solid #d1d5db; background: #fff; padding: 0.3rem 0.8rem; cursor: pointer; }
    .chip.active { background: #2563eb; border-color: #2563eb; color: #fff; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 0.8rem; }
    .card { background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 0.9rem; }
    .meta { color: #4b5563; font-size: 0.9rem; }
    .muted { color: #6b7280; }
    button { border: 1px solid #2563eb; background: #2563eb; color: #fff; border-radius: 8px; padding: 0.5rem 0.9rem; cursor: pointer; }
    button:disabled { opacity: 0.7; cursor: not-allowed; }
  </style>
</head>
<body>
  <main>
    <div class="header">
      <div>
        <h1 style="margin-bottom:0.25rem;">Hong Kong Event Discovery</h1>
        <p style="margin:0;" class="muted">Automated event feed with category colors and direct ticket links.</p>
      </div>
      <button id="refreshBtn" type="button">Run scrape now</button>
    </div>
    <p id="message" class="meta">Loading events...</p>
    <div id="chips" class="chip-wrap"></div>
    <div id="events" class="grid"></div>
  </main>
  <script>
    const state = { categories: [], events: [], selected: new Set() };
    const message = document.getElementById("message");
    const chips = document.getElementById("chips");
    const eventsEl = document.getElementById("events");
    const refreshBtn = document.getElementById("refreshBtn");

    async function fetchJson(url, options) {
      const response = await fetch(url, options);
      if (!response.ok) {
        const text = await response.text();
        throw new Error("Request failed (" + response.status + "): " + text);
      }
      return response.json();
    }

    function renderCategories() {
      chips.innerHTML = "";
      for (const category of state.categories) {
        const active = state.selected.has(category.slug);
        const btn = document.createElement("button");
        btn.className = "chip" + (active ? " active" : "");
        btn.textContent = category.name;
        btn.type = "button";
        btn.onclick = async () => {
          if (state.selected.has(category.slug)) state.selected.delete(category.slug);
          else state.selected.add(category.slug);
          renderCategories();
          await loadEvents();
        };
        chips.appendChild(btn);
      }
    }

    function renderEvents() {
      eventsEl.innerHTML = "";
      if (!state.events.length) {
        eventsEl.innerHTML = "<p class='meta'>No events found for the current filter.</p>";
        return;
      }
      for (const event of state.events) {
        const card = document.createElement("article");
        card.className = "card";
        const starts = new Date(event.start_datetime).toLocaleString();
        const ends = event.end_datetime ? new Date(event.end_datetime).toLocaleString() : "N/A";
        card.innerHTML = "<h3 style='margin:0 0 0.35rem;'>" + event.name + "</h3>" +
          "<p class='meta' style='margin:0 0 0.2rem;'><strong>Category:</strong> " + event.category + "</p>" +
          "<p class='meta' style='margin:0 0 0.2rem;'><strong>Starts:</strong> " + starts + "</p>" +
          "<p class='meta' style='margin:0 0 0.5rem;'><strong>Ends:</strong> " + ends + "</p>" +
          (event.url ? "<a href='" + event.url + "' target='_blank' rel='noopener'>View event</a>" : "");
        eventsEl.appendChild(card);
      }
    }

    async function loadEvents() {
      const params = new URLSearchParams();
      if (state.selected.size) params.set("categories", Array.from(state.selected).join(","));
      const url = "/api/events" + (params.size ? "?" + params.toString() : "");
      state.events = await fetchJson(url);
      renderEvents();
    }

    async function bootstrap() {
      try {
        state.categories = await fetchJson("/api/categories");
        renderCategories();
        await loadEvents();
        message.textContent = "Data loaded.";
      } catch (error) {
        message.textContent = error.message || "Failed to load data.";
      }
    }

    refreshBtn.onclick = async () => {
      refreshBtn.disabled = true;
      message.textContent = "Running scrape...";
      try {
        const result = await fetchJson("/api/events/run-scrape", { method: "POST" });
        await loadEvents();
        message.textContent = "Scrape complete. Processed " + result.processed + " events, source errors: " + result.source_errors + ".";
      } catch (error) {
        message.textContent = error.message || "Scrape failed.";
      } finally {
        refreshBtn.disabled = false;
      }
    };

    bootstrap();
  </script>
</body>
</html>"""


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


app.mount("/", StaticFiles(directory=str(frontend_out_dir), html=True, check_dir=False), name="frontend")
