// 0.12 I2 browser evidence: signing in from the browser against a real backend, on two models (the
// starter, and the starter under another product name), at 1440px and 390px, light and dark. A
// record page opened signed out leads to the engine's sign-in page; a wrong password is refused
// without saying which part; the right one, typed by keyboard, returns to that page. The account
// menu names the person and leads to Account, where the password is changed. A session ended by an
// administrator sends the person to the sign-in page, which says so, and back to the same page.
// Sign out from the menu returns to the sign-in page. Axe on the sign-in page (light and dark) and
// Account; screenshots of each; no horizontal scroll at 390px. Z1: the menu names the roles held in
// the workspace, its actions are buttons, and Account lists the roles, for the harness person (every
// role at the instance) and for a person granted Reader and a narrowed Contributor in one workspace.
import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

const NEW_PASSWORD = "a brand new harness passphrase";

const MODELS = [
  { name: "starter", record: "/apps/rdm-master/views/domains?workspaceKey=default", heading: "Domains" },
  {
    name: "renamed",
    product: "Northfield Reference Data",
    record: "/apps/rdm-systems/views/systems?workspaceKey=default",
    heading: "Systems",
  },
];

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
  const harness = await bootHarness({
    transformModel: configuration.product
      ? (model) => {
          model.product.name = configuration.product;
        }
      : undefined,
  });
  try {
    const { apiUrl, uiUrl, api, output, signedOutContext, harnessIdentity } = harness;
    const person = harnessIdentity.person;
    const tag = configuration.name;
    const starter = JSON.parse(await readFile(resolve("..", "model", "rdm-starter.json"), "utf8"));
    const product = configuration.product ?? starter.product.name;
    const overflow = (page) => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    const shot = (page, name) => page.screenshot({ path: resolve(output, `${tag}-${name}.png`), fullPage: true });
    const onSignInPage = (page) => page.getByRole("heading", { level: 1, name: "Sign in" }).waitFor();
    const record = `${uiUrl}${configuration.record}`;

    // 1. Signed out: the record page leads to the engine's sign-in page, the product named.
    const context = await signedOutContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    page.setDefaultTimeout(15000);
    page.on("pageerror", (error) => failures.push(`${tag}: ${error.message}`));
    await page.goto(record);
    await onSignInPage(page);
    expect(
      page.url().startsWith(`${apiUrl}/oauth/authorize?`),
      `${tag}: the sign-in page is the engine's: ${page.url()}`,
    );
    expect(
      await page.getByText(product, { exact: true }).isVisible(),
      `${tag}: the product's name ${product} is shown`,
    );
    const focused = (id) =>
      page
        .waitForFunction((wanted) => document.activeElement?.id === wanted, id, { timeout: 3000 })
        .then(() => true)
        .catch(() => false);
    expect(await focused("username"), `${tag}: the username has focus`);
    await shot(page, "sign-in-light");
    await axe(page, `${tag}-sign-in-light`);
    checks.push(`${tag}: a signed-out record page leads to the engine's sign-in page`);

    // 2. A wrong password by keyboard: refused without saying which part; the username kept.
    await page.keyboard.type(person.username);
    await page.keyboard.press("Tab");
    await page.keyboard.type("not the right passphrase at all");
    await page.keyboard.press("Enter");
    await page
      .getByRole("alert")
      .filter({ hasText: "The username or password is not right" })
      .waitFor()
      .catch(async (error) => {
        console.error((await page.locator("body").innerText()).slice(0, 800));
        throw error;
      });
    expect((await page.getByLabel("Username").inputValue()) === person.username, `${tag}: the username is kept`);
    expect(await focused("password"), `${tag}: the password has focus after a refusal`);
    await shot(page, "sign-in-wrong");
    checks.push(`${tag}: a wrong password is refused without saying which part`);

    // 3. The right password returns to the page asked for.
    await page.keyboard.type(person.password);
    await page.keyboard.press("Enter");
    await page.waitForURL(record);
    await page.getByRole("heading", { level: 1, name: configuration.heading }).waitFor();
    checks.push(`${tag}: the right password returns to ${configuration.record}`);

    // 4. The account menu names the person and leads to Account.
    const menuButton = page.getByRole("button", { name: "Account" });
    await menuButton.focus();
    await page.keyboard.press("Enter");
    const menu = page.getByRole("dialog", { name: "Account" });
    await menu.getByText("Test harness person").waitFor();
    await menu.getByText(/^Reader, Contributor, Data steward, .* and Security administrator in /).waitFor();
    for (const action of [
      menu.getByRole("link", { name: "Account" }),
      menu.getByRole("link", { name: "All settings" }),
      menu.getByRole("button", { name: "Sign out" }),
    ])
      expect(
        (await action.getAttribute("class"))?.includes("account-menu-action"),
        `${tag}: the menu's actions are buttons alike`,
      );
    await shot(page, "menu-roles");
    await menu.getByRole("link", { name: "Account" }).click();
    await page.waitForURL(`${uiUrl}/settings/account`);
    await page.getByRole("heading", { level: 1, name: "Account" }).waitFor();
    const sessions = page.getByRole("list", { name: "Where you’re signed in" });
    await sessions.getByText("This browser").waitFor();
    const roles = page.getByRole("list", { name: "What you can do" });
    await roles.getByText("Security administrator").waitFor();
    expect((await roles.getByRole("listitem").count()) === 9, `${tag}: Account lists the nine roles`);
    expect(
      (await roles.getByText("Every workspace").count()) === 9,
      `${tag}: the harness person's roles are at the instance`,
    );
    await shot(page, "account-wide");
    await axe(page, `${tag}-account`);
    checks.push(`${tag}: the menu names the person; Account lists this browser`);

    // 5. Change the password: the wrong current one is refused at its field, then it changes.
    await page.getByRole("button", { name: "Change password" }).click();
    await shot(page, "account-password-open");
    await page.getByLabel("Current password", { exact: true }).fill("not the current one at all");
    await page.getByLabel("New password", { exact: true }).fill(NEW_PASSWORD);
    await page.getByRole("button", { name: "Save new password" }).click();
    await page.getByText("The current password is not right").waitFor();
    await page.getByLabel("Current password", { exact: true }).fill(person.password);
    await page.getByRole("button", { name: "Save new password" }).click();
    await page.getByText(/Your password is changed/).waitFor();
    checks.push(`${tag}: the password changes; a wrong current password is refused at its field`);

    // 6. An administrator ends the person's sessions: the next request leads to the sign-in page,
    // which says the session ended, and back to the same page.
    const [user] = (await api(`/users?q=${encodeURIComponent(person.username)}`)).items;
    await api(`/users/${user.id}/sessions`, undefined, "DELETE");
    await page.getByRole("link", { name: "About" }).click();
    await onSignInPage(page);
    await page.getByText("Your session ended. Sign in again to return to where you were.").waitFor();
    await page.getByLabel("Username").fill(person.username);
    await page.getByLabel("Password").fill(NEW_PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();
    await page.waitForURL(`${uiUrl}/settings/about`);
    await page.getByRole("heading", { level: 1, name: "About" }).waitFor();
    checks.push(`${tag}: an ended session leads to the sign-in page, which says so, and back to the same page`);

    // 7. Sign out from the menu: the sign-in page.
    await page.getByRole("button", { name: "Account" }).click();
    await page.getByRole("dialog", { name: "Account" }).getByRole("button", { name: "Sign out" }).click();
    await onSignInPage(page);
    await page.goto(`${uiUrl}/settings/about`);
    await onSignInPage(page);
    checks.push(`${tag}: signing out leads to the sign-in page, and the app stays signed out`);
    await context.close();

    // 7b. A person granted Reader, and Contributor narrowed to one record type, in one workspace:
    // the menu names both there, and Account lists them, the narrowing by the type's name.
    const reader = { username: "rhea", password: "a passphrase for the reader" };
    const created = await api("/users", { username: reader.username, name: "Rhea Reader" }, "POST");
    const [recordType] = (await api("/object-types?workspaceKey=default")).items;
    await api(
      "/grants",
      { principal: { kind: "user", id: created.id }, role: "reader", scope: { workspaceKey: "default" } },
      "POST",
    );
    await api(
      "/grants",
      {
        principal: { kind: "user", id: created.id },
        role: "contributor",
        scope: { workspaceKey: "default", recordTypes: [recordType.key] },
      },
      "POST",
    );
    const link = await api(`/users/${created.id}/password-reset`, {}, "POST");
    const readers = await signedOutContext({ viewport: { width: 1440, height: 900 } });
    const rhea = await readers.newPage();
    rhea.setDefaultTimeout(15000);
    rhea.on("pageerror", (error) => failures.push(`${tag} (reader): ${error.message}`));
    await rhea.goto(link.url);
    await rhea.getByLabel("New password", { exact: true }).fill(reader.password);
    await rhea.getByLabel(/again|Repeat/i).fill(reader.password);
    await rhea.getByRole("button", { name: /Set password/i }).click();
    await rhea.goto(`${uiUrl}/settings/account`);
    await onSignInPage(rhea);
    await rhea.getByLabel("Username").fill(reader.username);
    await rhea.getByLabel("Password").fill(reader.password);
    await rhea.getByRole("button", { name: "Sign in" }).click();
    await rhea.getByRole("heading", { level: 1, name: "Account" }).waitFor();
    const rheaRoles = rhea.getByRole("list", { name: "What you can do" });
    await rheaRoles.getByText("Contributor").waitFor();
    const rows = await rheaRoles.getByRole("listitem").allInnerTexts();
    expect(rows.length === 2, `${tag}: the reader's Account lists two roles: ${rows.join(" | ")}`);
    expect(
      rows.some((row) => row.includes(`Changes narrowed to ${recordType.name}`)),
      `${tag}: the narrowing is named by the type's name: ${rows.join(" | ")}`,
    );
    await rhea.getByRole("button", { name: "Account" }).click();
    await rhea.getByRole("dialog", { name: "Account" }).getByText(/^Reader and Contributor in /).waitFor();
    await shot(rhea, "reader-menu");
    await rhea.keyboard.press("Escape");
    await shot(rhea, "reader-account");
    await axe(rhea, `${tag}-reader-account`);
    await rhea.setViewportSize({ width: 390, height: 844 });
    await rheaRoles.getByText("Contributor").waitFor();
    expect((await overflow(rhea)) <= 0, `${tag}: the reader's Account scrolls sideways at 390px`);
    await shot(rhea, "reader-account-narrow");
    await readers.close();
    checks.push(`${tag}: a reader's menu and Account name their roles, the narrowing by name`);

    // 8. At 390px: one column, no horizontal scroll, on the sign-in page and on Account.
    const narrow = await signedOutContext({ viewport: { width: 390, height: 844 }, hasTouch: true });
    const phone = await narrow.newPage();
    phone.setDefaultTimeout(15000);
    await phone.goto(`${uiUrl}/settings/account`);
    await onSignInPage(phone);
    expect((await overflow(phone)) <= 0, `${tag}: the sign-in page scrolls sideways at 390px`);
    await shot(phone, "sign-in-narrow");
    await phone.getByLabel("Username").fill(person.username);
    await phone.getByLabel("Password").fill(NEW_PASSWORD);
    await phone.getByRole("button", { name: "Sign in" }).click();
    await phone.waitForURL(`${uiUrl}/settings/account`);
    await phone.getByRole("heading", { level: 1, name: "Account" }).waitFor();
    expect((await overflow(phone)) <= 0, `${tag}: Account scrolls sideways at 390px`);
    await shot(phone, "account-narrow");
    checks.push(`${tag}: 390px: the sign-in page and Account without horizontal scroll`);
    await narrow.close();

    // 9. Dark, from the device.
    const dark = await signedOutContext({ viewport: { width: 1440, height: 900 }, colorScheme: "dark" });
    const night = await dark.newPage();
    await night.goto(record);
    await onSignInPage(night);
    await shot(night, "sign-in-dark");
    await axe(night, `${tag}-sign-in-dark`);
    await dark.close();
    checks.push(`${tag}: the sign-in page in dark`);
    const report = { browser: harness.browser.version(), model: tag, checks, failures, passed: !failures.length };
    await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
    console.log(`I2 browser evidence (${tag}): ${output}`);
  } finally {
    harness.cleanup();
  }
}

try {
  for (const configuration of MODELS) await walk(configuration);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("I2 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
}
