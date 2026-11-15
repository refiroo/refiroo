// 0.12 security surfaces in the accessibility and visual gates (0.12 R, D449): the sign-in screen (the
// password and the second-factor step), Home, Settings › Account, Security's people, a person, a group,
// roles, a client and a sign-in provider, Mail, the inbox panel, a submitted change set with its
// decision card (and A3's fixed bottom bar at 390px), the workspace page's tabs, Settings › Model's list
// and the unavailable workspace. They run on a harness of their own, since they make people, a client,
// a provider, a change set and a workspace the gates' other pages do not expect. Both gates call
// `visitSecuritySurfaces` with what they do on each surface; `dark` on a surface marks the representative
// subset the visual gate keeps dark baselines for, `phone` the ones it also keeps at 390px.
//
// Set up through the API, so each run shows the same screens: Ada (Contributor, in the group Curators),
// Nia (Reader), Pia (an authenticator app set up), a client with a consumer API grant, the sign-in
// provider Harness ID, mail set up against a harness SMTP server with three queued messages, the workspace
// Approval policy on, and Ada's change set submitted for publication (the inbox of the harness person, who
// approves, holds the notice). The last surface is a workspace on a release stored in schema 0.9.
import { execFileSync } from "node:child_process";
import { createHash, randomBytes } from "node:crypto";
import { resolve } from "node:path";
import { bootHarness } from "./harness.mjs";
import { startProvider } from "./oidc-provider.mjs";
import { startSmtp } from "./smtp-server.mjs";
import { totp } from "./totp.mjs";
import { python } from "./moves.mjs";

const root = resolve(import.meta.dirname, "..", "..", "..");
const PASSWORD = "a long passphrase for this person";
const base64Url = (bytes) => bytes.toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

/** The two dialogs and popovers a surface may leave open. */
async function closeOverlays(page) {
  for (let step = 0; step < 6; step += 1) {
    if (!(await page.locator("[role=dialog], [role=alertdialog], .inbox-panel").count())) return;
    await page.keyboard.press("Escape");
    await page.waitForFunction(() => document.getAnimations().every((animation) => animation.playState !== "running"));
  }
}

/**
 * Opens each surface in turn, light then dark, and calls `visit({ page, name, mask, dark, phone, axe })`;
 * `name` ends in the theme (and `-phone` at 390px), `mask` covers values that differ from run to run.
 */
export async function visitSecuritySurfaces(visit) {
  const harness = await bootHarness();
  const { page, uiUrl, apiUrl, api, signedOutContext, databaseUrl } = harness;
  let provider;
  let smtp;
  const contexts = [];
  try {
    provider = await startProvider();
    smtp = await startSmtp();
    page.setDefaultTimeout(15000);

    // ---- set-up through the API ----
    const model = await api("/model?workspaceKey=default");
    const start = (() => {
      for (const application of model.applications)
        for (const view of application.views) {
          const type = view.type === "table" && model.objectTypes.find((item) => item.key === view.objectTypeKey);
          if (type) return { application, type };
        }
      throw new Error("the starter has no table");
    })();
    const [record] = (
      await api(`/objects/${start.type.key}?workspaceKey=default&pageSize=1&applicationKey=${start.application.key}`)
    ).items;

    const person = async (username, name, grants = []) => {
      const created = await api("/users", { name, email: `${username}@example.org` });
      for (const [role, scope] of grants)
        await api("/grants", { principal: { kind: "user", id: created.id }, role, scope });
      const { url } = await api(`/users/${created.id}/password-reset`, {}, "POST");
      const set = await fetch(`${apiUrl}/oauth/password`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          token: new URL(url).searchParams.get("token"),
          password: PASSWORD,
          repeat: PASSWORD,
        }),
      });
      if (!set.ok) throw new Error(`${username}'s password was not set: ${set.status}`);
      return created;
    };
    /** A token for the person, as the browser gets one (PKCE); the runner's own fetch carries the harness client's. */
    const tokenFor = async (username) => {
      const context = await signedOutContext({ viewport: { width: 1440, height: 900 } });
      try {
        const verifier = base64Url(randomBytes(48));
        const redirectUri = `${uiUrl}/signed-in`;
        const form = await context.request.post(`${apiUrl}/oauth/authorize`, {
          form: {
            response_type: "code",
            client_id: "browser",
            redirect_uri: redirectUri,
            code_challenge: base64Url(createHash("sha256").update(verifier).digest()),
            code_challenge_method: "S256",
            state: "surfaces",
            email: `${username}@example.org`,
            password: PASSWORD,
          },
          maxRedirects: 0,
        });
        const exchanged = await context.request.post(`${apiUrl}/oauth/token`, {
          form: {
            grant_type: "authorization_code",
            client_id: "browser",
            code: new URL(form.headers().location).searchParams.get("code"),
            code_verifier: verifier,
            redirect_uri: redirectUri,
          },
        });
        return (await exchanged.json()).access_token;
      } finally {
        await context.close();
      }
    };
    const as = async (token, path, body, method) => {
      const response = await fetch(`${apiUrl}/api/v1${path}`, {
        method: method || (body ? "POST" : "GET"),
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        ...(body ? { body: JSON.stringify(body) } : {}),
      });
      if (!response.ok) throw new Error(`${path}: ${response.status} ${await response.text()}`);
      return response.json();
    };

    const ada = await person("ada", "Ada Varga");
    const nia = await person("nia", "Nia Okafor", [["reader", { workspaceKey: "default" }]]);
    const pia = await person("pia", "Pia Lind");
    const curators = await api("/groups", { name: "Curators", description: "Maintain the reference data" });
    await api(`/groups/${curators.id}/members`, { userId: ada.id });
    await api("/grants", {
      principal: { kind: "group", id: curators.id },
      role: "contributor",
      scope: { workspaceKey: "default" },
    });

    // Pia's authenticator app.
    const piaToken = await tokenFor("pia");
    const enrolment = await as(piaToken, "/me/second-factor", undefined, "POST");
    await as(piaToken, "/me/second-factor/confirmation", { code: totp(enrolment.secret) });

    const client = await api("/clients", { name: "Catalogue sync" });
    if (model.consumerApis?.[0])
      await api("/grants", {
        principal: { kind: "client", id: client.id },
        consumerApi: model.consumerApis[0].key,
        scope: { workspaceKey: "default" },
      });

    await api("/sign-in-providers", {
      key: "harness-id",
      name: "Harness ID",
      issuer: provider.issuer,
      clientId: "engine",
      clientSecret: provider.secret,
      groupsClaim: "groups",
      emailsTrusted: true,
      enabled: true,
    });

    await api(
      "/mail-settings",
      { host: "127.0.0.1", port: smtp.port, security: "none", fromAddress: "refiroo@example.org" },
      "PUT",
    );
    // Three messages the engine queued and finished, written from outside the API (as the M1 runner does):
    // no route queues one without sending it.
    execFileSync(
      resolve(root, "backend/.venv/bin/python"),
      [
        "-c",
        `
import os, sqlalchemy as sa
engine = sa.create_engine(os.environ["DATABASE_URL"])
with engine.begin() as connection:
    connection.execute(sa.text(
        "INSERT INTO mail_outbox (public_id, kind, to_address, subject, status, attempts, last_error, "
        "last_error_kind, created_at, next_attempt_at) "
        "VALUES (gen_random_uuid()::text, 'activation', 'waiting@example.org', 'Your account', 'pending', 2, "
        "'The server could not be reached', 'connection', now() - interval '10 minutes', now() + interval '1 hour')"))
    for status, kind, to, subject, error, error_kind in [
        ("sent", "activation", "grace@example.org", "Your account", None, None),
        ("failed", "password-reset", "gone@example.org", "Choose a new password",
         "127.0.0.1:25 refused the address: 550 5.1.1 no such mailbox", "recipient"),
    ]:
        connection.execute(sa.text(
            "INSERT INTO mail_outbox (public_id, kind, to_address, subject, status, attempts, last_error, "
            "last_error_kind, created_at, next_attempt_at, finished_at) "
            "VALUES (gen_random_uuid()::text, :kind, :to, :subject, :status, 1, :error, :error_kind, "
            "now() - interval '1 hour', now() - interval '1 hour', now() - interval '59 minutes')"),
            dict(kind=kind, to=to, subject=subject, status=status, error=error, error_kind=error_kind))
`,
      ],
      { cwd: resolve(root, "backend"), env: { ...process.env, DATABASE_URL: databaseUrl } },
    );

    // Approval on, and Ada's change set submitted: the harness person's inbox holds the notice.
    const policy = await api("/workspaces/default/approval-policy");
    await api(
      "/workspaces/default/approval-policy",
      { requireApproval: true, secondPerson: true, expectedVersion: policy.version },
      "PUT",
    );
    const adaToken = await tokenFor("ada");
    const changeSet = await as(adaToken, "/workspaces/default/change-sets", {
      name: "Corrections for spring",
      source: "currentLive",
    });
    await as(
      adaToken,
      `/objects/${start.type.key}/${record.id}`,
      {
        expectedVersion: record.version,
        name: `${record.name} (corrected)`,
        changeSetId: changeSet.id,
        expectedChangeSetVersion: changeSet.version,
      },
      "PATCH",
    );
    const current = await as(adaToken, `/change-sets/${changeSet.id}`);
    await as(adaToken, `/change-sets/${changeSet.id}/submission`, {
      expectedChangeSetVersion: current.version,
      comment: "Ready for review",
    });
    // Opening the submitted change set reads its notice (NT1, D464), so each surface that shows the unread
    // notice first has Ada submit one more change set under the same name.
    let noticeRead = false;
    const freshNotice = async () => {
      if (!noticeRead) return;
      noticeRead = false;
      const again = await as(adaToken, "/workspaces/default/change-sets", {
        name: "Corrections for spring",
        source: "currentLive",
      });
      const live = await api(`/objects/${start.type.key}/${record.id}?workspaceKey=default`);
      await as(
        adaToken,
        `/objects/${start.type.key}/${record.id}`,
        {
          expectedVersion: live.version,
          name: `${record.name} (corrected)`,
          changeSetId: again.id,
          expectedChangeSetVersion: again.version,
        },
        "PATCH",
      );
      const ready = await as(adaToken, `/change-sets/${again.id}`);
      await as(adaToken, `/change-sets/${again.id}/submission`, {
        expectedChangeSetVersion: ready.version,
        comment: "Ready for review",
      });
    };
    const reviewPath = `/apps/${start.application.key}/change-sets/${changeSet.id}/changes?workspaceKey=default`;

    // A workspace on a release of a schema outside the window. Such a release only arrives from an older
    // engine (this version never writes one), so the set-up rewrites an installed release's stored schema
    // version and hash, as the J37.9 journey does.
    {
      const other = python(
        "import json, sys; sys.path.insert(0, 'tests/journeys'); from configurations import generated; print(json.dumps(generated('b').model))",
      );
      other.schemaVersion = "0.10";
      const draft = await api("/model-drafts", { name: "Old herbarium", model: other });
      const release = await api(`/model-drafts/${draft.id}/installation`, { expectedVersion: draft.version });
      await api("/workspaces", { key: "old-herbarium", label: "Old herbarium", modelReleaseId: release.id });
      execFileSync(
        resolve(root, "backend/.venv/bin/python"),
        [
          "-c",
          `
import json, os, sys, sqlalchemy as sa
engine = sa.create_engine(os.environ["DATABASE_URL"])
model = json.loads(sys.argv[1])
with engine.begin() as connection:
    connection.execute(
        sa.text("UPDATE model_releases SET schema_version = '0.9', model_hash = 'stale-hash-surfaces', "
                "model_json = CAST(:m AS json) WHERE public_id = :id"),
        {"m": json.dumps({**model, "schemaVersion": "0.9"}), "id": sys.argv[2]},
    )
`,
          JSON.stringify(other),
          release.id,
        ],
        { cwd: resolve(root, "backend"), env: { ...process.env, DATABASE_URL: databaseUrl } },
      );
    }

    // What differs from run to run: times, ages, IDs, the engine's and the provider's ports.
    const varying = (target) => [
      target.getByText(/just now|\d+ (second|minute|hour|day|week|month)s? ago|\d{1,2}:\d{2}|\d{4}-\d{2}-\d{2}/),
      target.getByText(/^[0-9a-f]{8}(-|…)/),
      target.getByText(/127\.0\.0\.1:\d+|localhost:\d+/),
      target.locator("h1").filter({ hasText: /^Good (morning|afternoon|evening)/ }),
      target.locator(".account-muted, .settings-note, small").filter({ hasText: /\d/ }),
    ];

    // A signed-out screen in a context of its own, at the viewport and scheme asked for.
    const signedOut = async (state, goto) => {
      const context = await signedOutContext({
        viewport: state.viewport,
        colorScheme: state.scheme,
        hasTouch: state.viewport.width < 600,
      });
      contexts.push(context);
      const surface = await context.newPage();
      surface.setDefaultTimeout(15000);
      await goto(surface);
      return { page: surface, done: () => context.close() };
    };
    const staysOn = (path, ready) => async () => {
      await page.goto(`${uiUrl}${path}`);
      await ready();
    };
    const heading = (level, name) => () => page.getByRole("heading", { level, name }).waitFor();
    // Not "networkidle": a signed-in page keeps the inbox's event stream open for as long as it is shown.
    const settled = async () => {
      await page.waitForFunction(() => document.querySelectorAll('[aria-busy="true"]').length === 0);
      await page.evaluate(() => document.fonts.ready);
    };

    // Brought up to date (0.14 + 0.17 release review, ST1/UX1): People is a region of rows (Active people)
    // and a person's, group's, client's and provider's page is headed by the item header (level 1); a
    // person's roles are a list named "Roles in <place>"; a group's members are a region.
    // Each: [name, open, { dark, phone, axe }]. `open` may return `{ page, done }` for a page of its own.
    const surfaces = [
      [
        "security-sign-in",
        (state) =>
          signedOut(state, async (surface) => {
            await surface.goto(uiUrl);
            await surface.getByRole("heading", { level: 1, name: "Sign in" }).waitFor();
            await surface.getByLabel("E-mail address").waitFor();
          }),
        { dark: true, phone: true },
      ],
      [
        "security-sign-in-code",
        (state) =>
          signedOut(state, async (surface) => {
            await surface.goto(uiUrl);
            await surface.getByLabel("E-mail address").fill("pia@example.org");
            await surface.getByLabel("Password").fill(PASSWORD);
            await surface.getByRole("button", { name: "Sign in", exact: true }).click();
            await surface.getByRole("heading", { level: 1, name: "Enter your code" }).waitFor();
          }),
        { phone: true },
      ],
      [
        "security-home",
        async () => {
          await page.goto(uiUrl);
          await page.getByRole("region", { name: "Waiting for your approval" }).waitFor();
          await settled();
        },
        { dark: true, phone: true },
      ],
      [
        "security-account",
        staysOn("/settings/account", () => page.getByRole("heading", { name: "What you can do" }).waitFor()),
      ],
      [
        "security-people",
        staysOn("/settings/people", () =>
          page
            .getByRole("region", { name: "Active people" })
            .getByRole("button", { name: /Nia Okafor/ })
            .waitFor(),
        ),
        { phone: true },
      ],
      [
        "security-person",
        async () => {
          await page.goto(`${uiUrl}/settings/people/${nia.id}`);
          await heading(1, "Nia Okafor")();
          await page
            .getByRole("list", { name: /^Roles in / })
            .first()
            .waitFor();
          await settled();
        },
      ],
      [
        "security-group",
        async () => {
          await page.goto(`${uiUrl}/settings/groups/${curators.id}`);
          await heading(1, "Curators")();
          await page.getByRole("region", { name: "Members" }).getByRole("link", { name: "Ada Varga" }).waitFor();
          await settled();
        },
      ],
      ["security-roles", staysOn("/settings/roles", heading(1, "Roles"))],
      [
        "security-client",
        async () => {
          await page.goto(`${uiUrl}/settings/clients/${client.id}`);
          await heading(1, "Catalogue sync")();
          await settled();
        },
      ],
      [
        "security-provider",
        async () => {
          await page.goto(`${uiUrl}/settings/sign-in/harness-id`);
          await heading(1, "Harness ID")();
          await settled();
        },
      ],
      [
        "security-mail",
        async () => {
          await page.goto(`${uiUrl}/settings/mail`);
          await heading(1, "Mail")();
          // The outbox is on the Messages tab (0.17 ST1, PP-D62).
          await page.getByRole("tab", { name: "Messages" }).click();
          await page.getByText("gone@example.org").waitFor();
          await settled();
        },
      ],
      [
        "security-inbox",
        async () => {
          await freshNotice();
          await page.goto(uiUrl);
          await page.getByRole("button", { name: /^Inbox/ }).click();
          await page.locator(".inbox-panel").getByText("Waiting for your approval").waitFor();
          await settled();
        },
        { dark: true },
      ],
      [
        // NT1: the history page behind the bell's "See all notifications".
        "security-notifications",
        async () => {
          await freshNotice();
          await page.goto(`${uiUrl}/notifications`);
          await page.getByRole("heading", { level: 1, name: "Notifications" }).waitFor();
          await page
            .getByRole("button", { name: /Waiting for your approval/ })
            .first()
            .waitFor();
          await settled();
        },
        { dark: true, phone: true },
      ],
      [
        "security-change-set-decision",
        async () => {
          await page.goto(`${uiUrl}${reviewPath}`);
          noticeRead = true;
          await page.getByRole("region", { name: "Decision" }).waitFor();
          await settled();
        },
        { dark: true, phone: true },
      ],
      [
        "security-workspace-overview",
        // An opened workspace is its own page: its name the level-1 heading, "Workspaces" the trail back (0.17 ST1).
        staysOn("/settings/workspaces/default", async () => {
          await page.getByRole("heading", { level: 1 }).first().waitFor();
          await page.getByRole("tab", { name: "Overview", selected: true }).waitFor();
        }),
      ],
      [
        "security-workspace-access",
        staysOn("/settings/workspaces/default/access", () => page.getByRole("region", { name: "Access" }).waitFor()),
      ],
      [
        "security-workspace-approval",
        staysOn("/settings/workspaces/default/approval", () =>
          page.getByRole("region", { name: "Approval" }).waitFor(),
        ),
      ],
      [
        "security-workspace-activity",
        // The seed's changes are as old as the day its database was built, the run's as new as now, so the list has one
        // day heading or two depending on the day: the headings are left out of the picture.
        staysOn("/settings/workspaces/default/activity", async () => {
          await page.getByRole("tab", { name: "Activity", selected: true }).waitFor();
          await page.addStyleTag({ content: ".history-day { display: none; }" });
        }),
      ],
      ["security-model-list", staysOn("/settings/model", () => page.getByText("Runs the default workspace").waitFor())],
    ];

    const unavailableSurface = [
      "security-unavailable-workspace",
      async () => {
        await page.goto(`${uiUrl}/?workspaceKey=old-herbarium`);
        await page
          .getByText(/no longer reads/)
          .first()
          .waitFor();
        await settled();
      },
      { dark: true },
    ];
    surfaces.push(unavailableSurface);

    for (const width of [1440, 390]) {
      for (const scheme of ["light", "dark"]) {
        await page.emulateMedia({ colorScheme: scheme });
        await page.setViewportSize({ width, height: width < 600 ? 844 : 900 });
        const state = { viewport: { width, height: width < 600 ? 844 : 900 }, scheme };
        for (const [name, openSurface, { dark = false, phone = false, axe = true } = {}] of surfaces) {
          // At 390px the surfaces that matter there: the others are the same page in a narrower column.
          if (width < 600 && !phone) continue;
          await closeOverlays(page);
          const opened = (await openSurface(state)) ?? { page };
          await opened.page.mouse.move(0, 0);
          await visit({
            page: opened.page,
            name: `${name}${width < 600 ? "-phone" : ""}-${scheme}`,
            mask: varying(opened.page),
            dark,
            phone,
            axe,
          });
          await opened.done?.();
        }
        await closeOverlays(page);
      }
    }
    await page.emulateMedia({ colorScheme: "light" });
    await page.setViewportSize({ width: 1440, height: 900 });
  } finally {
    for (const context of contexts) await context.close().catch(() => undefined);
    harness.cleanup();
    smtp?.stop();
    provider?.child.kill();
  }
}
