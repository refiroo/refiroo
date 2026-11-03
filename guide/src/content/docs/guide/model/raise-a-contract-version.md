---
title: Raise a contract version
description: Review breaking consumer changes before activating a higher contract version.
reader: model-admin
---

Raise a consumer contract version when its consumers must read a changed shape or operation.
You need **Model authoring** to edit and release permission to activate. See
[Consumer APIs](/docs/model/consumer-apis/) for the versions involved.

1. Select the API under **Consumer APIs**. Read **Needs contract version …** and inspect the
   changes to exposed types, fields, related blocks, operations and filters. Fix draft errors
   first if it says **Checked once the draft is valid**.
2. Agree the change and its timing with the consuming teams. Download the generated documents
   for review. Raising a number is not a conversion of their software.
3. Open the API menu and choose **Raise contract version to …**. The action raises it by one
   as a saved step. Review the updated facts and History.
4. Open **Install and activate…** or **Apply to this workspace…** and inspect the consumer
   compatibility results for the destination. A comparison against the draft's base alone
   does not replace the check against the workspace's active contract.
5. If **A consumer API needs a higher contract version** still appears, read the listed API
   and differences. Correct or version that contract and check again. Activation is refused
   while the problem remains.

![Consumer API menu with Raise contract version action](/docs/screens/model-consumer-menu.png)

After activation, consumers use the new version. The old contract is not served alongside it
merely because its release remains installed. See [Releases](/docs/model/releases/).
