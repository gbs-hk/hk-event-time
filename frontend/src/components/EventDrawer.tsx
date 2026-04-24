"use client";

import { EventItem } from "@/types/event";

type EventDrawerProps = {
  event: EventItem | null;
  onClose: () => void;
};

function buildMapUrl(location: string | null): string | null {
  if (!location) {
    return null;
  }
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(location)}`;
}

export default function EventDrawer({ event, onClose }: EventDrawerProps) {
  if (!event) {
    return null;
  }

  const mapUrl = buildMapUrl(event.location);

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        right: 0,
        width: "min(420px, 95vw)",
        height: "100vh",
        background: "#fff",
        borderLeft: "1px solid #e5e7eb",
        padding: "1rem",
        overflowY: "auto",
        boxShadow: "-4px 0 12px rgba(0, 0, 0, 0.08)",
        zIndex: 100
      }}
    >
      <button type="button" onClick={onClose} style={{ float: "right" }}>
        Close
      </button>
      <h2 style={{ marginTop: 0 }}>{event.name}</h2>
      <p>
        <strong>Category:</strong> {event.category?.name ?? "Uncategorized"}
      </p>
      <p>
        <strong>Start:</strong> {new Date(event.start_datetime).toLocaleString()}
      </p>
      {event.end_datetime && (
        <p>
          <strong>End:</strong> {new Date(event.end_datetime).toLocaleString()}
        </p>
      )}
      {event.location && (
        <p>
          <strong>Location:</strong> {event.location}
        </p>
      )}
      {event.organizer && (
        <p>
          <strong>Organizer:</strong> {event.organizer}
        </p>
      )}
      {event.description && <p>{event.description}</p>}

      {mapUrl && (
        <p>
          <a href={mapUrl} target="_blank" rel="noreferrer">
            Open location in Google Maps
          </a>
        </p>
      )}
      {event.ticket_url && (
        <p>
          <a href={event.ticket_url} target="_blank" rel="noreferrer">
            Official ticket / registration page
          </a>
        </p>
      )}
      {event.discount_text && (
        <p style={{ background: "#FEF3C7", padding: "0.5rem", borderRadius: "6px" }}>
          <strong>Offer:</strong> {event.discount_text}
          {event.discount_url && (
            <>
              {" "}
              <a href={event.discount_url} target="_blank" rel="noreferrer">
                View deal
              </a>
            </>
          )}
        </p>
      )}
    </div>
  );
}
