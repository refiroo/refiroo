---
title: Submit a bulk change
description: Prepare a bounded batch, inspect its preview and reconcile every outcome.
reader: integrator
---

Use a batch when your source supplies several changes together. Read [Writing in bulk](/docs/integrate/writing-in-bulk/) for policies and limits.

1. Read the target workspace's [model and capabilities](/docs/api/?api=management#tag/model). Decide whether changes go live or into a change set. Keep the model release and current version claims.
2. Prepare items in dependency order: parents before children, then relationships that need those records. Use public IDs or declared unique keys. Choose atomic if nothing may apply on a refusal, or independent if valid items may apply separately.
3. Submit through the [batch operation](/docs/api/?api=management#tag/jobs), with an idempotency key saved beside the exact request. Choose background preview if you need to review the changes, including cascading deletion impact. Inline execution cannot preview.
4. Follow the returned [job](/docs/integrate/jobs/). In a preview, inspect proposed outcomes, the policy result and whether coverage is complete. A sample does not prove the remaining items are valid. Confirm through the [job confirmation operation](/docs/api/?api=management#tag/jobs), or cancel without applying changes.
5. After execution, page every item outcome. Record committed IDs and versions, correct rejected source items and inspect why unprocessed items stopped. A successful HTTP response alone does not mean the batch applied completely.
6. If the response was lost, replay the exact keyed request. If data was refused for stale versions or changed deletion impact, reread or preview before building a corrected request with a new key. Never change a request under an existing key.

For independent work, retain earlier committed outcomes when a job fails or is cancelled. For an atomic refusal, nothing from the batch applied. Check which case occurred before planning a retry.
