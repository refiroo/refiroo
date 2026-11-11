// 0.12 I6 browser evidence: a forgotten password on the application's sign-in screen, against a real
// backend and a harness SMTP server, on two models, at 1440px and 390px. Mail is not set up: the screen
// offers no reset. Mail set up: "Forgotten your password?" leads to the ask page; asking for a person
// and for a name nobody has shows the same words; one message arrives, to the person only, holding a
// link to the application's reset page; the page names the person, refuses a short password with the
// engine's words, sets a good one, and the person signs in with it; the used link says it no longer
// works and offers a new one. Axe on each page; screenshots; no horizontal scroll at 390px.
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { SHAPED_MODELS, bootShaped } from "./helpers/shaped-models.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { startSmtp } from "./helpers/smtp-server.mjs";

const OLD = "an old harness passphrase 1";
const NEW = "a brand new harness passphrase 2";
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

/** A message's text with its quoted-printable encoding undone, as a mail program shows it. */
function decoded(message) {
  return message.replace(/=\r\n/g, "").replace(/=([0-9A-F]{2})/g, (_, hex) => String.fromCharCode(parseInt(hex, 16)));
}

async function received(smtp, count) {
  for (let waited = 0; waited < 20000 && smtp.messages.length < count; waited += 250) {
    await new Promise((done) => setTimeout(done, 250));
  }
  return smtp.messages.length >= count;
}

async function walk(configuration) {
  let smtp;
  let harness;
  try {
    smtp = await startSmtp();
    harness = await bootShaped(configuration);
    const { apiUrl, uiUrl, api, output, browser, signedOutContext } = harness;
    const tag = configuration.name;
    const email = `ada-${tag}@example.org`;
    const overflow = (page) => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    const shot = (page, name) => page.screenshot({ path: resolve(output, `${tag}-${name}.png`), fullPage: true });

    // A person with a password and an address, set the way an administrator's link sets it.
    const made = await api("/users", { name: `Ada ${tag}`, email });
    const first = await api(`/users/${made.id}/password-reset`, {});
    expect(
      first.url.startsWith(`${uiUrl}/reset-password?token=`),
      `${tag}: an administrator's link opens the application: ${first.url}`,
    );
    const token = new URL(first.url).searchParams.get("token");
    const set = await fetch(`${apiUrl}/oauth/password`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ token, password: OLD, repeat: OLD }),
    });
    expect(set.ok, `${tag}: the first password was set`);

    const context = await signedOutContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    page.setDefaultTimeout(15000);
    page.on("pageerror", (error) => failures.push(`${tag}: ${error.message}`));
    const signInHeading = () => page.getByRole("heading", { level: 1, name: "Sign in" }).waitFor();

    // 1. Mail not set up: no link to reset, and the ask page says so.
    await page.goto(uiUrl);
    await signInHeading();
    expect(
      (await page.getByRole("link", { name: "Forgotten your password?" }).count()) === 0,
      `${tag}: no reset link without mail`,
    );
    await page.goto(`${uiUrl}/reset-password`);
    await page.getByText(/cannot be asked for by e-mail here/).waitFor();
    expect((await page.getByRole("button", { name: "Mail me a link" }).count()) === 0, `${tag}: no form without mail`);
    checks.push(`${tag}: without mail set up the screen offers no reset`);

    // 2. Mail set up: the link leads to the ask page.
    await api(
      "/mail-settings",
      { host: "127.0.0.1", port: smtp.port, security: "none", fromAddress: "refiroo@example.org" },
      "PUT",
    );
    await page.goto(uiUrl);
    await signInHeading();
    await shot(page, "sign-in-with-reset");
    await page.getByRole("link", { name: "Forgotten your password?" }).click();
    await page.getByRole("heading", { level: 1, name: "Forgotten your password?" }).waitFor();
    await page.getByLabel("E-mail address").waitFor();
    await shot(page, "ask");
    await axe(page, `${tag}-ask`);

    // 3. The same words for a person and for a name nobody has.
    async function ask(name) {
      await page.goto(`${uiUrl}/reset-password`);
      await page.getByLabel("E-mail address").fill(name);
      await page.getByRole("button", { name: "Mail me a link" }).click();
      return page.getByText(/If there is an account/).innerText();
    }
    const ghost = await ask("nobody-at-all");
    const known = await ask(email);
    expect(ghost === known, `${tag}: the same words whoever is named: "${ghost}" / "${known}"`);
    await shot(page, "asked");
    await axe(page, `${tag}-asked`);
    expect(await received(smtp, 1), `${tag}: the message reached the server`);
    await smtp.quiet();
    expect(smtp.messages.length === 1, `${tag}: only the person was written to (${smtp.messages.length})`);
    const mail = decoded(smtp.messages[0] ?? "");
    expect(mail.includes(`To: ${email}`), `${tag}: addressed to the person`);
    const link = mail.match(/https?:\/\/\S+reset-password\?token=\S+/)?.[0] ?? "";
    expect(link.startsWith(`${uiUrl}/reset-password?token=`), `${tag}: the mail links to the application: ${link}`);
    checks.push(
      `${tag}: the ask said the same for a person and a stranger; one message, to the person, with the application's link`,
    );

    // 4. The link: who it is for, the engine's refusal, then the new password.
    await page.goto(link);
    await page.getByRole("heading", { level: 1, name: "Choose a new password" }).waitFor();
    await page.getByText(email, { exact: true }).waitFor();
    await shot(page, "choose");
    await axe(page, `${tag}-choose`);
    await page.getByLabel("New password").fill("short");
    await page.getByLabel("Type it again").fill("short");
    await page.getByRole("button", { name: "Set password" }).click();
    await page
      .getByRole("alert")
      .filter({ hasText: /at least \d+ characters/ })
      .waitFor();
    await page.getByLabel("New password").fill(NEW);
    await page.getByLabel("Type it again").fill(NEW);
    await page.getByRole("button", { name: "Set password" }).click();
    await page.getByText(/Your password is set/).waitFor();
    await shot(page, "done");
    await axe(page, `${tag}-done`);
    checks.push(`${tag}: a short password was refused in the engine's words; a good one was set`);

    // 5. Sign in with it; the old one no longer works.
    await page.getByRole("link", { name: "Sign in" }).click();
    await signInHeading();
    await page.getByLabel("E-mail address").fill(email);
    await page.getByLabel("Password").fill(OLD);
    await page.getByRole("button", { name: "Sign in" }).click();
    await page.getByRole("alert").filter({ hasText: "The e-mail address or password is not right" }).waitFor();
    await page.getByLabel("Password").fill(NEW);
    await page.getByRole("button", { name: "Sign in" }).click();
    await page.locator(".account-button").waitFor();
    await page.waitForURL((url) => !url.pathname.includes("reset-password") && url.origin === uiUrl);
    expect(
      !(await page.getByRole("heading", { level: 1, name: "Sign in" }).isVisible()),
      `${tag}: signed in with the new password`,
    );
    checks.push(`${tag}: signed in with the new password; the old one was refused`);

    // 6. The used link is gone.
    await page.goto(link);
    await page.getByRole("heading", { level: 1, name: "This link no longer works" }).waitFor();
    await page.getByRole("link", { name: "Ask for a new link" }).waitFor();
    await shot(page, "gone");
    await axe(page, `${tag}-gone`);
    checks.push(`${tag}: the used link says it no longer works and offers a new one`);

    // 7. 390px.
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`${uiUrl}/reset-password`);
    await page.getByLabel("E-mail address").waitFor();
    await shot(page, "ask-390");
    expect((await overflow(page)) <= 0, `${tag}: no horizontal scroll at 390px`);
    checks.push(`${tag}: the ask page at 390px`);

    await context.close();
    const report = { browser: browser.version(), model: tag, checks, failures, passed: !failures.length };
    await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
    console.log(`I6 browser evidence (${tag}): ${output}`);
  } finally {
    harness?.cleanup();
    smtp?.stop();
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
  console.error("I6 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
}
