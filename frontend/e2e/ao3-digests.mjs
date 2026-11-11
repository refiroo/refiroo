// 0.16 AO3 browser evidence (J57): Settings › Notifications › Email (the three-way choice per kind, the digest's
// frequency and next time, Workspaces I follow with Stop following) and the Follow toggle on a home workspace card,
// against a real backend and a harness SMTP server for the mail settings (nothing is sent: the digest itself is the
// journey test's), on two models: the starter and generated-b. It names no key of either.
//
//  1. Home at 1440px by keyboard: the workspace card's Follow is pressed and says Following; the API lists the
//     workspace as followed. At 390px: no horizontal scroll, the button is 44px high.
//  2. Settings › Notifications: the mail switched on, each kind is At once; approvals go to the Digest by keyboard
//     (which starts a daily digest in the browser's time zone and says when the next is, at 07:00), the digest is
//     changed to Mondays; the followed workspace is listed with Stop following, which removes it, and Home shows Follow
//     again. Axe on each state, light and dark, 1440px and 390px.
//  3. A digest's link (`/notifications?notice=<id>`) opens the notice's subject (the change set's review) and marks
//     the notice read; a link to a notice that is gone says so and stays on the list.
// No console error or 4xx/5xx beyond the missing notice's 404; screenshots in the run's folder (inspect them
// against the mock-up).
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { watchErrors } from "./helpers/person.mjs";
import { bootShaped, SHAPED_MODELS, startingPoint } from "./helpers/shaped-models.mjs";
import { startSmtp } from "./helpers/smtp-server.mjs";
import { goDark } from "./helpers/theme.mjs";

const backend = resolve(import.meta.dirname, "..", "..", "backend");
const checks = [];

async function accessible(page, name) {
  const result = await runAxe(page, [], name);
  assert.equal(result.violations.length, 0, formatViolations(result.violations));
  checks.push(`axe ${name}: 0 violations`);
}

const noOverflow = (page, name) =>
  page
    .evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)
    .then((fits) => assert.equal(fits, true, `${name}: no horizontal page scroll`));

/** A statement run on the run's database, from outside the API. */
const execute = (databaseUrl, sql) =>
  execFileSync(
    resolve(backend, ".venv/bin/python"),
    [
      "-c",
      `import os, sqlalchemy as sa\nwith sa.create_engine(os.environ["DATABASE_URL"]).begin() as c: c.execute(sa.text(${JSON.stringify(sql)}))`,
    ],
    { cwd: backend, env: { ...process.env, DATABASE_URL: databaseUrl } },
  );

/** A value read from the run's database, from outside the API. */
const query = (databaseUrl, sql) =>
  execFileSync(
    resolve(backend, ".venv/bin/python"),
    [
      "-c",
      `import os, sqlalchemy as sa\nwith sa.create_engine(os.environ["DATABASE_URL"]).connect() as c: print(c.execute(sa.text(${JSON.stringify(sql)})).scalar())`,
    ],
    { cwd: backend, env: { ...process.env, DATABASE_URL: databaseUrl } },
  )
    .toString()
    .trim();

async function walk(configuration) {
  const label = configuration.name;
  const smtp = await startSmtp();
  const harness = await bootShaped(configuration);
  const { page, api, uiUrl, output, databaseUrl, harnessIdentity } = harness;
  const shot = (name) => page.screenshot({ path: resolve(output, `ao3-${label}-${name}.png`), fullPage: true });
  const clean = watchErrors(page, {
    allowResponse: (response) => response.status() === 404 && response.url().includes("/me/notifications/"),
    allowConsole: (message) => message.text().includes("404"),
  });
  try {
    // Mail is set up and the person has an address: the panel is offered.
    await api(
      "/mail-settings",
      {
        host: "127.0.0.1",
        port: smtp.port,
        security: "none",
        fromAddress: "refiroo@example.org",
        applicationUrl: uiUrl,
      },
      "PUT",
    );
    const people = (await api(`/users?pageSize=200`)).items;
    const me = people.find((item) => item.email === harnessIdentity.person.email) ?? people[0];
    await api(`/users/${me.id}`, { expectedVersion: me.version, email: "steward@example.org" }, "PATCH");
    const table = await startingPoint(api, { count: 3 });

    // 1. Follow on a home card.
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(`${uiUrl}/`);
    const follow = page.getByRole("button", { name: /^Follow(ing)? / }).first();
    await follow.waitFor();
    assert.equal(await follow.getAttribute("aria-pressed"), "false");
    await accessible(page, `ao3-${label}-home-before`);
    await shot("home-before");
    await follow.focus();
    await page.keyboard.press("Enter");
    await page.waitForFunction(() =>
      document.querySelector('.home-follow-button[aria-pressed="true"]')?.textContent?.includes("Following"),
    );
    assert.equal(query(databaseUrl, "SELECT count(*) FROM workspace_followers"), "1", "the workspace is followed");
    await accessible(page, `ao3-${label}-home-following`);
    await shot("home-following");
    await goDark(page);
    await accessible(page, `ao3-${label}-home-following-dark`);
    await shot("home-following-dark");
    await page.emulateMedia({ colorScheme: "light" });
    await page.evaluate(() => (document.documentElement.dataset.theme = "light"));
    checks.push(`${label}: Follow on a home card by keyboard shows Following and the engine holds the follow`);

    // 2. Settings › Notifications.
    for (const [tag, viewport, byKeyboard] of [
      ["1440", { width: 1440, height: 900 }, true],
      ["390", { width: 390, height: 844 }, false],
    ]) {
      await page.setViewportSize(viewport);
      if (tag === "390") {
        // Back to a clean choice for the narrow walk: the digest is kept, the followed workspace too.
        await page.goto(`${uiUrl}/`);
        await page
          .getByRole("button", { name: /^Follow(ing)? / })
          .first()
          .waitFor();
        await noOverflow(page, `${label} home 390`);
        const height = await page
          .getByRole("button", { name: /^Follow(ing)? / })
          .first()
          .evaluate((node) => node.getBoundingClientRect().height);
        assert.ok(height >= 44, `${label}: Follow is at least 44px high at 390px (${height})`);
        await shot("home-390");
      }
      await page.goto(`${uiUrl}/settings/notifications`);
      await page.getByRole("heading", { name: "Email", exact: true }).waitFor();
      const mailSwitch = page.getByRole("switch", { name: "Email me when something arrives in my inbox" });
      if ((await mailSwitch.getAttribute("aria-checked")) === "false") {
        if (byKeyboard) {
          await mailSwitch.focus();
          await page.keyboard.press("Space");
        } else await mailSwitch.click();
        await page.waitForFunction(
          () =>
            document.querySelector('[role="switch"][aria-label^="Email me"]')?.getAttribute("aria-checked") === "true",
        );
      }
      const approvals = page.getByRole("radiogroup", { name: "A change set is waiting for your approval" });
      await approvals.waitFor();
      const kinds = await page.locator(".account-kinds [role=radiogroup]").count();
      assert.ok(kinds >= 6, `${label}: every kind has its three-way choice (${kinds})`);
      await page.getByText("Workspaces I follow").waitFor();
      await accessible(page, `ao3-${label}-${tag}-settings`);
      await shot(`${tag}-settings`);
      await noOverflow(page, `${label} settings ${tag}`);

      if (tag === "1440") {
        // The approvals into the digest, by keyboard; the digest says when the next is.
        const digest = approvals.getByRole("radio", { name: "Digest" });
        if (!(await digest.isChecked())) {
          await digest.focus();
          await page.keyboard.press("Space");
        }
        await page.getByText(/Next digest: .*07:00\./).waitFor();
        assert.ok(await approvals.getByRole("radio", { name: "Digest" }).isChecked());
        assert.ok(await page.getByRole("radio", { name: "Every morning at 07:00" }).isChecked());
        await accessible(page, `ao3-${label}-${tag}-digest`);
        await shot(`${tag}-digest`);
        const mondays = page.getByRole("radio", { name: "Mondays at 07:00" });
        await mondays.focus();
        await page.keyboard.press("Space");
        await page.getByText(/Next digest: Monday .*07:00\./).waitFor();
        await shot(`${tag}-weekly`);
        await goDark(page);
        await accessible(page, `ao3-${label}-${tag}-digest-dark`);
        await shot(`${tag}-digest-dark`);
        await page.emulateMedia({ colorScheme: "light" });
        await page.evaluate(() => (document.documentElement.dataset.theme = "light"));
        checks.push(
          `${label}: approvals in the digest by keyboard, a daily digest started with the next time at 07:00, then Mondays`,
        );
      }
    }

    // Stop following removes the workspace from the list and Home offers Follow again.
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(`${uiUrl}/settings/notifications`);
    const stop = page.getByRole("button", { name: /^Stop following / }).first();
    await stop.waitFor();
    await stop.focus();
    await page.keyboard.press("Enter");
    await page.getByText("You do not follow a workspace.").waitFor();
    await shot("stopped");
    await page.goto(`${uiUrl}/`);
    const again = page.getByRole("button", { name: /^Follow(ing)? / }).first();
    await again.waitFor();
    assert.equal(await again.getAttribute("aria-pressed"), "false");
    checks.push(`${label}: Stop following removes it from the list and Home offers Follow again`);

    // 3. A digest's link opens the notice's subject; a gone notice is said so.
    const set = await api(`/workspaces/default/change-sets`, { source: "currentLive", name: "Digest link" });
    await api(`/objects`, {
      applicationKey: table.application.key,
      workspaceKey: "default",
      objectTypeKey: table.type.key,
      name: `Digest ${Date.now()}`,
      attributes: table.type.attributes
        .filter((binding) => binding.required)
        .map((binding) => ({ attributeTypeKey: binding.attributeTypeKey, value: `digest-${Date.now()}` })),
      changeSetId: set.id,
      expectedChangeSetVersion: (await api(`/change-sets/${set.id}`)).version,
    }).catch(() => undefined);
    await api(`/change-sets/${set.id}/submission`, {
      expectedChangeSetVersion: (await api(`/change-sets/${set.id}`)).version,
      comment: "Please look",
    });
    const id = query(databaseUrl, "SELECT id FROM notifications ORDER BY sequence_id DESC LIMIT 1");
    assert.match(id, /^[0-9a-f-]{36}$/);
    await page.goto(`${uiUrl}/notifications?notice=${id}`);
    await page.waitForURL(new RegExp(`change-sets/${set.id}`));
    assert.notEqual(
      query(databaseUrl, `SELECT read_at IS NOT NULL FROM notifications WHERE id = '${id}'`),
      "False",
      "the notice is read",
    );
    await shot("link-opened");
    checks.push(`${label}: a digest's link opens the notice's subject and marks it read`);

    // A followed publication: the link opens the publication.
    execute(
      databaseUrl,
      "INSERT INTO workspace_followers (user_id, workspace_key, created_at) SELECT id, 'default', now() FROM users WHERE email = '" +
        harnessIdentity.person.email +
        "'",
    );
    const published = await api("/workspaces/default/change-sets", { source: "currentLive", name: "Followed" });
    const staged = await api(
      `/objects/${table.type.key}/${table.records[0].id}?workspaceKey=default&changeSetId=${published.id}`,
    );
    await api(
      `/objects/${table.type.key}/${table.records[0].id}`,
      {
        expectedVersion: staged.version,
        name: `${table.records[0].name} followed`,
        changeSetId: published.id,
        expectedChangeSetVersion: (await api(`/change-sets/${published.id}`)).version,
      },
      "PATCH",
    );
    const active = (await api("/workspaces/default/publications?pageSize=1")).items.filter(
      (item) => item.status === "active",
    );
    await api(`/change-sets/${published.id}/publication`, {
      expectedChangeSetVersion: (await api(`/change-sets/${published.id}`)).version,
      expectedActivePublicationId: active[0]?.id ?? null,
    });
    const followed = query(
      databaseUrl,
      "SELECT id FROM notifications WHERE kind = 'change-set.published' ORDER BY sequence_id DESC LIMIT 1",
    );
    const publicationId = query(
      databaseUrl,
      `SELECT details->>'publicationId' FROM notifications WHERE id = '${followed}'`,
    );
    await page.goto(`${uiUrl}/notifications?notice=${followed}`);
    await page.waitForURL(new RegExp(`publicationId=${publicationId}`));
    await shot("publication-opened");
    checks.push(`${label}: a followed publication's link opens the publication`);

    await page.goto(`${uiUrl}/notifications?notice=00000000-0000-0000-0000-000000000000`);
    await page.getByText(/no longer in your inbox/).waitFor();
    await accessible(page, `ao3-${label}-link-gone`);
    await shot("link-gone");
    checks.push(`${label}: a link to a notice that is gone says so and stays on the list`);

    await clean(`${label}: the whole path`);
  } finally {
    await harness.cleanup();
    smtp.stop();
  }
}

for (const configuration of SHAPED_MODELS) await walk(configuration);
console.log(checks.map((check) => `ok - ${check}`).join("\n"));
console.log(`${checks.length} checks passed`);
