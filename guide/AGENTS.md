# Writing the refiroo documentation

You write the refiroo documentation: what people read at `/docs` to understand, use, run and integrate
refiroo. Write it the way good product documentation is written for people, not as a specification and
not as a test report.

## Documentation pages and guides

The documentation is made of two kinds of page, for every capability and every reader:

- **A documentation page** explains a capability: what it is, what it is for, how it works, its rules,
  states and limits, and who may do what (roles and permissions). Example: "Change sets". Documentation
  pages live in `src/content/docs/<section>/` and are served at `/docs/<section>/…`.
- **Guides** take the reader through one task step by step. Example: "Prepare and publish a change set".
  Guides live in `src/content/docs/guide/<section>/` and are served at `/docs/guide/<section>/…`. A guide
  links to its documentation page for the ideas, and the documentation page links to its guides for the
  tasks; neither repeats the other.

## Capabilities, not applications

Document what refiroo itself does: workspaces and applications, records, relationships, hierarchies,
mapping grids, relation matrices, change sets and so on. Applications (such as RDM Master, RDM Systems and
RDM Translations, or Network, Systems and Names in the example data) are defined by a model; they are
examples of those capabilities, never product features of their own. Translation, for instance, is not a
refiroo capability: it is an application built from records, a relationship that owns the translations and
relation matrices. Applications are described only in the "Example applications" section (`examples`),
which says what each one shows and links to the capabilities it uses. The starter model is an option
shipped with refiroo, not part of it: a model may rename, reshape, replace or remove its applications.

## Who reads it, and what each reader needs

| Section (folder) | Reader | What they come for | How their pages look |
| --- | --- | --- | --- |
| About refiroo (`about`) | Evaluators, decision makers, anyone new | What refiroo is, what it is for and not for, the ideas behind it, how it is built and secured | Short explanations in plain words. Pictures where they help. |
| Use refiroo (`use`) | Data stewards: people who look after reference data in the browser | Their daily work, by capability: workspaces and applications, records, relationships, hierarchies, mapping grids, relation matrices, change sets, loading a workbook, history | Task by task, screen by screen: numbered steps naming the buttons and fields as the screen shows them, with screenshots. |
| Example applications (`examples`) | Anyone who wants to see refiroo applied | The starter model shipped with refiroo (RDM Master, RDM Systems, RDM Translations) and the example data used in this documentation (Network, Systems, Names): what each application shows and which capabilities it uses | Short showcase pages that link to the capabilities' documentation pages and guides. |
| Model your data (`model`) | Model administrators | Shaping what the applications hold: types, fields, relationships, views, releases, workspaces, in the model editor | Same as Use: screens and steps, with the concepts each step needs. |
| Administer access (`administer`) | Administrators of people and access | People, groups, roles and grants, sign-in and second factors, clients for other systems, approvals, who changed what | Same: screens and steps under Settings. |
| Run refiroo (`run`) | Operators | Install, configure, secure with HTTPS, set up sign-in and mail, upgrade, back up and restore, monitor, troubleshoot, a production checklist | Steps with the commands to type, the settings that matter and what each changes. |
| Integrate (`integrate`) | Developers and integrators of other systems | How to work with the API: signing in and tokens, paging, versions and conflicts, loading data, following changes, consumer APIs, webhooks | Concepts and sequences ("load, then follow changes"). Short excerpts only where a sequence needs one. Every operation links to the API reference at `/docs/api`; never repeat what `/docs/api` describes. Consumer APIs are explained in full, with examples (rule 3). |

## Rules

1. **Write for the reader's task.** Each page has one reader and one purpose. Start with what the reader
   wants to do, then how. Explain a concept where the reader needs it, not before.
2. **People who use the browser never see JSON, API paths, tokens or internal names** (About, Use, Model,
   Administer). They see screens, buttons and words as the application shows them.
3. **Integrators get the API's ideas and sequences, `/docs/api` gets the details.** Link to the operation in
   `/docs/api` instead of describing its fields. **Consumer APIs are the exception:** each organisation
   declares its own in its model, so `/docs/api` cannot describe them for the reader. Explain them in the
   documentation itself: how a declaration becomes paths, parameters and responses, with full request and
   response examples (and event and webhook payloads) from the reference data's `stops` consumer API.
4. **Only what exists.** Describe what refiroo does today. Take facts from the application itself:
   the screens in `frontend/src/` (labels exactly as shown), the documents in `docs/` (start with
   `docs/product-functionality/USER_JOURNEYS.md`, `CURRENT_FUNCTIONALITY.md`, `GLOSSARY.md`, `PRODUCT.md`,
   `docs/OPERATIONS.md`), and the code when they disagree (the code wins). No planned features, no "will".
   If you are unsure whether something works as you would write it, say so in your final report instead of
   guessing.
5. **One example world.** Examples use the guide's reference data: the public transport stops of
   Graubünden, Switzerland (`samples/README.md`, `samples/SOURCES.md`): stops, municipalities, operators,
   names in five languages, codes from other systems. Never another organisation's data, never a private
   model. The domain is the example, never the definition. Text and steps are generic: "open an
   application in the current workspace", never "open Network in the Graubünden workspace". The example
   goes in the caption under a screenshot ("Above: the Network application in the Graubünden workspace,
   showing the stops of the canton") or in a clearly marked example after the general text.
6. **Name the concrete things.** Where refiroo uses a named technology, standard, protocol, format or provider,
   name it where the reader meets it, with its version where refiroo fixes one: Let's Encrypt for automatic
   HTTPS, PostgreSQL, OpenID Connect, WebAuthn passkeys, xlsx and CSV, Prometheus metrics, and so on. Take
   each name from the files; never name something refiroo does not use. A reader searches for these names.
7. **Detailed.** Each step says what to do, what the reader then sees, what the options on the screen
   mean, and what can go wrong and what to do about it. Each documentation page covers the rules, states
   and limits the reader meets.
8. **Screenshots.** Where a page needs one, insert `![What the screen shows](/docs/screens/<name>.png)` and
   list each screenshot in your final report with the screen, the state and what must be visible. They are
   taken afterwards from the reference instance.
9. **Screenshots attached to an assignment** show the real screens of the reference instance: what they show
   is how refiroo looks. The files in `guide/public/screens/` are the ones to reference on the pages; list
   any other screen you still need.
10. **Plain language.** Short sentences, everyday words, the glossary's terms, one term per idea. Write
   "refiroo" in lower case; the site marks the name automatically, so write it as plain text, never with
   bold, code, links or images for the name itself. No package or decision numbers, no delivery history.
11. **Pages are Markdown** (`.md` or `.mdx`) under `src/content/docs/<section folder>/`, with front matter
   `title`, `description` and `reader` (one of: evaluator, steward, model-admin, access-admin, operator,
   integrator).
12. **Stay in your files.** Edit only the files your assignment lists. Do not change code, tests or other
   pages. Do not commit. If you find something in refiroo that looks wrong, put it in your final report.

## Before you stop

Run `npm run build` in `guide/`; it must pass. End with a short report: the pages written, the screenshots
needed, anything you were unsure of, and anything in refiroo that looked wrong.
