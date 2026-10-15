// Base 0.10 R: US-P09 and US-P10 composed in the browser over a real backend, by keyboard alone (D149).
//
// Runs on both designer models (D20): the starter with every key renamed at 1440px, and the journey
// configuration generated-b at 390px, each raised to schema 0.10 on the migrated empty database. It
// names no configuration key: the workbooks are the generated W1, W1′ and W2 (backend
// tests/workbooks.py), and the elements the inference adds are read back by the names it gives them.
// Focus moves only by Tab, Shift+Tab and the arrow keys; every control is worked by Enter, Space or
// typing; a file is chosen through the file chooser its input opens. The browser is driven by the
// keyboard; the API is read only to check what a step did.
//
// US-P09, two differently shaped workbooks, a new application and additions to the model:
//   1. W1 as a new application: proposed, a proposed type renamed, the dry run refusing no row,
//      installed, activated and loaded into a change set, reviewed and published (200 items).
//   2. W2, the model description, as a new application, loaded and published; then W1 as additions
//      to that model: matched to its stored lists, its missing values created on load, loaded and
//      published.
// US-P10, on the first walk's saved profile: W1′ uploaded as the next version, its check (the
//   renamed column, the new column), the rename accepted and the new column ignored, loaded into a
//   change set whose review holds only W1′'s 3 added and 5 changed items, published.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { cloneDatabase } from "./helpers/database.mjs";

const root = resolve(import.meta.dirname, "..", "..");
const checks = [];

function python(code, ...args) {
  return execFileSync(resolve(root, "backend/.venv/bin/python"), ["-c", code, ...args], {
    cwd: resolve(root, "backend"),
  });
}
const json = (code) => JSON.parse(python(code).toString());
const book = (call) =>
  python(
    `import sys; sys.path.insert(0, 'tests'); import workbooks; sys.stdout.buffer.write(workbooks.${call}.content)`,
  );

const renamed = json(
  "import json; from tests.model_support import renamed_model; print(json.dumps(renamed_model()[0]))",
);
const generatedB = json(
  "import json, sys; sys.path.insert(0, 'tests/journeys'); from configurations import generated; print(json.dumps(generated('b').model))",
);
const W1 = book("w1(rows=200)");
const W1_NEXT = book("w1_next(rows=200)");
const W2 = book("w2(rows=200)");
const { S1, HEADERS, NEXT_HEADERS } = json(
  "import json, sys; sys.path.insert(0, 'tests'); import workbooks; " +
    "print(json.dumps({'S1': workbooks.S1, 'HEADERS': workbooks.HEADERS, 'NEXT_HEADERS': workbooks.w1_next(rows=200).headers}))",
);

/** The keyboard's way through a page: Tab to a control, then work it. */
function keyboard(page) {
  const focused = (target) => target.evaluate((node) => node === document.activeElement).catch(() => false);
  /** Tab (or Shift+Tab) until `target` has focus. */
  async function tabTo(target, { back = false, limit = 200 } = {}) {
    // A control may appear only once a job ends (a profile's check runs again after each change).
    await target.waitFor({ timeout: 90_000 });
    // A disabled control takes no focus: wait until it may be worked (a step still running).
    for (let wait = 0; wait < 600 && !(await target.isEnabled()); wait += 1) await page.waitForTimeout(100);
    for (let press = 0; press < limit; press += 1) {
      if (await focused(target)) return;
      await page.keyboard.press(back ? "Shift+Tab" : "Tab");
    }
    assert.fail(`Tab did not reach ${target}`);
  }
  /** An arrow key until `target` has focus, inside a widget that moves focus by arrows. */
  async function arrowTo(target, key = "ArrowDown", limit = 400) {
    await target.waitFor();
    for (let press = 0; press < limit; press += 1) {
      if (await focused(target)) return;
      await page.keyboard.press(key);
    }
    assert.fail(`${key} did not reach ${target}`);
  }
  return {
    tabTo,
    arrowTo,
    /** Tab to a button or link and press Enter. */
    async press(target, key = "Enter") {
      await tabTo(target);
      await page.keyboard.press(key);
    },
    /** Tab to a text field and type into it, replacing what it holds. */
    async type(target, text) {
      await tabTo(target);
      await page.keyboard.press("ControlOrMeta+A");
      await page.keyboard.type(text);
    },
    /** Tab to a file input and choose the file through the chooser Space opens. */
    async choose(target, path) {
      await tabTo(target);
      const [chooser] = await Promise.all([page.waitForEvent("filechooser"), page.keyboard.press("Space")]);
      await chooser.setFiles(path);
    },
    /** Tab into a radio group (to its checked radio), then arrow down to `radio`. */
    async radio(group, radio) {
      await tabTo(group.locator("input[type=radio]:checked"));
      for (let press = 0; press < 8 && !(await radio.isChecked()); press += 1) await page.keyboard.press("ArrowDown");
      assert.equal(await radio.isChecked(), true, `the arrows reach ${radio}`);
    },
  };
}

/** One walk group on a fresh database: `flat` (W1, then W1′) or `described` (W2, then W1 onto it). */
async function journey(label, source, viewport, walks) {
  let database;
  const model = structuredClone(source);
  model.schemaVersion = "0.10";
  const harness = await bootHarness({
    viewport,
    prepare: async (output) => {
      const modelPath = resolve(output, "model.json");
      await writeFile(modelPath, JSON.stringify(model));
      await writeFile(resolve(output, "catalogue.xlsx"), W1);
      await writeFile(resolve(output, "catalogue-v2.xlsx"), W1_NEXT);
      await writeFile(resolve(output, "described.xlsx"), W2);
      database = cloneDatabase("schema");
      return { modelPath, database };
    },
  });
  const { page } = harness;
  const keys = keyboard(page);
  const phone = viewport.width < 760;
  const shot = (name) => page.screenshot({ path: resolve(harness.output, `r-${label}-${name}.png`), fullPage: true });
  const dialog = () => page.getByRole("dialog").last();
  const api = (path, body) => harness.api(path, body);
  let draftId;

  /** The key of the type named `name` in the application named `application`. */
  async function typeKey(application, name) {
    const outline = await api(`/model-drafts/${draftId}/outline`);
    const app = outline.applications.find((item) => item.name === application);
    const type = outline.objectTypes.find((item) => item.name === name && app.objectTypeKeys.includes(item.key));
    assert.ok(type, `${application} holds ${name}`);
    return type.key;
  }

  /** At phone width the editor's panes are tabs: the one named `name` (a pattern) chosen by the arrows. */
  async function pane(name) {
    if (!phone) return;
    const tabs = page.getByRole("tablist", { name: "Editor panes" });
    await keys.tabTo(tabs.getByRole("tab", { selected: true }));
    const wanted = tabs.getByRole("tab", { name });
    for (let press = 0; press < 6 && (await wanted.getAttribute("aria-selected")) !== "true"; press += 1)
      await page.keyboard.press("ArrowRight");
    assert.equal(await wanted.getAttribute("aria-selected"), "true", `the arrows reach the ${name} tab`);
  }

  /** Settings › Model › New from a workbook, proposing `mode`; the editor open once proposals apply. */
  async function newFromWorkbook(file, name, mode) {
    await page.goto(`${harness.uiUrl}/settings/model`);
    await keys.press(page.getByRole("button", { name: "New from a workbook" }));
    await keys.type(dialog().getByLabel("Draft name"), name);
    await keys.choose(dialog().getByLabel("Workbook"), resolve(harness.output, file));
    await keys.radio(
      dialog().locator("fieldset.propose-fields"),
      dialog().getByRole("radio", { name: new RegExp(`^${mode}`) }),
    );
    if (mode === "A new application") await keys.type(dialog().getByLabel("Application name"), name);
    await keys.press(dialog().getByRole("button", { name: "Create and propose" }));
    await page.waitForURL(/\/editor/);
    draftId = new URL(page.url()).pathname.split("/")[4];
    await page.getByText("Proposing from the workbook").waitFor();
    await page.getByText("Proposing from the workbook").waitFor({ state: "hidden", timeout: 90_000 });
  }

  /** The dry run in the drawer (the Issues tab at phone width), checked; the number of refused figures. */
  async function refusedFigures() {
    if (phone) await pane(/^Issues/);
    else {
      const drawer = page.getByRole("button", { name: /^Issues, history and dry run/ });
      if ((await drawer.getAttribute("aria-expanded")) !== "true") await keys.press(drawer);
    }
    const tabs = page.getByRole("tablist").filter({ has: page.getByRole("tab", { name: /^Dry run/ }) });
    await keys.tabTo(tabs.getByRole("tab", { selected: true }));
    const dryRunTab = tabs.getByRole("tab", { name: /^Dry run/ });
    for (let press = 0; press < 4 && (await dryRunTab.getAttribute("aria-selected")) !== "true"; press += 1)
      await page.keyboard.press("ArrowRight");
    const dryRun = page.locator(".dry-run");
    await dryRun.getByText("Checked", { exact: true }).waitFor({ timeout: 90_000 });
    return dryRun.locator(".dry-run-figure.refused").count();
  }

  async function publishReview() {
    await keys.press(page.getByRole("button", { name: "Validate change set", exact: true }));
    await keys.press(page.getByRole("button", { name: "Publish change set", exact: true }));
    await keys.press(page.getByRole("alertdialog").getByRole("button", { name: "Publish change set", exact: true }));
    await page.getByText(/Reviewed changes are now live/).waitFor({ timeout: 30_000 });
  }

  /** Load into a change set: install, activate and load, the review, validated and published. */
  async function loadAndPublish(file) {
    const load = page.getByRole("button", { name: "Load into a change set…" });
    if (await load.isVisible()) await keys.press(load);
    else {
      await keys.press(page.getByRole("button", { name: /^More: / }));
      await keys.arrowTo(page.getByRole("menuitem", { name: "Load into a change set…" }));
      await page.keyboard.press("Enter");
    }
    await keys.press(dialog().getByRole("button", { name: "Install, activate and load" }));
    await dialog().getByText("Loaded into the change set").waitFor({ timeout: 120_000 });
    await keys.press(dialog().getByRole("button", { name: "Open the change set review" }));
    await page.waitForURL(/change-sets\/[^/]+\/changes/);
    await page
      .getByText(new RegExp(`Load ${file.replace(".", "\\.")}`))
      .first()
      .waitFor();
    await publishReview();
  }

  try {
    if (walks === "flat") await flat();
    else await described();
  } catch (error) {
    await page
      .screenshot({ path: resolve(harness.output, `r-${label}-${walks}-failure.png`), fullPage: true })
      .catch(() => {});
    await writeFile(resolve(harness.output, "server.log"), harness.log()).catch(() => {});
    // What each connection to the database does and waits for (a job that does not end).
    try {
      console.error(
        python(
          "import sys, json, psycopg; c = psycopg.connect(sys.argv[1].replace('+psycopg', '')); " +
            "rows = c.execute(\"SELECT pid, state, wait_event_type, wait_event, pg_blocking_pids(pid), now() - xact_start, left(query, 300) FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid() AND state <> 'idle'\").fetchall(); " +
            "print(json.dumps(rows, default=str, indent=1))",
          database.databaseUrl,
        ).toString(),
      );
    } catch (failure) {
      console.error("activity not read", failure.message);
    }
    const profiles = await api("/import-profiles").catch(() => ({ items: [] }));
    for (const item of profiles.items)
      await writeFile(
        resolve(harness.output, `profile-${item.key}.json`),
        JSON.stringify(await api(`/import-profiles/${item.key}`), null, 1),
      );
    const jobs = await api("/jobs?pageSize=6").catch(() => ({ items: [] }));
    for (const job of jobs.items)
      console.error(
        "JOB",
        job.kind,
        job.state,
        job.stage,
        job.processed,
        job.total,
        job.leaseOwner,
        job.leaseExpiresAt,
        job.createdAt,
        JSON.stringify(job.error),
      );
    console.error(harness.log().slice(-3000));
    throw error;
  } finally {
    harness.cleanup();
  }
  console.log(`Screenshots (${label}, ${walks}): ${harness.output}`);

  async function flat() {
    // --- US-P09, W1 as a new application ---
    await newFromWorkbook("catalogue.xlsx", "Catalogue R", "A new application");
    await shot("w1-proposed");
    // A proposal changed before loading: the proposed Category renamed in its centre.
    await pane("Model");
    const tree = page.getByRole("tree", { name: "Model" });
    const category = await typeKey("Catalogue R", "Category");
    const categoryRow = tree
      .locator(`[data-row^="type:"][data-row$="/${category}"], [data-row^="type:"][data-row$=":${category}"]`)
      .first();
    await keys.tabTo(tree.locator("[role=treeitem][tabindex='0']"));
    await page.keyboard.press("Home");
    await keys.arrowTo(categoryRow);
    await page.keyboard.press("Enter");
    await pane(/^Category/);
    await keys.press(page.getByRole("button", { name: /^Edit Name: Category/ }));
    await page.keyboard.press("ControlOrMeta+A");
    await page.keyboard.type("Product group");
    await page.keyboard.press("Enter");
    await page.getByRole("heading", { name: /^Product group/, level: 2 }).waitFor();
    assert.equal(await refusedFigures(), 0, "W1's dry run refuses no row");
    await shot("w1-renamed");
    checks.push(
      `${label}: W1 proposed as a new application; a proposed type renamed by keyboard; the dry run refuses no row`,
    );
    await loadAndPublish("catalogue.xlsx");
    const items = await api(`/objects/${await typeKey("Catalogue R", "Item")}?includeTotal=true&pageSize=1`);
    assert.equal(items.totalCount, 200);
    const groups = await api(`/objects/${category}?includeTotal=true&pageSize=1`);
    assert.equal(groups.totalCount > 0, true, "the renamed type holds W1's groups");
    checks.push(
      `${label}: W1 installed, activated, loaded into a change set, reviewed and published by keyboard: 200 items live`,
    );

    // --- US-P10, W1′ through the saved profile ---
    const profileKey = (await api(`/model-drafts/${draftId}/profile`)).profile.key;
    await page.goto(`${harness.uiUrl}/settings/import-profiles`);
    await keys.press(
      page.getByRole("navigation", { name: "Import profiles" }).getByRole("button", { name: /published/ }),
    );
    await page.waitForURL(new RegExp(`/settings/import-profiles/${profileKey}$`));
    await keys.press(page.getByRole("button", { name: "Upload the next version…" }));
    await keys.choose(dialog().getByLabel("Workbook"), resolve(harness.output, "catalogue-v2.xlsx"));
    await keys.press(dialog().getByRole("button", { name: "Upload", exact: true }));
    await page.getByText(/catalogue-v2\.xlsx checked: \d+ differences need a look/).waitFor({ timeout: 90_000 });
    const columnsPart = page.getByRole("region", { name: "Columns" });
    await columnsPart.getByText(NEXT_HEADERS.Ln, { exact: true }).waitFor();
    await columnsPart.getByText(NEXT_HEADERS.Y, { exact: true }).waitFor();
    await shot("w1-next-checked");
    // Each change saves the profile and checks the file again: the next step waits for that check.
    const checking = page.getByText(/^Checking catalogue-v2\.xlsx/);
    await keys.press(columnsPart.getByRole("button", { name: "Accept" }));
    await columnsPart.getByRole("button", { name: "Accept" }).waitFor({ state: "detached", timeout: 90_000 });
    await checking.waitFor({ state: "hidden", timeout: 90_000 });
    await keys.press(columnsPart.getByRole("button", { name: "Ignore" }));
    await columnsPart.getByRole("button", { name: "Ignore" }).waitFor({ state: "detached", timeout: 90_000 });
    await checking.waitFor({ state: "hidden", timeout: 90_000 });
    await columnsPart
      .getByText(/The file has the columns the profile reads/)
      .first()
      .waitFor({ timeout: 90_000 });
    checks.push(
      `${label}: W1′ uploaded to the profile is checked; the renamed column accepted and the new one ignored by keyboard`,
    );
    await keys.press(page.getByRole("button", { name: "Load into a change set…" }));
    await keys.press(dialog().getByRole("button", { name: "Load", exact: true }));
    await dialog().getByText("Loaded into the change set").waitFor({ timeout: 120_000 });
    await keys.press(dialog().getByRole("button", { name: "Open the change set review" }));
    await page.waitForURL(/change-sets\/[^/]+\/changes/);
    const changeSetId = new URL(page.url()).pathname.match(/change-sets\/([^/]+)/)[1];
    const itemType = await typeKey("Catalogue R", "Item");
    const changes = await api(`/change-sets/${changeSetId}/object-changes?objectTypeKey=${itemType}&pageSize=500`);
    const kinds = changes.items.reduce((found, item) => ({ ...found, [item.kind]: (found[item.kind] ?? 0) + 1 }), {});
    assert.deepEqual(kinds, { added: 3, changed: 5 }, JSON.stringify(kinds));
    await shot("w1-next-review");
    await publishReview();
    checks.push(
      `${label}: W1′ loads into a change set whose review holds its 3 added and 5 changed items only, published by keyboard`,
    );
  }

  async function described() {
    // --- US-P09, W2 as a new application, then W1 as additions to it ---
    await newFromWorkbook("described.xlsx", "Described R", "A new application");
    assert.equal(await refusedFigures(), 0, "W2's dry run refuses no row");
    await loadAndPublish("described.xlsx");
    const colours = await api(`/objects/${await typeKey("Described R", "Colour")}?includeTotal=true&pageSize=1`);
    assert.equal(colours.totalCount, 6);
    checks.push(
      `${label}: W2, the model description, proposed, loaded and published by keyboard: its colours list holds 6 records`,
    );

    await newFromWorkbook("catalogue.xlsx", "Catalogue onto R", "Additions to the model");
    await pane("Source");
    const columns = page
      .getByRole("region", { name: "Source", exact: true })
      .getByRole("listbox", { name: `Columns of ${S1}` });
    await keys.tabTo(columns.locator("[role=option][tabindex='0']"));
    await keys.arrowTo(columns.locator(`[role=option][data-column="${HEADERS.T}"]`));
    await page.keyboard.press("Enter");
    await pane(new RegExp(`^${HEADERS.T}`));
    const create = page.getByRole("button", { name: /^Create the \d+ missing Material values on load$/ });
    await keys.press(create);
    await create.waitFor({ state: "detached" });
    assert.equal(await refusedFigures(), 0, "no row refused once the missing values are created on load");
    await shot("additions");
    await loadAndPublish("catalogue.xlsx");
    checks.push(
      `${label}: W1 as additions to W2's model, matched to its stored lists, missing values created on load, loaded and published by keyboard`,
    );
    if (phone) assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
  }
}

// `R_ONLY=renamed-example` or `generated-b` runs one model, `R_WALKS=flat` or `described` one group,
// while iterating.
const only = process.env.R_ONLY;
const desktop = { width: 1440, height: 900 };
const narrow = { width: 390, height: 844 };
for (const walks of process.env.R_WALKS ? [process.env.R_WALKS] : ["flat", "described"]) {
  if (!only || only === "renamed-example") await journey("renamed-example", renamed, desktop, walks);
  if (!only || only === "generated-b") await journey("generated-b", generatedB, narrow, walks);
}

console.log(`R, US-P09 and US-P10 by keyboard alone: ${checks.length} checks passed`);
for (const check of checks) console.log(`- ${check}`);
