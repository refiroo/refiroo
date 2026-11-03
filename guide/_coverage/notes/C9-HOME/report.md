# C9-HOME handoff

## Pages

- Changed `src/content/docs/examples/the-starter-model.md`: checked applications against the starter declaration, completed capability links and made event watch scope explicit.
- Changed `src/content/docs/examples/the-example-data.md`: completed capability links, including the Systems hierarchy; kept snapshot counts, sources and fictional data explicit.
- Changed `src/content/docs/examples/translations.md`: clarified cell states, required ownership, duplicate refusals and shared history/permissions/publication capabilities.
- Added `src/content/docs/examples/the-consumer-api.md`: starter contract showcase, reference stops declaration excerpt, complete get/list/filtered-list/XREF/resolve/304/error/event/webhook examples. Source values were composed offline through the production renderer, not captured from live HTTP traffic. Positions, cursors, signatures and event occurrences are identified as illustrative or instance-dependent.
- Changed `src/content/docs/index.md`: introduction, four core ideas, six reader starting routes with four recommended pages each, User journeys and API reference links.
- Added `src/content/docs/404.md`: missing-page message, start page, search instructions and section links.

The existing examples sidebar already lists all four pages and was unchanged. All six examples coverage rows are covered; none is open. Coverage relative links were corrected. No new screenshot requests; screens-wanted/C9-HOME.md lists the eight existing captures reused.

## Checks

`GUIDE_OUT=_build/C9-HOME npm run verify`, in guide:

- Build passed: 207 generated pages; search index built. Starlight reported its custom 404 route precedence warning, and the generated 404.html contains the intended custom page.
- Terms and branding passed: 208 source pages.
- Links failed: 22 broken references. The start page's required `/docs/journeys/` destination does not exist in the current sources. The other 21 references belong to other waves' pages: 20 missing screenshot references and one obsolete `/docs/integrate/webhooks/` link. Exact list: `link-check.log`. No out-of-scope files were changed to suppress these failures.

`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend backend/.venv/bin/python guide/_coverage/notes/C9-HOME/compose-examples.py`, from repo root: passed; compiled reference model, composed reference values using production rendering.

`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend backend/.venv/bin/python guide/_coverage/notes/C9-HOME/verify-examples.py`, from repo root: passed. Six response bodies and the resolve request validate against generated stops OpenAPI; composed object values and event declaration match sources; filtered total is 13; webhook byte length and HMAC match production signing and the identity event matches the pull example.

Generated-HTML check: start and 404 headings present, Search controls rendered, 404 search anchor exists. All six coverage rows resolve to existing source files.

## Limits and unresolved points

- Full verify is not green because the destinations above are outside C9's allowed files. Asked whether another wave supplies User journeys; retained the required link pending that destination. The sidebar already reserves journeys/index. No answer received at handoff.
- No live API, database, receiver or browser checks were performed. The original snapshot data and source declarations were checked, and the examples' shapes and signatures were verified offline. Appearance and interaction were not inspected in a browser.
- No confirmed refiroo runtime defect found. The missing guide destinations are documentation completion issues, not verified engine defects.
- No servers or background services were started. No commits or git state-changing commands were run. Only the assigned content, coverage, screenshot-request, progress and note files were edited; build artifacts use the required C9 output directory.
