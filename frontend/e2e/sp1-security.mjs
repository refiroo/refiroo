// 0.12 SP1 browser evidence: Settings › Security against a real backend, on two models (the
// starter, and the differently shaped journey configuration generated-b), at 1440px and 390px, light and dark. As the
// harness person (Security administrator): create a person and copy their one-time link; they set a
// password through it and sign in; grant them Data steward in the default workspace narrowed to one
// record type of that workspace's model; make a group, add them to it and grant it Reader in a second
// workspace, so the person's page shows both, one through the group; copy Data steward into a custom
// role and untick Publish; a workspace's Access lists the grants and removes one; deactivating the
// only Security administrator is refused as the engine words it; the new person, without Security
// administration, is not shown the Security pages. The grant dialog by keyboard; axe on each page;
// screenshots; no horizontal page scroll at 390px. 0.12 Z4: the person's recent activity names who
// did what, and a record changed by a client names it in the record's history.
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { SHAPED_MODELS, bootShaped, startingPoint } from "./helpers/shaped-models.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

const SECOND = { key: "field-stations", label: "Field stations" };

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

/**
 * In an open picker, leaves exactly the options matching `name` ticked (the default workspace is chosen
 * for the person already), and is done.
 */
async function chooseOnly(page, name) {
  const options = page.getByRole("option");
  await options.first().waitFor();
  for (const option of await options.all()) {
    const wanted = name.test((await option.getAttribute("aria-label")) ?? (await option.innerText()));
    if (((await option.getAttribute("aria-selected")) === "true") !== wanted) await option.click();
  }
  await page.getByRole("button", { name: "Done" }).click();
}

async function walk(configuration) {
  const harness = await bootShaped(configuration);
  try {
    const { uiUrl, api, output, browser, signedOutContext, harnessIdentity } = harness;
    const tag = configuration.name;
    const overflow = (page) => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    const shot = (page, name) => page.screenshot({ path: resolve(output, `${tag}-${name}.png`), fullPage: true });
    await api("/workspaces", SECOND, "POST");
    const { type: recordType } = await startingPoint(api);
    const lena = { email: `lena-${tag}@example.org`, name: `Lena ${tag}`, password: "a passphrase for lena here" };

    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    page.setDefaultTimeout(15000);
    page.on("pageerror", (error) => failures.push(`${tag}: ${error.message}`));

    // 1. People: Security is in the navigation; a new person and their one-time link.
    await page.goto(`${uiUrl}/settings/people`);
    await page.getByRole("heading", { level: 1, name: "People" }).waitFor();
    const navigation = page.getByRole("navigation", { name: "Settings" });
    await navigation.getByRole("heading", { name: "Security" }).waitFor();
    await page.getByRole("button", { name: "New person" }).click();
    const create = page.getByRole("dialog", { name: "New person" });
    // The e-mail address is asked for; a malformed one is refused by the engine and said under its
    // field, not as "Request validation failed" (found by the user, 2026-10-24).
    await create.getByLabel("Name", { exact: true }).fill(lena.name);
    expect(
      await create.getByRole("button", { name: "Create and make a password link" }).isDisabled(),
      `${tag}: a person without an e-mail address is not sent`,
    );
    await create.getByLabel("E-mail", { exact: true }).fill("not an e-mail");
    await create.getByRole("button", { name: "Create and make a password link" }).click();
    await create.getByText("An e-mail address looks like name@example.org.").waitFor();
    expect(
      (await create.getByText("Request validation failed").count()) === 0,
      `${tag}: the engine's refusal is said by field`,
    );
    checks.push(`${tag}: New person asks for the e-mail address, and the engine's e-mail refusal by field`);
    await create.getByLabel("E-mail", { exact: true }).fill(lena.email);
    await create.getByLabel("Name", { exact: true }).fill(lena.name);
    await create.getByRole("button", { name: "Create and make a password link" }).click();
    const shown = page.getByRole("dialog", { name: "Pass on the password link" });
    const link = await shown.locator("code").innerText();
    expect(link.includes("/reset-password?token="), `${tag}: the link opens the application's reset page: ${link}`);
    await shot(page, "link-shown-once");
    await axe(page, `${tag}-link-dialog`);
    await shown.getByRole("button", { name: "I have copied it" }).click();
    await page.getByRole("heading", { level: 2, name: lena.name }).waitFor();
    await page.getByText("Has not set a password yet").waitFor();
    checks.push(`${tag}: a new person, their one-time link shown once`);

    // 2. They set their password through the link and sign in.
    const theirs = await signedOutContext({ viewport: { width: 1440, height: 900 } });
    const lenaPage = await theirs.newPage();
    lenaPage.setDefaultTimeout(15000);
    await lenaPage.goto(link);
    await lenaPage.getByLabel("New password", { exact: true }).fill(lena.password);
    await lenaPage.getByLabel(/again|Repeat/i).fill(lena.password);
    await lenaPage.getByRole("button", { name: /Set password/i }).click();
    await lenaPage.getByText(/Your password is set/).waitFor();
    checks.push(`${tag}: the person sets a password through the link`);

    // 3. Grant Data steward in the default workspace, narrowed to one record type; by keyboard into the
    // dialog, Escape returns to its button.
    await page.reload();
    await page.getByRole("heading", { level: 2, name: lena.name }).waitFor();
    const grantButton = page.getByRole("button", { name: "Grant", exact: true });
    await grantButton.focus();
    await page.keyboard.press("Enter");
    let dialog = page.getByRole("dialog", { name: `Grant ${lena.name} access` });
    await dialog.getByText("Where").waitFor();
    await page.keyboard.press("Tab");
    expect(
      await page.evaluate(() => !!document.activeElement?.closest("[role=dialog]")),
      `${tag}: focus stays in the grant dialog`,
    );
    await page.keyboard.press("Escape");
    await dialog.waitFor({ state: "detached" });
    expect(
      await grantButton
        .evaluate(
          (button) =>
            new Promise((done) => {
              const started = Date.now();
              const check = () =>
                button === document.activeElement
                  ? done(true)
                  : Date.now() - started > 2000
                    ? done(false)
                    : setTimeout(check, 50);
              check();
            }),
        )
        .catch(() => false),
      `${tag}: Escape returns to Grant`,
    );
    await grantButton.click();
    dialog = page.getByRole("dialog", { name: `Grant ${lena.name} access` });
    await dialog.getByRole("checkbox", { name: "Data steward" }).check();
    await dialog.getByRole("button", { name: "Add workspace" }).click();
    await chooseOnly(page, /^Default/);
    await dialog.getByText("Only these applications and record types").click();
    await dialog.getByRole("button", { name: "Add", exact: true }).click();
    await page.getByRole("searchbox", { name: /Search applications and record types/i }).fill(recordType.name);
    await page
      .getByRole("option", { name: new RegExp(`^${recordType.name}`) })
      .first()
      .click();
    await page.getByRole("button", { name: "Done" }).click();
    await dialog.getByText(`changing only ${recordType.name}`, { exact: false }).waitFor();
    await shot(page, "grant-dialog");
    await axe(page, `${tag}-grant-dialog`);
    await dialog.getByRole("button", { name: "Grant", exact: true }).click();
    await dialog.waitFor({ state: "detached" });
    const roles = page.getByRole("group", { name: "Roles" });
    await roles.getByRole("row", { name: new RegExp(`Data steward.*${recordType.name}`) }).waitFor();
    checks.push(`${tag}: Data steward granted in the default workspace, narrowed to ${recordType.name}`);

    // 3b. With a role, the person signs in; without Security administration they are not shown it.
    await lenaPage.goto(`${uiUrl}/settings/about`);
    await lenaPage.getByRole("heading", { level: 1, name: "Sign in" }).waitFor();
    await lenaPage.getByLabel("E-mail address").fill(lena.email);
    await lenaPage.getByLabel("Password").fill(lena.password);
    await lenaPage.getByRole("button", { name: "Sign in" }).click();
    await lenaPage
      .getByRole("heading", { level: 1, name: "About" })
      .waitFor()
      .catch(async (error) => {
        console.error((await lenaPage.locator("body").innerText()).slice(0, 800));
        throw error;
      });
    await lenaPage.getByRole("navigation", { name: "Settings" }).getByRole("link", { name: "Account" }).waitFor();
    expect(
      (await lenaPage
        .getByRole("navigation", { name: "Settings" })
        .getByRole("heading", { name: "Security" })
        .count()) === 0,
      `${tag}: a person without Security administration is not shown Security`,
    );
    checks.push(`${tag}: the person signs in; no Security for them`);

    // 4. A group with the person, granted Reader in the second workspace.
    await navigation.getByRole("link", { name: "Groups" }).click();
    await page.getByRole("heading", { level: 1, name: "Groups" }).waitFor();
    await page.getByRole("button", { name: "New group" }).click();
    const groupDialog = page.getByRole("dialog", { name: "New group" });
    await groupDialog.getByLabel("Name", { exact: true }).fill("Curators");
    await groupDialog.getByRole("button", { name: "Create group" }).click();
    await page.getByRole("heading", { level: 2, name: "Curators" }).waitFor();
    // 0.12 SP1b: people searched and ticked, or pasted as a list; added together.
    await page.getByRole("button", { name: "Add members" }).click();
    const memberDialog = page.getByRole("dialog", { name: "Add members to Curators" });
    await memberDialog.getByLabel("Search people").fill(lena.name);
    await memberDialog.getByRole("checkbox", { name: `Add ${lena.name}` }).check();
    await shot(page, "add-members-search");
    await memberDialog.getByRole("tab", { name: "Paste a list" }).click();
    await memberDialog
      .getByLabel("E-mail addresses")
      .fill(`${lena.email.toUpperCase()}\nnobody-${tag}@example.org`);
    await memberDialog.getByRole("button", { name: "Check 2 lines" }).click();
    const checkedLines = memberDialog.getByRole("list", { name: "Lines checked" });
    await checkedLines.getByText("Added to the people to add").waitFor();
    await checkedLines.getByText("No person with this e-mail address").waitFor();
    await shot(page, "add-members-paste");
    await axe(page, `${tag}-add-members`);
    await memberDialog.getByRole("button", { name: "Add 1 member" }).click();
    await page.getByRole("group", { name: "Members" }).getByText(lena.email).waitFor();
    checks.push(`${tag}: a member added from a search and a pasted list (an unknown line said so), together`);
    await page.getByRole("button", { name: "Grant", exact: true }).click();
    dialog = page.getByRole("dialog", { name: "Grant Curators access" });
    await dialog.getByRole("checkbox", { name: "Reader" }).check();
    await dialog.getByRole("button", { name: "Add workspace" }).click();
    await chooseOnly(page, new RegExp(SECOND.label));
    await dialog.getByText(`Curators will read everything in ${SECOND.label}.`).waitFor();
    await dialog.getByRole("button", { name: "Grant", exact: true }).click();
    await page
      .getByRole("group", { name: "Roles" })
      .getByRole("row", { name: new RegExp(SECOND.label) })
      .waitFor();
    await shot(page, "groups");
    await axe(page, `${tag}-groups`);
    checks.push(`${tag}: a group with the person, granted Reader in ${SECOND.label}`);

    // 5. The person's page: both roles, one through the group; their groups.
    await page.getByRole("group", { name: "Members" }).getByRole("link", { name: lena.name }).click();
    await page.getByRole("heading", { level: 2, name: lena.name }).waitFor();
    await roles.getByRole("row", { name: new RegExp(`${SECOND.label}.*Reader.*Group Curators`) }).waitFor();
    await page
      .getByRole("list", { name: `${lena.name}'s groups` })
      .getByRole("link", { name: "Curators" })
      .waitFor();
    const entry = page.getByRole("navigation", { name: "People" }).getByRole("button", { name: new RegExp(lena.name) });
    await entry.getByText(/Data steward · /).waitFor();
    await shot(page, "person");
    await axe(page, `${tag}-people`);
    checks.push(`${tag}: the person's page names both roles, one through the group; the list names their roles`);

    // 5b. Their recent activity (0.12 Z4, D319): what was done to them and by them, each by whom.
    // Grouped by day since 0.12 RA1: the name is the group's, a list under each day's heading.
    const activity = page.getByRole("group", { name: `${lena.name}'s recent activity` });
    const [administrator] = (await api(`/users?q=${encodeURIComponent(harnessIdentity.person.email)}`)).items;
    const admin = administrator.name;
    await activity.getByText("Added to Curators").waitFor();
    for (const line of [`Granted Data steward in Default`, "Person created", "Password set from a one-time link"])
      await activity.getByText(line).waitFor();
    await activity.getByText(/^Signed in from /).waitFor();
    expect(
      (await activity.getByText(`by ${admin}`).count()) >= 3,
      `${tag}: the administrator's changes name them in the person's activity`,
    );
    expect((await activity.getByText(`by ${lena.name}`).count()) >= 1, `${tag}: their own sign-in names them`);
    await activity.scrollIntoViewIfNeeded();
    await shot(page, "person-activity");
    checks.push(`${tag}: the person's recent activity names who did what`);

    // 5c. A record changed by a client names it in the record's history (0.12 Z4, D320).
    const [record] = (await api(`/objects/${recordType.key}?workspaceKey=default&pageSize=1`)).items;
    await api(
      `/objects/${recordType.key}/${record.id}`,
      { expectedVersion: record.version, name: `${record.name} (renamed by a client)` },
      "PATCH",
    );
    await page.goto(
      `${uiUrl}/apps/${record.applicationKey}/objects/${recordType.key}/${record.id}?workspaceKey=default`,
    );
    const history = page.locator(".history-panel");
    // Since 0.12 RH1 a line names who made the change; opened, it says "by …" with the link.
    const byClient = history.getByRole("button", { name: /\(client\)/ }).first();
    await byClient.click();
    await history
      .getByText(/by .+ \(client\)/)
      .first()
      .waitFor();
    await history.scrollIntoViewIfNeeded();
    await shot(page, "record-history");
    await axe(page, `${tag}-record-history`);
    checks.push(`${tag}: a record's history names the client that changed it`);
    await page.goto(`${uiUrl}/settings/people`);
    await page.getByRole("heading", { level: 1, name: "People" }).waitFor();

    // 6. A custom role copied from Data steward, without Publish.
    await navigation.getByRole("link", { name: "Roles" }).click();
    await page.getByRole("heading", { level: 1, name: "Roles" }).waitFor();
    await page.getByRole("button", { name: "New role" }).click();
    const roleDialog = page.getByRole("dialog", { name: "New role" });
    await roleDialog.getByLabel("Name", { exact: true }).fill("Careful steward");
    await roleDialog.getByRole("button", { name: /Start from$/ }).click();
    await page.getByRole("option", { name: /^Data steward/ }).click();
    await roleDialog.getByRole("button", { name: "Create role" }).click();
    const publish = page.getByRole("checkbox", { name: "Careful steward: Publish" });
    expect(await publish.isChecked(), `${tag}: the copy starts with Data steward's Publish`);
    await publish.uncheck();
    await page.getByRole("button", { name: "Save role" }).click();
    await page.getByRole("button", { name: "Edit Careful steward" }).waitFor();
    const careful = (await api("/roles?pageSize=500")).items.find((role) => role.name === "Careful steward");
    expect(
      careful && !careful.actionGroups.includes("publish") && careful.actionGroups.includes("edit-live"),
      `${tag}: the custom role is saved without Publish: ${JSON.stringify(careful?.actionGroups)}`,
    );
    expect((await overflow(page)) <= 0, `${tag}: Roles scrolls the page sideways at 1440px`);
    await shot(page, "roles");
    await axe(page, `${tag}-roles`);
    checks.push(`${tag}: a custom role copied from Data steward, Publish unticked in place`);

    // 7. The workspace's Access lists the grants; removing one there.
    await page.goto(`${uiUrl}/settings/workspaces/default/access`);
    const access = page.getByRole("region", { name: "Access" });
    // Each person, group or client is one row of the list (a list item), the roles its chips.
    const rowOf = (text) => access.getByRole("listitem").filter({ hasText: text });
    await rowOf(new RegExp(`${lena.name}[\\s\\S]*Data steward[\\s\\S]*writes: ${recordType.name}`))
      .first()
      .waitFor();
    await rowOf(/whole instance/)
      .first()
      .waitFor();
    await shot(page, "access");
    await axe(page, `${tag}-access`);
    await access.getByRole("button", { name: `Remove Data steward from ${lena.name}` }).click();
    await page
      .getByRole("alertdialog", { name: `Remove Data steward from ${lena.name}?` })
      .getByRole("button", { name: "Remove", exact: true })
      .click();
    await rowOf(new RegExp(`${lena.name}[\\s\\S]*Data steward`)).waitFor({ state: "detached" });
    checks.push(`${tag}: a workspace's Access lists who can do what and removes a grant`);

    // 7b. A client's consumer API grant (0.12 Z3) is listed in Access by the API's name, and
    // removed by keyboard; Access at 390px without a horizontal page scroll.
    const [consumerApi] = (await api("/model")).consumerApis;
    const sync = await api("/clients", { name: `Catalogue sync ${tag}` });
    await api("/grants", {
      principal: { kind: "client", id: sync.id },
      consumerApi: consumerApi.key,
      scope: { workspaceKey: "default" },
    });
    await page.reload();
    const held = `Consumer API: ${consumerApi.name}`;
    await rowOf(new RegExp(`${sync.name}[\\s\\S]*Client[\\s\\S]*${held}`))
      .first()
      .waitFor();
    await shot(page, "access-consumer-api");
    await axe(page, `${tag}-access-consumer-api`);
    const narrowAccess = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true });
    const accessPhone = await narrowAccess.newPage();
    await accessPhone.goto(`${uiUrl}/settings/workspaces/default/access`);
    await accessPhone.getByRole("region", { name: "Access" }).getByText(held).waitFor();
    expect((await overflow(accessPhone)) <= 0, `${tag}: Access scrolls sideways at 390px`);
    await shot(accessPhone, "access-consumer-api-narrow");
    await narrowAccess.close();
    await access.getByRole("button", { name: `Remove ${held} from ${sync.name}` }).focus();
    await page.keyboard.press("Enter");
    const removal = page.getByRole("alertdialog", { name: `Remove ${held} from ${sync.name}?` });
    await removal.getByRole("button", { name: "Remove", exact: true }).focus();
    await page.keyboard.press("Enter");
    await rowOf(new RegExp(sync.name)).waitFor({ state: "detached" });
    expect(!(await api(`/grants?principalId=${sync.id}`)).items.length, `${tag}: the consumer API grant is removed`);
    checks.push(`${tag}: a consumer API grant in Access by its API's name, removed by keyboard, 390px`);

    // 8. Deactivating the only Security administrator is refused as the engine words it.
    const [self] = (await api(`/users?q=${encodeURIComponent(harnessIdentity.person.email)}`)).items;
    await page.goto(`${uiUrl}/settings/people/${self.id}`);
    await page.getByRole("heading", { level: 2, name: self.name }).waitFor();
    await page.getByRole("button", { name: "Deactivate", exact: true }).click();
    const confirm = page.getByRole("alertdialog");
    await confirm.waitFor().catch(async (error) => {
      await shot(page, "debug-deactivate");
      console.error(output);
      throw error;
    });
    await confirm.getByRole("button", { name: "Deactivate", exact: true }).click();
    await confirm.getByText(/no active person holding Security administration/).waitFor();
    await confirm.getByRole("button", { name: "Cancel" }).click();
    checks.push(`${tag}: deactivating the last Security administrator is refused, as worded`);

    // 8b. Restore: a deactivated person without an e-mail address is asked for one first (0.17 EM1).
    const holder = await api("/users", { email: `holder-${tag}@example.org`, name: `Holder ${tag}` });
    const gone = await api("/users", { email: `gone-${tag}@example.org`, name: `Gone ${tag}` });
    await api(`/users/${gone.id}`, { expectedVersion: gone.version, active: false, email: null }, "PATCH");
    await page.goto(`${uiUrl}/settings/people/${gone.id}`);
    await page.getByRole("heading", { level: 2, name: `Gone ${tag}` }).waitFor();
    await page.getByRole("button", { name: "Restore", exact: true }).click();
    const restore = page.getByRole("dialog", { name: `Restore Gone ${tag}` });
    await restore.getByLabel("E-mail", { exact: true }).waitFor();
    await restore.getByRole("button", { name: "Restore", exact: true }).click();
    await restore.getByText(/needs an e-mail address/).waitFor();
    await shot(page, "restore-missing");
    await restore.getByLabel("E-mail", { exact: true }).fill(`HOLDER-${tag}@example.org`);
    await restore.getByRole("button", { name: "Restore", exact: true }).click();
    await restore.getByText("Another person has this e-mail address").waitFor();
    await shot(page, "restore-taken");
    await restore.getByLabel("E-mail", { exact: true }).fill(`back-${tag}@example.org`);
    await restore.getByRole("button", { name: "Restore", exact: true }).click();
    await restore.waitFor({ state: "detached" });
    await page.getByText(`back-${tag}@example.org`).first().waitFor();
    const back = await api(`/users/${gone.id}`);
    expect(
      back.active === true && back.email === `back-${tag}@example.org` && holder.email,
      `${tag}: the restored person is active with the address typed`,
    );
    await shot(page, "restored");
    checks.push(`${tag}: Restore asks a person without an address for one, refuses a missing and a taken one in place`);

    // 9. Dark at 1440px; People, a person and Roles at 390px without a horizontal page scroll.
    const dark = await browser.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: "dark" });
    const night = await dark.newPage();
    await night.goto(`${uiUrl}/settings/people`);
    await night.getByRole("heading", { level: 1, name: "People" }).waitFor();
    await night
      .getByRole("navigation", { name: "People" })
      .getByRole("button", { name: new RegExp(lena.name) })
      .click();
    await night.getByRole("heading", { level: 2, name: lena.name }).waitFor();
    await night.getByRole("group", { name: "Roles" }).waitFor();
    await shot(night, "person-dark");
    await axe(night, `${tag}-people-dark`);
    await night.goto(`${uiUrl}/settings/roles`);
    await night.getByRole("heading", { level: 1, name: "Roles" }).waitFor();
    await shot(night, "roles-dark");
    await dark.close();
    const narrow = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true });
    const phone = await narrow.newPage();
    phone.setDefaultTimeout(15000);
    await phone.goto(`${uiUrl}/settings/people`);
    await phone.getByRole("heading", { level: 1, name: "People" }).waitFor();
    expect((await overflow(phone)) <= 0, `${tag}: People scrolls sideways at 390px`);
    await shot(phone, "people-narrow");
    await phone
      .getByRole("navigation", { name: "People" })
      .getByRole("button", { name: new RegExp(lena.name) })
      .click();
    await phone.getByRole("heading", { level: 2, name: lena.name }).waitFor();
    expect((await overflow(phone)) <= 0, `${tag}: a person's page scrolls sideways at 390px`);
    await shot(phone, "person-narrow");
    await phone.goto(`${uiUrl}/settings/roles`);
    await phone.getByRole("heading", { level: 1, name: "Roles" }).waitFor();
    await phone.getByRole("group", { name: "Roles by action group" }).waitFor();
    expect((await overflow(phone)) <= 0, `${tag}: Roles scrolls the page sideways at 390px`);
    const box = phone.getByRole("group", { name: "Roles by action group" });
    expect(
      await box.evaluate((element) => element.scrollWidth > element.clientWidth),
      `${tag}: the matrix scrolls in its own box at 390px`,
    );
    await shot(phone, "roles-narrow");
    await narrow.close();
    checks.push(`${tag}: dark; 390px without horizontal page scroll, the matrix scrolling in its box`);

    await theirs.close();
    await context.close();
    const report = { browser: browser.version(), model: tag, checks, failures, passed: !failures.length };
    await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
    console.log(`SP1 browser evidence (${tag}): ${output}`);
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
  console.error("SP1 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
}
