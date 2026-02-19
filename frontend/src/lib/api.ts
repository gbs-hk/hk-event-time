/**
 * API client -- functions that call the backend REST API.
 *
 * The frontend never talks to the database directly.  Instead it sends HTTP
 * requests (fetch) to the FastAPI backend, which returns JSON.  Each function
 * here wraps one API call:
 *
 *   fetchCategories()  -> GET  /api/categories
 *   fetchEvents()      -> GET  /api/events
 *   triggerScrape()    -> POST /api/events/run-scrape
 */
import { Category, EventItem } from "@/types/event";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`API request failed (${response.status}): ${text}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchCategories(): Promise<Category[]> {
  const response = await fetch(`${API_BASE_URL}/categories`, { cache: "no-store" });
  return parseJson<Category[]>(response);
}

export async function fetchEvents(categorySlugs: string[]): Promise<EventItem[]> {
  const params = new URLSearchParams();
  if (categorySlugs.length > 0) {
    params.set("categories", categorySlugs.join(","));
  }

  const url = `${API_BASE_URL}/events${params.size ? `?${params.toString()}` : ""}`;
  const response = await fetch(url, { cache: "no-store" });
  return parseJson<EventItem[]>(response);
}

export async function triggerScrape(): Promise<{ processed: number; source_errors: number }> {
  const response = await fetch(`${API_BASE_URL}/events/run-scrape`, {
    method: "POST"
  });
  return parseJson<{ processed: number; source_errors: number }>(response);
}
