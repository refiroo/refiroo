# Screens wanted: C5b-RUN-DEPTH

The pages reuse the existing images below. No new missing-image URL was introduced. Recapture the
listed states after this writing pass; image files are outside this wave's edit allowance. Keep
examples in the Graubünden reference instance and protect secrets. Terminal-only procedures do not
need screenshots.

| File | Pages | Screen and state | What must be visible |
| --- | --- | --- | --- |
| `run-deployment.png` | `run/configure` | Settings › Administration › Deployment, current reference deployment | Capability groups, database revision, Runtime table with current image paths and Setting/Value/Default/Source/What it controls columns; secrets only Set/Not set. Existing screenshot has older paths, explicitly captioned on the page. |
| `run-operations.png` | `run/monitoring` | Settings › Administration › Operations, healthy instance with process expanded | Summary, workspace readiness, live process, running/off thread states, pool use, request counts and probe addresses. Capture enough to read without showing credentials. |
| `run-backup-rehearsal.png` | `run/backup-and-restore` | Operations, before any rehearsal | No backup has been rehearsed and How to rehearse a restore. The page's current alt text describes this existing empty state; retain it unless page/alt text is intentionally updated for a passed-state image in a later wave. |
| `admin-mail-settings.png` | `run/sign-in-and-mail-setup` | Settings › Integration › Mail, configured server and test area | Server, Port, Connection, From address, Application address, Save and Test message; no SMTP password or reset link. Reuses the access section's existing image. |

Useful later variants, not inserted as broken image placeholders here: a passed backup rehearsal
with restored workspace counts and Live now comparison; an unavailable workspace with its reason;
a failing worker with Last problem. If those are captured, coordinate new filenames and alt text
with the owning page before publication.
