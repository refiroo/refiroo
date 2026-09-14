# Temporary ADR-026 authority review handoff

Status: temporary, uncommitted planning material.

This folder preserves the 2026-09-07 read-only architecture and planning review before corrective
documentation or implementation work. It is intentionally under Git-ignored `build/` so it cannot be
swept into the pending WP8/ADR-026 commit accidentally.

The review concluded that ADR-026 corrected the original product-level mistake—routing ordinary
reference-data maintenance through a release ceremony—but did not migrate every dependent authority
boundary coherently.

Contents:

- `ARCHITECTURE_FINDINGS.md`: evidence-backed blockers and why earlier reviews missed them.
- `NEXT_SESSION_INPUTS.md`: unresolved decisions, sequencing and documentation update map.

Repository snapshot:

- Branch: `main`
- HEAD: `60b99d3 docs: add agent guidance and licensing checklist`
- ADR-026/WP8 changes were present but uncommitted; WP9 had not started.
- Focused command: `backend/.venv/bin/python -m pytest backend/tests/test_model_compatibility.py backend/tests/test_wp8_activation_merge.py backend/tests/test_wp8_retirement.py -q`
- Result: 30 passed, with existing dependency/deprecation warnings.

Passing focused tests do not resolve these findings. Several gaps exist because tests encode the same
stale authority assumption or omit the affected boundary.
