# Accessibility Audit

Audit target: local homepage at `http://127.0.0.1:5050/`  
Date: 2026-06-04  
Tool: `npx --yes pa11y http://127.0.0.1:5050/ --reporter json`

## Automated Scan Summary

pa11y reported 13 WCAG2AA errors:

- 2 empty heading errors: `#eventTitle` and `#dayTitle` are empty before their dialogs are populated.
- 3 contrast errors: month category count badges render white text on category colors with ratios below 4.5:1.
- 8 FullCalendar table/ARIA errors: generated table elements with `role="presentation"` contain semantic children.

The scan was run against the current Flask page served by `run.py`, not a static HTML file.

## Manual Keyboard Checklist

| Area | Check | Result | Notes |
| --- | --- | --- | --- |
| Event menu | Toggle opens/closes with mouse and has `aria-expanded`/`aria-controls`. | Pass with follow-up | Keyboard focus reaches the button; Escape closes menu. Add future focus-return check when menu closes. |
| Filters | Category chips use real checkboxes and visible `:focus-within` styling. | Pass | Implemented in `static/app.js` and `static/styles.css`. |
| Search | Search input and Clear button are native controls. | Pass | Search refreshes calendar data client-side. |
| Calendar days | Event days get `tabIndex=0` and open on Enter/Space. | Pass with follow-up | Code path is `bindDayCell()` in `static/app.js`; screen-reader semantics still depend on FullCalendar markup. |
| Event dialog | Close button is keyboard reachable. | Needs fix | Empty `#eventTitle` is reported before event content is populated. |
| Day dialog | Close button and event cards are keyboard reachable. | Needs fix | Empty `#dayTitle` is reported before day content is populated. |
| Links | Map, tickets, discount, and calendar links are hidden when unavailable. | Pass | `setLink()` and `setCalendarDownloadLink()` remove inactive links from the tab order. |

## Filed Defects

| ADO ID | Severity | Defect | Evidence |
| --- | --- | --- | --- |
| #44 | High | Event dialog heading is empty before event selection. | pa11y H42.2 on `#eventTitle`; see `templates/index.html` and `showEventDetails()` in `static/app.js`. |
| #45 | High | Day dialog heading is empty before day selection. | pa11y H42.2 on `#dayTitle`; see `templates/index.html` and `openDayEvents()` in `static/app.js`. |
| #46 | Medium | FullCalendar presentation roles contain semantic children. | pa11y F92/ARIA4 warnings in generated FullCalendar table markup. |
| #47 | Medium | Month event count badges fail contrast on green categories. | pa11y G18 ratio 3.52:1 on `.month-category-pill strong`. |
| #48 | Medium | Month event count badges fail contrast on amber categories. | pa11y G18 ratio 2.59:1 on `.month-category-pill strong`. |

## Remediation Order

1. Fix dialog headings first because they affect screen-reader orientation in modal workflows.
2. Fix month badge contrast by deriving accessible text colors or using darker badge backgrounds.
3. Investigate FullCalendar accessibility options before overriding generated ARIA roles manually.
4. Re-run pa11y after each UI fix and add automated a11y checks in CI under work item #33.

## Re-test Commands

```bash
.venv/bin/python run.py
npx --yes pa11y http://127.0.0.1:5050/ --reporter json
.venv/bin/python -m pytest
```
