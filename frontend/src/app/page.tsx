/**
 * Main page of the website.
 *
 * This is a React component that:
 *  1. Loads categories and events from the backend API when the page opens.
 *  2. Lets users filter events by category (the coloured pill buttons).
 *  3. Renders the calendar and a side drawer with event details.
 *
 * "use client" tells Next.js this component runs in the browser (not on the
 * server) because it uses React hooks like useState and useEffect.
 */
"use client";

import { useEffect, useMemo, useState } from "react";

import Calendar from "@/components/Calendar";
import EventDrawer from "@/components/EventDrawer";
import { fetchCategories, fetchEvents, triggerScrape } from "@/lib/api";
import { sortedCategories } from "@/lib/categories";
import { Category, EventItem } from "@/types/event";

export default function HomePage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [activeEvent, setActiveEvent] = useState<EventItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const categoryList = useMemo(() => sortedCategories(categories), [categories]);

  useEffect(() => {
    async function bootstrap() {
      setLoading(true);
      try {
        const [categoryData, eventData] = await Promise.all([fetchCategories(), fetchEvents([])]);
        setCategories(categoryData);
        setEvents(eventData);
      } catch (error) {
        setMessage(error instanceof Error ? error.message : "Failed to load data");
      } finally {
        setLoading(false);
      }
    }
    void bootstrap();
  }, []);

  useEffect(() => {
    async function loadFiltered() {
      try {
        const eventData = await fetchEvents(Array.from(selected));
        setEvents(eventData);
      } catch (error) {
        setMessage(error instanceof Error ? error.message : "Failed to load filtered events");
      }
    }
    void loadFiltered();
  }, [selected]);

  const toggleCategory = (slug: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(slug)) {
        next.delete(slug);
      } else {
        next.add(slug);
      }
      return next;
    });
  };

  const refreshViaScrape = async () => {
    setSyncing(true);
    setMessage(null);
    try {
      const result = await triggerScrape();
      const eventData = await fetchEvents(Array.from(selected));
      setEvents(eventData);
      setMessage(
        `Scrape complete. Processed ${result.processed} events, source errors: ${result.source_errors}.`
      );
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Scrape failed");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <main style={{ padding: "1.5rem", maxWidth: "1200px", margin: "0 auto" }}>
      <header style={{ display: "flex", justifyContent: "space-between", gap: "1rem" }}>
        <div>
          <h1 style={{ marginBottom: "0.25rem" }}>Hong Kong Event Discovery</h1>
          <p style={{ marginTop: 0, color: "#4b5563" }}>
            Automated event feed with category colors and direct ticket links.
          </p>
        </div>
        <button type="button" onClick={refreshViaScrape} disabled={syncing}>
          {syncing ? "Running scrape..." : "Run scrape now"}
        </button>
      </header>

      {message && (
        <p style={{ background: "#eff6ff", border: "1px solid #bfdbfe", padding: "0.75rem" }}>{message}</p>
      )}

      <section style={{ marginBottom: "1rem" }}>
        <h3>Filter by category</h3>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
          {categoryList.map((category) => {
            const active = selected.has(category.slug);
            return (
              <button
                key={category.slug}
                type="button"
                onClick={() => toggleCategory(category.slug)}
                style={{
                  border: `1px solid ${category.color}`,
                  background: active ? category.color : "#fff",
                  color: active ? "#fff" : "#111827",
                  borderRadius: "999px",
                  padding: "0.35rem 0.75rem",
                  cursor: "pointer"
                }}
              >
                {category.name}
              </button>
            );
          })}
        </div>
      </section>

      {loading ? (
        <p>Loading events...</p>
      ) : (
        <Calendar events={events} onEventClick={(event) => setActiveEvent(event)} />
      )}
      <EventDrawer event={activeEvent} onClose={() => setActiveEvent(null)} />
    </main>
  );
}
