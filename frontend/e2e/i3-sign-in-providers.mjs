// 0.12 I3 browser evidence: a sign-in provider against a real backend and the harness's minimal
// OpenID Connect provider (backend/tests/oidc_provider.py), on two models (the starter, and the differently shaped journey configuration generated-b), at 1440px and 390px, light and dark. As the harness person:
// add the provider on Settings › Security › Sign-in by keyboard and read the address to register.
// Signed out: the engine's sign-in page offers "Continue with"; the provider signs a new person in
// with two groups and the browser returns to the page asked for; Account names the provider. As the
// harness person again: the person "Signs in with" the provider, the two provider groups are listed
// under it with the members seen, one is renamed and granted Reader. Local sign-in is turned off
// through its confirmation; the sign-in page then shows only the provider's button and the local
// administrator's link, where the harness person (keeping local sign-in) signs in; turned on again.
// Axe on each page; screenshots; no horizontal page scroll at 390px.
// Brought up to date (0.14 + 0.17 release review, R17-F20): the harness provider sends no email_verified, so the provider is added with its e-mail addresses trusted.
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { SHAPED_MODELS, bootShaped } from "./helpers/shaped-models.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { startProvider } from "./helpers/oidc-provider.mjs";

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
  let provider;
  let harness;
  try {
    provider = await startProvider();
    harness = await bootShaped(configuration);
    const { uiUrl, apiUrl, api, output, browser, signedOutContext, harnessIdentity } = harness;
    const tag = configuration.name;
    const overflow = (target) => target.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    const shot = (target, name) => target.screenshot({ path: resolve(output, `${tag}-${name}.png`), fullPage: true });
    const pat = { sub: `p-${tag}`, name: `Pat ${tag}`, email: `pat-${tag}@provider.example` };

    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    page.setDefaultTimeout(15000);
    page.on("pageerror", (error) => failures.push(`${tag}: ${error.message}`));

    // 1. Sign-in is in the navigation; a provider added by keyboard; the address to register.
    await page.goto(`${uiUrl}/settings/sign-in`);
    await page.getByRole("heading", { level: 1, name: "Sign-in" }).waitFor();
    await page.getByRole("navigation", { name: "Settings" }).getByRole("link", { name: "Sign-in" }).waitFor();
    await page.getByText("No provider yet: people sign in with a password.").waitFor();
    await page.getByRole("button", { name: "New provider" }).focus();
    await page.keyboard.press("Enter");
    const dialog = page.getByRole("dialog", { name: "New sign-in provider" });
    await page.keyboard.type("Harness ID");
    for (const [label, value] of [
      ["Issuer", provider.issuer],
      ["Client ID", "engine"],
      ["Client secret", provider.secret],
      ["Groups claim (optional)", "groups"],
    ]) {
      await dialog.getByLabel(label, { exact: true }).focus();
      await page.keyboard.type(value);
    }
    // The harness provider sends no email_verified, so its addresses are trusted as sent (R17-F20).
    await dialog.getByLabel("Trust the e-mail addresses it sends").focus();
    await page.keyboard.press("Space");
    expect(
      (await dialog.getByLabel("Key", { exact: true }).inputValue()) === "harness-id",
      `${tag}: the key follows the name`,
    );
    await shot(page, "new-provider");
    await axe(page, `${tag}-new-provider`);
    await page.keyboard.press("Enter");
    await dialog.waitFor({ state: "detached" });
    await page.getByRole("heading", { level: 1, name: "Harness ID" }).waitFor();
    const address = `${apiUrl}/oauth/providers/harness-id/callback`;
    await page.getByText(address).first().waitFor();
    await page.getByRole("button", { name: /Copy/ }).first().waitFor();
    checks.push(`${tag}: a provider added by keyboard, checked when saved; the address to register shown`);

    // 2. Signed out: the provider signs a new person in and the browser returns to the page asked for.
    const outside = await signedOutContext({ viewport: { width: 1440, height: 900 } });
    const visitor = await outside.newPage();
    visitor.setDefaultTimeout(15000);
    await visitor.goto(`${uiUrl}/settings/account`);
    await visitor.getByRole("heading", { level: 1, name: "Sign in" }).waitFor();
    expect((await visitor.title()).includes("refiroo"), `${tag}: the sign-in screen is refiroo's`);
    await visitor.getByLabel("Password").waitFor();
    await visitor.getByRole("button", { name: "Continue with Harness ID" }).click();
    await visitor.getByRole("heading", { name: "Harness provider" }).waitFor();
    for (const [label, value] of [
      ["Subject", pat.sub],
      ["Name", pat.name],
      ["E-mail", pat.email],
      ["Username", pat.email],
      ["Groups (comma separated)", "herbarium-staff,data-governance"],
    ])
      await visitor.getByLabel(label, { exact: true }).fill(value);
    await visitor.getByRole("button", { name: "Sign in" }).click();
    await visitor.waitForURL(`${uiUrl}/settings/account`);
    await visitor.getByText("Signed in with Harness ID").waitFor();
    await visitor.getByText(pat.name).first().waitFor();
    await shot(visitor, "account-provider");
    checks.push(`${tag}: a new person signed in through the provider and returned to Account, which names it`);

    // 3. The person and the provider groups, as the harness person.
    const [person] = (await api(`/users?q=${encodeURIComponent(pat.email)}`)).items;
    await page.goto(`${uiUrl}/settings/people/${person.id}`);
    await page.getByRole("heading", { level: 1, name: pat.name }).waitFor();
    await page.getByText(/^Signs in with Harness ID/).waitFor();
    await page.goto(`${uiUrl}/settings/groups`);
    const groups = page;
    // Each entry names its source (the headings are gone, R); both provider groups are listed.
    for (const group of ["herbarium-staff", "data-governance"])
      await groups
        .getByRole("button", { name: new RegExp(group) })
        .filter({ hasText: "Harness ID" })
        .waitFor();
    await groups.getByRole("button", { name: /herbarium-staff/ }).click();
    await page.getByRole("heading", { level: 1, name: "herbarium-staff" }).waitFor();
    await page.getByText("Members come from the sign-in provider").waitFor();
    await page.getByRole("heading", { level: 2, name: "Members seen" }).waitFor();
    const seen = page.getByRole("group", { name: "Members" });
    await seen.getByRole("link", { name: pat.name }).waitFor();
    expect(
      !(await page.getByRole("button", { name: "Add members" }).count()),
      `${tag}: no Add members on a provider group`,
    );
    expect(!(await seen.getByRole("button", { name: /Remove/ }).count()), `${tag}: no Remove on a provider group`);
    await page.getByRole("button", { name: /Edit Name:/ }).click();
    const rename = page.getByRole("form", { name: "Edit Name" });
    await rename.getByLabel("Name", { exact: true }).fill("Herbarium staff");
    await page.keyboard.press("Enter");
    await page.getByRole("heading", { level: 1, name: "Herbarium staff" }).waitFor();
    await page.getByRole("button", { name: "Grant", exact: true }).click();
    const grant = page.getByRole("dialog", { name: "Herbarium staff's access" });
    await grant.getByRole("checkbox", { name: "Reader" }).check();
    // The only workspace is chosen already.
    await grant.getByText("No workspace chosen yet").waitFor({ state: "detached" });
    await grant.getByRole("button", { name: "Save", exact: true }).click();
    await page.getByRole("group", { name: "Roles" }).locator(".access-chip", { hasText: "Reader" }).waitFor();
    await shot(page, "provider-group");
    await axe(page, `${tag}-provider-group`);
    checks.push(`${tag}: two provider groups under the provider, members seen, renamed, granted Reader`);

    // 4. Local sign-in off through its confirmation; the sign-in page with the button and the link.
    // The harness person keeps local sign-in, as an administrator made on the server does (D365).
    const [kept] = (await api(`/users?q=${encodeURIComponent(harnessIdentity.person.email)}`)).items;
    await api(`/users/${kept.id}`, { expectedVersion: kept.version, localKept: true }, "PATCH");
    await page.goto(`${uiUrl}/settings/sign-in/local`);
    await page.getByRole("heading", { level: 1, name: "Local accounts" }).waitFor();
    await page.getByRole("button", { name: "Turn off…" }).focus();
    await page.keyboard.press("Enter");
    const confirm = page.getByRole("alertdialog", { name: "Turn local sign-in off?" });
    await confirm
      .getByText(
        /People sign in with Harness ID only\. Passwords stop working, except for the \d+ administrators? made on the server/,
      )
      .waitFor();
    await shot(page, "turn-off");
    await axe(page, `${tag}-turn-off`);
    await confirm.getByRole("button", { name: "Turn off" }).click();
    await page.getByRole("button", { name: "Turn on" }).waitFor();
    const locked = await signedOutContext({ viewport: { width: 1440, height: 900 } });
    const door = await locked.newPage();
    door.setDefaultTimeout(15000);
    await door.goto(`${uiUrl}/settings/about`);
    await door.getByRole("button", { name: "Continue with Harness ID" }).waitFor();
    expect(!(await door.getByLabel("Password").count()), `${tag}: no password form while local sign-in is off`);
    await shot(door, "sign-in-local-off");
    await axe(door, `${tag}-sign-in-local-off`);
    await door.getByRole("button", { name: "Sign in with a local administrator account" }).click();
    await door.getByLabel("E-mail address").fill(harnessIdentity.person.email);
    await door.getByLabel("Password").fill(harnessIdentity.person.password);
    await door.getByRole("button", { name: "Sign in" }).click();
    await door.waitForURL(`${uiUrl}/settings/about`);
    await locked.close();
    await page.getByRole("button", { name: "Turn on" }).click();
    await page.getByRole("button", { name: "Turn off…" }).waitFor();
    checks.push(`${tag}: local sign-in off and on; the kept administrator signed in through the link`);

    // 5. Dark, and 390px without horizontal page scroll.
    await page.goto(`${uiUrl}/settings/sign-in/harness-id`);
    await page.getByRole("heading", { level: 1, name: "Harness ID" }).waitFor();
    await shot(page, "provider");
    await axe(page, `${tag}-provider`);
    const dark = await browser.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: "dark" });
    const night = await dark.newPage();
    night.setDefaultTimeout(15000);
    await night.goto(`${uiUrl}/settings/sign-in/harness-id`);
    await night.getByRole("heading", { level: 1, name: "Harness ID" }).waitFor();
    await shot(night, "provider-dark");
    await axe(night, `${tag}-provider-dark`);
    await dark.close();
    const darkOut = await signedOutContext({ viewport: { width: 1440, height: 900 }, colorScheme: "dark" });
    const nightDoor = await darkOut.newPage();
    await nightDoor.goto(`${uiUrl}/settings/about`);
    await nightDoor.getByRole("button", { name: "Continue with Harness ID" }).waitFor();
    await shot(nightDoor, "sign-in-dark");
    await axe(nightDoor, `${tag}-sign-in-dark`);
    await darkOut.close();
    const narrow = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true });
    const phone = await narrow.newPage();
    phone.setDefaultTimeout(15000);
    await phone.goto(`${uiUrl}/settings/sign-in/harness-id`);
    await phone.getByRole("heading", { level: 1, name: "Harness ID" }).waitFor();
    expect((await overflow(phone)) <= 0, `${tag}: a provider's page scrolls sideways at 390px`);
    await shot(phone, "provider-narrow");
    await narrow.close();
    const narrowOut = await signedOutContext({ viewport: { width: 390, height: 844 }, hasTouch: true });
    const phoneDoor = await narrowOut.newPage();
    await phoneDoor.goto(`${uiUrl}/settings/about`);
    await phoneDoor.getByRole("button", { name: "Continue with Harness ID" }).waitFor();
    expect((await overflow(phoneDoor)) <= 0, `${tag}: the sign-in page scrolls sideways at 390px`);
    await shot(phoneDoor, "sign-in-narrow");
    await narrowOut.close();
    checks.push(`${tag}: dark; 390px without horizontal page scroll`);

    await outside.close();
    await context.close();
    const report = { browser: browser.version(), model: tag, checks, failures, passed: !failures.length };
    await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
    console.log(`I3 browser evidence (${tag}): ${output}`);
  } finally {
    harness?.cleanup();
    provider?.child.kill();
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
  console.error("I3 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
}
