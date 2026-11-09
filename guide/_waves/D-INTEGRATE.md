# D-INTEGRATE: "Integrate" documented in full

Read `guide/AGENTS.md`, `_waves/COMPLETE-COMMON.md` and `_waves/DEPTH-COMMON.md`, in that order. Reader: integrators, who connect other systems to refiroo through the management API, the consumer API, webhooks, MCP and agents.

Your scope: the entries of section `integrate` in `_coverage/inventory/*.json` (those still in `_coverage/inventory/uncovered.md`
first), then every page of the section and its guides, each held against the depth questions of `DEPTH-COMMON.md`.

The management API's operations are listed in the API reference at `/docs/api` (generated from the code); your pages explain the concepts, sequences and rules and link there, they do not repeat each operation. The consumer API's operations (`_coverage/inventory/consumer-api.json`, from `consumer/router.py` and the reference model's contract) and every MCP tool (`management/mcp_tools.py`) are each named and explained.

## Files you may edit

- `src/content/docs/integrate/**`
- `src/content/docs/guide/integrate/**`
- `sidebar/integrate.mjs`
- `_waves/coverage/integrate.md`
- `_coverage/exclusions.md` (only lines for section `integrate`)
- `_waves/screens-wanted/D-INTEGRATE.md`
- `_coverage/notes/D-INTEGRATE/**` (working notes)

## Report

As `DEPTH-COMMON.md` says.
