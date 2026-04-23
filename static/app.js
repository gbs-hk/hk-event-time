const categoryFiltersEl = document.getElementById("categoryFilters");
const scrapeButton = document.getElementById("scrapeButton");
const refreshDebugButton = document.getElementById("refreshDebugButton");
const dialog = document.getElementById("eventDialog");
const closeDialogButton = document.getElementById("closeDialog");
const emptyState = document.getElementById("emptyState");
const emptyStateText = document.getElementById("emptyStateText");
const calendarStatus = document.getElementById("calendarStatus");
const viewRangeLabel = document.getElementById("viewRangeLabel");
const scrapeProgress = document.getElementById("scrapeProgress");
const debugSources = document.getElementById("debugSources");
const mobileListView = document.getElementById("mobileListView");
const calendarViewButton = document.getElementById("calendarViewButton");
const listViewButton = document.getElementById("listViewButton");

const eventTitle = document.getElementById("eventTitle");
const eventMeta = document.getElementById("eventMeta");
const eventDescription = document.getElementById("eventDescription");
const eventPrice = document.getElementById("eventPrice");
const eventSource = document.getElementById("eventSource");
const eventVenue = document.getElementById("eventVenue");
const eventCategory = document.getElementById("eventCategory");
const sourceLink = document.getElementById("sourceLink");
const mapLink = document.getElementById("mapLink");
const ticketLink = document.getElementById("ticketLink");
const discountLink = document.getElementById("discountLink");
const calendarLink = document.getElementById("calendarLink");

const lastScrapeValue = document.getElementById("lastScrapeValue");
const lastScrapeMeta = document.getElementById("lastScrapeMeta");
const sourcesCheckedValue = document.getElementById("sourcesCheckedValue");
const sourcesCheckedMeta = document.getElementById("sourcesCheckedMeta");
const eventsImportedValue = document.getElementById("eventsImportedValue");
const eventsImportedMeta = document.getElementById("eventsImportedMeta");
const failedSourcesValue = document.getElementById("failedSourcesValue");
const failedSourcesMeta = document.getElementById("failedSourcesMeta");

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
const relativeFormatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

let activeCategories = new Set();
let categories = [];
let activeJobId = null;
let lastRenderedEvents = [];
let currentViewMode = window.innerWidth <= 700 ? "list" : "calendar";

async function loadCategories() {
  const response = await fetch("/api/categories");
  categories = await response.json();
  categories.forEach((category) => activeCategories.add(category.slug));
  renderCategoryFilters();
}

function renderCategoryFilters() {
  categoryFiltersEl.innerHTML = "";
  categories.forEach((category) => {
    const label = document.createElement("div");
    label.className = "legend-chip";

    const dot = document.createElement("span");
    dot.className = "legend-dot";
    dot.style.background = category.color;

    const text = document.createElement("span");
    text.textContent = category.label;

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

function buildCalendarLink(event) {
  const start = event.start ? event.start.toISOString().replace(/[-:]/g, "").split(".")[0] + "Z" : "";
  const end = event.end ? event.end.toISOString().replace(/[-:]/g, "").split(".")[0] + "Z" : start;
  const details = encodeURIComponent(event.extendedProps.description || "");
  const location = encodeURIComponent(event.extendedProps.location_name || "");
  return `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent(event.title)}&dates=${start}/${end}&details=${details}&location=${location}`;
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
  eventPrice.textContent = props.price_text || "TBD";
  eventSource.textContent = props.source_name || "Unknown";
  eventVenue.textContent = props.location_name || props.location_address || "TBD";
  eventCategory.textContent = props.category || "Other";

  setLink(sourceLink, props.source_url, "Source Page");
  setLink(mapLink, props.map_url, "Open Map");
  setLink(ticketLink, props.ticket_url, "Tickets / Registration");
  setLink(discountLink, props.discount_url, props.discount_text || "Discount Offer");
  setLink(calendarLink, buildCalendarLink(event), "Add to calendar");

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
  emptyState.hidden = !isEmpty || currentViewMode === "list";
}

function describeEmptyState() {
  return "Try another month or refresh the sources to pull the latest listings.";
}

function renderMobileList(events) {
  if (currentViewMode !== "list") {
    mobileListView.hidden = true;
    return;
  }

  mobileListView.hidden = false;
  mobileListView.innerHTML = "";

  if (!events.length) {
    return;
  }

  events.forEach((event) => {
    const card = document.createElement("article");
    card.className = "list-card";
    card.innerHTML = `
      <div class="list-card-top">
        <span class="list-pill">${event.extendedProps.source_name || "Source"}</span>
      </div>
      <h3>${event.title}</h3>
      <p>${formatEventMeta(event)}</p>
      <div class="list-card-bottom">
        <span>${event.extendedProps.price_text || "Price TBD"}</span>
        <button class="ghost">Details</button>
      </div>
    `;
    card.querySelector("button").addEventListener("click", () => showEventDetails(event));
    mobileListView.appendChild(card);
  });
}

function updateStatusCards(payload) {
  const lastCompleted = payload.last_completed || null;
  const currentJob = payload.job || null;
  const history = payload.history || [];

  if (lastCompleted) {
    const finished = new Date(lastCompleted.finished_at_utc);
    lastScrapeValue.textContent = shortDateFormatter.format(finished);
    lastScrapeMeta.textContent = `${lastCompleted.processed} kept, ${lastCompleted.rejected_events} rejected`;
    sourcesCheckedValue.textContent = `${lastCompleted.sources_total}`;
    sourcesCheckedMeta.textContent = `${payload.source_mode} mode`;
    eventsImportedValue.textContent = `${lastCompleted.processed}`;
    eventsImportedMeta.textContent = `${history.length} run${history.length === 1 ? "" : "s"} tracked`;
    failedSourcesValue.textContent = `${lastCompleted.failed_sources}`;
    failedSourcesMeta.textContent = `${lastCompleted.empty_sources} empty after filters`;
  } else {
    sourcesCheckedMeta.textContent = `${payload.source_mode} mode`;
  }

  if (currentJob && ["queued", "running"].includes(currentJob.status)) {
    scrapeProgress.textContent = currentJob.message || "Scrape queued";
  } else if (lastCompleted) {
    scrapeProgress.textContent = `Last run finished ${relativeTimeFromNow(lastCompleted.finished_at_utc)}.`;
  }
}

function relativeTimeFromNow(isoString) {
  if (!isoString) {
    return "recently";
  }
  const diffMs = new Date(isoString).getTime() - Date.now();
  const diffHours = Math.round(diffMs / 3600000);
  if (Math.abs(diffHours) >= 1) {
    return relativeFormatter.format(diffHours, "hour");
  }
  const diffMinutes = Math.round(diffMs / 60000);
  return relativeFormatter.format(diffMinutes, "minute");
}

function renderDebugSources(report) {
  const sourceRows = report?.sources || [];
  debugSources.innerHTML = "";

  if (!sourceRows.length) {
    debugSources.innerHTML = `<article class="debug-card"><h3>No debug data yet</h3><p>Run a scrape to inspect raw kept and rejected events.</p></article>`;
    return;
  }

  sourceRows.forEach((source) => {
    const kept = (source.kept || []).slice(0, 4).map(renderDebugItem).join("");
    const rejected = (source.rejected || []).slice(0, 4).map(renderDebugItem).join("");
    const card = document.createElement("article");
    card.className = "debug-card";
    card.innerHTML = `
      <div class="debug-card-head">
        <h3>${source.source_name}</h3>
        <span class="debug-status ${source.status}">${source.status}</span>
      </div>
      <p>${source.fetched} raw scraped, ${source.processed} kept, ${(source.rejected || []).length} rejected.</p>
      <div class="debug-columns">
        <section>
          <h4>Kept</h4>
          <div class="debug-items">${kept || "<p class='muted'>Nothing kept.</p>"}</div>
        </section>
        <section>
          <h4>Rejected</h4>
          <div class="debug-items">${rejected || "<p class='muted'>Nothing rejected.</p>"}</div>
        </section>
      </div>
    `;
    debugSources.appendChild(card);
  });
}

function renderDebugItem(item) {
  const reasons = (item.reasons || []).join(", ") || "none";
  return `
    <div class="debug-item">
      <strong>${item.title}</strong>
      <span>${item.start_time_utc || "no date"}${item.location_name ? ` | ${item.location_name}` : ""}</span>
      <span>score ${item.quality_score || 0} | ${reasons}</span>
    </div>
  `;
}

async function pollScrapeStatus() {
  try {
    const suffix = activeJobId ? `?job_id=${encodeURIComponent(activeJobId)}` : "";
    const response = await fetch(`/api/scrape-status${suffix}`);
    if (!response.ok) {
      throw new Error(`Status request failed with ${response.status}`);
    }
    const payload = await response.json();
    updateStatusCards(payload);
    renderDebugSources(payload.last_completed);

    if (payload.job && ["queued", "running"].includes(payload.job.status)) {
      activeJobId = payload.job.job_id;
      scrapeButton.disabled = true;
      scrapeButton.textContent = payload.job.status === "running" ? "Scraping..." : "Queued...";
      window.setTimeout(pollScrapeStatus, 1500);
    } else {
      scrapeButton.disabled = false;
      scrapeButton.textContent = "Refresh Events";
      activeJobId = null;
    }
  } catch (error) {
    console.error(error);
    scrapeButton.disabled = false;
    scrapeButton.textContent = "Refresh Events";
    scrapeProgress.textContent = "Status unavailable. Check server or reload.";
  }
}

scrapeButton.addEventListener("click", async () => {
  try {
    scrapeButton.disabled = true;
    scrapeButton.textContent = "Queueing...";
    updateCalendarStatus("Queueing live scrape...", false);
    const response = await fetch("/api/scrape-now", { method: "POST" });
    if (!response.ok) {
      throw new Error(`Scrape request failed with ${response.status}`);
    }
    const payload = await response.json();
    activeJobId = payload.job_id;
    scrapeProgress.textContent = "Checking sources...";
    pollScrapeStatus();
  } catch (error) {
    console.error(error);
    scrapeButton.disabled = false;
    scrapeButton.textContent = "Refresh Events";
    scrapeProgress.textContent = "Could not start scrape.";
  }
});

refreshDebugButton.addEventListener("click", async () => {
  await pollScrapeStatus();
});

document.getElementById("emptyPrevMonth").addEventListener("click", () => {
  calendar.prev();
});

document.getElementById("emptyRescrape").addEventListener("click", () => {
  scrapeButton.click();
});

closeDialogButton.addEventListener("click", () => dialog.close());

document.addEventListener("click", (event) => {
  if (event.target === dialog) {
    dialog.close();
  }
});

calendarViewButton.addEventListener("click", () => {
  currentViewMode = "calendar";
  calendarViewButton.classList.add("active");
  listViewButton.classList.remove("active");
  document.getElementById("calendar").hidden = false;
  calendar.updateSize();
  emptyState.hidden = lastRenderedEvents.length > 0;
  renderMobileList([]);
});

listViewButton.addEventListener("click", () => {
  currentViewMode = "list";
  listViewButton.classList.add("active");
  calendarViewButton.classList.remove("active");
  document.getElementById("calendar").hidden = true;
  emptyState.hidden = true;
  renderMobileList(lastRenderedEvents);
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
          lastRenderedEvents = events.map((event) => ({
            ...event,
            start: event.start ? new Date(event.start) : null,
            end: event.end ? new Date(event.end) : null,
          }));
          successCallback(events);
          renderMobileList(lastRenderedEvents);
          if (events.length === 0) {
            emptyStateText.textContent = describeEmptyState();
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
  if (currentViewMode === "list") {
    document.getElementById("calendar").hidden = true;
    listViewButton.classList.add("active");
    calendarViewButton.classList.remove("active");
  }
  await pollScrapeStatus();
})();
