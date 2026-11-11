# LB-GUIDE-NE progress

2026-11-11T02:32:00+01:00 — `src/content/docs/use/lists-and-filters.md` finished. The switch hides only marked No records, keeps missing values, shows “Active: not No”, and displays a zero count; the ordinary Yes filter remains distinct. Checked switch, pill and query code; no steering file exists and no uncertainty affects this text.

2026-11-11T02:32:12+01:00 — `src/content/docs/guide/use/find-records.md` finished. The task now checks the “Active: not No” pill and explains that missing values stay visible, while choosing Yes separately excludes them. Kept sidebar details linked to Applications; no steering file exists and no uncertainty affects this text.

2026-11-11T02:32:24+01:00 — `src/content/docs/use/applications.md` finished. Find a list now says it matches one phrase in the typed word order, ignoring case; reversing words does not match that phrase. Verified `narrowNavigation`; kept counts, groups and keyboard instructions unchanged. No steering file exists.

2026-11-11T02:32:35+01:00 — `src/content/docs/model/record-pages-and-tables.md` finished. The table-setting explanation now describes exactly the marked records being hidden, the not No pill, retained missing values and the zero count, separately from an ordinary Yes choice. Left authoring and context rules unchanged; no steering file exists and no uncertainty affects this text.

2026-11-11T02:32:48+01:00 — `src/content/docs/guide/model/choose-table-columns-filters-and-sort.md` finished. The post-activation check now verifies not No, retained missing values and the zero count; an ordinary Yes filter no longer incorrectly turns the switch on. Kept the authoring steps unchanged; no steering file exists and no uncertainty affects this text.

2026-11-11T02:33:15+01:00 — `src/content/docs/integrate/identifiers-paging-and-errors.md` reviewed and left unchanged. It explains paging and errors but does not list filter operators, so the wave explicitly calls for no addition; checked the yes/no attribute ne contract in `docs/API.md` against the query implementation. No steering file exists.

2026-11-11T02:33:15+01:00 — `src/content/docs/use/lists-and-filters.md` illustration and final wording finished. Added the screenshot placeholder `list-hide-inactive-not-no.png`: capture the reference table with the switch on, its count and not No pill visible, and Yes plus unset rows retained. The picture is not taken yet; no steering file exists.

2026-11-11T02:33:44+01:00 — Final validation finished. `GUIDE_OUT=_build/LB-GUIDE-NE npm run build` passed (257 pages, 3.74 s); Astro warned about the existing competing /404 routes. Checked six pages’ front matter and local documentation link targets and confirmed built HTML for the five edited pages.

Evidence and limits: switch recognition/count/filter, boolean pill wording, ordinary Yes filtering, exact-false table marking, backend ne inclusion of absent values, sidebar phrase matching, and the API contract were checked in source. No running-instance or screenshot inspection was performed; all existing picture references resolve, and only the new `list-hide-inactive-not-no.png` remains to capture. No behavior in scope could not be described honestly. The comment immediately above `HideInactive` still says `<field> = true`, although its implementation uses `ne false`; this stale source comment was left untouched. No steering file was present at any unit boundary.
