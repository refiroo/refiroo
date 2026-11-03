# C6b evidence and limitations

## Scope

Changed the four assigned pages, adding the shared-form concept for their respective readers. The integrator page compares all fields of a reference stop and its operator side by side. Existing worked requests, event payloads and screenshots remain in place. No new screenshots are needed. This concept wave has no assigned coverage rows or sidebar changes.

## Sources read

- `guide/AGENTS.md`, `_waves/COMPLETE-COMMON.md`, `_waves/C6b-CONSUMER-CONCEPT.md`, the four assigned pages, and reference-data source notes under `guide/samples/`.
- `docs/CONSUMER_API.md`: Why a second API tier and Engine design / Principle and nearby contract lifecycle sections.
- `backend/app/consumer/router.py`: common routes, operation refusal, publication selection, index/OpenAPI, ETags and shared answer handling.
- `backend/app/consumer/etag.py`: common cache semantics.
- `backend/app/engine/reads/consumer_objects.py`: shared object construction, declared field names, related cardinality, nulls and parent/path outputs.
- `backend/app/models/schema.py`: configurable role output names and optional fields/parts.
- `backend/app/engine/model/consumer_contract.py`: compatibility diagnostics and breaking-change comparison.
- `backend/app/engine/model/consumer_openapi.py` and `consumer_rendering.py`: contract-generated documents and declared operations/fields.
- `backend/app/engine/events/delivery.py` and `backend/app/management/errors.py`: shared delivery formats and error envelopes.
- Existing C6 worked stop values in `_coverage/notes/C6-INTEGRATE/examples.json` and their offline composition script; these were read, not run or changed.

## Claims that need qualification

1. Identical literal schemas across all consumer APIs are not guaranteed. Role output names, extra fields, parent/path names, related field names and optional parts are declared. Only the object type discriminator is fixed by the object composer. Within a definition, every type does use that definition's shared shape.
2. Every API does not offer every operation: Get by ID, XREF, Resolve, lists and events can be omitted. The router refuses undeclared operations. Crosswalk needs a targetable related filter and business-date reads depend on declared validity periods.
3. No-new-code client adoption is conditional on a client driven by the declared contract. A client tied to particular fields or operations may need changes. The code does not guarantee every consumer can adopt every declaration unchanged.
4. Collection envelopes are common across declarations for the same operation, but lists, XREF, Resolve and events have different envelopes. Webhooks support RDM JSON and CloudEvents, with single/batched variants.
5. Contract stability is separately versioned. Breaking changes require a raised version; the current workspace does not retain a parallel old live endpoint automatically.

These are documented as current behavior, without proposing product changes.

## Validation

`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend backend/.venv/bin/python guide/_coverage/notes/C6b-CONSUMER-CONCEPT/compose_operator.py` composed the reference operator through the production renderer with no database or HTTP calls; output is `operator.json`. The stop body reuses the existing reference-data composition evidence. These are worked examples, not live API captures.

In `guide/`, `GUIDE_OUT=_build/C6b-CONSUMER-CONCEPT npm run verify` built 222 pages successfully and passed terms/brand checks. Link checking failed with 28 missing targets, all outside the four assigned pages: 27 screenshot references and the home page's `/docs/journeys/` target. Full details are in `verify.log`. None of the link failures names an assigned page. No out-of-scope files were changed to repair them. The build also emitted its duplicate `/404` route warning.

No steering file existed at the start of any unit. No server or database was started. No commits or git state-changing commands were run.
