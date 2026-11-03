# Integrate

Read `guide/AGENTS.md`, then the "integrate" section of `guide/_waves/OUTLINE.md`: it lists every page of
this section, what each must cover and its sources (mainly `docs/INTEGRATION_API.md`,
`docs/CONSUMER_API.md`, `docs/API.md` for concepts, `docs/OPERATIONS.md`, the USER_JOURNEYS integration
journeys).

Reader: developers and integrators of other systems. Explain the API's ideas and the sequences an
integration follows (sign in as a client and get a token; read and page; versions and conflicts; load data
in batches and jobs; follow changes through the change feed, events and webhooks; read a consumer API;
resolve codes with a lookup). Short excerpts only where a sequence needs one, taken from the sources; every
operation links to its entry in the API reference at `/docs/api` (link `/docs/api` with the operation's
tag or path as the API reference names it), and nothing `/docs/api` describes (fields, parameters,
responses) is repeated. Use the reference data's consumer API ("stops") as the example where one helps.

Write every page and guide the outline lists for "integrate". Where an administrator creates the client or
grants it access in the browser, link to the Administer pages; where a model administrator designs a
consumer API, link to the Model pages.

## Files you may edit

- `src/content/docs/integrate/*.md`
- `src/content/docs/guide/integrate/*.md`

## Report

The pages written, anything you could not confirm, and anything in refiroo that looked wrong.
