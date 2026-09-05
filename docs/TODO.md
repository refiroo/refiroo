# Project TODO

This file is the prioritized delivery queue. The roadmap owns sequencing and outcomes; the Base 0.6
implementation plan owns detailed contracts and work packages. Keep completed historical work in its
release plan and changelog rather than accumulating it here.

## Now — Base 0.6

- [ ] WP0: walk the Base 0.6 acceptance journeys and approve the interaction specification.
- [ ] D1: define workspace authority, provisioning, default selection and retirement behavior.
- [ ] D2: define the authority and allowed values for runtime object state.
- [ ] D3: define typed table/mapping-grid contracts and schema 0.4 compatibility.
- [ ] D4: define atomic mapping replacement and its concurrency token.
- [ ] D5: choose ownership or adoption of accessible UI primitives.
- [ ] WP1: implement the UI foundation and simplified application shell.
- [ ] WP2: add the workspace catalogue, typed collection semantics and configured attribute filters/
  sorts.
- [ ] WP3: provide one coherent create/edit object workflow.
- [ ] WP4: improve model-workbench navigation, diagnostics, provenance and dirty-input protection.
- [ ] WP5: implement cursor-paged single-row mapping create/remove/replace and create-target.
- [ ] WP6: add browser, accessibility and visual-regression gates and complete release validation.

See `BASE_0_6_IMPLEMENTATION_PLAN.md` for scope, file boundaries and exit criteria.

## Next

- [ ] Translation coverage matrix and in-cell lifecycle workflow.
- [ ] Lazy hierarchy workspace with contextual creation and atomic reparenting.
- [ ] Integration-grade query expressions beyond Base 0.6 daily-use filters.
- [ ] Bounded bulk object and relation operations, including bulk mapping.
- [ ] Asynchronous CSV/Excel import and export with validation previews.
- [ ] Ordered change feed and retryable webhooks.

## Later — production and self-service authoring

- [ ] PostgreSQL performance and multi-writer uniqueness hardening.
- [ ] OIDC, application/object/operation authorization and audit identity.
- [ ] Multi-node active-model propagation and protected publication.
- [ ] Structured model designer with reference-aware forms, matrices and live preview.
- [ ] Read-only dependency graph visualization where it improves comprehension.
- [ ] Executable runtime-data migration plans for currently blocked model changes.
- [ ] Extension packaging after two concrete reuse cases exist.

## Explicitly not planned for Base 0.6

- Graph-canvas-first model authoring.
- Arbitrary server-filesystem model load/save.
- Client-side loops over single-item APIs presented as bulk operations.
- Starter-key branches in backend or frontend behavior.
