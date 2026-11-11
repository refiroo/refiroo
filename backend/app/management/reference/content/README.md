# Writing the reference

This folder is the text of the management API reference (`/docs/api`). `content.py` merges it into the
OpenAPI document; this file is not merged. Read it before writing an area.

**The reader** is an integrator who has to get something done. Say what they are doing and which facts
they must act on. A fact that does not change what the client sends or expects is left out. Every
statement is checked against the code path; where the code and `docs/API.md` differ, document the code
and log the difference in `docs/TODO.md`. No package or decision IDs, no history, no "new in".

**One fact lives in one place.** The place is the one a reader looks in when they need it.

| Where | What it holds | Size |
| --- | --- | --- |
| Area overview (the text under `# tag`) | What the thing is in the integrator's terms; why and when they touch this area; the one or two sequences that matter, as a numbered list naming operations. No limits, enum values or version mechanics. One sentence on a concept only if this area's operations depend on it. | At most about 120 words |
| `## Schemas` | The detail of an object: a line of plain text for the schema itself, then one `- field: text` line per field, which becomes that property's description. Formats and limits, values and what each means, derived flags. | One short line each |
| Operation section | What it does and when to use it, in the first sentence. Then at most three short sentences or bullets the client must act on: what it changes beyond the obvious, what it does not do and what to use instead, a precondition that is easy to miss. Never repeat a field's meaning or list the response's fields. | 30 to 70 words |
| `### Parameters` | A line for a parameter only where the code gives it no description or a misleading one. | One line each |
| `### Errors` | `- STATUS CODE: when`, at most about ten words. The catalogue explains the code. | One line each |
| `errors.md` | Per code: what it means, why it usually happens, what the client does. The status is a badge. | A few sentences |
| `index.md`, `### Fields of every page` | The navigation fields every page schema has, once. | One line each |
| `index.md` | Conventions every operation shares: signing in, the error envelope, what every operation can answer. | Short |

An operation with several tags is written in the file of its first tag. The operations that carry no tag are written in `untagged.md` (`# untagged`, no overview). A schema section may name several schemas, separated by commas. A line of plain text under a schema's heading is the schema's own description and replaces the one in the code, which may not name packages or decisions. A field not listed keeps the code's description; `tests/test_reference_complete.py` fails on a field with none, on an operation without a section or example, on a code without an entry and on any description that carries a package, decision or release number.

**Examples are recorded, never written by hand** (`tests/test_reference_*.py`), and never hold a real secret: the normaliser replaces passwords, client secrets, tokens, reset links, authenticator seeds and recovery codes by fixed placeholders (`SECRET_MASKS` in `tests/test_reference_recording.py`, and a call's `mask` for a key that is secret only in its answer).

An operation section may start with `Title: <plain name>` (the sidebar name instead of FastAPI's).
The in-code description of an operation or parameter is replaced where a section or note exists.

## Example

````markdown
## DELETE /api/v1/workspaces/{workspace_key}

Title: Delete a workspace

Deletes a workspace so a mistyped key can be corrected. Only a workspace that is not the default, was
never published and holds nothing can be deleted; otherwise retire it.

### Parameters

- expectedVersion: The workspace's `version`.

### Errors

- 409 WORKSPACE_NOT_EMPTY: it has records or change sets
````

The first sentence says what it does. The second is the precondition that is easy to miss, with the
operation to use instead. The reader finds what `version` is under `## Schemas`, and what the 409
means in the catalogue.
