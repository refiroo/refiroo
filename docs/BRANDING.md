# Branding

## The name

**refiroo** is the name of the application. It is written in lower case, always, including at the
start of a sentence.

refiroo is an RDM (reference data management) engine, and it has an engine inside it. So "the RDM
engine" and "the engine" remain the right words for the part that runs models, serves the API and
keeps the data, wherever a technical text is clearer for using them: `rdm-engine` is the Python
distribution and the directories (the repository is `refiroo/refiroo`, 0.12 L1), and "the engine" is the layer in [ARCHITECTURE.md](ARCHITECTURE.md). The
rule is the one between a product and its parts:

| Say | When |
| --- | --- |
| refiroo | the application as a whole: what a person opens, signs in to, reads about or asks for |
| the engine, the RDM engine | the runtime inside it, in technical text: layers, packages, processes, contracts |
| `rdm-engine` | directories, the package and anything already named so in code |

Nothing is renamed by search and replace. Package names, the `RDM_*` settings, the `rdm:` storage keys
and history in the changelog and in old plans keep what they say; they are technical names, and
pre-1.0 nothing is kept for compatibility, so they can follow later if one is worth it.

A model's `product.name` is still the model's own (the instance's name, 0.12 D338): the interface shows the
refiroo mark and, beside it, a model's own name when it is not one of the defaults (`refiroo`, `RDM
Engine`).

## The logo

The originals are in [`logos/`](../logos). The interface and the engine's own pages keep their own
resized copies, so each can change without the others.

| File in `logos/` | What it is | Used for |
| --- | --- | --- |
| `refiroo-mascot.png` | the kangaroo alone, transparent | the mark in the top bar, loading and empty screens, Home, the favicon |
| `refiroo-wordmark.png` | "refiroo" in navy, transparent | the name beside the mark (drawn light on a dark surface) |
| `refiroo-lockup.png` | mascot and wordmark side by side, transparent | documents and slides on a light background |
| `refiroo-stacked.png` | mascot above the wordmark, transparent | square placements on a light background |
| `refiroo-app-icon.png` | the mascot on a cream square, no transparency | the touch icon and any place that needs a filled square |

Copies, resized:

- `frontend/public/brand/` — the interface: the top bar (`ui/ProductMark.tsx`), `index.html` (title,
  favicon, touch icon), the loading, no-workspace and Home screens and Settings › About.
- `guide/public/` — the guide's favicon and mark (`favicon.png`, `refiroo-mascot.png`, 0.13 DOC1).
- `backend/app/management/brand/` — served at `/brand/<file>` for the pages the engine renders
  itself: the sign-in and password pages and the API reference at `/docs` (the title, the favicon
  and a header with the mark). Only the files listed in `management/brand_assets.py` are served.

The wordmark is dark ink on a transparent ground; on a dark surface it is drawn light with a CSS
filter, so the mascot (whose colours work on both) is never filtered.

The colours the logo uses (periwinkle, mint and navy) are not yet the interface's colours; the
palettes in `tokens.css` are unchanged.
