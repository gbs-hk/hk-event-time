const categoryFiltersEl = document.getElementById("categoryFilters");
const scrapeButton = document.getElementById("scrapeButton");
const controlsToggle = document.getElementById("controlsToggle");
const controlsMenu = document.getElementById("controlsMenu");
const dialog = document.getElementById("eventDialog");
const closeDialogButton = document.getElementById("closeDialog");
const dayDialog = document.getElementById("dayDialog");
const closeDayDialogButton = document.getElementById("closeDayDialog");
const calendarStatus = document.getElementById("calendarStatus");
const viewRangeLabel = document.getElementById("viewRangeLabel");

const eventTitle = document.getElementById("eventTitle");
const eventMeta = document.getElementById("eventMeta");
const eventDescription = document.getElementById("eventDescription");
const mapLink = document.getElementById("mapLink");
const ticketLink = document.getElementById("ticketLink");
const discountLink = document.getElementById("discountLink");
const dayTitle = document.getElementById("dayTitle");
const daySubtitle = document.getElementById("daySubtitle");
const dayEventGroups = document.getElementById("dayEventGroups");

const HK_TIME_ZONE = "Asia/Hong_Kong";
const shortDateFormatter = new Intl.DateTimeFormat("en-HK", {
  timeZone: HK_TIME_ZONE,
  month: "short",
  day: "numeric",
  year: "numeric",
});
const timeFormatter = new Intl.DateTimeFormat("en-HK", {
  timeZone: HK_TIME_ZONE,
  hour: "numeric",
  minute: "2-digit",
  hour12: true,
});
const detailFormatter = new Intl.DateTimeFormat("en-HK", {
  timeZone: HK_TIME_ZONE,
  weekday: "short",
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
  hour12: true,
});
const dayTitleFormatter = new Intl.DateTimeFormat("en-HK", {
  timeZone: HK_TIME_ZONE,
  weekday: "long",
  month: "long",
  day: "numeric",
  year: "numeric",
});
const dateKeyFormatter = new Intl.DateTimeFormat("en-US", {
  timeZone: HK_TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

let activeCategories = new Set();
let categories = [];
let calendar;
let monthPaintToken = 0;
let latestEventsByDate = new Map();

async function loadCategories() {
  const response = await fetch("/api/categories");
  categories = await response.json();
  categories.forEach((category) => activeCategories.add(category.slug));
  renderCategoryFilters();
}

function renderCategoryFilters() {
  categoryFiltersEl.innerHTML = "";
  categories.forEach((category) => {
    const label = document.createElement("label");
    label.className = "filter-chip";
    label.style.setProperty("--category-color", category.color);

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = activeCategories.has(category.slug);
    checkbox.className = "filter-input";
    label.classList.toggle("is-active", checkbox.checked);
    label.setAttribute("aria-label", `Toggle ${category.label}`);
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        activeCategories.add(category.slug);
      } else {
        activeCategories.delete(category.slug);
      }
      label.classList.toggle("is-active", checkbox.checked);
      calendar.refetchEvents();
    });

    const dot = document.createElement("span");
    dot.style.width = "10px";
    dot.style.height = "10px";
    dot.style.borderRadius = "50%";
    dot.style.display = "inline-block";
    dot.style.background = category.color;

    const text = document.createElement("span");
    text.textContent = category.label;

    label.appendChild(checkbox);
    label.appendChild(dot);
    label.appendChild(text);
    categoryFiltersEl.appendChild(label);
  });
}

function buildEventsUrl(fetchInfo) {
  const params = new URLSearchParams({
    start: fetchInfo.startStr,
    end: fetchInfo.endStr,
  });

  for (const category of activeCategories) {
    params.append("category", category);
  }

  return `/api/events?${params.toString()}`;
}

function toDateKey(value) {
  const parts = Object.fromEntries(
    dateKeyFormatter
      .formatToParts(new Date(value))
      .filter((part) => part.type !== "literal")
      .map((part) => [part.type, part.value])
  );
  return `${parts.year}-${parts.month}-${parts.day}`;
}

function addDaysToDateKey(dateKey, days) {
  const [year, month, day] = dateKey.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day + days, 12));
  return date.toISOString().slice(0, 10);
}

function dateKeysBetween(start, end) {
  const startKey = toDateKey(start);
  const endKey = end ? toDateKey(end) : startKey;
  const keys = [];
  let cursor = startKey;

  while (cursor <= endKey && keys.length < 370) {
    keys.push(cursor);
    if (cursor === endKey) break;
    cursor = addDaysToDateKey(cursor, 1);
  }
  return keys;
}

function getCalendarViewType(fetchInfo = {}) {
  return fetchInfo.view ? fetchInfo.view.type : calendar?.view?.type || "dayGridMonth";
}

function getCategoryMeta(categorySlug) {
  return categories.find((category) => category.slug === categorySlug) || {
    slug: categorySlug || "other",
    label: "Other",
    color: "#6c7284",
    text_color: "#f8f9fb",
  };
}

function getCategoryRank(categorySlug) {
  const index = categories.findIndex((category) => category.slug === categorySlug);
  return index === -1 ? categories.length : index;
}

function toDialogEvent(event) {
  return {
    title: event.title,
    start: event.start ? new Date(event.start) : null,
    end: event.end ? new Date(event.end) : null,
    extendedProps: {
      ...(event.extendedProps || {}),
      original_start: event.start,
      original_end: event.end,
    },
  };
}

function clearMonthMarkers() {
  latestEventsByDate = new Map();
  document.querySelectorAll(".month-category-stack").forEach((stack) => stack.remove());
  document.querySelectorAll(".has-day-events").forEach((cell) => {
    cell.classList.remove("has-day-events");
    cell.removeAttribute("tabindex");
    cell.removeAttribute("aria-label");
  });
}

function queueMonthMarkerPaint(events) {
  const token = ++monthPaintToken;
  const paintIfCurrent = () => {
    if (token === monthPaintToken) {
      paintMonthMarkers(events);
    }
  };

  requestAnimationFrame(paintIfCurrent);
  window.setTimeout(paintIfCurrent, 75);
  window.setTimeout(paintIfCurrent, 200);
}

function groupEventsByDate(events) {
  const grouped = new Map();

  events.forEach((event) => {
    if (!event.start) return;
    dateKeysBetween(event.start, event.end).forEach((dateKey) => {
      if (!grouped.has(dateKey)) grouped.set(dateKey, []);
      grouped.get(dateKey).push(event);
    });
  });

  return grouped;
}

function groupEventsByCategory(events) {
  const grouped = new Map();

  events
    .slice()
    .sort((first, second) => new Date(first.start) - new Date(second.start))
    .forEach((event) => {
      const category = event.category || "other";
      if (!grouped.has(category)) grouped.set(category, []);
      grouped.get(category).push(event);
    });

  return Array.from(grouped.entries()).sort(([firstCategory, firstEvents], [secondCategory, secondEvents]) => {
    if (secondEvents.length !== firstEvents.length) {
      return secondEvents.length - firstEvents.length;
    }
    return getCategoryRank(firstCategory) - getCategoryRank(secondCategory);
  });
}

function dateFromDateKey(dateKey) {
  return new Date(`${dateKey}T12:00:00+08:00`);
}

function formatEventTimeRange(event) {
  if (!event.start) return "Time TBD";

  const start = new Date(event.start);
  const end = event.end ? new Date(event.end) : null;
  const startsAtMidnight = start.getHours() === 0 && start.getMinutes() === 0;
  const endsAtMidnight = end && end.getHours() === 0 && end.getMinutes() === 0;

  if (end && toDateKey(start) !== toDateKey(end)) {
    return `${shortDateFormatter.format(start)} ${timeFormatter.format(start)} to ${shortDateFormatter.format(end)} ${timeFormatter.format(end)}`;
  }
  if (startsAtMidnight && (!end || endsAtMidnight)) {
    return "All day";
  }
  if (end) {
    return `${timeFormatter.format(start)} to ${timeFormatter.format(end)}`;
  }
  return timeFormatter.format(start);
}

function openDayEvents(dateKey, events) {
  const grouped = groupEventsByCategory(events);
  dayTitle.textContent = dayTitleFormatter.format(dateFromDateKey(dateKey));
  daySubtitle.textContent = `${events.length} event${events.length === 1 ? "" : "s"} grouped by category`;
  dayEventGroups.innerHTML = "";

  grouped.forEach(([categorySlug, categoryEvents]) => {
    const category = getCategoryMeta(categorySlug);
    const section = document.createElement("section");
    section.className = "day-category-section";
    section.style.setProperty("--event-color", category.color);

    const header = document.createElement("div");
    header.className = "day-category-header";

    const label = document.createElement("span");
    label.textContent = category.label;

    const count = document.createElement("span");
    count.textContent = `${categoryEvents.length} event${categoryEvents.length === 1 ? "" : "s"}`;

    header.appendChild(label);
    header.appendChild(count);
    section.appendChild(header);

    categoryEvents.forEach((event) => {
      const props = event.extendedProps || {};
      const card = document.createElement("button");
      card.type = "button";
      card.className = "day-event-card";
      card.addEventListener("click", () => {
        dayDialog.close();
        showEventDetails(toDialogEvent(event));
      });

      const title = document.createElement("strong");
      title.textContent = event.title;

      const meta = document.createElement("span");
      meta.textContent = [formatEventTimeRange(event), props.location_name || "Location TBD"].join(" | ");

      card.appendChild(title);
      card.appendChild(meta);
      section.appendChild(card);
    });

    dayEventGroups.appendChild(section);
  });

  dayDialog.showModal();
}

function bindDayCell(cell) {
  if (cell.dataset.dayOpenBound === "true") return;
  cell.dataset.dayOpenBound = "true";
  cell.addEventListener("click", (event) => {
    if (event.target.closest("button, a")) return;
    const eventsForDay = latestEventsByDate.get(cell.dataset.date) || [];
    if (eventsForDay.length > 0) {
      openDayEvents(cell.dataset.date, eventsForDay);
    }
  });
  cell.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const eventsForDay = latestEventsByDate.get(cell.dataset.date) || [];
    if (eventsForDay.length > 0) {
      event.preventDefault();
      openDayEvents(cell.dataset.date, eventsForDay);
    }
  });
}

function paintMonthMarkers(events) {
  clearMonthMarkers();

  if (!calendar || calendar.view.type !== "dayGridMonth" || events.length === 0) {
    return;
  }

  const grouped = groupEventsByDate(events);
  latestEventsByDate = grouped;
  document.querySelectorAll(".fc-daygrid-day[data-date]").forEach((cell) => {
    const eventsForDay = grouped.get(cell.dataset.date);
    if (!eventsForDay || eventsForDay.length === 0) return;

    const categoryGroups = groupEventsByCategory(eventsForDay);
    const stack = document.createElement("div");
    stack.className = "month-category-stack";

    categoryGroups.slice(0, 3).forEach(([categorySlug, categoryEvents]) => {
      const category = getCategoryMeta(categorySlug);
      const pill = document.createElement("button");
      pill.type = "button";
      pill.className = "month-category-pill";
      pill.style.setProperty("--event-color", category.color);
      pill.title = `${category.label}: ${categoryEvents.length} event${categoryEvents.length === 1 ? "" : "s"}`;
      pill.addEventListener("click", (clickEvent) => {
        clickEvent.preventDefault();
        clickEvent.stopPropagation();
        openDayEvents(cell.dataset.date, eventsForDay);
      });

      const label = document.createElement("span");
      label.textContent = category.label.split("/")[0].trim();

      const count = document.createElement("strong");
      count.textContent = categoryEvents.length;

      pill.appendChild(label);
      pill.appendChild(count);
      stack.appendChild(pill);
    });

    if (categoryGroups.length > 3) {
      const overflow = document.createElement("span");
      overflow.className = "category-overflow";
      overflow.textContent = `+${categoryGroups.length - 3} more categories`;
      stack.appendChild(overflow);
    }

    cell.classList.add("has-day-events");
    cell.tabIndex = 0;
    cell.setAttribute("aria-label", `${eventsForDay.length} events on ${dayTitleFormatter.format(dateFromDateKey(cell.dataset.date))}`);
    bindDayCell(cell);

    const frame = cell.querySelector(".fc-daygrid-day-frame") || cell;
    frame.appendChild(stack);
  });
}

function isPlaceholderOrInvalidUrl(url) {
  if (!url) return true;
  const lower = url.toLowerCase();
  return lower.includes("example.com") || lower.includes("example.org") || lower.includes("example.net");
}

function setLink(linkEl, href, fallbackText) {
  if (href && !isPlaceholderOrInvalidUrl(href)) {
    linkEl.href = href;
    linkEl.style.display = "inline";
  } else {
    linkEl.removeAttribute("href");
    linkEl.style.display = "none";
  }
  linkEl.textContent = fallbackText;
}

function formatEventMeta(event) {
  const parts = [];
  const originalStart = event.extendedProps.original_start ? new Date(event.extendedProps.original_start) : event.start;
  const originalEnd = event.extendedProps.original_end ? new Date(event.extendedProps.original_end) : event.end;

  if (originalStart) {
    parts.push(detailFormatter.format(originalStart));
  }
  if (originalEnd) {
    parts.push(`to ${detailFormatter.format(originalEnd)}`);
  }
  const location = event.extendedProps.location_name || "Location TBD";
  parts.push(location);
  if (event.extendedProps.organizer) {
    parts.push(event.extendedProps.organizer);
  }
  return parts.join(" | ");
}

function showEventDetails(event) {
  const props = event.extendedProps;

  eventTitle.textContent = event.title;
  eventMeta.textContent = formatEventMeta(event);
  eventDescription.textContent = props.description || "No description available.";

  setLink(mapLink, props.map_url, "Open Map");
  setLink(ticketLink, props.ticket_url, "Tickets / Registration");
  setLink(discountLink, props.discount_url, props.discount_text || "Discount Offer");

  dialog.showModal();
}

function updateViewSummary() {
  const view = calendar.view;
  const start = new Date(view.activeStart);
  const end = new Date(view.activeEnd.getTime() - 1);
  viewRangeLabel.textContent = `${shortDateFormatter.format(start)} to ${shortDateFormatter.format(end)}`;
}

function updateCalendarStatus(message) {
  calendarStatus.textContent = message;
}

function closeControlsMenu() {
  controlsMenu.hidden = true;
  controlsToggle.setAttribute("aria-expanded", "false");
}

function toggleControlsMenu() {
  const shouldOpen = controlsMenu.hidden;
  controlsMenu.hidden = !shouldOpen;
  controlsToggle.setAttribute("aria-expanded", String(shouldOpen));
}

controlsToggle.addEventListener("click", (event) => {
  event.stopPropagation();
  toggleControlsMenu();
});

controlsMenu.addEventListener("click", (event) => {
  event.stopPropagation();
});

scrapeButton.addEventListener("click", async () => {
  scrapeButton.disabled = true;
  scrapeButton.textContent = "Refreshing...";
  updateCalendarStatus("Refreshing source listings...");
  try {
    await fetch("/api/scrape-now", { method: "POST" });
    calendar.refetchEvents();
  } finally {
    scrapeButton.disabled = false;
    scrapeButton.textContent = "Refresh Events";
  }
});

closeDialogButton.addEventListener("click", () => dialog.close());
closeDayDialogButton.addEventListener("click", () => dayDialog.close());

document.addEventListener("click", (event) => {
  closeControlsMenu();
  if (event.target === dialog) {
    dialog.close();
  }
  if (event.target === dayDialog) {
    dayDialog.close();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeControlsMenu();
  }
});

const calendarEl = document.getElementById("calendar");
calendar = new FullCalendar.Calendar(calendarEl, {
  initialView: "dayGridMonth",
  timeZone: HK_TIME_ZONE,
  firstDay: 1,
  height: "100%",
  expandRows: true,
  nowIndicator: true,
  dayMaxEventRows: 3,
  fixedWeekCount: false,
  showNonCurrentDates: false,
  headerToolbar: {
    left: "prev today next",
    center: "title",
    right: "dayGridMonth,timeGridWeek,timeGridDay",
  },
  buttonText: {
    today: "Today",
    month: "Month",
    week: "Week",
    day: "Day",
  },
  eventTimeFormat: {
    hour: "numeric",
    minute: "2-digit",
    meridiem: "short",
  },
  titleFormat: { year: "numeric", month: "long" },
  datesSet: () => {
    clearMonthMarkers();
    updateViewSummary();
    updateCalendarStatus("Loading events for this view...");
  },
  eventSources: [
    {
      events: async (fetchInfo, successCallback, failureCallback) => {
        try {
          clearMonthMarkers();
          if (activeCategories.size === 0) {
            successCallback([]);
            updateCalendarStatus("Select at least one category to show events.");
            return;
          }
          const response = await fetch(buildEventsUrl(fetchInfo));
          const rawEvents = await response.json();
          const viewType = getCalendarViewType(fetchInfo);
          const events = viewType === "dayGridMonth" ? [] : rawEvents;
          successCallback(events);
          if (viewType === "dayGridMonth") {
            queueMonthMarkerPaint(rawEvents);
          }
          if (rawEvents.length === 0) {
            updateCalendarStatus("No events landed in this date range yet.");
          } else {
            updateCalendarStatus(`${rawEvents.length} event${rawEvents.length === 1 ? "" : "s"} in this view`);
          }
        } catch (error) {
          updateCalendarStatus("Could not load events right now.");
          failureCallback(error);
        }
      },
    },
  ],
  eventClick: (info) => {
    showEventDetails(info.event);
  },
  eventContent: (info) => {
    const viewType = getCalendarViewType(info);
    if (viewType !== "dayGridMonth") {
      return undefined;
    }

    const dot = document.createElement("span");
    dot.className = "calendar-dot";
    dot.style.background = info.event.backgroundColor || info.event.borderColor || "#ffffff";
    dot.setAttribute("aria-label", info.event.title);
    return { domNodes: [dot] };
  },
  eventDidMount: (info) => {
    const startLabel = info.event.start ? timeFormatter.format(info.event.start) : "";
    info.el.title = startLabel ? `${info.event.title} - ${startLabel}` : info.event.title;
  },
});

(async () => {
  await loadCategories();
  calendar.render();
  updateViewSummary();
  requestAnimationFrame(() => {
    calendar.updateSize();
    calendar.refetchEvents();
  });
})();
