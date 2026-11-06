# C10-SCREENS-5 handoff report

## Recipes added or changed, in manifest order

47 entries (34 added, 13 changed); earlier unrelated recipes remain. Execute dependent groups as described by the fixture list, not an unfiltered full-file replay.

1. `admin-agent-access-enabled` — changed.
2. `integrate-agent-access-connect` — changed.
3. `admin-agent-new-client` — changed.
4. `admin-agent-register` — changed.
5. `c10-setup-matching-proposals` — added.
6. `use-mapping-proposed` — changed.
7. `c10-setup-assistant-ready` — added.
8. `use-assistant-stopped` — changed.
9. `use-assistant-proposal` — changed.
10. `model-assistant-workbook-proposal` — changed.
11. `use-assistant-loaded` — changed.
12. `model-assistant-workbook-loaded` — changed.
13. `use-assistant-reload` — changed.
14. `notification-email-digest` — changed.
15. `admin-agent-calls` — changed.
16. `c10-setup-assistant-words` — added.
17. `use-assistant-words` — added.
18. `c10-setup-assistant-whole-type-move` — added.
19. `model-assistant-whole-type-move` — added.
20. `c10-setup-stale-migration` — added.
21. `model-migration-stale` — added.
22. `c10-setup-assistant-partial-move` — added.
23. `c10-setup-partial-activate` — added.
24. `model-assistant-partial-move` — added.
25. `c10-setup-publish-assistant-history` — added.
26. `use-history-assistant` — added.
27. `admin-agent-block` — added.
28. `workspace-cannot-open` — added.
29. `model-language-raise-review` — added.
30. `run-jobs` — added.
31. `c10-setup-import-preview` — added.
32. `import-preview-columns` — added.
33. `admin-webhook-deliveries` — added.
34. `admin-webhook-rotate` — added.
35. `c10-setup-webhook-suspend` — added.
36. `admin-webhook-resume` — added.
37. `c10-setup-person-device-person` — added.
38. `c10-setup-person-local-target` — added.
39. `admin-person-link-provider` — added.
40. `c10-setup-local-group` — added.
41. `admin-group-members` — added.
42. `admin-person-second-factor` — added.
43. `admin-signin-provider` — added.
44. `c10-setup-local-signin-off` — added.
45. `admin-local-signin-off` — added.
46. `admin-ai-test-failed` — added.
47. `model-account-provider-failure` — added.

## Fixture list

`../C10-SCREENS/fifth-round-fixtures.md` gives exact external setup and restoration:

1. Nine isolated public-transport workspaces; working container assistant.
2. Two matching fictional system codes and genuine proposed targets.
3. Real MCP preparation/submission; human browser publication.
4. Two deliberate provider failures; exact restoration and healthy test.
5. Browser-created stale migration after a genuine separate-session edit.
6. Isolated older-language release; unavailable and raising-preview states.
7. Real queued/running jobs held briefly by a disposable-workspace lock.
8. For people XLSX retaining metadata, with one invalid Height cell.
9. Docker receiver, real delivery attempts, suspension and resume recovery.
10. Docker OpenID Connect provider, fictional people/group, temporary local-sign-in Off and restoration.
11. Genuine TOTP and virtual-authenticator WebAuthn enrolments on a fictional person.

Browser-created state is in setup entries. External work has not been executed. The offline public-data copies are prepared under `picture-data/`; all copied IDs are UUID4.

## Captions and image references

- `administer/agent-access.md`: enabled overview says empty client/assistant sections; Calls names Stops checker (guide) and answered/refused outcomes.
- `use/notifications-settings.md`: caption says account has no address or followed workspaces; existing image retained, no invented digest preferences.
- `use/mapping-grids.md`: requests the nonempty proposed-target grid, with confidence and reasons.
- `use/history.md`: requests actual assistant preparation and human publication, without promising a separate requester/editor.
- Restored fourteen image references with descriptive captions on the original deferred pages; the fifteenth, Notification email, was already present. The contributor reference is restored too, following the removal inventory rather than the incomplete old table.
- Inspected all five accepted Agent access PNGs plus Notification email. Connect and unsaved client/registration dialog captions already matched and were retained.

## Checks and limits

- `GUIDE_OUT=_build/C10-SCREENS-5 npm run build`: PASS, 247 pages, 3.40 s.
- `npm run check`: PASS, terms and brand, 247 pages.
- Screenshot tool `--list`: PASS, 94 manifest entries parsed; no browser launched.
- Offline checks: unique names, supported action syntax, every missing image has a recipe, all fifteen deferred references restored, Python notes parse and generated IDs are UUID4.
- `GUIDE_OUT=_build/C10-SCREENS-5 npm run check:links`: 28 missing-image references for 27 PNGs awaiting external capture; no other broken links reported. See `links.log`. Do not insert placeholder images just to make this check green.
- New recipes are source-checked, not browser-verified. Provider output, Stop timing, model-move proposals/bridge activation, screenshot framing, the two Docker fixtures and authentication enrolments need the real capture and image review. The invalid export workbook remains an external fixture because it must preserve genuine export metadata.
- No instance calls, new provider costs, security changes, commits or Git state changes occurred in this writing turn. No servers or database processes were started. The supplied assistant container-permission defect remains a prerequisite to verify in the reference image; no new runtime defect is claimed from these writing checks.
