// 0.12 HM1 browser evidence: the home page after sign-in, against a real backend on two models (the
// starter in the default workspace, the journey configuration generated-b installed into a second
// workspace). People are made and granted through the API, set a password through their link and sign
// in on the engine's page. Signing in lands on Home; each card names its own model's applications and
// one opens its view there; after a record is opened, the product name returns Home and Continue
// reopens it; a Contributor's proposal is listed under Your change sets with its count and opens its
// review; a publisher's card counts every open change set; a Reader's card has no such count and says
// they can read; a person with no workspace sees the no-workspace text at `/`. Keyboard from Continue
// to a card's application; axe; screenshots at 1440px light and dark and 390px; no horizontal page
// scroll at 390px. Applications and types are read from each model, never named.
import { execFileSync } from "node:child_process";
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

const harness = await bootHarness();
try {
  const { uiUrl, api, output, signedOutContext } = harness;
  const overflow = (page) => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  const shot = (page, name) => page.screenshot({ path: resolve(output, `hm1-${name}.png`), fullPage: true });
  const dark = goDark;
  const seen = (page, locator) =>
    locator.waitFor().catch(async (error) => {
      console.error(`${page.url()}\n${(await page.locator("body").innerText()).slice(0, 1500)}`);
      throw error;
    });

  // Setup: generated-b installed and a second workspace on it.
  const b = structuredClone(generatedB);
  b.schemaVersion = "0.10";
  const draft = await api("/model-drafts", { name: "Second model", model: b });
  const release = await api(`/model-drafts/${draft.id}/installation`, { expectedVersion: draft.version });
  await api("/workspaces", { ...SECOND, modelReleaseId: release.id });
  const models = {
    default: await api("/model?workspaceKey=default"),
    [SECOND.key]: await api(`/model?workspaceKey=${SECOND.key}`),
  };
  const defaultLabel = (await api("/workspaces/default")).label;
  const table = models.default.applications
    .flatMap((application) =>
      application.views
        .filter((view) => view.type === "table" && view.objectTypeKey)
        .map((view) => ({
          application,
          view,
          type: models.default.objectTypes.find((item) => item.key === view.objectTypeKey),
        })),
    )
    .find(Boolean);
  const record = (
    await api(`/objects/${table.type.key}?workspaceKey=default&pageSize=1&applicationKey=${table.application.key}`)
  ).items[0];
  // Someone else's open change set in the second workspace, which its publisher's card counts.
  await api(`/workspaces/${SECOND.key}/change-sets`, { name: "Another's work", source: "currentLive" });

  /** A person granted `grants`, signed in in a context of their own at `width`. */
  async function person(username, grants, width = 1440) {
    const created = await api("/users", { email: `${username}@example.org`, name: `${username[0].toUpperCase()}${username.slice(1)} Varga` });
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
    await page.goto(uiUrl);
    await page.getByRole("heading", { level: 1, name: "Sign in" }).waitFor();
    await page.getByLabel("E-mail address").fill(created.email);
    await page.getByLabel("Password").fill(PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();
    await page.waitForURL(
      (address) => !address.pathname.startsWith("/oauth") && !address.pathname.startsWith("/signed-in"),
    );
    await page.getByRole("link", { name: "Settings" }).waitFor();
    return { ...created, context, page };
  }
  const card = (page, label) =>
    page.locator(".home-card").filter({ has: page.getByRole("heading", { level: 3, name: label }) });
  const appNames = async (page, label) =>
    (await card(page, label).locator(".home-app").allInnerTexts()).map((text) => text.trim());

  // 1. Signing in lands on Home: the default workspace first, each card on its own model.
  const ana = await person("ana", [
    ["contributor", { workspaceKey: "default" }],
    ["steward", { workspaceKey: SECOND.key }],
  ]);
  let page = ana.page;
  await seen(page, page.getByRole("heading", { level: 1, name: /^Good (morning|afternoon|evening), Ana$/ }));
  expect(new URL(page.url()).pathname === "/", `Home at the bare address: ${page.url()}`);
  const labels = await page.locator(".home-card h3").allInnerTexts();
  expect(
    labels[0].startsWith(defaultLabel) && labels[0].includes("Default"),
    `the default first: ${labels.join(" | ")}`,
  );
  expect(labels.length === 2, `two cards: ${labels.join(" | ")}`);
  for (const [key, label] of [
    ["default", defaultLabel],
    [SECOND.key, SECOND.label],
  ])
    expect(
      JSON.stringify(await appNames(page, label)) === JSON.stringify(models[key].applications.map((item) => item.name)),
      `${label}'s card names its own model's applications: ${(await appNames(page, label)).join(", ")}`,
    );
  expect(
    JSON.stringify(await appNames(page, defaultLabel)) !== JSON.stringify(await appNames(page, SECOND.label)),
    "the two cards name different applications",
  );
  // A publisher's card counts every open change set; a Contributor's only their own.
  await card(page, SECOND.label).getByText("open change set to publish").waitFor();
  expect(
    (await card(page, defaultLabel)
      .getByText(/open change sets? to publish/)
      .count()) === 0,
    "no publish count where Ana proposes",
  );
  await card(page, defaultLabel).getByText("Propose a change from any record.").waitFor();
  checks.push(
    "signing in lands on Home; the default first; each card names its own model's applications; counts follow the role",
  );
  await shot(page, "home-wide");
  await axe(page, "hm1-home-wide");

  // 2. An application on the second card opens its view in that workspace.
  await card(page, SECOND.label).locator(".home-app").first().click();
  await page.waitForURL(new RegExp(`workspaceKey=${SECOND.key}`));
  // The band no longer repeats the workspace (0.17 SH1); the workspace selector names it.
  await page.waitForFunction(
    (label) =>
      [...document.querySelectorAll(".workspace-selector input, .workspace-selector strong")].some((element) =>
        (element.value ?? element.textContent ?? "").includes(label),
      ),
    SECOND.label,
  );
  checks.push("an application on a card opens its view in that card's workspace");
  // The workspace's name opens the workspace at its start (D339).
  await page.getByRole("button", { name: /home$/ }).click();
  await card(page, SECOND.label).getByRole("link", { name: SECOND.label, exact: true }).click();
  await page.waitForURL(new RegExp(`workspaceKey=${SECOND.key}`));
  await page.getByRole("heading", { level: 1 }).filter({ hasText: SECOND.label }).first().waitFor();
  checks.push("a workspace's name on its card opens the workspace at its start");

  // 3. A record opened, the product name returns Home, Continue reopens the record.
  await page.goto(`${uiUrl}/apps/${table.application.key}/objects/${table.type.key}/${record.id}?workspaceKey=default`);
  await page.getByRole("heading", { level: 1, name: record.name }).waitFor();
  await page.getByRole("button", { name: /home$/ }).click();
  await page.waitForURL((address) => address.pathname === "/" && !address.search);
  const resume = page.locator(".home-continue");
  await resume.getByText(record.name, { exact: true }).waitFor();
  await resume.getByText(`${table.type.name} in ${defaultLabel}`).waitFor();
  await resume.click();
  await page.getByRole("heading", { level: 1, name: record.name }).waitFor();
  checks.push("the product name returns Home; Continue names the record and reopens it");

  // 4. A Contributor's proposal is listed with its count and opens its review.
  await page.getByRole("button", { name: "Propose a change" }).click();
  const dialog = page.getByRole("dialog", { name: "Propose a change" });
  await dialog.getByRole("button", { name: "Start and edit" }).click();
  await dialog.waitFor({ state: "detached" });
  // The record's form opens in the new change set (Z5, D324); closed unchanged.
  await page.getByRole("dialog").first().waitFor();
  await page.keyboard.press("Escape");
  await page.getByRole("dialog").waitFor({ state: "detached" });
  await page.getByRole("button", { name: /home$/ }).click();
  await page.waitForURL((address) => address.pathname === "/");
  const ownList = page.getByRole("region", { name: "Your change sets" });
  const row = ownList.locator(".home-change-set").filter({ hasText: "Changes by Ana Varga" });
  await row.waitFor();
  await row.getByText(/\d+ changes?/).waitFor();
  await card(page, defaultLabel).getByText("your change set", { exact: true }).waitFor();
  await shot(page, "home-with-change-set");
  await row.locator("a").click();
  await page.waitForURL(/\/change-sets\/[^/]+\/changes/);
  checks.push("a Contributor's change set is listed with its count, counted on its card, and opens its review");

  // 5. Keyboard: from Continue to a card's application, opened with Enter.
  await page.goto(uiUrl);
  await page.locator(".home-card").first().waitFor();
  const focused = () => page.evaluate(() => document.activeElement?.className ?? "");
  let stops = 0;
  const order = [];
  while (stops++ < 40) {
    await page.keyboard.press("Tab");
    const name = await focused();
    order.push(name);
    if (String(name).includes("home-app")) break;
  }
  expect(
    order.some((name) => String(name).includes("home-continue")),
    `Continue is reached by Tab: ${order.join(" > ")}`,
  );
  expect(String(order.at(-1)).includes("home-app"), `a card's application is reached by Tab: ${order.join(" > ")}`);
  await page.keyboard.press("Enter");
  await page.waitForURL(/\/apps\//);
  checks.push("keyboard: Tab reaches Continue then a card's application; Enter opens it");

  // 6. Dark, and 390px without a horizontal page scroll.
  await page.goto(uiUrl);
  await page.locator(".home-card").first().waitFor();
  await dark(page);
  await shot(page, "home-wide-dark");
  await axe(page, "hm1-home-wide-dark");
  await ana.context.close();

  // 7. A Reader with one workspace: no open count, a note that they read, no change sets section.
  const reader = await person("tamas", [["reader", { workspaceKey: "default" }]], 390);
  page = reader.page;
  await card(page, defaultLabel).getByText("You can read this workspace.").waitFor();
  expect((await page.locator(".home-card").count()) === 1, "a Reader with one workspace has one card");
  expect((await page.getByText(/open change sets? to publish/).count()) === 0, "a Reader's card has no publish count");
  expect((await page.getByRole("region", { name: "Your change sets" }).count()) === 0, "no change sets section");
  expect((await overflow(page)) <= 0, "390px: no horizontal page scroll");
  await shot(page, "home-reader-narrow");
  await axe(page, "hm1-home-reader-narrow");
  await reader.context.close();
  checks.push("a Reader's one card has no publish count and says they can read; 390px without horizontal scroll");

  // 8. No workspace: the no-workspace text at the bare address.
  const security = await person("sofia", [["security-admin", { instance: true }]]);
  await security.page.getByRole("heading", { level: 1, name: "There is no workspace you can open yet" }).waitFor();
  expect(new URL(security.page.url()).pathname === "/", `no workspace at the bare address: ${security.page.url()}`);
  // The top bar names the instance's product, not the release (D338).
  const mark = await security.page.locator(".product-mark").getAttribute("aria-label");
  expect(
    mark === `${models.default.product.name} home`,
    `no workspace: the product mark reads "${mark}", not "${models.default.product.name} home"`,
  );
  await security.context.close();
  checks.push("a person with no workspace sees the no-workspace text at / under the instance's product name");

  const report = { checks, failures, passed: !failures.length };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`HM1 browser evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("HM1 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
} finally {
  harness.cleanup();
}
