---
title: Licence and source
description: Offer the corresponding source for the version people use.
reader: operator
---

refiroo is offered under **AGPL-3.0-or-later**. People interacting with a modified version over a
network must have the corresponding source offer required by section 13. Keep that offer correct
for the software actually running on your installation.

`SOURCE_CODE_URL` defaults to the project's source tag for the running engine version:
`https://github.com/refiroo/refiroo/tree/v<version>`. When running a modified build, set it to the
address of your own corresponding source, including your modifications and the scripts and
configuration that form part of the work. Publish safe configuration templates; never publish
installation secrets or filled private environment files.

The setting must be an absolute HTTP or HTTPS URL. An invalid value refuses startup and names the
setting. Apply it in the installation environment and recreate the engine:

```bash
docker compose up -d engine
```

Check the source link in **Settings › General › About** and the account menu. It must lead
to the source of that running build. The authenticated system-information operation
`GET /api/v1/system` also reports it as `engine.sourceCode`, alongside engine version and licence;
see the [API reference](/docs/api).

Keep this source address with the version and configuration in your upgrade and backup records.
Changing it provides the link; it does not publish the source for you.

## Set and verify the source offer

You need the corresponding source for the running build, permission to publish that source, a
reachable HTTP/HTTPS address and access to the installation's private environment. Determine the
exact source revision before changing the link. The default project tag is suitable only when it
corresponds to the code you actually serve.

1. Make the source, including your modifications and needed build scripts, available at the
   intended address. Review its contents for secrets; publish safe templates in place of private
   installation values.
2. For a modified installation, put its source address in `.env`, for example:

   ```dotenv
   SOURCE_CODE_URL=https://source.example.org/refiroo/installed-version
   ```

   This setting is not secret. It is read at startup and requires engine recreation, not a browser
   refresh alone. Leave it unset for the unmodified version's default project tag.
3. Apply and check:

   ```bash
   docker compose up -d engine
   curl -i https://refiroo.example.org/health
   ```

   Expect readiness 200. Sign in, open About and follow **Source code**. Verify the published
   source matches the reported engine/build version and is accessible to the people receiving
   the offer. Merely returning an HTTP success page does not prove it is the correct source.
4. Keep the source/version association with the backup and upgrade record. If the link is wrong,
   correct the private setting and recreate again. The source publication itself is managed by
   your source-hosting service, not by refiroo.

A malformed value is refused with the exact prefix
`SOURCE_CODE_URL must be an absolute http or https address, not`, followed by the supplied value.
Correct its scheme/address; do not repair it by publishing a filled `.env` or a credential-bearing
source URL. This procedure provides the product's source link; evaluate your organisation's licence
obligations against the licence text accompanying the source.
