const categoryFiltersEl = document.getElementById("categoryFilters");
const scrapeButton = document.getElementById("scrapeButton");
const dialog = document.getElementById("eventDialog");
const closeDialogButton = document.getElementById("closeDialog");
const emptyState = document.getElementById("emptyState");
const calendarStatus = document.getElementById("calendarStatus");
const viewRangeLabel = document.getElementById("viewRangeLabel");

const eventTitle = document.getElementById("eventTitle");
const eventMeta = document.getElementById("eventMeta");
const eventDescription = document.getElementById("eventDescription");
const mapLink = document.getElementById("mapLink");
const ticketLink = document.getElementById("ticketLink");
const discountLink = document.getElementById("discountLink");

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

let activeCategories = new Set();
let categories = [];

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

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = activeCategories.has(category.slug);
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        activeCategories.add(category.slug);
      } else {
        activeCategories.delete(category.slug);
      }
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

function setLink(linkEl, href, fallbackText) {
  if (href) {
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
  if (event.start) {
    parts.push(detailFormatter.format(event.start));
  }
  if (event.end) {
    parts.push(`to ${timeFormatter.format(event.end)}`);
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

function updateCalendarStatus(message, isEmpty) {
  calendarStatus.textContent = message;
  emptyState.hidden = !isEmpty;
}

scrapeButton.addEventListener("click", async () => {
  scrapeButton.disabled = true;
  scrapeButton.textContent = "Refreshing...";
  updateCalendarStatus("Refreshing source listings...", false);
  try {
    await fetch("/api/scrape-now", { method: "POST" });
    calendar.refetchEvents();
  } finally {
    scrapeButton.disabled = false;
    scrapeButton.textContent = "Refresh Events";
  }
});

closeDialogButton.addEventListener("click", () => dialog.close());

document.addEventListener("click", (event) => {
  if (event.target === dialog) {
    dialog.close();
  }
});

const calendarEl = document.getElementById("calendar");
const calendar = new FullCalendar.Calendar(calendarEl, {
  initialView: "dayGridMonth",
  timeZone: HK_TIME_ZONE,
  firstDay: 1,
  height: "auto",
  nowIndicator: true,
  dayMaxEventRows: 3,
  headerToolbar: {
    left: "prev,next today",
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
    updateViewSummary();
    updateCalendarStatus("Loading events for this view...", false);
  },
  eventSources: [
    {
      events: async (fetchInfo, successCallback, failureCallback) => {
        try {
          const response = await fetch(buildEventsUrl(fetchInfo));
          const events = await response.json();
          successCallback(events);
          if (events.length === 0) {
            updateCalendarStatus("No events landed in this date range yet.", true);
          } else {
            updateCalendarStatus(`${events.length} event${events.length === 1 ? "" : "s"} in this view`, false);
          }
        } catch (error) {
          updateCalendarStatus("Could not load events right now.", true);
          failureCallback(error);
        }
      },
    },
  ],
  eventClick: (info) => {
    showEventDetails(info.event);
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
})();
