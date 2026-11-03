# C7-ABOUT validation

Final command (guide directory): `GUIDE_OUT=_build/C7-ABOUT npm run verify`.

- Build passed, including the ten About pages and copied SVG.
- Terms and brand passed across 199 source pages.
- Links checked 44,946 local references across 200 built pages. No About page link or image failed.
- Whole-guide verification exited 1 for 32 references in other waves, listed below. Files outside this assignment were not edited to resolve them.
- Front matter confirmed for all ten authored pages; SVG parsed as valid XML. All 45 coverage rows accounted for, with zero uncovered markers. C0038 remains an internal test exclusion; C0040 retains its deferred AI marker, with current security content mapped in completion notes.
- Existing phone screenshot inspected directly. Authored SVG rendered through the installed sharp package into this notes directory and visually inspected: all text fits and arrows clearly distinguish Live application and publication creation.
- A Chrome launch for diagram inspection failed under this session's sandbox (SIGABRT). No built-page browser appearance, screen-reader testing, application tests or security reassessment was completed. The diagram inspection used the raster fallback, not a browser.

## References outside wave ownership

- `links: guide/integrate/subscribe-a-webhook-and-verify-it/index.html: href "/docs/administer/webhooks/" points to nothing`
- `links: guide/model/map-a-column/index.html: src "/docs/screens/model-workbook-map-column.png" points to nothing`
- `links: guide/model/map-a-column/index.html: src "/docs/screens/model-workbook-value-map.png" points to nothing`
- `links: guide/model/migrate-a-workspace/index.html: src "/docs/screens/model-migration-review.png" points to nothing`
- `links: guide/model/migrate-a-workspace/index.html: src "/docs/screens/model-migration-loss-confirm.png" points to nothing`
- `links: guide/model/migrate-a-workspace/index.html: src "/docs/screens/model-migration-stale.png" points to nothing`
- `links: guide/model/raise-a-model-language-version/index.html: src "/docs/screens/model-language-raise-review.png" points to nothing`
- `links: guide/model/read-lists-in-a-sheet/index.html: src "/docs/screens/model-workbook-list-range.png" points to nothing`
- `links: guide/use/add-a-language-with-a-workbook/index.html: src "/docs/screens/workbook-columns-per-parent.png" points to nothing`
- `links: guide/use/add-a-record/index.html: src "/docs/screens/new-record-required-connections.png" points to nothing`
- `links: guide/use/continue-a-long-list/index.html: src "/docs/screens/list-position-and-seek.png" points to nothing`
- `links: guide/use/delete-many-records/index.html: src "/docs/screens/bulk-delete-impact.png" points to nothing`
- `links: guide/use/export-records/index.html: src "/docs/screens/export-for-people.png" points to nothing`
- `links: guide/use/load-the-next-version-of-a-workbook/index.html: src "/docs/screens/import-profile-next-version.png" points to nothing`
- `links: guide/use/open-a-retired-or-unavailable-workspace/index.html: src "/docs/screens/workspace-cannot-open.png" points to nothing`
- `links: guide/use/propose-a-change/index.html: src "/docs/screens/contributor-propose-change.png" points to nothing`
- `links: guide/use/replace-a-records-related-records/index.html: src "/docs/screens/replace-related-records.png" points to nothing`
- `links: guide/use/reshape-a-hierarchy/index.html: src "/docs/screens/hierarchy-restructure-plan.png" points to nothing`
- `links: integrate/consumer-events-and-webhooks/index.html: href "/docs/administer/webhooks/" points to nothing`
- `links: model/migrations/index.html: src "/docs/screens/model-migration-review.png" points to nothing`
- `links: run/background-jobs/index.html: src "/docs/screens/run-jobs.png" points to nothing`
- `links: run/backup-and-restore/index.html: src "/docs/screens/run-backup-rehearsal.png" points to nothing`
- `links: run/configure/index.html: src "/docs/screens/run-deployment.png" points to nothing`
- `links: run/monitoring/index.html: src "/docs/screens/run-operations.png" points to nothing`
- `links: run/sign-in-and-mail-setup/index.html: href "/docs/guide/administer/set-up-mail/" points to nothing`
- `links: run/webhook-delivery/index.html: href "/docs/guide/administer/create-a-webhook/" points to nothing`
- `links: use/appearance-and-devices/index.html: src "/docs/screens/appearance-display-choices.png" points to nothing`
- `links: use/appearance-and-devices/index.html: src "/docs/screens/phone-navigation-drawer.png" points to nothing`
- `links: use/changing-many-records/index.html: src "/docs/screens/bulk-selection-preview.png" points to nothing`
- `links: use/importing-and-exporting/index.html: src "/docs/screens/import-preview-columns.png" points to nothing`
- `links: use/jobs/index.html: src "/docs/screens/job-results-and-file.png" points to nothing`
- `links: use/notifications-settings/index.html: src "/docs/screens/notification-email-digest.png" points to nothing`
