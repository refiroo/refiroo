// 0.16 AP12 browser evidence: "Change this model…" from the workspace and the records that move with the model,
// against a real backend with a stand-in for the Claude Code session (`helpers/reshape-stand-in.py`, set as
// AI_AGENT_COMMAND), on the starter and on generated-b (the runner derives its probe types from whichever model it
// booted on and names none of their keys). As the harness person: the workspace ⋯ menu offers Change this model…
// (by keyboard on the starter, by pointer on generated-b) and the dialog fixes the workspace, asks for the words
// first and the workbook second; the proposal's table says what happens to the records from the engine's counts;
// accepting installs the new model and leaves the records where they were; Preview the migration opens the
// existing migration page with the assistant's choices and Back to the proposal returns; the migration moves
// every record with its ID and values; the three steps of a part-of-a-type move are each shown when they can
// be done. Light and dark, 1440px and 390px without sideways scroll, axe on each state. Then a backend with no
// assistant offers no item.
import assert from "node:assert/strict";
import { writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { bootShaped, SHAPED_MODELS } from "./helpers/shaped-models.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { goDark } from "./helpers/theme.mjs";
import { workspaceAction } from "./helpers/workspaceMenu.mjs";

const root = resolve(import.meta.dirname, "..", "..");
const PLAN = resolve(tmpdir(), `ap12-plan-${process.pid}.json`);
const SESSION = `${resolve(root, "backend/.venv/bin/python")} ${resolve(import.meta.dirname, "helpers/reshape-stand-in.py")} ${PLAN}`;
const checks = [];

async function accessible(target, name) {
  const result = await runAxe(target, [], name);
  assert.equal(result.violations.length, 0, formatViolations(result.violations));
  checks.push(`axe ${name}: 0 violations`);
}
const overflow = (target) => target.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);

const LABEL = "zz-shape-label";
const NOTE = "zz-shape-note";
const EXTRA = "zz-shape-extra";

/** The booted model with types added to its first application, named by nothing in either model. */
function shaped(source, tag, types) {
  const model = structuredClone(source);
  model.schemaVersion = "0.10";
  for (const key of [LABEL, NOTE, EXTRA])
    if (!model.attributeTypes.some((item) => item.key === key)) model.attributeTypes.push({ key, name: key });
  const application = model.applications[0];
  for (const [key, name, attributes] of types) {
    model.objectTypes.push({
      key,
      name,
      pluralName: `${name}s`,
      displayAttributeTypeKey: LABEL,
      attributes: attributes.map((attributeTypeKey, n) => ({ attributeTypeKey, order: 10 * (n + 1) })),
      features: { rootCreatable: true },
    });
    application.objectTypeKeys.push(key);
  }
  model.release = { ...model.release, version: `${model.release.version}-${tag}` };
  return model;
}

async function release(api, model, name) {
  const draft = await api("/model-drafts", { name, model });
  return (await api(`/model-drafts/${draft.id}/installation`, { expectedVersion: draft.version })).id;
}

async function workspaceOn(api, key, releaseId) {
  await api("/workspaces", { key, label: `Shape ${key}`, modelReleaseId: releaseId });
}

async function record(api, application, workspaceKey, objectTypeKey, name, values) {
  return api("/objects", {
    workspaceKey,
    applicationKey: application,
    objectTypeKey,
    name,
    attributes: Object.entries(values).map(([attributeTypeKey, value]) => ({ attributeTypeKey, value })),
  });
}

async function inventory(api, workspaceKey, types) {
  const found = {};
  for (const type of types) {
    const listed = await api(`/objects/${type}?workspaceKey=${workspaceKey}&pageSize=100`).catch(() => ({ items: [] }));
    for (const item of listed.items) {
      const full = await api(`/objects/${type}/${item.id}?workspaceKey=${workspaceKey}`);
      found[item.id] = {
        type,
        name: full.name,
        values: Object.fromEntries(full.attributes.map((a) => [a.attributeTypeKey, a.value])),
      };
    }
  }
  return found;
}

async function asking(page, uiUrl, application, workspaceKey, words, keyboard, shot) {
  await page.emulateMedia({ colorScheme: "light" });
  await page.goto(`${uiUrl}/apps/${application.key}/views/${application.defaultView}?workspaceKey=${workspaceKey}`);
  await workspaceAction(page, "Change this model…", { keyboard });
  const dialog = page.getByRole("dialog", { name: "Change this model" });
  await dialog.waitFor();
  assert.equal(await dialog.getByLabel("Into").count(), 0, "the workspace is fixed");
  assert.equal(await dialog.getByRole("button", { name: /Import without the assistant/ }).count(), 0);
  assert.equal(
    await dialog.getByRole("button", { name: "Ask the assistant" }).isDisabled(),
    true,
    "the words are required",
  );
  const order = await dialog.evaluate((node) =>
    [...node.querySelectorAll("label")].map((label) => label.textContent.trim()).slice(0, 2),
  );
  assert.match(order[0], /What should change\?/);
  assert.match(order[1], /A workbook \(optional\)/);
  await dialog.getByLabel("What should change?").fill(words);
  await shot("dialog");
  await accessible(page, "ap12-dialog");
  await dialog.getByRole("button", { name: "Ask the assistant" }).click();
  await page.waitForURL(/\/settings\/ai-tasks\//);
}

async function scenario(configuration, index) {
  const label = configuration.name;
  const keyboard = index === 0;
  const harness = await bootShaped(configuration, { backendEnv: { AI_AGENT_COMMAND: SESSION } });
  const { page, api, uiUrl, output } = harness;
  const shot = (name) => page.screenshot({ path: resolve(output, `ap12-${label}-${name}.png`), fullPage: true });
  try {
    const base = await api("/model");
    const application = base.applications[0];
    const t = (name) => `zz-${name}`;

    // ---- whole types: a merge by one migration ----
    const merged = shaped(base, "merge-1", [
      [t("supplier"), "Supplier", [LABEL, NOTE]],
      [t("vendor"), "Vendor", [LABEL, EXTRA]],
    ]);
    const mergedFinal = shaped(base, "merge-2", [[t("partner"), "Partner", [LABEL, NOTE, EXTRA]]]);
    const first = await release(api, merged, "Suppliers and vendors");
    await workspaceOn(api, "merge-ws", first);
    for (let n = 0; n < 3; n++)
      await record(api, application.key, "merge-ws", t("supplier"), `Supplier ${n}`, {
        [LABEL]: `S${n}`,
        [NOTE]: `note ${n}`,
      });
    for (let n = 0; n < 2; n++)
      await record(api, application.key, "merge-ws", t("vendor"), `Vendor ${n}`, {
        [LABEL]: `V${n}`,
        [EXTRA]: `extra ${n}`,
      });
    const before = await inventory(api, "merge-ws", [t("supplier"), t("vendor")]);
    assert.equal(Object.keys(before).length, 5);
    await writeFile(
      PLAN,
      JSON.stringify({
        mode: "merge",
        workspace: "merge-ws",
        final: mergedFinal,
        summary: "Suppliers and Vendors become one type, Partners, with every attribute either had.",
        moves: [
          { from: t("supplier"), to: t("partner") },
          { from: t("vendor"), to: t("partner") },
        ],
      }),
    );
    await asking(
      page,
      uiUrl,
      application,
      "merge-ws",
      "Suppliers and vendors are the same thing. Make them one type, Partners.",
      keyboard,
      shot,
    );
    checks.push(
      `${label}: Change this model… on the workspace menu opens the dialog with the workspace fixed and the words first`,
    );

    await page.getByText("What happens to the records").waitFor();
    const table = page.getByRole("group", { name: "Types that become others" });
    assert.equal(await table.getByRole("row").count(), 3, "a head and two moves");
    assert.match(await table.innerText(), /Supplier[\s\S]*Partner[\s\S]*3/);
    assert.match(await table.innerText(), /Vendor[\s\S]*Partner[\s\S]*2/);
    assert.match(await page.locator("main").innerText(), /5 records keep their IDs, history and relationships/);
    assert.equal(await page.getByRole("heading", { name: "Load a workbook" }).count(), 0);
    assert.match(await page.locator("body").innerText(), /Change this model/);
    await shot("proposal");
    await accessible(page, `ap12-${label}-proposal`);
    await goDark(page);
    await shot("proposal-dark");
    await accessible(page, `ap12-${label}-proposal-dark`);
    await page.emulateMedia({ colorScheme: "light" });
    await page.evaluate(() => delete document.documentElement.dataset.theme);
    const phone = await page.context().newPage();
    await phone.setViewportSize({ width: 390, height: 844 });
    await phone.goto(page.url());
    await phone.getByText("What happens to the records").waitFor();
    assert.ok((await overflow(phone)) <= 0, `${label}: the proposal overflows at 390px`);
    await phone.screenshot({ path: resolve(output, `ap12-${label}-proposal-390.png`), fullPage: true });
    await accessible(phone, `ap12-${label}-proposal-390`);
    await phone.close();
    checks.push(`${label}: the proposal tables each type's records from the engine's counts; dark, 390px, axe`);

    const taskUrl = page.url();
    await page.getByLabel("The assistant’s proposal").getByRole("button", { name: "Accept the model" }).click();
    await page.getByText("The new model is ready").waitFor();
    assert.deepEqual(
      await inventory(api, "merge-ws", [t("supplier"), t("vendor")]),
      before,
      "nothing moved at acceptance",
    );
    await shot("accepted");
    await accessible(page, `ap12-${label}-accepted`);
    const preview = page.getByRole("button", { name: "Preview the migration" });
    await preview.waitFor();
    await preview.click();
    await page.waitForURL(/\/settings\/model\/migrations\//);
    await page.getByRole("button", { name: "Back to the proposal" }).first().waitFor();
    await page
      .getByText(/Supplier/)
      .first()
      .waitFor();
    await shot("migration");
    await accessible(page, `ap12-${label}-migration`);
    await page.getByRole("button", { name: "Back to the proposal" }).first().click();
    await page.waitForURL(taskUrl);
    await page.getByRole("button", { name: "Preview the migration" }).click();
    await page.waitForURL(/\/settings\/model\/migrations\//);
    const migrate = page.getByRole("button", { name: /^Migrate / });
    await migrate.waitFor();
    if (keyboard) {
      await migrate.focus();
      await page.keyboard.press("Enter");
    } else await migrate.click();
    await page.getByRole("button", { name: "Back to the proposal" }).first().waitFor();
    await page
      .getByText(/changed type/)
      .first()
      .waitFor();
    await shot("migrated");
    await page.getByRole("button", { name: "Back to the proposal" }).first().click();
    await page.waitForURL(taskUrl);
    await page.getByText(/runs the new model/).waitFor();
    const after = await inventory(api, "merge-ws", [t("partner")]);
    assert.deepEqual(Object.keys(after).sort(), Object.keys(before).sort(), "every ID kept");
    for (const [id, was] of Object.entries(before)) {
      assert.equal(after[id].name, was.name);
      assert.deepEqual(after[id].values, was.values);
    }
    await shot("done");
    checks.push(
      `${label}: acceptance moves nothing; the migration page opens with the choices, Back to the proposal returns; the migration moves 5 records with IDs and values kept`,
    );

    // ---- part of a type: the three steps ----
    const items = shaped(base, "split-1", [[t("item"), "Item", [LABEL, NOTE]]]);
    const two = [
      [t("part"), "Part", [LABEL, NOTE]],
      [t("service"), "Service", [LABEL, NOTE]],
    ];
    const both = shaped(base, "split-2", [[t("item"), "Item", [LABEL, NOTE]], ...two]);
    const final = shaped(base, "split-3", two);
    await workspaceOn(api, "split-ws", await release(api, items, "Items"));
    for (let n = 0; n < 4; n++)
      await record(api, application.key, "split-ws", t("item"), `Item ${n}`, {
        [LABEL]: `I${n}`,
        [NOTE]: n % 2 ? "service" : "part",
      });
    const itemsBefore = await inventory(api, "split-ws", [t("item")]);
    await writeFile(
      PLAN,
      JSON.stringify({
        mode: "parts",
        workspace: "split-ws",
        final,
        both,
        from: t("item"),
        note: NOTE,
        targets: { part: t("part"), service: t("service") },
        summary: "Items split into Parts and Services by their note.",
      }),
    );
    await asking(
      page,
      uiUrl,
      application,
      "split-ws",
      "Split the items into parts and services by their note.",
      !keyboard,
      shot,
    );
    await page.getByLabel("The assistant’s proposal").getByRole("button", { name: "Accept the model" }).waitFor();
    assert.equal(await page.getByText("What happens to the records").count(), 0, "no whole type moves here");
    await page.getByLabel("The assistant’s proposal").getByRole("button", { name: "Accept the model" }).click();
    await page.getByRole("heading", { name: "Three steps are yours" }).waitFor();
    assert.equal(
      await page.getByRole("button", { name: "Review the change set" }).count(),
      0,
      "step 2 waits for step 1",
    );
    const open = page.getByRole("button", { name: "Open the release" });
    assert.equal(await open.count(), 1, "only step 1 can be done");
    await shot("steps-1");
    await accessible(page, `ap12-${label}-steps-1`);
    const phone2 = await page.context().newPage();
    await phone2.setViewportSize({ width: 390, height: 844 });
    await phone2.goto(page.url());
    await phone2.getByRole("heading", { name: "Three steps are yours" }).waitFor();
    assert.ok((await overflow(phone2)) <= 0, `${label}: the steps overflow at 390px`);
    await phone2.screenshot({ path: resolve(output, `ap12-${label}-steps-390.png`), fullPage: true });
    await accessible(phone2, `ap12-${label}-steps-390`);
    await phone2.close();
    const taskPage = page.url();
    assert.deepEqual(await inventory(api, "split-ws", [t("item")]), itemsBefore, "live data is unchanged");
    await open.click();
    await page.waitForURL(/\/settings\/model\/releases\//);
    const bothId = page.url().split("/releases/")[1].split(/[?#]/)[0];
    const activate = async (releaseId) => {
      const current = await api("/workspaces/split-ws/model");
      await api("/workspaces/split-ws/model/activation", {
        releaseId,
        expectedVersion: current.version,
        expectedReleaseId: current.releaseId,
      });
    };
    await activate(bothId);
    await page.goto(taskPage);
    await page.getByRole("button", { name: "Review the change set" }).waitFor();
    assert.equal(
      await page.getByRole("button", { name: "Open the release" }).count(),
      0,
      "step 3 waits for the publication",
    );
    await shot("steps-2");
    await page.getByRole("button", { name: "Review the change set" }).click();
    await page.waitForURL(/\/change-sets\//);
    const changeSetId = page.url().match(/change-sets\/([^/]+)/)[1];
    const changeSet = await api(`/change-sets/${changeSetId}`);
    await api(`/change-sets/${changeSetId}/publication`, {
      expectedChangeSetVersion: changeSet.version,
      expectedActivePublicationId: null,
    });
    await page.goto(taskPage);
    await page.getByRole("button", { name: "Open the release" }).waitFor();
    assert.equal(await page.getByRole("button", { name: "Review the change set" }).count(), 0);
    await shot("steps-3");
    const live = await inventory(api, "split-ws", [t("part"), t("service")]);
    assert.deepEqual(Object.keys(live).sort(), Object.keys(itemsBefore).sort(), "every ID kept under the new types");
    const finalId = (await api("/model-releases?pageSize=200")).items.find(
      (r) => r.version === final.release.version,
    ).id;
    await activate(finalId);
    await page.goto(taskPage);
    await page.getByText(/runs the release you accepted/).waitFor();
    assert.equal(await page.getByRole("button", { name: "Open the release" }).count(), 0);
    await shot("steps-done");
    await accessible(page, `ap12-${label}-steps-done`);
    checks.push(
      `${label}: the three steps appear one at a time (activate both shapes, review and publish, activate the final release); 4 records keep their IDs under the new types`,
    );
  } catch (error) {
    await page.screenshot({ path: resolve(output, `ap12-${label}-failure.png`), fullPage: true }).catch(() => {});
    console.error(harness.log().slice(-3000));
    throw error;
  } finally {
    harness.cleanup();
  }
  console.log(`Screenshots (AP12 ${label}): ${output}`);
}

async function withoutAssistant() {
  const harness = await bootHarness({});
  const { page, uiUrl } = harness;
  try {
    const base = await harness.api("/model");
    const application = base.applications[0];
    // The system and the permissions are read before a missing item means anything.
    const system = page.waitForResponse((a) => new URL(a.url()).pathname === "/api/v1/system" && a.ok());
    const permissions = page.waitForResponse((a) => new URL(a.url()).pathname === "/api/v1/me/permissions" && a.ok());
    await page.goto(`${uiUrl}/apps/${application.key}/views/${application.defaultView}?workspaceKey=default`);
    const trigger = page.getByRole("button", { name: "Workspace actions" });
    await trigger.waitFor();
    await trigger.click();
    await page.getByRole("menuitem", { name: "Edit model" }).waitFor();
    await Promise.all([system, permissions]);
    assert.equal(await page.getByRole("menuitem", { name: "Change this model…" }).count(), 0);
    checks.push("without AI_AGENT_COMMAND the workspace menu has no Change this model…");
  } finally {
    harness.cleanup();
  }
}

try {
  let index = 0;
  for (const configuration of SHAPED_MODELS) await scenario(configuration, index++);
  await withoutAssistant();
  console.log(`AP12 change this model: ${checks.length} checks passed`);
  for (const check of checks) console.log(`- ${check}`);
} catch (error) {
  console.error("AP12 browser evidence failed:", error);
  process.exitCode = 1;
}
