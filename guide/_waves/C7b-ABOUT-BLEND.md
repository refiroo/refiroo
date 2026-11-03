# C7b: blend "what refiroo is" into About

Read `guide/AGENTS.md` and `_waves/COMPLETE-COMMON.md`. Reader: evaluators, decision makers, anyone new.

The person who owns refiroo wants the account below blended into the existing About pages: not a new page,
not a second copy, but the current pages made to tell it. Keep what is right in them; keep them short and
plain. Source: `docs/PRODUCT.md` ("Product overview", "What makes it different", "Who it is for") and the
existing About pages; check each claim there or in the code.

**`about/what-is-refiroo.md`** becomes the page that tells it whole:
1. What it is: an engine for reference data (the fairly stable lists other systems depend on: codes,
   categories, names and the connections between them). A team defines its own reference-data applications
   with a model, without building software for each; refiroo supplies the screens, the API, validation,
   history, search, access control, approvals and publication.
2. The problem it solves, told as a story in the guide's example world: the same thing is known by
   different codes and names in different systems (a stop with its own number, its SLOID, a ticketing
   system's code, names in five languages); without a shared place each system keeps its own list and
   people reconcile them by hand; with refiroo a steward keeps the agreed meaning once, connects each
   system's code to it and supplies the names, and the systems read the agreed data.
3. What makes it different, in one place, one short paragraph each, each linking to the About page that
   explains it: one engine, many applications (a new domain is another model; the shipped applications are
   examples); connections that keep their meaning (hierarchy, equivalent in another system, translation,
   each with its rules); three weights of change (a live edit, a change set approved and published as one
   consistent publication, a model release; daily work never blocked by prepared change); one set of rules
   on every path (browser, API, bulk loads); API first, with consumer APIs that give every system the same
   shape; governed (roles and narrowed grants, approval policies, history of who changed what and why);
   workspaces, each with a model of its own, one installation per organisation.
4. Who it helps (keep the table) and where it fits / what it is not (keep).

**The other About pages:** where one of them explains an idea from point 3, make sure its opening says the
idea in the same words, so the reader recognises it, and links back to "What refiroo is". Do not repeat the
whole account on them.

## Files you may edit

- `src/content/docs/about/*.md`
- `public/about/*.svg`
- `_waves/coverage/about.md`

## Report

The pages changed, and any claim the sources or the code did not support.
