---
title: Work on a draft with others
description: Recover an edit refused because another person saved a newer draft.
reader: model-admin
---

Several model authors can open the same draft. Each save checks the version it was based on,
so an older edit cannot silently replace a newer one. See [The model editor](/docs/model/the-model-editor/).

1. When **Another change came first** appears, stop repeating the original action. Your change
   was not applied. The notice lists steps applied since you opened the draft, and the model
   beneath it shows the newer version. A rename names both the old and new name, so you
   can identify the definition before deciding whether to retry.
2. Read those steps and inspect the affected definitions. Check whether your intended change
   is still needed and whether its target still means the same thing.
3. Choose **Apply mine again** to try your change against that version, or **Discard mine**
   to leave it out. A further edit by someone else can refuse the retry too; review again.
4. Open **History** to confirm the saved result and **Issues** to check its validity.

![Newer draft notice with applied steps and retry or discard actions](/docs/screens/model-conflict-editor.png)

In the specialist [JSON view](/docs/model/json-view/), **A newer draft version exists** preserves
your local text. Choose **Copy local JSON** before **Reload saved version** if you need that text.
Reloading reads the saved draft; it does not merge your local text into it. Review and reapply
only the changes still needed, then save against the current version.

![JSON editor preserving local work after a version conflict](/docs/screens/model-json-newer-version.png)
