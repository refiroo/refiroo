// 0.12 I4 browser evidence, grown by each part (`--part a|b|c`, default all): against a real
// backend and the harness's minimal OpenID Connect provider (backend/tests/oidc_provider.py), on
// two models (the starter, and the starter under another product name), at 1440px and 390px, light
// and dark.
//
// Part a (a provider identity linked, signing out of the provider, the switch): a person made at a
// provider sign-in is linked to an existing person from their page by keyboard, the dialog saying
// what moves; the existing person then signs in with the provider and the made one is deactivated;
// unlink; the provider's "Sign people out of … too" is saved and signing out of the app takes the
// browser through the provider's sign-out and back to the sign-in page; with local sign-in off, the
// last person who keeps it cannot stop (the engine's refusal in the confirmation). Axe on each page;
// screenshots; no horizontal page scroll at 390px.
//
// Part b (a second factor): a person with a password sets up an authenticator app on Account (the
// drawn QR code, the key, a code, ten recovery codes shown once), then signs in with the app's code
// (a wrong one refused first) and with a recovery code; the requirement is turned on in Settings ›
// Security › Sign-in › Local accounts and a person without an app sets one up on the sign-in page,
// their recovery codes shown before the session starts; an administrator removes that person's
// second factor from their page. Axe on each page and each sign-in step, light and dark, and 390px.
//
// Part c (passkeys): a person adds a passkey on the engine's own page from Account (Chromium's
// virtual authenticator answers the browser's prompt), signs in with it alone and as the second
// step after a password, renames it, and an administrator removes it from their page. The servers
// are reached as localhost: WebAuthn takes no IP address as its relying party. Axe on each page,
// light and dark, and 390px.
import { createHmac } from "node:crypto";
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { startProvider } from "./helpers/oidc-provider.mjs";

const MODELS = [{ name: "starter" }, { name: "renamed", product: "Northfield Reference Data" }];
const PARTS = ["a", "b", "c"];
const requested = process.argv.includes("--part") ? process.argv[process.argv.indexOf("--part") + 1] : "all";
const parts = requested === "all" ? PARTS : [requested];
if (!parts.every((part) => PARTS.includes(part))) throw new Error(`--part is one of ${PARTS.join(", ")} or all`);

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

/** Sign a person in at the provider from a browser that holds no session; the page they land on. */
async function signInThroughProvider(c, person, landing = "/settings/account") {
  const outside = await c.signedOutContext({ viewport: { width: 1440, height: 900 } });
  const page = await outside.newPage();
  page.setDefaultTimeout(15000);
  await page.goto(`${c.uiUrl}${landing}`);
  await page.getByRole("button", { name: "Continue with Harness ID" }).click();
  await page.getByRole("heading", { name: "Harness provider" }).waitFor();
  for (const [label, value] of [
    ["Subject", person.sub],
    ["Name", person.name],
    ["E-mail", person.email],
    ["Username", person.username],
    ["Groups (comma separated)", person.groups ?? ""],
  ])
    await page.getByLabel(label, { exact: true }).fill(value);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(`${c.uiUrl}${landing}`);
  return { context: outside, page };
}

async function partA(c) {
  const { tag, uiUrl, api, page, shot, overflow } = c;
  const ann = await api("/users", { username: `ann.${tag}`, name: `Ann ${tag}` });
  const pat = {
    sub: `p-${tag}`,
    name: `Pat ${tag}`,
    email: `pat-${tag}@provider.example`,
    username: `pat.${tag}`,
    groups: "herbarium-staff",
  };

  // 1. Pat signs in through the provider and is a new person with no roles.
  const first = await signInThroughProvider(c, pat);
  await first.context.close();
  const [made] = (await api(`/users?q=${encodeURIComponent(pat.username)}`)).items;
  expect(made && made.identities.length === 1, `${tag}: the sign-in made a person with the provider's identity`);

  // 2. From the made person's page, by keyboard: link to the existing person.
  await page.goto(`${uiUrl}/settings/people/${made.id}`);
  await page.getByRole("heading", { level: 2, name: pat.name }).waitFor();
  await page.getByRole("heading", { level: 2, name: "Sign-in", exact: true }).waitFor();
  await page.getByRole("button", { name: "Unlink…" }).waitFor();
  await shot(page, "person-made");
  await axe(page, `${tag}-person-made`);
  await page.getByRole("button", { name: "Link to an existing person…" }).focus();
  await page.keyboard.press("Enter");
  const dialog = page.getByRole("dialog", { name: "Link this sign-in to an existing person" });
  await dialog.getByRole("combobox", { name: "Person" }).fill(`Ann ${tag}`);
  await page.getByRole("option", { name: new RegExp(`Ann ${tag}`) }).click();
  await dialog.getByText(/will sign in with Harness ID from now on, keeping their roles and history/).waitFor();
  await shot(page, "link-dialog");
  await axe(page, `${tag}-link-dialog`);
  await dialog.getByRole("button", { name: `Link to Ann ${tag}` }).click();
  await dialog.waitFor({ state: "detached" });
  await page.getByRole("heading", { level: 2, name: `Ann ${tag}` }).waitFor();
  await page.getByRole("button", { name: "Unlink…" }).waitFor();
  await shot(page, "person-linked");
  await axe(page, `${tag}-person-linked`);
  const afterLink = await api(`/users/${made.id}`);
  expect(
    !afterLink.active && !afterLink.identities.length,
    `${tag}: the made person is deactivated and holds no identity`,
  );
  const linked = await api(`/users/${ann.id}`);
  expect(linked.identities.length === 1, `${tag}: Ann holds the provider identity`);
  checks.push(`${tag}: a provider sign-in linked to an existing person by keyboard; the made person deactivated`);

  // 3. Ann's next sign-in through the provider is Ann.
  const again = await signInThroughProvider(c, pat);
  await again.context.close();
  // The provider's name follows at each sign-in (D363), so Ann is now named as the provider has her.
  const signedIn = await api(`/users/${ann.id}`);
  expect(
    signedIn.lastSignInAt && signedIn.name === pat.name,
    `${tag}: the next provider sign-in was the existing person`,
  );
  expect((await api(`/users/${made.id}`)).lastSignInAt === afterLink.lastSignInAt, `${tag}: not the made one`);
  checks.push(`${tag}: the next provider sign-in is the existing person, named as the provider names her`);

  // 4. Unlink behind its confirmation.
  await page.getByRole("button", { name: "Unlink…" }).click();
  const confirm = page.getByRole("alertdialog", { name: "Unlink Harness ID?" });
  await confirm.getByText(/Signing in with Harness ID again makes a new person/).waitFor();
  await shot(page, "unlink");
  await axe(page, `${tag}-unlink`);
  await confirm.getByRole("button", { name: "Unlink" }).click();
  await confirm.waitFor({ state: "detached" });
  await page.getByText("Not set yet").waitFor();
  expect(!(await page.getByRole("button", { name: "Unlink…" }).count()), `${tag}: no Unlink once unlinked`);
  checks.push(`${tag}: unlink behind a confirmation; the provider row gone`);

  // 5. Signing out of the provider too: saved on the provider's page, then used.
  await page.goto(`${uiUrl}/settings/sign-in/harness-id`);
  await page.getByRole("heading", { level: 2, name: "Signing out" }).waitFor();
  const tick = page.getByRole("checkbox", { name: /Sign people out of Harness ID too/ });
  await tick.focus();
  await page.keyboard.press("Space");
  await page.getByText(`${c.apiUrl}/oauth/providers/harness-id/signed-out`).waitFor();
  await shot(page, "provider-sign-out");
  await axe(page, `${tag}-provider-sign-out`);
  await page.getByRole("button", { name: "Save", exact: true }).first().click();
  await page.getByText("are signed out of it too").waitFor();
  const lake = await signInThroughProvider(c, { ...pat, sub: `${pat.sub}-2`, username: `${pat.username}.2` });
  const visited = [];
  lake.page.on("request", (request) => visited.push(request.url()));
  await lake.page.getByRole("button", { name: "Sign out", exact: true }).click();
  await lake.page.getByRole("heading", { level: 1, name: "Sign in" }).waitFor();
  expect(
    visited.some((url) => url.startsWith(`${c.provider.issuer}/logout?id_token_hint=`)),
    `${tag}: signing out went through the provider's sign-out address with the ID token`,
  );
  await lake.context.close();
  checks.push(`${tag}: signing out of the app went through the provider's sign-out and back to the sign-in page`);

  // 6. The switch: the last person who keeps local sign-in cannot stop while local sign-in is off.
  const everyone = (await api("/users?pageSize=500")).items;
  const self = everyone.find((user) => user.username === c.harnessIdentity.person.username);
  for (const other of everyone.filter((user) => user.localKept && user.id !== self.id))
    await api(`/users/${other.id}`, { expectedVersion: other.version, localKept: false }, "PATCH");
  const current = await api(`/users/${self.id}`);
  if (!current.localKept)
    await api(`/users/${self.id}`, { expectedVersion: current.version, localKept: true }, "PATCH");
  const local = await api("/sign-in-providers/local");
  await api("/sign-in-providers/local", { expectedVersion: local.version, enabled: false }, "PATCH");
  await page.goto(`${uiUrl}/settings/people/${self.id}`);
  const keeps = page.getByRole("switch", { name: "Keeps local sign-in" });
  await keeps.waitFor();
  expect((await keeps.getAttribute("aria-checked")) === "true", `${tag}: the switch is on for a kept person`);
  await keeps.focus();
  await page.keyboard.press("Enter");
  const stop = page.getByRole("alertdialog", { name: /stops keeping local sign-in\?/ });
  await stop.getByRole("button", { name: "Stop keeping it" }).click();
  await stop.getByText(/this is the last person who keeps it/).waitFor();
  await shot(page, "last-kept");
  await axe(page, `${tag}-last-kept`);
  await stop.getByRole("button", { name: "Cancel" }).click();
  const on = await api("/sign-in-providers/local");
  await api("/sign-in-providers/local", { expectedVersion: on.version, enabled: true }, "PATCH");
  checks.push(`${tag}: the last person who keeps local sign-in cannot stop while it is off`);

  // 7. Dark, and 390px without horizontal page scroll.
  const dark = await c.browser.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: "dark" });
  const night = await dark.newPage();
  night.setDefaultTimeout(15000);
  await night.goto(`${uiUrl}/settings/people/${ann.id}`);
  await night.getByRole("heading", { level: 2, name: pat.name }).waitFor();
  await shot(night, "person-dark");
  await axe(night, `${tag}-person-dark`);
  await dark.close();
  const narrow = await c.browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true });
  const phone = await narrow.newPage();
  phone.setDefaultTimeout(15000);
  for (const [path, heading, name] of [
    [`/settings/people/${ann.id}`, pat.name, "person-narrow"],
    ["/settings/sign-in/harness-id", "Harness ID", "provider-narrow"],
  ]) {
    await phone.goto(`${uiUrl}${path}`);
    await phone.getByRole("heading", { level: 2, name: heading }).waitFor();
    expect((await overflow(phone)) <= 0, `${tag}: ${name} scrolls sideways at 390px`);
    await shot(phone, name);
  }
  await narrow.close();
  checks.push(`${tag}: dark; 390px without horizontal page scroll`);
}

const PASSPHRASE = "a long passphrase for testing";
const BASE32 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

/** RFC 6238's six-digit code of the current 30-second step, or `ahead` steps later. */
function totp(secret, ahead = 0) {
  let bits = "";
  for (const letter of secret.replace(/\s/g, "")) bits += BASE32.indexOf(letter).toString(2).padStart(5, "0");
  const key = Buffer.from(bits.match(/.{8}/g).map((byte) => Number.parseInt(byte, 2)));
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000) + ahead));
  const mac = createHmac("sha1", key).update(counter).digest();
  const offset = mac[mac.length - 1] & 15;
  return String((mac.readUInt32BE(offset) & 0x7fffffff) % 1000000).padStart(6, "0");
}

/** A person with a password: made through the API, the password set on the engine's own page. */
async function personWithPassword(c, username, name) {
  const person = await c.api("/users", { username, name });
  const link = await c.api(`/users/${person.id}/password-reset`, {}, "POST");
  const outside = await c.signedOutContext({ viewport: { width: 1440, height: 900 } });
  const page = await outside.newPage();
  page.setDefaultTimeout(15000);
  await page.goto(link.url);
  await page.getByLabel("New password").fill(PASSPHRASE);
  await page.getByLabel("Repeat the password").fill(PASSPHRASE);
  await page.getByRole("button", { name: "Set password" }).click();
  await page.getByText("Your password is set").waitFor();
  await outside.close();
  return person;
}

/** The engine's sign-in page with a username and password typed; the page that answers. */
async function passwordStep(c, username, options = {}) {
  const outside = await c.signedOutContext({ viewport: { width: 1440, height: 900 }, ...options });
  const page = await outside.newPage();
  page.setDefaultTimeout(15000);
  await page.goto(`${c.uiUrl}/settings/account`);
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(PASSPHRASE);
  await page.getByRole("button", { name: "Sign in" }).click();
  return { context: outside, page };
}

async function partB(c) {
  const { tag, uiUrl, api, page, shot, overflow } = c;
  const mei = await personWithPassword(c, `mei.${tag}`, `Mei ${tag}`);

  // 1. Account: not set up, then the set-up with the QR code, the key and a code, then the codes.
  const { context, page: account } = await passwordStep(c, mei.username);
  await account.waitForURL(`${uiUrl}/settings/account`);
  await account.getByRole("heading", { level: 2, name: "Authenticator app" }).waitFor();
  await account.getByText("Not set up").waitFor();
  await shot(account, "factor-off");
  await axe(account, `${tag}-factor-off`);
  await account.getByRole("button", { name: "Set up an authenticator app" }).focus();
  await account.keyboard.press("Enter");
  await account.getByRole("img", { name: "QR code for the authenticator app" }).waitFor();
  const secret = await account
    .getByText(/^[A-Z2-7]{4}( [A-Z2-7]{4})+$/)
    .first()
    .innerText();
  await account.getByLabel("Code from the app").fill("000000");
  await account.getByRole("button", { name: "Confirm" }).click();
  await account.getByText("That code is not right, or was already used").waitFor();
  await shot(account, "factor-setting-up");
  await axe(account, `${tag}-factor-setting-up`);
  await account.getByLabel("Code from the app").fill(totp(secret));
  await account.keyboard.press("Enter");
  await account.getByRole("button", { name: "I have kept them" }).waitFor();
  const codes = await account.getByRole("list", { name: "Recovery codes" }).getByRole("listitem").allInnerTexts();
  expect(codes.length === 10, `${tag}: ten recovery codes shown (${codes.length})`);
  await shot(account, "factor-codes");
  await axe(account, `${tag}-factor-codes`);
  await account.getByRole("button", { name: "I have kept them" }).click();
  await account.getByText(/10 of\s+10 recovery codes left/).waitFor();
  await account.getByText("On · authenticator app").waitFor();
  await shot(account, "factor-on");
  await axe(account, `${tag}-factor-on`);
  checks.push(
    `${tag}: an authenticator app set up on Account by keyboard, a wrong code refused, ten recovery codes shown once`,
  );

  // 2. Signing in: the code page, a wrong code, the right code.
  await account.getByRole("button", { name: "Sign out", exact: true }).click();
  await account.getByRole("heading", { level: 1, name: "Sign in" }).waitFor();
  await context.close();
  const second = await passwordStep(c, mei.username);
  await second.page.getByRole("heading", { level: 1, name: "Enter your code" }).waitFor();
  await shot(second.page, "code-page");
  await axe(second.page, `${tag}-code-page`);
  await second.page.getByLabel("Code", { exact: true }).fill("000000");
  await second.page.getByRole("button", { name: "Sign in" }).click();
  await second.page.getByText("That code is not right, or was already used").waitFor();
  await shot(second.page, "code-wrong");
  await axe(second.page, `${tag}-code-wrong`);
  await second.page.getByLabel("Code", { exact: true }).fill(totp(secret, 1));
  await second.page.getByRole("button", { name: "Sign in" }).click();
  await second.page.waitForURL(`${uiUrl}/settings/account`);
  await second.page.getByText("On · authenticator app").waitFor();
  await second.context.close();
  checks.push(`${tag}: the password leads to the code page; a wrong code refused, the right one signs in`);

  // 3. A recovery code, once.
  const third = await passwordStep(c, mei.username);
  await third.page.getByRole("button", { name: "Use a recovery code instead" }).click();
  await third.page.getByRole("heading", { level: 1, name: "Use a recovery code" }).waitFor();
  await shot(third.page, "recovery-page");
  await axe(third.page, `${tag}-recovery-page`);
  await third.page.getByLabel("Recovery code").fill(codes[0]);
  await third.page.getByRole("button", { name: "Sign in" }).click();
  await third.page.waitForURL(`${uiUrl}/settings/account`);
  await third.page.getByText(/9 of\s+10 recovery codes left/).waitFor();
  await third.context.close();
  const fourth = await passwordStep(c, mei.username);
  await fourth.page.getByRole("button", { name: "Use a recovery code instead" }).click();
  await fourth.page.getByLabel("Recovery code").fill(codes[0]);
  await fourth.page.getByRole("button", { name: "Sign in" }).click();
  await fourth.page.getByText("That code is not right, or was already used").waitFor();
  await fourth.context.close();
  checks.push(`${tag}: a recovery code signs in once and is refused the second time`);

  // 4. The requirement, turned on by an administrator; a person without an app sets one up on the
  // sign-in page and meets the recovery codes before the session starts.
  await page.goto(`${uiUrl}/settings/sign-in/local`);
  await page.getByRole("heading", { level: 2, name: "Local accounts" }).waitFor();
  await page.getByRole("checkbox", { name: /Require a second factor with a password/ }).focus();
  await page.keyboard.press("Space");
  const ask = page.getByRole("alertdialog", { name: "Require a second factor?" });
  await shot(page, "require-confirmation");
  await axe(page, `${tag}-require-confirmation`);
  await ask.getByRole("button", { name: "Require it" }).click();
  await ask.waitFor({ state: "detached" });
  const noa = await personWithPassword(c, `noa.${tag}`, `Noa ${tag}`);
  const setup = await passwordStep(c, noa.username);
  await setup.page.getByRole("heading", { level: 1, name: "Set up a second factor" }).waitFor();
  await setup.page.getByRole("img", { name: "QR code for the authenticator app" }).waitFor();
  const noaSecret = await setup.page.locator("#key").innerText();
  await shot(setup.page, "setup-page");
  await axe(setup.page, `${tag}-setup-page`);
  await setup.page.getByLabel("Code from the app").fill("000000");
  await setup.page.getByRole("button", { name: "Confirm and continue" }).click();
  await setup.page.getByText("That code is not right, or was already used").waitFor();
  expect(
    (await setup.page.locator("#key").innerText()) === noaSecret,
    `${tag}: the key stays the same after a wrong code`,
  );
  await setup.page.getByLabel("Code from the app").fill(totp(noaSecret));
  await setup.page.getByRole("button", { name: "Confirm and continue" }).click();
  await setup.page.getByRole("heading", { level: 1, name: "Keep your recovery codes" }).waitFor();
  expect(
    (await setup.page.locator(".sign-in-codes span").count()) === 10,
    `${tag}: ten recovery codes on the sign-in page`,
  );
  await shot(setup.page, "setup-codes");
  await axe(setup.page, `${tag}-setup-codes`);
  await setup.page.getByRole("button", { name: "I have kept them; continue" }).click();
  await setup.page.waitForURL(`${uiUrl}/settings/account`);
  await setup.page.getByText(/10 of\s+10 recovery codes left/).waitFor();
  expect(
    !(await setup.page.getByRole("button", { name: "Remove…" }).count()),
    `${tag}: no Remove while the instance requires a second factor`,
  );
  await setup.context.close();
  checks.push(`${tag}: with the requirement on, a person set the app up on the sign-in page, then saw the codes`);

  // 5. An administrator removes Noa's second factor from her page.
  await page.goto(`${uiUrl}/settings/people/${noa.id}`);
  await page.getByRole("heading", { level: 2, name: `Noa ${tag}` }).waitFor();
  await page.getByText("Second factor: authenticator app").waitFor();
  await shot(page, "person-factor");
  await axe(page, `${tag}-person-factor`);
  await page.getByRole("button", { name: "Remove second factor…" }).click();
  const removal = page.getByRole("alertdialog", { name: /second factor\?/ });
  await removal.getByText(/set one up again at their next sign-in/).waitFor();
  await axe(page, `${tag}-remove-factor`);
  await removal.getByRole("button", { name: "Remove second factor" }).click();
  await removal.waitFor({ state: "detached" });
  expect(
    !(await page.getByText("Second factor: authenticator app").count()),
    `${tag}: the second factor row is gone after the removal`,
  );
  const again = await passwordStep(c, noa.username);
  await again.page.getByRole("heading", { level: 1, name: "Set up a second factor" }).waitFor();
  await again.context.close();
  const local = await api("/sign-in-providers/local");
  await api("/sign-in-providers/local", { expectedVersion: local.version, secondFactorRequired: false }, "PATCH");
  checks.push(`${tag}: an administrator removed the second factor; the next sign-in asks to set one up`);

  // 6. The sign-in pages in dark and at 390px, without horizontal page scroll.
  for (const [options, label] of [
    [{ colorScheme: "dark" }, "dark"],
    [{ viewport: { width: 390, height: 844 }, hasTouch: true }, "narrow"],
  ]) {
    const view = await passwordStep(c, mei.username, options);
    await view.page.getByRole("heading", { level: 1, name: "Enter your code" }).waitFor();
    await shot(view.page, `code-page-${label}`);
    if (label === "dark") await axe(view.page, `${tag}-code-page-dark`);
    else expect((await overflow(view.page)) <= 0, `${tag}: the code page scrolls sideways at 390px`);
    await view.context.close();
  }
  const phone = await c.browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true });
  const phoneAccount = await phone.newPage();
  phoneAccount.setDefaultTimeout(15000);
  await phoneAccount.goto(`${uiUrl}/settings/account`);
  await phoneAccount.getByRole("heading", { level: 2, name: "Authenticator app" }).waitFor();
  expect((await overflow(phoneAccount)) <= 0, `${tag}: Account's second factor scrolls sideways at 390px`);
  await shot(phoneAccount, "factor-narrow");
  await phone.close();
  checks.push(`${tag}: the code page in dark and at 390px; Account at 390px without horizontal page scroll`);
}

/** A Chromium virtual authenticator that holds discoverable credentials and verifies the user. */
async function virtualAuthenticator(context, page) {
  const cdp = await context.newCDPSession(page);
  await cdp.send("WebAuthn.enable");
  await cdp.send("WebAuthn.addVirtualAuthenticator", {
    options: {
      protocol: "ctap2",
      transport: "internal",
      hasResidentKey: true,
      hasUserVerification: true,
      isUserVerified: true,
      automaticPresenceSimulation: true,
    },
  });
  return cdp;
}

async function partC(c) {
  const { tag, uiUrl, api, page, shot, overflow } = c;
  const pia = await personWithPassword(c, `pia.${tag}`, `Pia ${tag}`);

  // 1. Add a passkey from Account: the engine's own page, the virtual authenticator, back to Account.
  const { context, page: account } = await passwordStep(c, pia.username);
  await account.waitForURL(`${uiUrl}/settings/account`);
  await virtualAuthenticator(context, account);
  await account.getByRole("heading", { level: 2, name: "Passkeys" }).waitFor();
  await shot(account, "passkeys-none");
  await axe(account, `${tag}-passkeys-none`);
  await account.getByRole("button", { name: /Add a passkey/ }).focus();
  await account.keyboard.press("Enter");
  await account.getByRole("heading", { level: 1, name: "Add a passkey" }).waitFor();
  expect(
    new URL(account.url()).origin === c.apiUrl,
    `${tag}: the passkey is made on the engine's own page (${account.url()})`,
  );
  await account.getByLabel("Name it").fill("Test laptop");
  await shot(account, "passkey-add-page");
  await axe(account, `${tag}-passkey-add-page`);
  await account.getByRole("button", { name: "Create passkey" }).click();
  await account.waitForURL(`${uiUrl}/settings/account`);
  await account.getByRole("list", { name: "Your passkeys" }).getByText("Test laptop").waitFor();
  await account.getByText(/not used yet/).waitFor();
  await shot(account, "passkeys-one");
  await axe(account, `${tag}-passkeys-one`);
  checks.push(`${tag}: a passkey added from Account on the engine's page and named`);

  // 2. Sign in with it alone: the button, no username.
  await account.getByRole("button", { name: "Sign out", exact: true }).click();
  await account.getByRole("heading", { level: 1, name: "Sign in" }).waitFor();
  await account.getByRole("button", { name: "Sign in with a passkey" }).waitFor();
  await shot(account, "sign-in-passkey");
  await axe(account, `${tag}-sign-in-passkey`);
  await account.getByRole("button", { name: "Sign in with a passkey" }).click();
  // Signing out returned to the front page, where the sign-in came back to.
  await account.waitForURL((url) => url.origin === uiUrl && url.pathname !== "/signed-in");
  await account.goto(`${uiUrl}/settings/account`);
  await account.getByText("Signed in with a passkey").waitFor();
  await account.getByText(/last used/).waitFor();
  await shot(account, "passkeys-used");
  checks.push(`${tag}: signed in with the passkey alone, no username typed; the passkey reads as used`);

  // 3. As the second step after a password.
  await account.getByRole("button", { name: "Sign out", exact: true }).click();
  await account.getByRole("heading", { level: 1, name: "Sign in" }).waitFor();
  await account.getByLabel("Username").fill(pia.username);
  await account.getByLabel("Password").fill(PASSPHRASE);
  await account.getByRole("button", { name: "Sign in", exact: true }).click();
  await account.getByRole("heading", { level: 1, name: "Confirm it is you" }).waitFor();
  expect(!(await account.getByLabel("Code", { exact: true }).count()), `${tag}: no code field without an app`);
  await shot(account, "second-step-passkey");
  await axe(account, `${tag}-second-step-passkey`);
  await account.getByRole("button", { name: "Use a passkey" }).click();
  await account.waitForURL((url) => url.origin === uiUrl && url.pathname !== "/signed-in");
  await account.goto(`${uiUrl}/settings/account`);
  await account.getByText("Signed in with your password").waitFor();
  checks.push(`${tag}: after the password, the passkey is the second step`);

  // 4. Rename on Account, then an administrator removes it from the person's page.
  await account.getByRole("button", { name: "Rename Test laptop" }).click();
  const rename = account.getByRole("dialog", { name: "Rename Test laptop" });
  await rename.getByLabel("Name").fill("Work laptop");
  await rename.getByRole("button", { name: "Save" }).click();
  await account.getByRole("list", { name: "Your passkeys" }).getByText("Work laptop").waitFor();
  await context.close();
  await page.goto(`${uiUrl}/settings/people/${pia.id}`);
  await page.getByRole("heading", { level: 2, name: `Pia ${tag}` }).waitFor();
  await page.getByText("Passkey: Work laptop").waitFor();
  await shot(page, "person-passkey");
  await axe(page, `${tag}-person-passkey`);
  await page.getByRole("button", { name: "Remove the passkey Work laptop" }).click();
  const gone = page.getByRole("alertdialog", { name: /passkey Work laptop\?/ });
  await axe(page, `${tag}-remove-passkey`);
  await gone.getByRole("button", { name: "Remove passkey" }).click();
  await gone.waitFor({ state: "detached" });
  await page.getByText("Passkey: Work laptop").waitFor({ state: "detached" });
  expect((await api(`/users/${pia.id}`)).passkeys === 0, `${tag}: the person holds no passkey`);
  checks.push(`${tag}: renamed on Account; an administrator removed it from the person's page`);

  // 5. The sign-in page with a passkey offered, in dark and at 390px, without horizontal scroll.
  const other = await personWithPassword(c, `ola.${tag}`, `Ola ${tag}`);
  const holder = await passwordStep(c, other.username);
  await holder.page.waitForURL(`${uiUrl}/settings/account`);
  await virtualAuthenticator(holder.context, holder.page);
  await holder.page.getByRole("button", { name: /Add a passkey/ }).click();
  await holder.page.getByRole("button", { name: "Create passkey" }).click();
  await holder.page.waitForURL(`${uiUrl}/settings/account`);
  await holder.context.close();
  for (const [options, label] of [
    [{ colorScheme: "dark" }, "dark"],
    [{ viewport: { width: 390, height: 844 }, hasTouch: true }, "narrow"],
  ]) {
    const outside = await c.signedOutContext({ viewport: { width: 1440, height: 900 }, ...options });
    const view = await outside.newPage();
    view.setDefaultTimeout(15000);
    await view.goto(`${uiUrl}/settings/account`);
    await view.getByRole("button", { name: "Sign in with a passkey" }).waitFor();
    await shot(view, `sign-in-passkey-${label}`);
    if (label === "dark") await axe(view, `${tag}-sign-in-passkey-dark`);
    else expect((await overflow(view)) <= 0, `${tag}: the sign-in page scrolls sideways at 390px`);
    await outside.close();
  }
  checks.push(`${tag}: the sign-in page's passkey button in dark and at 390px without horizontal page scroll`);
}

const SECTIONS = { a: partA, b: partB, c: partC };

async function walk(configuration) {
  const provider = await startProvider();
  const harness = await bootHarness({
    host: "localhost",
    transformModel: configuration.product
      ? (model) => {
          model.product.name = configuration.product;
        }
      : undefined,
  });
  try {
    const { uiUrl, apiUrl, api, output, browser, signedOutContext, harnessIdentity } = harness;
    const tag = configuration.name;
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    page.setDefaultTimeout(15000);
    page.on("pageerror", (error) => failures.push(`${tag}: ${error.message}`));
    await api("/sign-in-providers", {
      key: "harness-id",
      name: "Harness ID",
      issuer: provider.issuer,
      clientId: "engine",
      clientSecret: provider.secret,
      groupsClaim: "groups",
      enabled: true,
    });
    const c = {
      tag,
      uiUrl,
      apiUrl,
      api,
      browser,
      page,
      provider,
      signedOutContext,
      harnessIdentity,
      overflow: (target) => target.evaluate(() => document.documentElement.scrollWidth - window.innerWidth),
      shot: (target, name) => target.screenshot({ path: resolve(output, `${tag}-${name}.png`), fullPage: true }),
    };
    for (const part of parts) await SECTIONS[part](c);
    await context.close();
    const report = { browser: browser.version(), model: tag, parts, checks, failures, passed: !failures.length };
    await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
    console.log(`I4 browser evidence (${tag}): ${output}`);
  } finally {
    harness.cleanup();
    provider.child.kill();
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
  console.error("I4 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
}
