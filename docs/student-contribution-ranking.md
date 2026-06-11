# Student Contribution Ranking — End of Project

This document summarizes individual contributions to [Hong Kong Event Time](https://hk-event-time-chc0gye3c5byckcq.southeastasia-01.azurewebsites.net/) at the end of the student project phase. It is based on git history, code review, and the [Azure DevOps board](https://dev.azure.com/gbs-hk/hk-event-time).

**Official project window:** 23 April – 11 June 2026 (~7 weeks, ~17.5 expected hours per student). Scores below are **raw/comparative**; see [First-project calibration](#first-project-calibration-apr-23--jun-11-2026) for age-, time-, and participation-adjusted grades.

Teacher commits (`acuhlmann@gmail.com`) are excluded from student totals. Teacher CI/OIDC scaffolding (Apr 22–23) is credited separately in the calibration section. Dependabot and automated agents are excluded.

## Final ranking

| Rank | Student | GitHub | Score |
| ---: | --- | --- | ---: |
| 1 | Leo Zillekens | `LeoZille` | **92 / 100** |
| 2 | Ezra Böhm | `ezraboehm07` | **78 / 100** |
| 3 | Ferdinand von Schönfels | `Doidir` | **71 / 100** |
| 4 | Jonah Busch | `JNAB856` | **58 / 100** |

## How we scored (100 points)

| Dimension | Weight | What it measures |
| --- | ---: | --- |
| Features | 30 | User-visible product value — calendar UI, scrapers, data freshness |
| NFRs | 25 | Accessibility, observability, ops, security, performance, documentation |
| Production success | 25 | Would the live site work and stay healthy without this work? |
| ADO discipline | 10 | Commits linked to work items; board items closed with evidence |
| Understanding | 10 | Tests, iterative fixes, precise commits — not blind prompting |

## Score breakdown

| Rank | Student | Features | NFRs | Prod success | ADO | Understanding | **Total** |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Leo Zillekens | 28 | 24 | 25 | 10 | 10 | **92** |
| 2 | Ezra Böhm | 27 | 12 | 18 | 3 | 8 | **78** |
| 3 | Ferdinand von Schönfels | 8 | 22 | 16 | 6 | 7 | **71** |
| 4 | Jonah Busch | 22 | 8 | 14 | 4 | 9 | **58** |

---

## 1. Leo Zillekens — 92 / 100

**Summary:** Broadest impact. Only student who both **shipped the app to Azure** and **closed full NFR epics** with traceable Azure DevOps links.

**Features**
- Initial Flask stack and sustained scraper/data pipeline (URBTIX, quality filters in `app/services.py`).
- Critical production path (~15 commits, Apr 24–27): SQLite writable path, `startup.sh`, `azure-deploy` workflow, health endpoint, dependency bundling. Without this work the site would not be live on App Service.

**NFRs**
- **Epic 17 Accessibility (Done):** #30–#33, #44–#48 — audit in [a11y-audit.md](a11y-audit.md), UI fixes, pa11y CI in `.github/workflows/accessibility.yml`.
- **Epic 18 Docs (Done):** #34 mental model, #36 quiz cards, #37 [AGENTS.md](../AGENTS.md).
- **Epic 14 Observability:** #25 structured scrape logs + `tests/test_scrape_observability.py`.
- **Epic 15 Analytics:** #21 HKET.* telemetry, PII-safe endpoint, [analytics.md](analytics.md), `tests/test_analytics.py`.
- **Security:** #41 dependency patches.

**ADO discipline:** 23 of 41 commits reference work items (`#21`, `#25`, `#30`–`#37`, `#41`). Use this as the model for future work.

**Understanding:** Iterative pa11y CI fixes, analytics sanitization tests, a11y defects filed back to exact code paths, structured scrape log payloads with unit tests.

---

## 2. Ezra Böhm — 78 / 100

**Summary:** Product founder and primary UI author — the calendar experience users interact with today.

**Features**
- Initial project import — app skeleton, tests, categories, scraper baseline.
- Core UX (#38, #39 Done): event search, select-all/clear category filters, `.ics` “Add to Calendar” in `static/app.js`.
- Event menu polish, detail popups, link bug fixes.
- Responsive layout — `@media` breakpoints in `static/styles.css` (see ownership note below).
- PostgreSQL / Azure DB support.

**ADO discipline:** Board items #7, #38, #39 are Done and assigned correctly, but **no commits use `#` work-item prefixes**. Deliverables match the board; traceability is implicit only.

**Understanding:** Strong commit on calendar usability (lists behaviors, validation steps). ICS builder and client-side search show domain knowledge, not generic copy-paste.

**Improve for next time:** Put `#38 Add calendar download` (or similar) in every commit message that closes a board item.

---

## 3. Ferdinand von Schönfels — 71 / 100

**Summary:** Strong operations and reliability work; less user-facing surface area, but production-grade NFR delivery including Azure portal configuration.

**Features**
- Auto-delete events older than 30 days.
- Calendar popover readability, post-deploy healthcheck alignment, Python 3.10 runtime.

**NFRs**
- **#35 Done:** [operations.md](operations.md) — site down, health degraded, stale scrape, rollback, RBAC tables.
- **#22 Done:** Deepened `/health` with DB probe, 503 on failure, `tests/test_health.py`.
- **#23 Done:** Azure Monitor availability alerting — **verified in production** (see below).
- **#24 Doing:** Error/performance alerts — incomplete.

**WI #23 verification (Azure CLI, Jun 2026)**

Ferdinand’s portal work for “Azure Monitor alert when site unavailable” is configured and enabled:

| Resource | Purpose |
| --- | --- |
| Web test `hk-event-time-health-appinsights-hk-event-time` | Pings production `/health` from Application Insights |
| Alert `hk-event-time-health-unavailable` | Fires when availability drops below 100% over 5 minutes |
| Action group `hk-event-time-alerts` | Email to `ferdinand.schoenfels@gmail.com` and teacher |

This matches acceptance criteria for #23: multi-region availability test, alert on failure, action group with team + teacher, runbook cross-reference in [operations.md](operations.md).

**ADO discipline:** Board assignments align (#22, #23, #35 Done). Commits do not use `#` prefixes.

**Understanding:** Correct health-check semantics (SQLAlchemy `SELECT 1`, HTTP 503). Runbook shows ops thinking with exact `az`/`curl` commands.

---

## 4. Jonah Busch — 58 / 100

**Summary:** High-impact early backend work; limited follow-through on later assigned epics.

**Features**
- Major scraper expansion: Eventbrite (~367 LOC), Luma, sample scraper enhancements.
- Flask debug reloader fix (`WERKZEUG_RUN_MAIN`) stopping infinite scrape loop; month-pagination scraping; placeholder URL cleanup.
- Dependency vulnerability patch.

**NFRs**
- Security patch only.
- **Epic 16 Performance (assigned, Doing):** #26–#29 all **To Do**; test plan #50–#51 “stresstesting” active — no load-test scripts or docs in repo.
- **Epic 15 Analytics** marked Done on board for Jonah, but implementation was Leo’s #21.

**Understanding:** Best quality-per-commit ratio — scheduler/reloader fix and month-pagination design show real Flask/scraping knowledge. Small sample size limits total impact.

---

## Lessons for the team

### Azure DevOps linking — do what Leo did

Every commit or PR that closes board work should include the work item ID:

```text
#33 Fix accessibility workflow YAML
#38 Add calendar download (.ics) to event dialog
```

Why it matters:

- Links git history to the board automatically (when GitHub connection is authorized).
- Makes grading and retrospectives evidence-based.
- Proves you know *which* task you finished, not just that code changed.

**Model:** Leo — 23 commits with explicit `#NN` references.

### Epic ownership mismatches to clarify

These board states do not fully match git delivery. Discuss as a team so credit and assignments stay honest:

| Item | Board state | What git shows |
| --- | --- | --- |
| **#3 Responsive design** | Done, assigned to Ferdinand | `@media` responsive CSS largely authored by Ezra |
| **Epic 15 Analytics** | Done, assigned to Jonah | Implemented by Leo (#21 — telemetry, docs, tests) |
| **Epic 16 Performance** | Doing, assigned to Jonah | #26–#29 still To Do; no load-test artifacts in repo |

**Recommendation:** When closing a work item, the assignee (or whoever did the work) should add a short ADO comment with the commit SHA and file paths — especially when work is pair-reviewed or handoff happens mid-epic.

### Understanding vs prompting — signals we looked for

**Strong signals (rewarded):**

- Unit tests that assert real behavior (`test_analytics.py`, `test_health.py`, `test_scrape_observability.py`).
- Iterative fix chains (13 commits tuning pa11y CI).
- Detailed commit bodies with validation steps.
- Docs that cite exact routes and files ([a11y-audit.md](a11y-audit.md), [quiz-prep.md](quiz-prep.md)).

**Weaker signals (not penalized harshly, but noted):**

- Generic messages (“UI improvements”, “Initial commit”) without work-item IDs.
- Board items marked Done without matching commits or portal evidence.

No evidence of copy-paste-only contribution at scale; the main gap is **incomplete epics**, not low quality where work exists.

---

## Grading narrative (teacher summary)

1. **Leo** — Distinguished: carried production, closed Epics 17–18, major Epic 14/15 deliverables, gold-standard ADO linking.
2. **Ezra** — Strong: founded the product and core UX; improve work-item traceability in commits.
3. **Ferdinand** — Solid NFR/ops: runbook, health endpoint, and verified Azure alerts; finish #24; clarify #3 ownership with Ezra.
4. **Jonah** — Competent early backend, incomplete later epics: reward scraper/scheduler quality; Epic 16 and Epic 15 board state need correction.

---

## Limitations

- GitHub PR review comments were not available for this ranking (commit history only).
- Some infrastructure (MCP, entitlements, early App Insights) was set up by the teacher before student epics.
- Scores are comparative within this cohort, not absolute industry benchmarks.

---

## First-project calibration (Apr 23 – Jun 11, 2026)

This section adjusts the scores above for **context**, not to change the relative order lightly.

### Project constraints

| Factor | Value |
| --- | --- |
| Official project start | **23 April 2026** |
| End | 11 June 2026 |
| Duration | ~7 weeks |
| Expected time | ~2 h/week class + ~30 min/week homework ≈ **17.5 h** per student |
| Cohort | 18-year-olds, **first software project** |
| Tools | Full access to AI coding agents (expected, not cheating) |

### What the teacher contributed (do not credit students)

Alex Uhlmann (`acuhlmann@gmail.com`) shipped scaffolding students built on top of:

- **Initial CI/CD (Apr 22–23):** GitHub Actions auto-deploy, Azure OIDC login, health-check workflow foundation — before the Flask pivot ([`310b37f`](git) and related Apr 23 commits).
- **Post–Apr 23:** Azure DevOps MCP docs (#40), entitlements/onboarding (#43, #49), and **runbook expansion** on top of Ferdinand’s draft (#42, May 22).

Students still earn credit for **extending** this (Leo’s Flask `azure-deploy.yml` iterations, Leo’s `accessibility.yml`, Ferdinand’s healthcheck tweak), but not for **inventing** the pipeline.

### Activity since project start (Apr 23)

| Student | Commits Apr 23 – Jun 11 | In-window delivery |
| --- | ---: | --- |
| Leo Zillekens | 39 | Flask/Azure deploy fixes, scrapers, full Epics 14–18 code + a11y CI |
| Ferdinand von Schönfels | 6 | Runbook, health endpoint, README/deploy hygiene (+ portal alerts #23) |
| Ezra Böhm | 5 | UI shell refresh, event menu, search/filters/`.ics` (#38, #39) |
| Jonah Busch | **2** (both 24 Apr) | Scheduler fix, month-pagination scrape, dependency patch — **then no commits for ~7 weeks** |

Jonah’s large Eventbrite/Luma scraper commit (**13 Apr**) predates the official project start and is noted as prior work only.

### Better or worse than the raw scores?

**Judge active students’ outcomes better; judge Jonah worse on participation.**

- **Better (curve up):** For Leo, Ezra, and Ferdinand, a live Azure app with a11y CI, analytics, ops runbook, and verified alerts in ~17.5 expected hours is **strong for a first project with AI**. Absolute scores should be gentler than an industry-junior bar.
- **Unchanged:** Relative rank (Leo → Ezra → Ferdinand → Jonah) stays the same.
- **Stricter where effort is near-zero:** ADO `#NN` linking costs seconds; Leo proved the habit is doable.
- **Jonah — explicit downgrade:** Months lost to **coding-tool setup** instead of contributing is a **professionalism / engagement** failure, independent of ability. His last in-window commits are **24 Apr**; Epic 16 (#26–#29) undelivered; Epic 15 marked Done on the board but implemented by Leo (#21). Quality of the two April commits does not offset disengagement.

### Calibrated scores

| Rank | Student | Raw score | **Calibrated** | Letter (suggested) |
| ---: | --- | ---: | ---: | --- |
| 1 | Leo Zillekens | 92 | **95** | A+ |
| 2 | Ezra Böhm | 78 | **82** | B+ |
| 3 | Ferdinand von Schönfels | 71 | **83** | B+ |
| 4 | Jonah Busch | 58 | **50** | D |

**Adjustments in plain language:**

1. **Leo (+3):** Exceptional volume and epic closure in the project window; small discount because deploy CI **started from teacher OIDC/Actions**, not from zero.
2. **Ezra (+4):** Strong user-facing delivery for a beginner; May UI work maps to Done board items; not penalized for pre–Apr 23 history, but “founder” framing is reduced to **in-window UI lead**.
3. **Ferdinand (+12):** Raw score underweighted ops — runbook, health, and verified Azure alerts are high **return per hour** for a first project; feature points were low only because assigned epics were NFR/ops.
4. **Jonah (−8):** **Participation penalty** for prolonged tool-setup delay and **2 commits in 7 weeks** after Apr 24; Epic 16 not attempted; misleading Epic 15 board state. Technical quality of the reload/pagination fix remains noted but does not carry the grade.

### Calibrated grading narrative

1. **Leo — Outstanding (A+):** Carried the Flask production path and closed multiple epics with tests and ADO links; model for how to use AI with verification.
2. **Ezra — Very good (B+):** Delivered the core calendar UX students were assigned; improve commit ↔ work-item linking.
3. **Ferdinand — Very good (B+):** Best ops arc in the cohort; portal alerting counts fully; finish #24 next time.
4. **Jonah — Poor engagement, competent snippet (D):** Two good April commits show ability, but **months without meaningful contribution** and abandoned assigned epic are not acceptable; tool setup is homework for week one, not weeks three–seven.

*Generated at end of project — Jun 2026. Calibrated section added for first-project context (Apr 23 start).*
