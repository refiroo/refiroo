# LB guide: Find a list in the sidebar, and a table's inactive records

Read `guide/AGENTS.md`. Readers: the guide's readers, as each page names.

## Why

Two additions to the product (CHANGELOG, Unreleased, "Added (list browsing: Find a list and a table's inactive records, 0.13 LB)").
The code wins: `frontend/src/features/objects/Explorer.tsx` (`Find a list`, `FIND_LIST_AFTER`), `frontend/src/model/collections.ts`
(`narrowNavigation`), `frontend/src/ui/ObjectTable.tsx` (the Inactive pill), `frontend/src/features/objects/ObjectToolbar.tsx`
(`HideInactive`), `frontend/src/model/fields.ts` (`unavailableWord`), `frontend/src/features/model-editor/layout.ts`
(`tableAvailabilitySpec`), `docs/APPLICATION_MODEL.md` ("Table view", Inactive records), `docs/product-functionality/CURRENT_FUNCTIONALITY.md`.

## What the product does now (check each point in the code)

- **Find a list.** When an application has more than ten entries in the sidebar's Collections (collections and
  relation matrices placed in groups, counted together), a search box labelled **Find a list** sits under the
  **Collections** heading, with a count at the right of the heading ("25 lists" while empty, "3 of 25" while
  typing; read out politely). Typing shows only the entries whose name contains the words, in every group and among
  the entries in no group, ignoring case, with the matching letters in bold. A group with a match is open and shows
  only its matches; a group with none is hidden. **Enter** opens the first match; **Esc** clears the box. While
  a search stands the group fold buttons are not shown, and clearing the box returns each group to the fold the reader
  chose. A hint under the box says "Enter opens the first match · Esc clears", or "No list matches". **Find a record**
  under Browse records is unchanged. An application with ten entries or fewer has no Find a list box.
- **Inactive records.** A table view may name a yes/no attribute as its availability field (the model editor
  calls the setting **Inactive records…**, under a table's settings, next to **Filters…** and **Sort menu and
  page size…**; it offers None and the type's yes/no attributes). Where it is set, a row whose value is No keeps its
  place, its name in a quieter colour with a grey **Inactive** pill after it (the pill reads "Not <attribute name in lower
  case>" when the attribute is not called Active). The toolbar beside Filter gains a switch, **Hide inactive (N)** (or
  "Hide not <name> (N)"), N being how many records of this list, with its search and other filters, have the field
  at No. Turning it on adds an ordinary filter pill ("Active: Yes") that stays in the page address and can be removed
  like any filter; turning it off removes it. The default is to show them. Editing is unchanged: the value is changed
  in its cell or on the record. The same applies in a change set and a publication. A table without the setting looks
  as before.

## What to do

- Fix each passage that no longer matches, and add what is missing, in the page that already owns the topic. Keep each
  page's voice and structure. Candidates: `use/applications.md` (the sidebar: Find a list, with the existing text on
  groups), `use/lists-and-filters.md` (the Hide inactive switch and the Inactive mark), `guide/use/find-records.md` if it
  describes finding a collection or a list, `model/record-pages-and-tables.md` and
  `guide/model/choose-table-columns-filters-and-sort.md` (the new **Inactive records…** setting: what it does, what it
  offers, what it refuses: a field that is not a yes/no attribute of the type). Keep the model pages' reader away from
  JSON and key names (rule 2).
- No new pages. Pictures: list in the report (name, page, screen, what must show) any picture that no longer matches or
  that the change calls for; do not invent files. A reference instance with more than ten lists and a table with the
  setting does not exist yet.
- A point the guide cannot describe honestly: list it in the report with the evidence.

## Files you may edit

- `src/content/docs/use/applications.md`
- `src/content/docs/use/lists-and-filters.md`
- `src/content/docs/guide/use/find-records.md`
- `src/content/docs/model/record-pages-and-tables.md`
- `src/content/docs/guide/model/choose-table-columns-filters-and-sort.md`
- `_waves/progress/LB-GUIDE.md`

## Report

Per page: what changed and why (one line each), the passages you checked and left as they are, the pictures that no
longer match or are needed, and any product point the guide cannot describe honestly.
