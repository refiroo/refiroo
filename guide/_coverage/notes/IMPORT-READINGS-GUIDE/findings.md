# Import readings guide evidence

Five pages updated: use/importing-and-exporting.md; guide/use/load-the-next-version-of-a-workbook.md; integrate/files-imports-and-exports.md; integrate/model-and-release-operations.md; integrate/workspaces-contexts-and-models.md.

## Code and changelog

CHANGELOG.md, Unreleased, PL3b engine/API says a column the next file lacks takes its reading with it. In backend/app/engine/sources/profile_check.py, _follow_readings instead removes missing members of fillDown and unpivot, retaining fillDown while any column remains and unpivot while at least two remain. Losing the heading column does remove headings; bindings for removed added columns leave the effective reading. The integration page uses the code's precise behavior.

The PL3b canvas changelog's initial positions-only canvas description is extended by CE1's folded cards and scope. Current canvas.py and route/reference text agree on merging positions/folded by key, replacing scope, and exclusion from the draft version/history/release.

The PL3b plan's Engine and API work list calls for readings in PostgreSQL; current readings.py streams rows in Python. Join candidates do compare the full selected tables in PostgreSQL. This is a plan/code difference, not a changelog discrepancy; the pages do not promise a storage implementation.

## Validation

GUIDE_OUT=_build/IMPORT-READINGS-GUIDE npm run build — passed, 259 pages.
GUIDE_OUT=_build/IMPORT-READINGS-GUIDE npm run verify — passed: build, static checks (including sidebar), inventory freshness, coverage, links. The verify environment additionally sets TMPDIR to this notes directory and NODE_OPTIONS to redirect-coverage.mjs, so temporary inventory generation and the generated uncovered report stay inside this wave's notes. No check logic is skipped.

git diff --check restricted to the five pages — passed.

No screenshot references added; no screenshots requested by this wave. No application behavior was tested live. Existing unrelated page changes were preserved; the git diff contains earlier work as well as this wave's additions. Nothing committed.
