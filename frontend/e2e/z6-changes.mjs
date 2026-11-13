// 0.12 Z6 browser evidence: one person's changes across workspaces, against a real backend on two
// models (the starter in the default workspace, the journey configuration generated-b installed into a
// second workspace). People and a client are made and granted through the API; Ana's and the client's
// writes go through their own tokens, so each entry names them. A Reader of the default workspace opens
// a record, follows Ana's name in its history to her changes (only the default workspace's), opens a
// record from an entry, and follows the client's name to its changes. Ana on Home sees Your recent
// changes and opens all of them: both workspaces, narrowed by workspace, kind and period, Show more
// continuing. A Security administrator without data roles is offered no "See changes" on her page; the
// harness person, who reads every workspace, is. Keyboard from the filters to Show more; axe; screenshots
// at 1440px light and dark and 390px; no horizontal page scroll at 390px. Applications and types are read
// from each model, never named.
// Brought up to date (0.14 + 0.17 release review, UX1): the changes page's foot is the settings log foot, whose button reads Show more; a person's page is headed by the item header (level 1) and its See changes is a More actions item.
import { execFileSync } from "node:child_process";
import { createHash, randomBytes } from "node:crypto";
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { goDark } from "./helpers/theme.mjs";

const root = resolve(import.meta.dirname, "..", "..");
const SECOND = { key: "branch-b", label: "Branch B" };
const PASSWORD = "a long passphrase for this person";

const checks = [];
const failures = [];

function expect(condition, message) {
  if (!condition) failures.push(message);
}

async function axe(page, name) {
  const result = await runAxe(page, [], name);
  if (result.violations.length) failures.push(`${name}:\n${formatViolations(result.violations)}`);
  checks.push(`axe ${name}: ${result.violations.length} violations`);
}

const generatedB = JSON.parse(
  execFileSync(
    resolve(root, "backend/.venv/bin/python"),
    [
      "-c",
      "import json, sys; sys.path.insert(0, 'tests/journeys'); from configurations import generated; print(json.dumps(generated('b').model))",
    ],
    { cwd: resolve(root, "backend") },
  ).toString(),
);

const base64Url = (bytes) => bytes.toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

const harness = await bootHarness();
try {
  const { uiUrl, apiUrl, api, output, signedOutContext, page: harnessPage } = harness;
  const overflow = (page) => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  const shot = async (page, name) => {
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: resolve(output, `z6-${name}-top.png`) });
    await page.screenshot({ path: resolve(output, `z6-${name}.png`), fullPage: true });
  };
  const dark = goDark;
  /** A call to the API with `token`, as that person or client. */
  async function as(token, path, body, method) {
    const response = await fetch(`${apiUrl}/api/v1${path}`, {
      method: method || (body ? "POST" : "GET"),
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
    if (!response.ok) throw new Error(`${path}: ${response.status} ${await response.text()}`);
    return response.json();
  }

  // Setup: generated-b installed and a second workspace on it.
  const b = structuredClone(generatedB);
  b.schemaVersion = "0.10";
  const draft = await api("/model-drafts", { name: "Second model", model: b });
  const release = await api(`/model-drafts/${draft.id}/installation`, { expectedVersion: draft.version });
  await api("/workspaces", { ...SECOND, modelReleaseId: release.id });
  const model = await api("/model?workspaceKey=default");
  const table = model.applications
    .flatMap((application) =>
      application.views
        .filter((view) => view.type === "table" && view.objectTypeKey)
        .map((view) => ({ application, type: model.objectTypes.find((item) => item.key === view.objectTypeKey) })),
    )
    .find(Boolean);
  const records = (
    await api(`/objects/${table.type.key}?workspaceKey=default&pageSize=60&applicationKey=${table.application.key}`)
  ).items;
  const record = records[0];

  /** A person granted `grants` whose password is set; signed in on the engine's page at `width`. */
  async function person(username, name, grants, width = 1440) {
    const created = await api("/users", { email: `${username}@example.org`, name });
    for (const [role, scope] of grants)
      await api("/grants", { principal: { kind: "user", id: created.id }, role, scope });
    const { url } = await api(`/users/${created.id}/password-reset`, {}, "POST");
    const context = await signedOutContext({ viewport: { width, height: width < 600 ? 844 : 900 } });
    const page = await context.newPage();
    page.setDefaultTimeout(15000);
    page.on("pageerror", (error) => failures.push(`${username}: ${error.message}`));
    await page.goto(url);
    await page.getByLabel("New password", { exact: true }).fill(PASSWORD);
    await page.getByLabel(/again|Repeat/i).fill(PASSWORD);
    await page.getByRole("button", { name: /Set password/i }).click();
    await page.getByText(/Your password is set/).waitFor();
    // A token of their own for the API writes the runner makes as them (PKCE, as the browser does).
    const verifier = base64Url(randomBytes(48));
    const redirectUri = `${uiUrl}/signed-in`;
    const form = await context.request.post(`${apiUrl}/oauth/authorize`, {
      form: {
        response_type: "code",
        client_id: "browser",
        redirect_uri: redirectUri,
        code_challenge: base64Url(createHash("sha256").update(verifier).digest()),
        code_challenge_method: "S256",
        state: "z6",
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
    const token = (await exchanged.json()).access_token;
    await page.goto(uiUrl);
    await page.getByRole("link", { name: "Settings" }).waitFor();
    return { ...created, context, page, token };
  }

  // Ana, Data steward in both workspaces: a rename in the default one, a change set in the second,
  // and enough renames for a second page of her changes.
  const ana = await person("ana", "Ana Varga", [
    ["steward", { workspaceKey: "default" }],
    ["steward", { workspaceKey: SECOND.key }],
  ]);
  let current = await as(ana.token, `/objects/${table.type.key}/${record.id}?workspaceKey=default`);
  current = await as(
    ana.token,
    `/objects/${table.type.key}/${record.id}`,
    { expectedVersion: current.version, name: `${record.name} (checked)` },
    "PATCH",
  );
  // Fifty-five more, over the type's other records in turn (each rename takes its record's new version).
  const others = records.slice(1).length ? records.slice(1) : [current];
  const versions = new Map(others.map((item) => [item.id, item.version]));
  for (let index = 0; index < 55; index++) {
    const item = others[index % others.length];
    const renamed = await as(
      ana.token,
      `/objects/${table.type.key}/${item.id}`,
      { expectedVersion: versions.get(item.id), name: `${item.name} · ${index}` },
      "PATCH",
    );
    versions.set(item.id, renamed.version);
  }
  if (others[0].id === record.id) current = { version: versions.get(record.id) };
  const spring = await as(ana.token, `/workspaces/${SECOND.key}/change-sets`, {
    name: "Spring work",
    source: "currentLive",
  });
  // A client, Data steward in the default workspace, renames the same record next.
  const client = await api("/clients", { name: "Catalogue sync" });
  await api("/grants", {
    principal: { kind: "client", id: client.id },
    role: "steward",
    scope: { workspaceKey: "default" },
  });
  const clientToken = (
    await (
      await fetch(`${apiUrl}/oauth/token`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          Authorization: `Basic ${Buffer.from(`${client.id}:${client.secret}`).toString("base64")}`,
        },
        body: "grant_type=client_credentials",
      })
    ).json()
  ).access_token;
  await as(
    clientToken,
    `/objects/${table.type.key}/${record.id}`,
    { expectedVersion: current.version, name: `${record.name} (synced)` },
    "PATCH",
  );

  // 1. A Reader of the default workspace follows Ana's name from a record's history.
  const rex = await person("rex", "Rex Hill", [["reader", { workspaceKey: "default" }]]);
  let page = rex.page;
  await page.goto(`${uiUrl}/apps/${table.application.key}/objects/${table.type.key}/${record.id}?workspaceKey=default`);
  const history = page.locator(".history-panel");
  // Since 0.12 RH1 the name links from the opened entry (a line is a button of its own).
  await history
    .getByRole("button", { name: /Ana Varga/ })
    .first()
    .click();
  await history.getByRole("link", { name: "Ana Varga: their changes" }).first().click();
  await page.getByRole("heading", { level: 1, name: "Ana Varga's changes" }).waitFor();
  expect(new URL(page.url()).pathname === "/changes", `the changes page: ${page.url()}`);
  let entries = page.locator(".history-timeline li");
  await entries.first().waitFor();
  const seenByRex = await entries.allInnerTexts();
  expect(seenByRex.length === 50, `the first 50 of Ana's changes: ${seenByRex.length}`);
  expect(!seenByRex.some((text) => text.includes(SECOND.label)), "Rex sees nothing of the workspace he cannot read");
  const options = await page.getByLabel("Workspace").locator("option").allInnerTexts();
  expect(!options.includes(SECOND.label), `Rex's workspace filter offers only his: ${options.join(", ")}`);
  checks.push("a name in a record's history opens that person's changes, only in the workspaces the reader reads");
  await shot(page, "reader-wide");
  await axe(page, "z6-changes-reader");
  // An entry's title opens the record in its workspace.
  await page.getByRole("button", { name: "Show more" }).click();
  const renamed = page.getByRole("link", { name: `Updated ${record.name} (synced)` });
  await renamed.waitFor();
  await renamed.click();
  await page.getByRole("heading", { level: 1, name: `${record.name} (synced)` }).waitFor();
  checks.push("Show more continues; an entry's title opens the record it changed");
  // The client's name opens the client's changes.
  await page
    .locator(".history-panel")
    .getByRole("button", { name: /Catalogue sync \(client\)/ })
    .first()
    .click();
  await page.locator(".history-panel").getByRole("link", { name: "Catalogue sync (client): their changes" }).click();
  await page.getByRole("heading", { level: 1, name: "Catalogue sync's changes" }).waitFor();
  await page.getByText("Client · newest first, in the workspaces you can read").waitFor();
  checks.push("a client's name in the history opens its changes, marked as a client's");
  await rex.context.close();

  // 2. Ana on Home: Your recent changes, then all of them, across both workspaces.
  page = ana.page;
  await page.goto(uiUrl);
  const recent = page.getByRole("region", { name: "Your recent changes" });
  await recent.waitFor();
  await recent.getByText("Created change set “Spring work”").waitFor();
  expect((await recent.locator(".home-change").count()) === 5, "Home shows the five latest");
  await shot(page, "home-recent");
  await axe(page, "z6-home-recent");
  await recent.getByRole("link", { name: "See all your changes" }).click();
  await page.getByRole("heading", { level: 1, name: "Your changes" }).waitFor();
  entries = page.locator(".history-timeline li");
  await entries.first().waitFor();
  const all = await entries.allInnerTexts();
  expect(
    all.some((text) => text.includes(SECOND.label)),
    "Ana's own include the second workspace",
  );
  expect(
    all.some((text) => text.includes(table.type.name)),
    "a record's type named from its model",
  );
  checks.push("Home lists the five latest changes; See all opens Your changes across both workspaces");

  // 3. Filters narrow the list and keep it in the address.
  await page.getByLabel("Workspace").selectOption({ label: SECOND.label });
  await page.waitForURL(/workspace=branch-b/);
  await page.getByRole("link", { name: "Created change set “Spring work”" }).waitFor();
  expect((await entries.count()) === 1, `one change in ${SECOND.label}: ${await entries.count()}`);
  await page.getByRole("link", { name: "Created change set “Spring work”" }).click();
  await page.waitForURL(new RegExp(`/change-sets/${spring.id}/changes`));
  await page.goBack();
  await page.getByLabel("Workspace").selectOption({ label: "All workspaces" });
  await page.getByLabel("What").selectOption({ label: "Change sets" });
  await page.waitForURL(/kind=change-set/);
  await page.waitForFunction(() => document.querySelectorAll(".history-timeline li").length === 1);
  await page.getByLabel("What").selectOption({ label: "Everything" });
  await page.getByLabel("Period").selectOption({ label: "Last 24 hours" });
  await page.waitForURL(/period=day/);
  await page.getByRole("button", { name: "Show more" }).waitFor();
  checks.push(
    "workspace, kind and period narrow the list and stay in the address; a change set entry opens its review",
  );

  // 4. Keyboard: from the filters through the timeline's links to Show more.
  await page.getByLabel("Workspace").focus();
  let reached = false;
  for (let stops = 0; stops < 150 && !reached; stops++) {
    await page.keyboard.press("Tab");
    reached = await page.evaluate(() => document.activeElement?.textContent?.trim() === "Show more");
  }
  expect(reached, "Tab reaches Show more from the filters");
  await page.keyboard.press("Enter");
  await page.waitForFunction(() => document.querySelectorAll(".history-timeline li").length > 50);
  checks.push("keyboard: Tab from the filters reaches Show more; Enter loads the next page");
  await dark(page);
  await shot(page, "own-wide-dark");
  await axe(page, "z6-changes-dark");
  await ana.context.close();

  // 5. 390px: the filters stack, no horizontal page scroll.
  const small = await person("nora", "Nora Field", [["reader", { instance: true }]], 390);
  await small.page.goto(`${uiUrl}/changes?actorId=${ana.id}`);
  await small.page.getByRole("heading", { level: 1, name: "Ana Varga's changes" }).waitFor();
  await small.page.locator(".history-timeline li").first().waitFor();
  expect((await overflow(small.page)) <= 0, "390px: no horizontal page scroll");
  await shot(small.page, "narrow");
  await axe(small.page, "z6-changes-narrow");
  await small.context.close();
  checks.push("390px: the page and its filters fit without a horizontal scroll");

  // 6. A person's page offers See changes only to an administrator who would see something.
  const sofia = await person("sofia", "Sofia Lind", [["security-admin", { instance: true }]]);
  await sofia.page.goto(`${uiUrl}/settings/people/${ana.id}`);
  await sofia.page.getByRole("heading", { level: 1, name: "Ana Varga" }).waitFor();
  // The page's actions wait for the permissions; the Security administrator's own action shows they are in.
  await sofia.page.getByRole("button", { name: "Grant", exact: true }).waitFor();
  // See changes is an item of the page's More actions menu (PP-D63), so the menu is opened before it is looked for.
  const sofiaMore = sofia.page.getByRole("button", { name: "More actions" });
  if (await sofiaMore.count()) await sofiaMore.click();
  expect(
    (await sofia.page.getByRole("menuitem", { name: /^See changes/ }).count()) === 0,
    "no See changes without data roles",
  );
  await sofia.context.close();
  await harnessPage.goto(`${uiUrl}/settings/people/${ana.id}`);
  await harnessPage.getByRole("button", { name: "More actions" }).click();
  await harnessPage.getByRole("menuitem", { name: /^See changes/ }).click();
  await harnessPage.getByRole("heading", { level: 1, name: "Ana Varga's changes" }).waitFor();
  checks.push("See changes is offered on a person's page only to an administrator who reads data, and opens them");

  const report = { checks, failures, passed: !failures.length };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`Z6 browser evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("Z6 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
} finally {
  harness.cleanup();
}
