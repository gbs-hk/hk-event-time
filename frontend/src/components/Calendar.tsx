"use client";

import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import timeGridPlugin from "@fullcalendar/timegrid";
import interactionPlugin, { EventClickArg } from "@fullcalendar/interaction";

import { categoryColor } from "@/lib/categories";
import { EventItem } from "@/types/event";

type CalendarProps = {
  events: EventItem[];
  onEventClick: (event: EventItem) => void;
};

export default function Calendar({ events, onEventClick }: CalendarProps) {
  const byId = new Map(events.map((event) => [String(event.id), event]));

  return (
    <div style={{ background: "#fff", borderRadius: "10px", padding: "1rem" }}>
      <FullCalendar
        plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
        initialView="dayGridMonth"
        headerToolbar={{
          left: "prev,next today",
          center: "title",
          right: "dayGridMonth,timeGridWeek,timeGridDay"
        }}
        buttonText={{
          month: "Month",
          week: "Week",
          day: "Day"
        }}
        height="auto"
        events={events.map((event) => ({
          id: String(event.id),
          title: event.name,
          start: event.start_datetime,
          end: event.end_datetime ?? undefined,
          backgroundColor: categoryColor(event.category),
          borderColor: categoryColor(event.category),
          textColor: "#fff"
        }))}
        eventClick={(arg: EventClickArg) => {
          const selected = byId.get(arg.event.id);
          if (selected) {
            onEventClick(selected);
          }
        }}
      />
    </div>
  );
}
