# Validation

- `GUIDE_OUT=_build/C13-AI-MODEL npm run verify` in guide: build passed, 242 pages, 3.79 s. Static check stopped at one brand error in `src/content/docs/use/history.md` (capitalized Refiroo). This file is outside wave ownership and was not edited.
- `GUIDE_OUT=_build/C13-AI-MODEL npm run check:links`: 66,775 links/sources checked; 22 failures, all absent screenshot assets. Eight are this wave's required screenshot placeholders, each recorded in the screens-wanted ledger; fourteen belong to other sections. No broken page/anchor link reported.
- No provider requests, live tasks, application tests, servers or databases started. No git state commands or commits.
- Screenshot placeholders are intentional under guide/AGENTS.md; actual visual states remain unverified. Three captures require a provider unavailable on the reference instance.
- Source disagreements are recorded heading by heading in the reconciliation ledger. Historical rules-only assistant design and provider naming helper were not copied into current task instructions.

- `node --check guide/sidebar/model.mjs`: passed. `GUIDE_OUT=_build/C13-AI-MODEL npm run check:terms` from guide: passed. One initial check:terms attempt from repository root found no package.json; rerun from guide.
