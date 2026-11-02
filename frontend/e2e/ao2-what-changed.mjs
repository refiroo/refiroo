// 0.16 AO2 browser evidence (J56): What changed, the account of a period above a workspace's Activity and
// on a record's History, against a real backend whose provider is a stand-in (`helpers/ask_stand_in.py`;
// nothing leaves the process), on two models: the starter (send level values) and generated-b (structure). It
// names no key of either.
//
// A workspace's records are changed directly, by a batch job and by a change set that is published, and a second
// change set is left open. Then, on each model:
//  1. Activity at 1440px by keyboard: before asking the line says what is sent (names at values, none at
//     structure) and no call is made; Explain this period words the facts, the numbers lead to their facts, the
//     facts are all listed, each says where it leads.
//  2. Show them narrows the list in place under the banner to the changes the fact counted (the same number the
//     API lists), and Show all activity brings the rest back.
//  3. The provider fails: the facts stand alone, Try again words them. A statement with no source is dropped.
//  4. Chosen dates: a period with no change says so and sends nothing.
//  5. A record's History: the same section, the fact narrows the timeline to the live changes of its kind.
//  6. At 390px: no horizontal scroll, the same states. Axe on each state, light and dark.
// Without a provider the Activity has no section. No console error or 4xx/5xx; screenshots in the run's folder
// (inspect them against the mock-up).
import assert from "node:assert/strict";
import { rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { bootHarness } from "./helpers/harness.mjs";
import { watchErrors } from "./helpers/person.mjs";
import { bootShaped, SHAPED_MODELS, startingPoint } from "./helpers/shaped-models.mjs";
import { goDark } from "./helpers/theme.mjs";

const checks = [];

async function accessible(page, name) {
  const result = await runAxe(page, [], name);
  assert.equal(result.violations.length, 0, formatViolations(result.violations));
  checks.push(`axe ${name}: 0 violations`);
}

const noOverflow = (page, name) =>
  page
    .evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)
    .then((fits) => {
      assert.equal(fits, true, `${name}: no horizontal page scroll`);
    });

/** The records of the table, with their current versions. */
const current = async (api, application, type) =>
  (await api(`/objects/${type.key}?workspaceKey=default&pageSize=20&applicationKey=${application.key}`)).items;

/** Changes made directly, by a job and by a published change set; another change set left open. */
async function changed(api, { application, type, model }) {
  const text = type.attributes
    ?.map((binding) => model.attributeTypes.find((item) => item.key === binding.attributeTypeKey))
    .find((kind) => kind?.valueType === "text" && !kind.features?.unique);
  let records = await current(api, application, type);
  for (const [index, record] of records.slice(0, 3).entries()) {
    await api(
      `/objects/${type.key}/${record.id}`,
      {
        expectedVersion: record.version,
        name: `${record.name} direct`,
        ...(text && index < 2
          ? { attributes: [{ attributeTypeKey: text.key, value: `direct ${index} ${Date.now()}` }] }
          : {}),
      },
      "PATCH",
    );
  }
  records = await current(api, application, type);
  await api("/batches", {
    policy: "independent",
    run: "inline",
    workspaceKey: "default",
    items: records.slice(3, 6).map((record) => ({
      op: "update",
      target: { id: record.id },
      expectedVersion: record.version,
      name: `${record.name} by a job`,
    })),
  });
  const set = await api("/workspaces/default/change-sets", { source: "currentLive", name: "Spring labels" });
  const staged = await api(`/objects/${type.key}/${records[6].id}?workspaceKey=default&changeSetId=${set.id}`);
  const claim = (await api(`/change-sets/${set.id}`)).version;
  await api(
    `/objects/${type.key}/${records[6].id}`,
    {
      expectedVersion: staged.version,
      name: `${records[6].name} published`,
      changeSetId: set.id,
      expectedChangeSetVersion: claim,
    },
    "PATCH",
  );
  const active = (await api("/workspaces/default/publications?pageSize=1")).items.filter(
    (item) => item.status === "active",
  );
  await api(`/change-sets/${set.id}/publication`, {
    expectedChangeSetVersion: (await api(`/change-sets/${set.id}`)).version,
    expectedActivePublicationId: active[0]?.id ?? null,
  });
  await api("/workspaces/default/change-sets", { source: "currentLive", name: "Left open" });
  return records[0];
}

async function walk(configuration, level) {
  const label = configuration.name;
  const modeFile = resolve(tmpdir(), `ao2-mode-${process.pid}-${label}`);
  const harness = await bootShaped(configuration, {
    backendEnv: {
      AI_PROVIDER: "ask_stand_in:provider",
      AI_SEND_LEVEL: level,
      PYTHONPATH: resolve(import.meta.dirname, "helpers"),
      STAND_IN_MODE_FILE: modeFile,
    },
  });
  const { page, api, uiUrl, output } = harness;
  const mode = (value) => writeFile(modeFile, value);
  await mode("ok");
  const clean = watchErrors(page);
  const shot = (name) => page.screenshot({ path: resolve(output, `ao2-${label}-${name}.png`), fullPage: true });
  const calls = async () => (await api("/ai/calls")).items.filter((call) => call.purpose === "historyAccount").length;
  try {
    const table = await startingPoint(api, { count: 8 });
    const record = await changed(api, table);
    const section = page.locator(".what-changed");
    const explain = () => section.getByRole("button", { name: /^Explain (this period|again)$/ });

    for (const [tag, viewport, byKeyboard] of [
      ["1440", { width: 1440, height: 900 }, true],
      ["390", { width: 390, height: 844 }, false],
    ]) {
      const name = `${label}-${tag}`;
      await page.setViewportSize(viewport);
      await mode("ok");
      await page.goto(`${uiUrl}/settings/workspaces/default/activity`);
      await section.getByRole("heading", { name: "What changed" }).waitFor();

      // 1. Before asking, and the account.
      await explain().waitFor();
      await section
        .getByText(
          level === "values"
            ? /with the names of records, people and change sets\. Nothing is sent until you press the button/
            : /At the send level "structure": .* No names of records, people, change sets or files/,
        )
        .waitFor();
      const before = await calls();
      await page.waitForTimeout(400);
      assert.equal(await calls(), before, `${name}: nothing is sent before the person asks`);
      await accessible(page, `ao2-${name}-before`);
      await shot(`${tag}-before`);
      checks.push(`${name}: before asking the line says what is sent, and no call was made`);

      if (byKeyboard) {
        await explain().focus();
        await page.keyboard.press("Enter");
      } else await explain().click();
      await section.getByText(/Written by AI from the facts below/).waitFor();
      assert.equal(await calls(), before + 1);
      const heading = await section.getByRole("heading", { name: /^The facts \(/ }).textContent();
      assert.match(heading, /all of them\), .* to .*, live data/);
      const total = Number(heading.match(/\d+/)[0]);
      assert.ok(total >= 5, `${name}: the facts cover records, fields, sources, people and change sets (${total})`);
      const kinds = await section
        .locator(".impact-facts > li")
        .evaluateAll((items) => items.map((item) => item.dataset.kind));
      for (const wanted of ["records", "source", "people", "changeSet"])
        assert.ok(kinds.includes(wanted) || total > 10, `${name}: a ${wanted} fact is listed`);
      await accessible(page, `ao2-${name}-account`);
      await shot(`${tag}-account`);
      await noOverflow(page, name);
      // A number leads to its fact.
      const cite = section.locator(".impact-statements button").first();
      await cite.focus();
      if (byKeyboard) await page.keyboard.press("Enter");
      else await cite.click();
      await page.waitForFunction(() => document.activeElement?.closest(".impact-facts") !== null);
      checks.push(`${name}: the account cites facts (${total}), a number lands on its fact`);

      // 2. Show them narrows the list in place.
      const show = section
        .locator(".impact-facts > li")
        .first()
        .getByRole("button", { name: /^Show (it|them)$/ });
      await show.focus();
      if (byKeyboard) await page.keyboard.press("Enter");
      else await show.click();
      const banner = page.locator(".scope-banner");
      await banner.getByText(/^Narrowed by: /).waitFor();
      await page.locator(".workspace-activity .activity-list").first().waitFor();
      await accessible(page, `ao2-${name}-narrowed`);
      await shot(`${tag}-narrowed`);
      await banner.getByRole("button", { name: "Show all activity" }).click();
      await page.waitForFunction(() => document.querySelector(".scope-banner") === null);
      checks.push(`${name}: Show them narrows the list under a banner, Show all activity brings it back`);
      if (tag === "1440") {
        await goDark(page);
        await accessible(page, `ao2-${name}-account-dark`);
        await shot(`${tag}-account-dark`);
        await page.emulateMedia({ colorScheme: "light" });
        await page.evaluate(() => (document.documentElement.dataset.theme = "light"));
      }

      // 3. The provider fails; a statement with no source.
      await mode("fail");
      await explain().click();
      await section.getByText(/The account could not be written/).waitFor();
      await section.getByText(/The provider could not be reached. The facts below do not depend on it/).waitFor();
      assert.equal(await section.getByText(/Written by AI/).count(), 0);
      await accessible(page, `ao2-${name}-failed`);
      await shot(`${tag}-failed`);
      await mode("ok");
      await section.getByRole("button", { name: "Try again" }).click();
      await section.getByText(/Written by AI from the facts below/).waitFor();
      await mode("unsourced");
      await explain().click();
      await section.getByText(/1 statement removed: no source\./).waitFor();
      assert.equal(await section.getByText("Nothing backs this.").count(), 0);
      checks.push(
        `${name}: a failing provider leaves the facts alone and Try again words them; a statement with no source is dropped`,
      );

      // 4. A period with no change.
      await mode("ok");
      await section.getByRole("combobox", { name: "Period" }).selectOption("dates");
      assert.equal(await section.getByText(/Written by AI/).count(), 0, `${name}: a new period clears the account`);
      await section.getByLabel("From").fill("2020-01-01");
      await section.getByLabel("To, included").fill("2020-01-15");
      const asked = await calls();
      await explain().click();
      await section.getByText(/Nothing changed in this workspace between .* Nothing was sent to the AI/).waitFor();
      assert.equal(await calls(), asked, `${name}: an empty period makes no call`);
      await shot(`${tag}-empty`);
      checks.push(`${name}: a period with no change says so and sends nothing`);
    }

    // 5. A record's History.
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(
      `${uiUrl}/apps/${table.application.key}/objects/${table.type.key}/${record.id}?workspaceKey=default`,
    );
    const history = page.locator(".history-panel");
    await history.getByRole("heading", { name: "What changed" }).waitFor();
    assert.equal(await history.getByRole("combobox", { name: "Period" }).inputValue(), "30");
    await history.getByRole("button", { name: "Explain this period" }).click();
    await history.getByText(/Written by AI from the facts below/).waitFor();
    await accessible(page, `ao2-${label}-record`);
    await shot("record");
    const lead = history.locator(".impact-facts li button", { hasText: /^Show (it|them)$/ }).first();
    if ((await lead.count()) > 0) {
      await lead.click();
      await page
        .locator(".scope-banner")
        .getByText(/^Narrowed by: /)
        .waitFor();
      await page.locator(".scope-banner").getByRole("button", { name: "Show all history" }).click();
    }
    checks.push(`${label}: a record's History offers the same section, and a fact narrows its timeline`);
    await page.setViewportSize({ width: 390, height: 844 });
    await noOverflow(page, `${label} record 390`);
    await shot("record-390");

    await clean(`${label}: the whole path`);
  } finally {
    await harness.cleanup();
    await rm(modeFile, { force: true });
  }
}

await walk(SHAPED_MODELS[0], "values");
await walk(SHAPED_MODELS[1], "structure");

// Without a provider the Activity has no section.
const bare = await bootHarness();
try {
  await bare.page.goto(`${bare.uiUrl}/settings/workspaces/default/activity`);
  await bare.page.getByRole("group", { name: "Filter the activity" }).waitFor();
  assert.equal(await bare.page.getByRole("heading", { name: "What changed" }).count(), 0);
  checks.push("without a provider the Activity has no What changed section");
} finally {
  await bare.cleanup();
}

console.log(checks.map((check) => `ok - ${check}`).join("\n"));
console.log(`${checks.length} checks passed`);
