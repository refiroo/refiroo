# Base 0.15 implementation plan

**Status:** Planned 2026-10-26 at the user's request. D418–D430 are all decided by the user (2026-10-26). Planned before 1.0
for now, like 0.14; nothing in it blocks another release.

**Target:** Product 0.15.0, [interface language](ROADMAP.md#product-release-015--interface-language).

**Depends on:** nothing that is not built. The areas the security release (0.12) and the documentation
and API reference release (0.13, 0.14) are still changing are converted last (see
[Order](#order-and-the-shared-working-tree)).

## Why

refiroo's browser interface is English only: all text is written into about 224 component files
(and a few `.ts` files such as `features/home/homeText.ts`), there is no translation library, and the
backend's error messages reach the screen as English text (`errorMessage()` returns `cause.message`,
used in 76 files). An organisation whose people work in German cannot use the interface in their
language, although the engine already stores and serves translated reference data.

**What this release is not.** It is not the translation of reference data (the engine already does that)
and not the translation of a model's own names and labels: a German organisation builds a German model
with German keys and labels (D418). It is not a change to the backend.

## Outcome

A person chooses a language in Settings › Appearance, and the whole browser interface reads in it: menus,
buttons, forms, dialogs, empty states, validation messages and the engine's error messages for the codes
the interface can meet. Dates and numbers follow the language. English and German ship; a third language is
a catalogue of translations, not a code change. New interface text cannot be added as a literal: the build
refuses it.

## Packages

| Package | Needs | Scope in one line | Model |
| --- | --- | --- | --- |
| [LG1](#lg1-the-foundation) | — | Library, catalogues, the language setting, formatting, the guards, the conventions in AGENTS.md; the shell converted as the pattern | Primary agent (strong model) |
| [LG2](#lg2-the-engines-errors-in-the-interface-language) | LG1 | Backend error codes mapped to translated texts; validation messages; the fallback | Primary agent; table drafts by Haiku |
| [LG3–LG6](#lg3lg6-converting-the-areas) | LG1 | The interface converted area by area, English catalogue then German | **Haiku** for the conversion and the German draft; primary agent for the rest |
| [LG7](#lg7-german-reviewed) | LG3–LG6 | The German catalogue reviewed for terms and fit | Primary agent; a German reader (D429) |
| [R](#r-build-acceptance-and-release) | all | Full review of every change since 0.14, the gates in both languages, the release | Primary agent |

## Decisions

| # | Question | Decision |
| --- | --- | --- |
| D418 | What is translated? | **Decided by the user 2026-10-26: the browser interface only.** Everything the frontend writes is translated. The backend, the API, the model's names and labels (a German organisation builds a German model), and the pages the engine itself serves (the API reference, the sign-in page it renders for outside applications) stay as they are. Cost: a German screen can show a model's English label, if the model has one |
| D419 | Backend errors on screen | **Decided by the user 2026-10-26: shown in the interface language where the interface can.** The browser holds a table from an error `code` to a translated text. A code without an entry shows the backend's message, which is English. The backend sends the same body as today. Why a table in the browser and not translated messages from the backend: the backend stays unchanged (D418), and the code is the stable part of an error. Cost: 286 codes are raised in the backend (counted 2026-10-26 from the literal `api_error(...)` calls, so at least that many); the table covers the ones a screen can actually meet and grows code by code |
| D420 | Messages with values in them | **Decided by the user 2026-10-26: accepted.** A translated text can only use values the error carries in `details`. A code whose backend message embeds a value that is not in `details` keeps showing the backend's English message. Nothing in the backend changes to avoid this. Cost: a few English sentences on an otherwise German screen |
| D421 | Validation errors (`REQUEST_VALIDATION_ERROR`) | **Decided by the user 2026-10-26.** The body carries FastAPI's raw list of problems (`type`, `loc`, `msg`). The interface maps the common types (a value is required, too short, too long, the wrong type, not one of the allowed values, a number out of range, the wrong format) to translated field messages, and shows the engine's text for a type it does not know. Why: this is the error people meet most, on every form |
| D422 | Library | **Decided by the user 2026-10-26: i18next with react-i18next**, keys typed from the English catalogue. Basis: key-based catalogues give each translation a stable name, which fits the error table (keyed by code), the parallel work by area (D425) and a catalogue test; plurals and interpolation are built in. Checked: the repository has no i18n library today and the frontend is React 19. **Not checked:** the bundle size and how it works with `react-aria-components`; LG1 measures the first once and reports. The alternative is react-intl (ICU messages); it fits less well with the area-by-area catalogues. react-aria-components carries its own translated strings for its widgets (date fields, calendars); LG1 gives them the chosen language through react-aria's locale provider (to be confirmed in LG1) |
| D423 | Catalogues | **Decided by the user 2026-10-26:** one JSON file per area and language, `frontend/src/i18n/locales/<language>/<area>.json`, the area being a namespace (`app`, `ui`, `objects`, `model-editor`, `settings`, …). English is the source: its files define the keys, and TypeScript derives the key type from them, so a misspelled or missing key fails `tsc`. Keys name the place and purpose (`objects.list.emptyTitle`), never the English text. A language loads on demand, so English readers download no German. Why one file per area: each area has one owner at a time (D425), and a catalogue cannot collide across areas |
| D424 | Where is the language chosen | **Decided by the user 2026-10-26** (the per-browser form, which differs from the first wording, a per-user setting that the backend would store): Settings › Appearance, saved in the browser like theme and density; the default is the browser's language when it is a shipped language, English otherwise.** It also sets `<html lang>`, the locale for dates, numbers and sorting, and the widgets' locale. Why not the account: the choice is stored by the backend, which D418 leaves unchanged; the Appearance page already states that its choices are per browser. Cost: a person who works on two devices sets it twice. Later, if wanted, an account preference can be added without changing the catalogues |
| D425 | Which languages | **English and German** (the user's example, 2026-10-26). German is drafted by Haiku (D427) and reviewed (LG7, D429). English stays the language the browser runners, the documentation and the screenshots use |
| D426 | The guards | **Decided by the user 2026-10-26, each over the whole set:** (1) **A lint rule** that fails a literal in JSX text and in the attributes people read (`aria-label`, `title`, `placeholder`, `alt`, and the text props of the UI components), over all of `src` but tests. It starts with a committed list of files not yet converted that may only shrink (the pattern of V-D6), so the rule is on from LG1 and every new file is held to it. (2) **A catalogue test:** every German key exists in English and the reverse, and each key's placeholders (`{{count}}`) match across languages. (3) **The English-identical check** (below). A fourth, the **pseudo-language**, is a development setting generated from the English catalogue (accented, about 40% longer, bracketed) that lets a screen's layout be checked without knowing German |
| D427 | Which model does which work | **Decided by the user 2026-10-26: the low-cost model, Haiku (`claude-haiku-5-5`), does the repetitive work, and this plan names which, so the delivery uses it.** Haiku: converting the files of an area into catalogue keys (LG3–LG6), drafting the German catalogue for an area, drafting the code-to-text table entries (LG2). The primary agent (strong model): the foundation and conventions (LG1), the error and validation mapping logic (LG2), the strings the table below marks as tricky, the checks, and the review of every Haiku batch. Why: the conversion is the largest part of the work, it is mechanical once the pattern is fixed, and the guards (D426) catch what a cheaper model gets wrong; what it cannot be trusted with is the design. Cost: each batch is a billed multi-agent run, announced and approved one at a time (release-run discipline) |
| D428 | The rule for agents writing in parallel | **Decided by the user 2026-10-26; the approval is the explicit request AGENTS.md's agent-orchestration section asks for.** AGENTS.md allows one writing agent per package; this release makes one exception, only for the Haiku conversion batches: each Haiku agent owns a fixed list of component files and that area's catalogue file, no two lists overlap, and the primary agent writes nothing while a batch runs. Agents do not commit and preserve other changes in the shared working tree. LG1 writes the exception, the model allocation and the conversion conventions into AGENTS.md ("Interface text") |
| D429 | Who reviews the German | **Decided by the user 2026-10-26: other language models, not a person.** Nobody is paid to read it. After LG6 the German catalogue (with the English beside it and the glossary) goes to at least two models that are not Claude, each asked for corrections key by key: wrong or unnatural wording, a term used differently from the glossary, a lost or changed placeholder. The primary agent applies the corrections the models agree on and lists the disagreements for the user. Why other models and not Claude: Claude drafted it through Haiku, and a second reader from another model family has different blind spots. Limit, stated in the release notes: this finds mistakes of grammar and terminology, but it is not a native speaker's judgement of tone. Cost: the user names the models and supplies access (the primary agent cannot reach them from this session) |
| D430 | Shipping the German | **Decided by the user 2026-10-26: German ships after the review by other models (D429).** The release notes call it a machine translation reviewed by machine. The catalogue is complete at release (the catalogue test) |

## Order and the shared working tree

The areas are converted in this order, the ones least likely to change first: shell and shared
components (LG1, LG3), the record screens (LG4), the model editor and administration (LG5), then
security, sign-in, workspaces, jobs and moves (LG6). Security and sign-in are still being built in 0.12 as
this is written; converting them earlier would be rework. The rule from LG1 on (AGENTS.md): **any new
interface text goes through the translation function from the start**, so work in other releases does not
add literals, because the lint rule refuses them.

Other sessions edit the same checkout. Each Haiku batch works on files that no other session has
uncommitted changes in (checked with `git status` before the batch; a file with someone else's changes is
left for later), and the batch's diff is reviewed as its own hunks.

## LG1: The foundation

**Needs:** —. **Model:** primary agent.

**Scope.**

- The library (D422) and `frontend/src/i18n/`: setup, the typed keys, loading a language on demand, the
  fallback to English for a missing key.
- The language setting (D424): the preference, `<html lang>`, the widgets' locale, and the control in
  Settings › Appearance (mock-up below).
- One formatting helper for dates, times, numbers and sorting, used by `lib/dates.ts` and the other
  `Intl`/`toLocale*` call sites (44 counted 2026-10-25), taking the chosen language.
- The shell converted as the pattern every later batch copies: the top bar, the settings menu, the sidebar
  chrome, the sign-in page, the shared `ui` components used there. It includes a plural, an
  interpolation, a text with a link in it and an `aria-label`, so the conventions have a worked example
  of each tricky case.
- The guards (D426): the lint rule and its list, the catalogue test, the pseudo-language generator and the
  English-identical check.
- The journey catalogue (`USER_JOURNEYS.md`) extended with the language journeys below.
- AGENTS.md "Interface text": the conventions (key names, plurals, interpolation, no sentence built by
  joining pieces, text with markup, what is not translated), D427's model allocation and D428's
  exception; the glossary for German (D429).
- Measured once: the bundle size added, and what a language switch does to a page that is open.

**The English-identical check.** A script, run on every converted file, replaces each translation call
by the English text from the catalogue and compares the result with the file as it was before the
conversion, ignoring formatting. Equal means the conversion changed text and nothing else: no logic, no
markup, no attribute. It runs over every converted file, not a sample, and is how the primary agent
verifies a Haiku batch without reading every line. Where a conversion has to change code (a sentence
built from pieces becomes one message with placeholders), the check reports it and the primary agent
reads that file. Cost: the script, and JSX whitespace rules, which LG1 works out on sample files.

**The tricky strings** (the primary agent converts these, not Haiku, in every batch): text built from
pieces; plurals; text that includes a link, bold or an icon; text passed through props or computed in
`.ts` helpers; texts compared against elsewhere (a status shown and also tested); anything a `switch`
returns; text in `homeText.ts`-style files. A Haiku agent is told to leave such a string unconverted and
list it with its file and line.

**Mock-up (Settings › Appearance).**

```text
General › Appearance
These choices are saved in this browser. Other browsers and devices keep their own.

Display
  Theme            (•) System   ( ) Light   ( ) Dark
  Language         [ English            v ]      <- new
                   The language of the interface. Model names and labels are shown as the model defines them.
  Table density    (•) Comfortable   ( ) Compact
  ...
```

The control is a select with each language written in its own language ("English", "Deutsch"). After a
change the page is in the new language at once, without a reload. A browser whose language is not shipped
starts in English. 390px: the same control in the same place, stacked like the others.

**Tests.** The catalogue test; a unit test of the language preference (default from the browser, stored,
blocked storage); the formatting helper in two languages; the English-identical check run on the shell;
one browser journey (below). The existing Vitest files and browser runners that read English text stay
green unchanged, which is itself the check that English is untouched.

**Still manual after LG1:** nearly everything outside the shell is English. The language control exists and
switches the shell only.

## LG2: The engine's errors in the interface language

**Needs:** LG1. **Model:** primary agent for the mechanism and the validation mapping; **Haiku** for the
table entries.

**Scope.**

- `errorMessage()` and the places that show an `ApiError` look up the code in the table (D419) and fall
  back to the backend's message. The text may use `details` values (D420).
- The validation mapping (D421): the common problem types to translated field messages, shown where the
  forms show field errors today.
- A script lists every code the backend raises with the message at its raise site and the `details` keys
  it passes, so the table is written from the code and not from memory. Haiku drafts, per code, the
  English text and the German text for the codes a screen can meet, taking the backend message as the
  source and leaving a code out when its message embeds a value that is not in `details` (D420).
- The check: every code in the table is a code the backend raises; every placeholder a text uses is a
  key the code's `details` carries; both languages have every entry. A code in the table that the
  backend no longer raises fails the test.
- The 13 places that branch on a code today are untouched; they already read the code.

**Tests.** The table's check (above); a unit test of the fallback and the interpolation; the
validation mapping for each problem type in both languages; one browser journey (below).

**Still manual after LG2:** codes the table does not cover show the backend's English; the README of the
table says how to add one.

## LG3–LG6: Converting the areas

**Needs:** LG1 (LG2 for the errors). **Model:** **Haiku** for the conversion and the German draft; the
primary agent for the tricky strings, the checks and the review of each batch.

| Package | Area (non-test component files, counted 2026-10-26) | Why this place in the order |
| --- | --- | --- |
| LG3 | `ui` (69) and `app` (9), the shared pieces, minus what LG1 did | Everything else uses them; a shared label converted once |
| LG4 | `features/objects` (43), `changes` (1), `home` (1) | The screens used daily |
| LG5 | `features/model-editor` (33), `model-admin` (10), `settings` (16) | The authoring and administration surfaces |
| LG6 | `features/security` (13), `workspaces` (10), `jobs` (8), `moves` (8), `administration` (1), `sign-in` (1) | Converted last because 0.12 is still changing them |

Counts are of `.tsx` files; strings in `.ts` helpers in the same folders belong to the same batch.

**How a batch runs** (D427, D428):

1. The primary agent prepares the batch: the list of files, each file's catalogue namespace, a check that
   no other session has uncommitted changes in them, and the instructions (a reference to AGENTS.md
   "Interface text" and to LG1's converted shell as the worked example; no copy of the plan).
2. The user gives the go-ahead for the run (each heavy run on its own).
3. **Haiku agents**, each owning a disjoint list of files and one catalogue file, convert the files:
   literals in JSX and in the listed attributes become keys; the English catalogue gets the text; the file
   is otherwise untouched. A tricky string is left as it is and listed. Then a second Haiku pass per area
   drafts the German catalogue from the finished English one and the glossary, keeping every placeholder.
4. The primary agent checks the whole batch: `tsc` and the build, the lint rule, the catalogue test, the
   English-identical check on every file, the Vitest files of the area, and the pseudo-language on the
   area's main screens at 1440px and 390px for overflow. It converts the tricky strings, reads every file
   the identical check flagged, and shrinks the lint list by the converted files.
5. One browser look per area in German at 1440px and 390px, light and dark (what the screenshots show is
   reported, with what was not looked at).

**Tests.** Only the guards above and the area's own Vitest files, plus the browser look; no new
per-screen test programme (the existing runners cover English). The tests added in LG3–LG6 are well under
a quarter of the work.

**Still manual after each batch:** the areas not yet converted read English; the tricky strings of the
batch wait for the primary agent's pass, so the batch is not finished until the lint list for its area is
empty.

## LG7: German reviewed

**Needs:** LG3–LG6. **Model:** primary agent applies; the reviewers are other models (D429).

The primary agent prepares one file per reviewer: each key with its English text, its German text, the
placeholders and the glossary, and a fixed instruction asking for a correction per key or "ok". The user
runs it with the models of their choice and returns the answers (D429). The primary agent applies the
corrections that at least two reviewers agree on, keeps every placeholder (the catalogue test checks it),
records the terms in the glossary, and lists the disagreements for the user to decide. Layout problems the
German text causes (longer words, buttons that wrap, a truncated top bar) are fixed here or reported.

## R: Build acceptance and release

The same discipline as earlier releases: a full review of every change since 0.14, announced heavy runs one
at a time, a stop on any failure or odd figure.

- The full backend suite (the release touches no backend code, so the run confirms it) and Vitest.
- The browser runners, in English, unchanged; the lint list is empty.
- The accessibility and visual gates in English, and the visual gate repeated in German at 1440px and
  390px, light and dark, with baselines for German added.
- The catalogue test, the identical check over the whole `src`, and a search for any literal the lint rule
  does not cover (text built in `.ts` files, text in `public/` and `index.html`).
- Journeys through the interface in German: sign in, open a list, edit a record, an error shown from the
  table, a validation message, a date and a number.
- The release notes: what is translated, what is not (D418, D420), that the German is machine-translated and machine-reviewed (D429, D430).

## Journey test cases

The journeys are scenario-driven through the browser, two of them in the release's browser runner
`language`:

1. Given a browser whose language is German, when a person opens refiroo for the first time, then the
   interface is German, `<html lang>` is `de`, and a date in a list reads in the German format.
2. Given the interface in English, when the person chooses Deutsch in Settings › Appearance, then the page
   changes at once, without a reload, and a reload keeps German.
3. Given German, when a save is refused with `VERSION_CONFLICT`, then the message is the German text of
   the table; when it is refused with a code the table lacks, then the backend's English message shows.
4. Given German, when a form is submitted with a required field empty, then the field shows the German
   validation message.
5. Given the pseudo-language, when the main screens of each area open at 390px, then nothing overflows
   its container.

Unit: the catalogue test, the preference, the formatting helper, the error table's checks.

## Not included

- Translating anything the backend sends other than through the table (D418, D419).
- A model's names and labels, and the engine-served pages (D418).
- A third language, right-to-left scripts and a language setting stored on the account (D424).
- Translating the documentation and the screenshots; they stay English.

**Composable domains (ADR-032):** no door is affected. The release changes how the browser writes text and
leaves every contract as it is.
