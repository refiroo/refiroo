
- 2026-11-05T20:44:51+01:00 — `guide/src/content/docs/run/overview.md`: Updated the storage tables with both assistant volumes, paths, contents, optional backups and upgrade persistence. Explained what `down` keeps and `down -v` removes. No uncertainties; no steering file was present.

- 2026-11-05T20:44:51+01:00 — `guide/src/content/docs/run/ai.md`: Replaced the obsolete loss warning with named volumes, mount paths, upgrade persistence and the optional backup tradeoff, preserving retention rules. No uncertainties; no steering file was present.

- 2026-11-05T20:44:51+01:00 — `guide/src/content/docs/run/background-jobs.md`: Corrected persistence across replacement and upgrades and explained the consequence of omitting assistant volumes from backups. No uncertainties; no steering file was present.

- 2026-11-05T20:45:19+01:00 — `guide/src/content/docs/run/set-up-ai.md`: Replaced the instruction to finish or discard tasks before recreation with the persistence provided by the two named volumes. No uncertainties; no steering file was present.

- 2026-11-05T20:45:19+01:00 — `guide/src/content/docs/run/backup-and-restore.md`: Explained which assistant volumes the backup procedure omits, their mount paths and contents, and the effect on open tasks after recovery. No uncertainties; no steering file was present.

- 2026-11-05T20:45:19+01:00 — `guide/src/content/docs/run/install-with-compose.md`: Updated backup scope, upgrade persistence and custom mount paths. Explained all named volumes removed by `down -v`. No uncertainties; no steering file was present.

- 2026-11-05T20:45:19+01:00 — `guide/src/content/docs/run/upgrades.md`: Named the volumes retained during upgrades, explained assistant contents and paths, optional backup consequences and the destructive effect of `down -v`. No uncertainties; no steering file was present.

- 2026-11-05T20:45:46+01:00 — Validation complete for all seven pages: `GUIDE_OUT=_build/C5f-ASSISTANT-VOLUMES npm run build` in `guide/` passed (247 pages, 8.86 seconds). Build warnings: unsupported `caddyfile` highlighting in unchanged `run/https.md` fell back to text, and a conflicting `/404` route; no uncertainties about the volume facts, and no screenshots needed.
