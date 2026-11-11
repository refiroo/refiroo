// 0.12 Z5 browser evidence: the interface follows the person's permissions, against a real backend
// on two models (the starter, and the differently shaped journey configuration generated-b). People are made and
// granted through the API, then each sets a password through their link and signs in on the
// engine's page. A Reader sees no write affordance and the band says they can read; a Contributor
// proposes a change from a record, names their change set, edits the record in it, sees no Publish,
// and a second proposal continues the same change set, counted in the band; a Data steward narrowed
// to one record type has no Edit on another type, and the band names the permitted type; a person
// with Browse only in a second workspace lands there; a Security administrator without data roles
// sees the no-workspace page and reaches People; a Reader's settings navigation lists only their
// pages. Keyboard through Propose a change and its dialog; axe; screenshots at 1440px light and dark
// and 390px; no horizontal page scroll at 390px. Record types are read from the model, never named.
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { SHAPED_MODELS, bootShaped, startingPoints } from "./helpers/shaped-models.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

const SECOND = { key: "field-stations", label: "Field stations" };
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

async function walk(configuration) {
  const harness = await bootShaped(configuration);
  try {
    const { uiUrl, api, output, signedOutContext } = harness;
    const tag = configuration.name;
    const overflow = (page) => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    const shot = (page, name) => page.screenshot({ path: resolve(output, `${tag}-${name}.png`), fullPage: true });
    const band = (page) => page.locator(".data-context-band");
    /** Waits for `locator`; on a timeout says what the page shows instead. */
    const seen = (page, locator) =>
      locator.waitFor().catch(async (error) => {
        console.error(`${page.url()}\n${(await page.locator("body").innerText()).slice(0, 1500)}`);
        throw error;
      });

    // The model's own tables: two record types of one application, each with a record.
    await api("/workspaces", SECOND, "POST");
    const [first, second] = await startingPoints(api);
    const [one, other] = [first.records[0], second.records[0]];
    const recordUrl = (table, record, extra = "") =>
      `${uiUrl}/apps/${table.application.key}/objects/${table.type.key}/${record.id}?workspaceKey=default${extra}`;

    /** A person granted `grants`, signed in in a context of their own at `width`. */
    async function person(username, grants, width = 1440) {
      const created = await api("/users", { email: `${username}-${tag}@example.org`, name: `${username} ${tag}` });
      for (const [role, scope] of grants)
        await api("/grants", { principal: { kind: "user", id: created.id }, role, scope });
      const { url } = await api(`/users/${created.id}/password-reset`, {}, "POST");
      const context = await signedOutContext({ viewport: { width, height: width < 600 ? 844 : 900 } });
      const page = await context.newPage();
      page.setDefaultTimeout(15000);
      page.on("pageerror", (error) => failures.push(`${tag} ${username}: ${error.message}`));
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
      // Signed in once the application has opened: its top bar's Settings.
      await page.waitForURL(
        (address) => !address.pathname.startsWith("/oauth") && !address.pathname.startsWith("/signed-in"),
      );
      await page.getByRole("link", { name: "Settings" }).waitFor();
      return { ...created, context, page };
    }
    const actions = async (page) => {
      await page.getByRole("button", { name: "Record actions" }).click();
      const items = await page.getByRole("menuitem").allInnerTexts();
      await page.keyboard.press("Escape");
      return items;
    };

    // 1. A Reader: nothing to write anywhere; the band says they can read.
    const reader = await person("reader", [["reader", { workspaceKey: "default" }]]);
    await reader.page.goto(recordUrl(first, one));
    await seen(reader.page, reader.page.getByRole("heading", { level: 1, name: one.name }));
    await band(reader.page).getByText("You can read this workspace.", { exact: false }).waitFor();
    expect(
      JSON.stringify(await actions(reader.page)) === JSON.stringify(["Copy link"]),
      `${tag}: a Reader's record actions are Copy link only`,
    );
    expect(
      (await reader.page.getByRole("button", { name: "Propose a change" }).count()) === 0,
      `${tag}: no proposal for a Reader`,
    );
    await shot(reader.page, "reader-record");
    await axe(reader.page, `${tag}-reader-record`);
    await reader.page.goto(`${uiUrl}/apps/${first.application.key}/views/${first.view.key}?workspaceKey=default`);
    await reader.page.getByRole("heading", { level: 1 }).first().waitFor();
    await reader.page.getByRole("table").first().waitFor();
    expect(
      (await reader.page
        .getByRole("button", { name: new RegExp(`^(Add|Propose a new) ${first.type.name}`) })
        .count()) === 0,
      `${tag}: a Reader's collection offers no Add`,
    );
    // Export is offered to a reader, so the menu may stand; it holds no Import and no Edit model.
    const menu = reader.page.getByRole("button", { name: "Workspace actions" });
    if (await menu.count()) {
      await menu.click();
      await reader.page.getByRole("menu").waitFor();
      expect(
        (await reader.page.getByRole("menuitem", { name: /^(Import|Edit model)/ }).count()) === 0,
        `${tag}: no Import and no Edit model for a Reader`,
      );
      await reader.page.keyboard.press("Escape");
    }
    checks.push(`${tag}: a Reader's record and collection offer no write; the band says they can read`);
    await reader.page.goto(`${uiUrl}/settings/about`);
    const readerNav = reader.page.getByRole("navigation", { name: "Settings" });
    await readerNav.getByRole("link", { name: "Consumer APIs" }).waitFor();
    const readerLinks = await readerNav.getByRole("link").allInnerTexts();
    expect(
      JSON.stringify(readerLinks) ===
        JSON.stringify([
          "About",
          "Appearance",
          "Account",
          "Notification email",
          "Workspaces",
          "Jobs",
          "Consumer APIs",
          "API reference",
        ]),
      `${tag}: a Reader's settings navigation: ${readerLinks.join(", ")}`,
    );
    checks.push(`${tag}: a Reader's settings navigation lists only their pages`);
    await reader.context.close();

    // 2. A Contributor proposes a change, by keyboard; a second proposal continues the change set.
    const contributor = await person("contributor", [["contributor", { workspaceKey: "default" }]]);
    let page = contributor.page;
    await page.goto(recordUrl(first, one));
    await band(page).getByText("Changes you make go into your change set, not live.", { exact: false }).waitFor();
    const propose = page.getByRole("button", { name: "Propose a change" });
    await propose.focus();
    await page.keyboard.press("Enter");
    const dialog = page.getByRole("dialog", { name: "Propose a change" });
    const name = dialog.getByLabel("Change set name");
    expect((await name.inputValue()) === `Changes by contributor ${tag}`, `${tag}: the change set's name is suggested`);
    expect(
      await page.evaluate(() => !!document.activeElement?.closest("[role=dialog]")),
      `${tag}: focus is in the dialog`,
    );
    await shot(page, "propose-dialog");
    await axe(page, `${tag}-propose-dialog`);
    await name.fill(`Proposed ${tag}`);
    await page.keyboard.press("Enter");
    const form = page.getByRole("dialog", { name: one.name });
    await form.waitFor();
    expect(page.url().includes("changeSetId="), `${tag}: the proposal opens the record in the change set`);
    const changeSetId = new URL(page.url()).searchParams.get("changeSetId");
    const nameField = form.getByLabel("Name", { exact: true });
    await nameField.fill(`${one.name} proposed`);
    await form.getByRole("button", { name: "Save changes" }).click();
    await form.waitFor({ state: "detached" });
    await band(page).getByText("until someone who holds Publish", { exact: false }).waitFor();
    expect(
      (await page.getByRole("button", { name: "Publish change set" }).count()) === 0,
      `${tag}: a Contributor has no Publish`,
    );
    checks.push(`${tag}: Propose a change names a change set, edits the record in it; no Publish`);
    await page.goto(recordUrl(first, one));
    await band(page)
      .getByRole("button", { name: `Your change set: Proposed ${tag} · 1 change` })
      .waitFor();
    expect(
      (await api(`/objects/${first.type.key}/${one.id}?workspaceKey=default`)).name === one.name,
      `${tag}: live is unchanged`,
    );
    await shot(page, "contributor-record");
    await axe(page, `${tag}-contributor-record`);
    await page.getByRole("button", { name: "Propose a change" }).click();
    await page.getByRole("dialog", { name: `${one.name}` }).waitFor();
    expect(
      new URL(page.url()).searchParams.get("changeSetId") === changeSetId,
      `${tag}: the second proposal continues it`,
    );
    checks.push(`${tag}: the band counts the change; a second proposal continues the same change set`);
    await contributor.context.close();

    // The Contributor at 390px, and dark.
    const narrow = await person("contributor-narrow", [["contributor", { workspaceKey: "default" }]], 390);
    await narrow.page.goto(recordUrl(first, one));
    await narrow.page.getByRole("button", { name: "Propose a change" }).waitFor();
    expect((await overflow(narrow.page)) <= 0, `${tag}: the Contributor's record scrolls sideways at 390px`);
    await shot(narrow.page, "contributor-record-narrow");
    await narrow.page.emulateMedia({ colorScheme: "dark" });
    await narrow.page.evaluate(() => (document.documentElement.dataset.theme = "dark"));
    await shot(narrow.page, "contributor-record-narrow-dark");
    await axe(narrow.page, `${tag}-contributor-record-narrow-dark`);
    await narrow.context.close();
    checks.push(`${tag}: 390px without horizontal page scroll, light and dark`);

    // 3. A Data steward narrowed to the first type: no Edit on the second; the band names the first.
    const steward = await person("steward", [["steward", { workspaceKey: "default", recordTypes: [first.type.key] }]]);
    await steward.page.goto(recordUrl(second, other));
    await steward.page.getByRole("heading", { level: 1, name: other.name }).waitFor();
    await band(steward.page).getByText(`Your role changes ${first.type.name} records here`, { exact: false }).waitFor();
    expect(!(await actions(steward.page)).includes("Edit record"), `${tag}: no Edit on a type outside the narrowing`);
    await steward.page.goto(recordUrl(first, one));
    await steward.page.getByRole("heading", { level: 1 }).first().waitFor();
    expect((await actions(steward.page)).includes("Edit record"), `${tag}: Edit on the permitted type`);
    await steward.page.emulateMedia({ colorScheme: "dark" });
    await steward.page.evaluate(() => (document.documentElement.dataset.theme = "dark"));
    await shot(steward.page, "steward-record-dark");
    await steward.context.close();
    checks.push(`${tag}: a narrowed steward edits only the permitted type; the band names it`);

    // 4. Browse only in the second workspace: Home shows it alone (0.12 HM1), and an application
    // address naming no workspace opens there.
    const elsewhere = await person("elsewhere", [["reader", { workspaceKey: SECOND.key }]]);
    await elsewhere.page.getByRole("heading", { level: 3, name: SECOND.label }).waitFor();
    expect((await elsewhere.page.locator(".home-card").count()) === 1, `${tag}: Home shows ${SECOND.key} alone`);
    await elsewhere.page.goto(`${uiUrl}/apps/${first.application.key}/views/${first.view.key}`);
    await band(elsewhere.page).getByText(SECOND.label, { exact: false }).first().waitFor();
    expect(
      elsewhere.page.url().includes(`workspaceKey=${SECOND.key}`),
      `${tag}: opens in ${SECOND.key}: ${elsewhere.page.url()}`,
    );
    await elsewhere.context.close();
    checks.push(`${tag}: a person with Browse only in ${SECOND.key} lands there`);

    // 5. A Security administrator without data roles: no workspace; People from there.
    const security = await person("security", [["security-admin", { instance: true }]]);
    await security.page.getByRole("heading", { level: 1, name: "There is no workspace you can open yet" }).waitFor();
    await security.page.getByText("A role in a workspace is granted on People.", { exact: false }).waitFor();
    await shot(security.page, "no-workspace");
    await axe(security.page, `${tag}-no-workspace`);
    await security.page.getByRole("button", { name: "People" }).click();
    await security.page.getByRole("heading", { level: 1, name: "People" }).waitFor();
    await security.context.close();
    checks.push(`${tag}: a Security administrator without data sees the no-workspace page and reaches People`);

    const report = { model: tag, checks, failures, passed: !failures.length };
    await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
    console.log(`Z5 browser evidence (${tag}): ${output}`);
  } finally {
    harness.cleanup();
  }
}

try {
  for (const configuration of SHAPED_MODELS) await walk(configuration);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("Z5 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
}
