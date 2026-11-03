# Steering for C10, third round (2026-11-03)

- `tools/screens.mjs` now signs in as any role with `"as": "<role>"`; the reference instance has a contributor
  (`"as": "contributor"`, GUIDE_CONTRIBUTOR_* in its .env). Add the recipe for `contributor-propose-change`
  (see `_waves/screens-wanted/C10-LATER.md`) with it, and any other entry of C10-LATER that only needed the
  contributor or the approver. Put the image reference back on its page and take the entry out of C10-LATER.
- Everything else in C10-LATER stays deferred.
