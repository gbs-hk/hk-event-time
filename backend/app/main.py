"""Entry point of the backend API server.

FastAPI is a Python web framework.  This file creates the app, configures
which frontend URLs are allowed to call it (CORS), and registers the API
routes defined in app/api/events.py.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

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


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>HK Event Discovery API</title>
  <style>
    * { box-sizing: border-box; }
    body {
      font-family: system-ui, -apple-system, sans-serif;
      margin: 0;
      padding: 2rem;
      background-color: #f5f5f5;
      color: #1a1a1a;
      line-height: 1.5;
    }
    a { color: #0d47a1; }
    a:hover { text-decoration: underline; }
    code { background: #e0e0e0; color: #1a1a1a; padding: 0.2em 0.4em; border-radius: 4px; }
    @media (prefers-color-scheme: dark) {
      body { background-color: #1a1a1a; color: #e5e5e5; }
      a { color: #64b5f6; }
      code { background: #333; color: #e5e5e5; }
    }
  </style>
</head>
<body>
  <h1>HK Event Discovery API</h1>
  <p><strong>Status:</strong> ok</p>
  <ul>
    <li><a href="/docs">API docs (Swagger)</a></li>
    <li><a href="/health">Health</a></li>
    <li><a href="/api/events">Events</a></li>
  </ul>
</body>
</html>"""


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
