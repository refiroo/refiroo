# Finding dispositions and evidence

## 1 — Not changed: environment limitation

The reader recorded curl 7 / HTTP 000 against an assigned local service. This does not establish an error in the installation page. No service setup or repair is part of this writing wave; no live acceptance is claimed.

## 2 — Fixed

`guide/use/correct-a-record.md` now distinguishes change-set Review changes from Live History, including checking prepared before/after values. Source: `frontend/src/features/objects/ObjectDetail.tsx:441` renders History only when neither changeSet nor publication is selected. Existing task `guide/use/review-what-a-change-set-changes.md` supplies the review route.

## 3 — Fixed

Two existing workbook task pages now embed downloadable XLSX files as data URLs, so no unpublished sample path or new public asset is needed. The first is byte-for-byte `guide/samples/Haltestellen_Busbetrieb_Nord.xlsx`; the update is byte-for-byte `guide/_coverage/notes/C10-SCREENS/Haltestellen_Busbetrieb_Nord_next.xlsx`. Compared all sheet cells with openpyxl: update renames Haltestellen D3, adds K3 and K4:K8, with other sheets unchanged. Both files parse. `frontend/src/features/model-editor/AddWorkbookDialog.tsx` accepts XLSX/CSV. The page explains that counts depend on mappings/workspace and that the update does not fix unresolved references. Guide CSP (`backend/app/management/guide_site.py`) has no navigation restriction; built download links still require verification.

## 4 — Product defect; pages unchanged

Visually inspected `admin-client-rotate.png`: the panel behind the dialog says Could not load this content / Not Found. Source inspection identifies a path to this failure: `frontend/src/features/security/ClientsPage.tsx:374` checks only the integration-admin action group, and line 482 renders ClientWebhooks. Line 688 requests subscriptions through `frontend/src/api/securityClient.ts:170-171`. `backend/app/main.py:662-665` mounts that endpoint only when consumer_subscriptions_enabled; the default is false (`backend/app/config.py:187`). Thus an integration administrator can request an unmounted route on an installation with subscriptions disabled. This is a source-confirmed capability-gating defect, consistent with the picture; the capture's actual environment setting and a live reproduction were not checked. No guide workaround or new picture was added. The creation page already calls it a load error, not an empty result, but cannot fix that product behavior.

## 5 — Fixed

`run/sign-in-and-mail-setup.md` now uses Settings › General › Notification email, as declared in `frontend/src/features/settings/navigation.ts:17-24`. Corrected the mail screenshot alt text and added a caption identifying the unconfigured state; no configured/delivered-mail evidence is claimed. Visually inspected `admin-mail-settings.png`. `frontend/src/features/settings/MailPage.tsx:370-378` disables the recipient/test while unconfigured, consistent with the picture. No new pictures requested by this wave.

## Final checks

- Read guide/AGENTS.md first, then C11-FIX wave and C11-READER findings. No top-level AGENTS workflow used. Only four existing content pages edited; working notes and progress confined to this wave. No commits or state-changing git commands.
- `GUIDE_OUT=_build/C11-FIX npm run build` in guide: passed, 247 pages, reported 4.09 seconds. Log: build.log. No plain build or dist replacement.
- `backend/.venv/bin/python guide/_coverage/notes/C11-FIX/check-built.py`: passed, four changed pages, 1,034 static link/image occurrences including sidebar links; fragments checked. Runtime API and external links excluded. Both embedded downloads survive rendering with download filenames, decode byte-for-byte to the sources and parse as three-sheet XLSX files. Evidence: built-check.json.
- `node guide/_coverage/notes/C11-FIX/check-downloads.mjs`: browser launch failed (Chrome SIGABRT under the sandbox), before page navigation. Browser clicking/downloading remains unverified; no live product tasks were exercised. Log: download-check.log. No server, database clone or background service was started.
- Reviewed the diff of the four edited pages, with base64 bodies elided for readability. Original and update data retain exact source bytes. No new pages or pictures. No screenshot requests: the wave prohibits new pictures. Mail's existing unconfigured picture is labelled honestly; the client picture's error remains a reported product defect.
- Steering file absent at each unit check, including final validation. No steering corrections applied.
