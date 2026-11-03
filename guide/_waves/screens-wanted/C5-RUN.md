# Screens wanted: Run refiroo

Capture from the reference instance with safe settings and no credentials exposed.

| Name | Page | Screen and state | Must be visible |
| --- | --- | --- | --- |
| `run-deployment.png` | `run/configure` | Settings › Administration › Deployment; loaded, read only | API address note; Capability groups with On/Off and switching setting; Database › Migration revision; settings columns Setting, Value, Default, Source, What it controls. Secrets only Set/Not set. |
| `run-operations.png` | `run/monitoring` | Settings › Administration › Operations; loaded, process detail expanded | As of and Refresh; summary figures; Workspaces state and Not served by; process Live/Ready, Background threads and Database connections; For monitoring addresses and Copy controls. |
| `run-jobs.png` | `run/background-jobs` | Settings › Data operations › Jobs with several job states | Workspace, State, Items, Requested by, Created, Finished and Actions; queued/running/finished examples if safely available, with no private files. |
| `run-backup-rehearsal.png` | `run/backup-and-restore` | Operations › Last backup rehearsal; Passed, workspace rows visible | Backup label, time, copy revision; Records, Relationships, Open change sets, Publications and Live now; earlier-rehearsal toggle where records exist. |

## Capture status at the end of this wave

Three files arrived from the screenshot wave and were visually inspected: `run-deployment.png`,
`run-operations.png` and `run-backup-rehearsal.png`. Deployment and Operations show the intended
surfaces. The deployment image runs an older image layout (`/model`, `/data`); its caption explains
that current defaults are in the text. Refresh it with the current image when available.

`run-jobs.png` is still missing. The current backup image shows **No backup has been rehearsed**,
so its page now describes that empty state accurately. The requested **Passed** rehearsal with
workspace counts remains outstanding; replace the image and update the page's alt text together
when that state has been captured. Operations could also use an uncropped footer including Metrics.
